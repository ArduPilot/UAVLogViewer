"""
Chat Orchestrator - Central coordinator for the request-execution-response loop.

This module implements the core orchestration logic for processing user messages
through an LLM with tool calling capabilities, managing conversation state,
and coordinating with telemetry analysis tools.
"""

import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any, List, Union
from uuid import UUID, uuid4
from dataclasses import dataclass, asdict

from services.prompt_templates import _get_usage_instructions
from db import SQLiteManager, DuckDBManager
from services.llm_client import LLMClient, LLMServiceError
from services.flight_context import extract_flight_metrics, has_sufficient_flight_data
from services.types import ToolCall, ToolResult
from schemas import ChatRequest, ChatResponse, FlightMetrics

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Ensure this logger accepts INFO level


@dataclass
class ConversationContext:
    """Context for the current conversation turn."""

    session_id: UUID
    conversation_id: UUID
    user_message: str
    session_data: Dict[str, Any]
    flight_metrics: Optional[FlightMetrics]
    has_flight_data: bool
    conversation_history: List[Dict[str, Any]]
    is_first_turn: bool


class ChatOrchestrator:
    """
    Central coordinator for the chat request-execution-response loop.

    This class orchestrates the flow from user message to final response,
    handling tool calls, conversation state, and response synthesis.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        tool_registry: Optional[
            Any
        ] = None,  # Will be properly typed when ToolRegistry is implemented
    ):
        """
        Initialize the chat orchestrator.

        Args:
            llm_client: LLM client for generating responses
            tool_registry: Registry of available analysis tools that contains database managers
        """
        self.llm_client = llm_client
        self.tool_registry = tool_registry

        # Configuration for guardrails
        self.max_tool_calls_per_turn = 3
        self.max_total_rows_per_turn = 10000
        self.max_conversation_history = 10
        self.max_tool_calling_iterations = 5  # Prevent infinite tool calling loops

    @property
    def sqlite_manager(self) -> SQLiteManager:
        """Access SQLite manager through tool registry or fallback."""
        if self.tool_registry:
            return self.tool_registry.sqlite_manager
        else:
            # Fallback for backward compatibility during transition
            from db import get_sqlite_manager

            return get_sqlite_manager()

    @property
    def duckdb_manager(self) -> DuckDBManager:
        """Access DuckDB manager through tool registry or fallback."""
        if self.tool_registry:
            return self.tool_registry.duckdb_manager
        else:
            # Fallback for backward compatibility during transition
            from db import get_duckdb_manager

            return get_duckdb_manager()

    async def process_message(self, request: ChatRequest) -> ChatResponse:
        """
        Process a user message through the complete request-execution-response loop.

        Args:
            request: The chat request from the user

        Returns:
            ChatResponse: The complete response with metadata

        Raises:
            HTTPException: For various error conditions
        """

        logger.info(f"Processing message: {request}")

        try:
            # Step 1: Validate session and build context
            context = await self._build_conversation_context(request)

            # Step 2: Persist user message
            await self._store_user_message(context)

            # Step 3: Generate LLM response (with potential tool calls)
            response_data = await self._generate_llm_response(context)

            # Step 4: Persist assistant response
            await self._store_assistant_response(context, response_data)

            # Step 5: Build final response
            return self._build_chat_response(context, response_data)

        except Exception as e:
            logger.error(f"Error in chat orchestrator: {e}", exc_info=True)
            # Try to store error message if we have valid context
            try:
                if "context" in locals():
                    await self._store_error_response(context, str(e))
            except:
                pass  # Don't let error handling fail the response
            raise

    async def _build_conversation_context(
        self, request: ChatRequest
    ) -> ConversationContext:
        """Build conversation context from the request."""

        # Validate session exists and is ready
        session = await self.sqlite_manager.get_session(request.session_id)
        if not session:
            from fastapi import HTTPException, status

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
            )

        if session["status"] != "completed":
            from fastapi import HTTPException, status

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Session not ready for chat. Status: {session['status']}",
            )

        # Determine conversation ID
        conversation_id = request.conversation_id or uuid4()

        # Validate message
        user_message = request.message.strip()
        if not user_message:
            from fastapi import HTTPException, status

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message cannot be empty",
            )

        # Extract flight metrics
        flight_metrics = extract_flight_metrics(session)
        has_flight_data = has_sufficient_flight_data(session)

        # Get conversation history
        conversation_history = await self.sqlite_manager.get_conversation(
            conversation_id, limit=self.max_conversation_history
        )

        # Check if first turn
        prev_resp_id = await self.sqlite_manager.get_last_assistant_response_id(
            conversation_id
        )
        is_first_turn = prev_resp_id is None

        return ConversationContext(
            session_id=request.session_id,
            conversation_id=conversation_id,
            user_message=user_message,
            session_data=session,
            flight_metrics=flight_metrics,
            has_flight_data=has_flight_data,
            conversation_history=conversation_history,
            is_first_turn=is_first_turn,
        )

    async def _store_user_message(self, context: ConversationContext) -> None:
        """Store the user message in conversation history."""
        await self.sqlite_manager.store_conversation(
            conversation_id=context.conversation_id,
            session_id=context.session_id,
            message_type="user",
            message=context.user_message,
            metadata=None,
        )

    async def _generate_llm_response(
        self, context: ConversationContext
    ) -> Dict[str, Any]:
        """
        Generate LLM response, potentially with tool calls.

        This implements the complete tool calling orchestration loop.
        """

        try:
            # If tool registry is available, use tool calling
            if self.tool_registry:
                return await self._generate_tool_aware_response(context)
            else:
                # Fall back to basic response for backward compatibility
                return await self._generate_basic_llm_response(context)

        except LLMServiceError as e:
            logger.error(f"LLM service error: {e}")
            return self._create_fallback_response(context, f"LLM service error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in LLM generation: {e}")
            return self._create_fallback_response(context, f"Unexpected error: {e}")

    async def _generate_tool_aware_response(
        self, context: ConversationContext
    ) -> Dict[str, Any]:
        """
        Generate LLM response with tool calling support.

        This implements the complete tool execution loop:
        1. Send initial request with available tools
        2. If LLM responds with tool calls, execute them
        3. Feed results back to LLM for final response
        4. Return final response with metadata
        """
        from services.tool_registry import create_tool_registry
        import json

        logger.info(
            f"Generating tool-aware response for user message: {context.user_message}"
        )

        tool_calls_made = []
        total_tools_executed = 0

        try:
            # Initialize tool registry for this session
            if (
                not hasattr(self.tool_registry, "session_id")
                or self.tool_registry.session_id != context.session_id
            ):
                # Create fresh tool registry for this session
                tool_registry = await create_tool_registry(
                    session_id=context.session_id,
                    sqlite_manager=self.sqlite_manager,
                    duckdb_manager=self.duckdb_manager,
                )
            else:
                tool_registry = self.tool_registry
                # Reset turn stats for new conversation turn
                tool_registry.reset_turn_stats()

            # Get available tools
            available_tools = tool_registry.get_tool_schemas()

            # Build system instructions with tools and flight context
            tools_description = self._build_tools_description(available_tools)
            system_instructions = self._build_system_message(context, tools_description)
            usage_instructions = _get_usage_instructions()

            # Determine conversation strategy based on turn
            tool_choice_strategy = "auto"
            # Heuristic to force tool use for data-related questions
            query_keywords = [
                "what",
                "show",
                "list",
                "get",
                "query",
                "find",
                "calculate",
                "how many",
                "when did",
            ]
            if any(
                keyword in context.user_message.lower() for keyword in query_keywords
            ):
                tool_choice_strategy = "required"
                logger.info("Forcing tool use due to query keywords.")

            if context.is_first_turn:
                # First turn: Use instructions with flight context
                input_content = f"User: {context.user_message}"
                llm_kwargs = {
                    "instructions": system_instructions,
                    "tools": available_tools,
                    "tool_choice": tool_choice_strategy,
                    "model": "gpt-4o-mini",
                    "max_tokens": 1000,
                    "temperature": 0.1,
                }
            else:
                # Subsequent turns: Use conversation chaining for continuity
                prev_resp_id = await self.sqlite_manager.get_last_assistant_response_id(
                    context.conversation_id
                )
                input_content = context.user_message
                llm_kwargs = {
                    "previous_response_id": prev_resp_id,
                    "tools": available_tools,
                    "tool_choice": tool_choice_strategy,
                    "model": "gpt-4o-mini",
                    "max_tokens": 1000,
                    "temperature": 0.1,
                    "instructions": usage_instructions,
                }

            # Main tool calling loop
            iteration = 0
            llm_response = None

            while iteration < self.max_tool_calling_iterations:
                iteration += 1
                logger.debug(f"Tool calling iteration {iteration}")

                # Call LLM with tools
                llm_response = await self.llm_client.complete(
                    prompt=input_content, **llm_kwargs
                )

                # Check if LLM wants to call tools
                if not llm_response.tool_calls:
                    # No tool calls - we have our final response
                    break

                # Execute tool calls
                tool_results = []
                for tool_call_data in llm_response.tool_calls:
                    if total_tools_executed >= self.max_tool_calls_per_turn:
                        logger.warning(
                            f"Maximum tool calls ({self.max_tool_calls_per_turn}) exceeded"
                        )
                        break

                    try:
                        # Parse tool call
                        function_name = tool_call_data["function"]["name"]
                        function_args = json.loads(
                            tool_call_data["function"]["arguments"]
                        )
                        call_id = tool_call_data.get("call_id", tool_call_data["id"])

                        # Print the tool call request
                        logger.info(f"Tool call request: {tool_call_data}")

                        # Create ToolCall object
                        tool_call = ToolCall(
                            tool_name=function_name,
                            parameters=function_args,
                            call_id=call_id,
                        )

                        # Execute tool
                        logger.info(f"Executing tool: {function_name}")
                        result = await tool_registry.execute_tool(tool_call)
                        tool_results.append(result)
                        total_tools_executed += 1

                        # Track for metadata
                        tool_calls_made.append(
                            {
                                "tool_name": function_name,
                                "parameters": function_args,
                                "success": result.success,
                                "execution_time": result.execution_time,
                            }
                        )

                    except Exception as e:
                        logger.error(f"Error executing tool {function_name}: {e}")
                        # Create error result
                        error_result = ToolResult(
                            tool_name=function_name,
                            call_id=call_id,
                            success=False,
                            data=None,
                            metadata={"error_type": type(e).__name__},
                            execution_time=0.0,
                            error_message=str(e),
                        )
                        tool_results.append(error_result)

                # Build input array for Responses API with both function_call and function_call_output
                # This follows the OpenAI documentation pattern exactly
                input_list = []

                # Print the tool results
                logger.info(f"Tool results: {tool_results}")

                # For Responses API: Send ONLY the function_call_output items
                # The API already has the function_call context from the previous response
                for result in tool_results:
                    try:
                        serialized_output = json.dumps(result.data)
                    except TypeError:
                        serialized_output = json.dumps(str(result.data))

                    input_list.append(
                        {
                            "type": "function_call_output",
                            "call_id": result.call_id,
                            "output": (
                                serialized_output
                                if result.success
                                else result.error_message or "error"
                            ),
                        }
                    )

                llm_kwargs = {
                    "previous_response_id": llm_response.metadata["response_id"],
                    "messages": input_list,  # LLM client expects messages parameter
                    "model": "gpt-4o-mini",
                    "max_tokens": 1000,
                    "temperature": 0.1,
                }

                # For subsequent iterations, don't pass input_content
                input_content = ""

            # Check if we hit the iteration limit
            hit_iteration_limit = iteration >= self.max_tool_calling_iterations

            # If we hit iteration limit and LLM hasn't provided a final response,
            # make one final call to get a proper conclusion
            if hit_iteration_limit and llm_response and llm_response.tool_calls:
                logger.warning(
                    f"Hit max tool calling iterations ({self.max_tool_calling_iterations}), requesting final response"
                )

                # Make final call without tools to force a conclusion
                final_input = f"Based on the analysis above, please provide a comprehensive final answer to the user's original question: '{context.user_message}'"

                final_kwargs = {
                    "model": "gpt-4o-mini",
                    "max_tokens": 1000,
                    "temperature": 0.1,
                }

                if llm_response.metadata and llm_response.metadata.get("response_id"):
                    final_kwargs["previous_response_id"] = llm_response.metadata[
                        "response_id"
                    ]

                final_response = await self.llm_client.complete(
                    prompt=final_input, **final_kwargs
                )

                # Use the final response
                llm_response = final_response

            # Get execution stats
            execution_stats = tool_registry.get_execution_stats()

            # Build final response data
            return {
                "content": llm_response.content,
                "response_id": (
                    llm_response.metadata.get("response_id")
                    if llm_response.metadata
                    else None
                ),
                "metadata": {
                    "model": llm_response.model,
                    "usage": llm_response.usage,
                    "llm_metadata": llm_response.metadata,
                    "has_flight_data": context.has_flight_data,
                    "is_first_turn": context.is_first_turn,
                    "tool_calls": tool_calls_made,
                    "execution_stats": execution_stats,
                    "tool_calling_iterations": iteration,
                    "hit_iteration_limit": hit_iteration_limit,
                    "orchestrator_version": "2.1.0",  # Updated version
                },
            }

        except Exception as e:
            logger.error(f"Error in tool-aware response generation: {e}")
            # Fall back to basic response
            return await self._generate_basic_llm_response(context)

    def _build_tools_description(self, available_tools: list) -> str:
        """Build description of available tools for system prompt."""
        if not available_tools:
            return "No analysis tools are currently available."

        tools_desc = "Available analysis tools:\n"
        for tool in available_tools:
            tools_desc += f"- {tool['name']}: {tool['description']}\n"
        return tools_desc

    def _build_system_message(
        self, context: ConversationContext, tools_description: str
    ) -> str:
        """Build system message for tool-aware conversation."""

        system_message_parts = []

        system_message_parts.append(
            # "You are a highly capable UAV flight data analyst. "
            # "Your primary function is to use the provided tools to answer user questions about the flight session. "
            # "Do not answer from your own knowledge. Use the tools to find the data."
            # "If you need more information, ask the user to provide it."
            # "If you don't have the information, say so."
            # "Be creative and use the tools you have to answer the user's question."
            """
                **UAV Flight-Data Assistant - System Instructions**

                You are an expert UAV log analyst.
                You are given a specific flight log and you are asked to answer questions about it, and about it only.
                All answers must be grounded in the session's telemetry stored in the database.  
                Follow this 3-step workflow:

                ──────────────────────────────────  
                1  Retrieve the flight summary  
                ──────────────────────────────────  
                • Call `get_flight_summary()` **first**.  
                It returns per-flight metadata and aggregate metrics:

                ```
                max_altitude_m , max_speed_ms , error_count , warning_count , …
                ```

                Use these numbers for high-level statements and to decide which detailed queries are worth running.

                ──────────────────────────────────  
                2  Discover which detailed data exist  
                ──────────────────────────────────  
                • Fast check: `check_data_availability(message_type="system_status")` etc.  
                Returns `{available: true/false, rows: N}`.  
                • Full overview: call without parameters - you'll get row counts for *all* tables.  
                • To see exact column names:  
                `list_table_columns(message_type="sensor_telemetry")`

                Table guide (use the value in `message_type`):

                | Table name       | Main columns & meaning                                             |
                |------------------|--------------------------------------------------------------------|
                | gps_telemetry    | lat, lon, alt, velocities, fix_type, satellites                    |
                | attitude_telemetry | roll, pitch, yaw angles and angular rates                        |
                | sensor_telemetry | xacc, yacc, zacc (m/s²) + gyro & mag axes                          |
                | system_status    | battery_voltage/current/temp, radio RSSI/noise, mode, armed flag   |
                | flight_events    | event_type, event_description, severity (error ≤ 3, warning = 4)   |

                **Never assume** a column exists; use `list_table_columns` if unsure.

                ──────────────────────────────────  
                3  Query the data you need  
                ──────────────────────────────────  
                Use `query_telemetry`:

                ```
                query_telemetry(
                    message_type = "<table_from_above>",
                    columns      = ["col1","col2",…],   # list_table_columns shows valid names
                    limit        = 200,                 # start small
                    start_time   = <ms UTC>,            # optional
                    end_time     = <ms UTC>             # optional
                )
                ```

                For error events:

                ```json
                {"name":"query_telemetry",
                "arguments":{
                "message_type":"flight_events",
                "columns":["time_boot_ms","event_type","event_description","severity"],
                "limit":500
                }}
                ```

                Always check availability first.  
                If the table or column is missing, explain that to the user.

                ──────────────────────────────────  
                Tool catalogue  
                ──────────────────────────────────  
                • **get_flight_summary** () → per-flight metrics & message counts  
                • **check_data_availability** (message_type?) → true/false + row count  
                • **list_table_columns** (message_type) → array of column names  
                • **query_telemetry** (message_type, columns, …) → rows of raw data  
                    (Use the table guide above.)  
                • **search_ardu_doc** (query, k=3) → semantic search in ArduPilot documentation  
                    (Coverage limited to log messages, vibration analysis, troubleshooting guides)

                If you need to know whether a particular field exists or how many rows there are, you *must* call one of the discovery tools before querying.  

                Only after you have gathered the necessary data should you craft your final answer.  
                If data are genuinely missing after the above steps, say so explicitly; otherwise provide the requested analysis with numeric values and sources.
            """
        )

        # Add flight data context if available
        if context.has_flight_data:
            system_message_parts.append(
                "\n--- Flight Context ---\n"
                "A flight log has been uploaded and processed. "
                "Use the provided tools to analyze it. The user is asking questions about this specific flight."
            )

            # Add high-level summary to give the model context
            if context.flight_metrics:
                from services.prompt_templates import (
                    _format_flight_metrics_for_developer_message,
                )

                summary = _format_flight_metrics_for_developer_message(
                    context.flight_metrics
                )
                system_message_parts.append(f"\n--- Flight Summary ---\n{summary}")
                system_message_parts.append(
                    "\nThe summary above is for high-level context ONLY. For specific values or details, you MUST use a tool to query the underlying data."
                )

        else:
            system_message_parts.append(
                "No flight log is currently loaded. Please inform the user."
            )

        # Add tools description
        system_message_parts.append(
            f"""
{tools_description}

GUIDELINES:
- Use tools to gather specific data for your analysis
- For log message meanings or troubleshooting guidance, use **search_ardu_doc** to search the embedded ArduPilot documentation
- If documentation search doesn't find relevant information, you can fall back to **fetch_url_content** for broader ArduPilot documentation
- Multiple tool calls are allowed for comprehensive analysis
- Always verify data availability before making claims
- If you can't find specific data, explain what's missing
- Remember the flight summary information provided above

Answer the user's question thoroughly using the available tools."""
        )

        return "\n".join(system_message_parts)

    async def _generate_basic_llm_response(
        self, context: ConversationContext
    ) -> Dict[str, Any]:
        """Generate basic LLM response (existing functionality)."""

        logger.info("Using BASIC LLM response (no tool registry available)")

        # Import here to avoid circular dependencies
        from services.prompt_templates import (
            validate_prompt_inputs,
            _get_flight_aware_instructions,
            _get_no_session_instructions,
            _format_flight_metrics_for_developer_message,
        )

        # Validate inputs
        is_valid, validation_error = validate_prompt_inputs(
            context.user_message, context.flight_metrics
        )
        if not is_valid:
            from fastapi import HTTPException, status

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid input: {validation_error}",
            )

        # Prepare LLM request
        llm_kwargs = {}

        if context.is_first_turn:
            # First turn: Use instructions + developer message with flight context
            if context.has_flight_data:
                instructions = _get_flight_aware_instructions()
                developer_message = _format_flight_metrics_for_developer_message(
                    context.flight_metrics
                )
                input_content = f"{developer_message}\n\nUser: {context.user_message}"
            else:
                instructions = _get_no_session_instructions()
                input_content = context.user_message

            llm_kwargs["instructions"] = instructions
            llm_response = await self.llm_client.complete(input_content, **llm_kwargs)
        else:
            # Subsequent turns: Use conversation chaining
            prev_resp_id = await self.sqlite_manager.get_last_assistant_response_id(
                context.conversation_id
            )
            llm_kwargs["previous_response_id"] = prev_resp_id
            llm_response = await self.llm_client.complete(
                context.user_message, **llm_kwargs
            )

        # Build response data
        return {
            "content": llm_response.content,
            "response_id": (
                llm_response.metadata.get("response_id")
                if llm_response.metadata
                else None
            ),
            "metadata": {
                "model": llm_response.model,
                "usage": llm_response.usage,
                "llm_metadata": llm_response.metadata,
                "has_flight_data": context.has_flight_data,
                "is_first_turn": context.is_first_turn,
                "tool_calls": [],  # No tool calls yet
                "orchestrator_version": "1.0.0",
            },
        }

    def _create_fallback_response(
        self, context: ConversationContext, error_message: str
    ) -> Dict[str, Any]:
        """Create a fallback response when LLM fails."""

        logger.error(f"Creating fallback response: {error_message}")

        message_count = context.session_data.get("message_count", 0)
        fallback_text = (
            f"I apologize, but I'm experiencing technical difficulties. "
            f"I can see your session has {message_count} messages parsed, "
            f"but I cannot process your question: '{context.user_message}' right now."
        )

        return {
            "content": fallback_text,
            "response_id": None,
            "metadata": {
                "error": error_message,
                "fallback": True,
                "has_flight_data": context.has_flight_data,
                "orchestrator_version": "1.0.0",
            },
        }

    async def _store_assistant_response(
        self, context: ConversationContext, response_data: Dict[str, Any]
    ) -> None:
        """Store the assistant response in conversation history."""

        await self.sqlite_manager.store_conversation(
            conversation_id=context.conversation_id,
            session_id=context.session_id,
            message_type="assistant",
            message=response_data["content"],
            metadata=response_data["metadata"],
            response_id=response_data.get("response_id"),
        )

    async def _store_error_response(
        self, context: ConversationContext, error_message: str
    ) -> None:
        """Store an error response when processing fails."""

        error_response = f"I apologize, but I encountered an error processing your request: {error_message}"

        await self.sqlite_manager.store_conversation(
            conversation_id=context.conversation_id,
            session_id=context.session_id,
            message_type="assistant",
            message=error_response,
            metadata={"error": True, "error_message": error_message},
        )

    def _build_chat_response(
        self, context: ConversationContext, response_data: Dict[str, Any]
    ) -> ChatResponse:
        """Build the final ChatResponse object."""

        return ChatResponse(
            response=response_data["content"],
            session_id=context.session_id,
            conversation_id=context.conversation_id,
            timestamp=datetime.utcnow(),
            metadata=response_data["metadata"],
        )


# Dependency injection function for FastAPI
def get_chat_orchestrator(
    sqlite_manager: SQLiteManager = None,  # Will be injected
    duckdb_manager: DuckDBManager = None,  # Will be injected
    llm_client: LLMClient = None,  # Will be injected
) -> ChatOrchestrator:
    """
    FastAPI dependency to create and return a ChatOrchestrator instance.

    This will be properly wired up in main.py with actual dependencies.
    """
    # This is a placeholder - actual implementation will use FastAPI Depends()
    # to inject the proper database managers and llm_client instances
    if sqlite_manager is None or duckdb_manager is None or llm_client is None:
        raise RuntimeError("ChatOrchestrator dependencies not properly configured")

    return ChatOrchestrator(
        sqlite_manager=sqlite_manager,
        duckdb_manager=duckdb_manager,
        llm_client=llm_client,
    )
