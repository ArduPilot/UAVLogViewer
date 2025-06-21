"""
Tool Registry - Dynamic Function Menu for LLM Tool Calling

This module implements the registry of available analysis tools that the LLM
can call to perform sophisticated flight data analysis. Tools are registered
dynamically based on available data and session capabilities.
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Type, Union
from uuid import UUID
from dataclasses import dataclass, asdict

from db import SQLiteManager, DuckDBManager
from services.types import ToolCall, ToolResult

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """
    Abstract base class for all analysis tools.

    All tools must implement the execute method and provide metadata
    about their capabilities and requirements.
    """

    def __init__(
        self,
        session_id: UUID,
        sqlite_manager: SQLiteManager,
        duckdb_manager: DuckDBManager,
    ):
        """
        Initialize the tool with database access.

        Args:
            session_id: The flight session this tool will analyze
            sqlite_manager: For session metadata and conversation state
            duckdb_manager: For telemetry data queries and analysis
        """
        self.session_id = session_id
        self.sqlite_manager = sqlite_manager
        self.duckdb_manager = duckdb_manager

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name for this tool."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this tool does."""
        pass

    @property
    @abstractmethod
    def parameters_schema(self) -> Dict[str, Any]:
        """JSON Schema for the tool's parameters (OpenAI function calling format)."""
        pass

    @abstractmethod
    async def execute(self, **parameters) -> ToolResult:
        """
        Execute the tool with the given parameters.

        Args:
            **parameters: Tool-specific parameters

        Returns:
            ToolResult: Structured result with data, metadata, and execution info
        """
        pass

    def get_openai_function_schema(self) -> Dict[str, Any]:
        """Get the OpenAI function calling schema for this tool (Responses API format)."""
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters_schema,
        }

    async def _safe_execute(
        self, call_id: Optional[str] = None, **parameters
    ) -> ToolResult:
        """
        Execute the tool safely with timing and error handling.

        Args:
            call_id: Optional call ID for tracking
            **parameters: Tool parameters

        Returns:
            ToolResult: Result with execution metadata
        """
        start_time = time.time()

        try:
            result = await self.execute(**parameters)
            execution_time = time.time() - start_time

            # Update result with execution metadata
            result.call_id = call_id
            result.execution_time = execution_time

            logger.info(
                f"Tool {self.name} executed successfully in {execution_time:.3f}s"
            )
            return result

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Tool {self.name} failed after {execution_time:.3f}s: {e}")

            return ToolResult(
                tool_name=self.name,
                call_id=call_id,
                success=False,
                data=None,
                metadata={"error_type": type(e).__name__},
                execution_time=execution_time,
                error_message=str(e),
            )


@dataclass
class ExecutionLimits:
    """Guardrails for tool execution."""

    max_tools_per_turn: int = 3
    max_total_rows: int = 10000
    max_execution_time_seconds: float = 30.0
    max_single_tool_rows: int = 5000


class ToolRegistry:
    """
    Registry of available analysis tools for a specific flight session.

    The registry builds a dynamic catalog of tools based on what data
    is available in the session, and provides safe execution with guardrails.
    """

    def __init__(
        self,
        session_id: UUID,
        sqlite_manager: SQLiteManager,
        duckdb_manager: DuckDBManager,
        limits: Optional[ExecutionLimits] = None,
    ):
        """
        Initialize the tool registry for a specific session.

        Args:
            session_id: Flight session to analyze
            sqlite_manager: Database manager for session metadata
            duckdb_manager: Database manager for telemetry data
            limits: Execution limits and guardrails
        """
        self.session_id = session_id
        self.sqlite_manager = sqlite_manager
        self.duckdb_manager = duckdb_manager
        self.limits = limits or ExecutionLimits()

        # Registry of available tools
        self._tools: Dict[str, BaseTool] = {}

        # Execution tracking for current turn
        self._current_turn_stats = {
            "tools_executed": 0,
            "total_rows_returned": 0,
            "total_execution_time": 0.0,
        }

    async def initialize(self) -> None:
        """
        Initialize the registry by discovering available tools.

        This builds the tool catalog dynamically based on what data
        is available for this session.
        """
        logger.info(f"Initializing tool registry for session {self.session_id}")

        # Get session information to determine available tools
        session_data = await self.sqlite_manager.get_session(self.session_id)
        if not session_data:
            raise ValueError(f"Session {self.session_id} not found")

        # Register core tools that are always available
        await self._register_core_tools()

        # Register data-specific tools based on available message types
        await self._register_data_specific_tools(session_data)

        logger.info(f"Tool registry initialized with {len(self._tools)} tools")

    async def _register_core_tools(self) -> None:
        """Register core tools that are always available."""
        from services.telemetry_tools import (
            FlightSummaryTool,
            SessionInfoTool,
            DataAvailabilityTool,
            TableInfoTool,
            DocumentationFetchTool,
        )

        # Doc semantic search tool
        from services.doc_tools import ArduDocSearchTool

        # Core tools that work with session metadata
        core_tools = [
            FlightSummaryTool(
                self.session_id, self.sqlite_manager, self.duckdb_manager
            ),
            SessionInfoTool(self.session_id, self.sqlite_manager, self.duckdb_manager),
            DataAvailabilityTool(
                self.session_id, self.sqlite_manager, self.duckdb_manager
            ),
            # New tool for column discovery
            TableInfoTool(self.session_id, self.sqlite_manager, self.duckdb_manager),
            DocumentationFetchTool(
                self.session_id, self.sqlite_manager, self.duckdb_manager
            ),
            # Semantic documentation search
            ArduDocSearchTool(
                self.session_id, self.sqlite_manager, self.duckdb_manager
            ),
        ]

        for tool in core_tools:
            self._tools[tool.name] = tool
            logger.debug(f"Registered core tool: {tool.name}")

    async def _register_data_specific_tools(self, session_data: Dict[str, Any]) -> None:
        """Register tools based on available data types."""
        from services.telemetry_tools import (
            TelemetryQueryTool,
            StatisticsTool,
            TableInfoTool,
            DocumentationFetchTool,
        )

        # Check what message types are available
        available_types = session_data.get("available_message_types", [])
        if isinstance(available_types, str):
            # Parse JSON string if needed
            import json

            try:
                available_types = json.loads(available_types)
            except:
                available_types = []

        if available_types:
            # Register telemetry analysis tools
            telemetry_tools = [
                TelemetryQueryTool(
                    self.session_id, self.sqlite_manager, self.duckdb_manager
                ),
                StatisticsTool(
                    self.session_id, self.sqlite_manager, self.duckdb_manager
                ),
                TableInfoTool(
                    self.session_id, self.sqlite_manager, self.duckdb_manager
                ),
                DocumentationFetchTool(
                    self.session_id, self.sqlite_manager, self.duckdb_manager
                ),
            ]

            for tool in telemetry_tools:
                self._tools[tool.name] = tool
                logger.debug(f"Registered telemetry tool: {tool.name}")

    def get_available_tools(self) -> List[str]:
        """Get list of available tool names."""
        return list(self._tools.keys())

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get OpenAI function calling schemas for all tools."""
        return [tool.get_openai_function_schema() for tool in self._tools.values()]

    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """Get a specific tool by name."""
        return self._tools.get(tool_name)

    async def execute_tool(self, tool_call: ToolCall) -> ToolResult:
        """
        Execute a tool call with safety checks and guardrails.

        Args:
            tool_call: The tool call request from the LLM

        Returns:
            ToolResult: Execution result with data and metadata
        """
        # Check execution limits
        if not self._check_execution_limits(tool_call):
            return ToolResult(
                tool_name=tool_call.tool_name,
                call_id=tool_call.call_id,
                success=False,
                data=None,
                metadata={"limit_exceeded": True},
                execution_time=0.0,
                error_message="Execution limits exceeded",
            )

        # Get the tool
        tool = self._tools.get(tool_call.tool_name)
        if not tool:
            return ToolResult(
                tool_name=tool_call.tool_name,
                call_id=tool_call.call_id,
                success=False,
                data=None,
                metadata={"tool_not_found": True},
                execution_time=0.0,
                error_message=f"Tool '{tool_call.tool_name}' not found",
            )

        # Execute the tool
        result = await tool._safe_execute(
            call_id=tool_call.call_id, **tool_call.parameters
        )

        # Update execution stats
        self._update_execution_stats(result)

        return result

    def _check_execution_limits(self, tool_call: ToolCall) -> bool:
        """Check if executing this tool would exceed limits."""
        stats = self._current_turn_stats

        # Check tool count limit
        if stats["tools_executed"] >= self.limits.max_tools_per_turn:
            logger.warning(
                f"Tool execution limit exceeded: {stats['tools_executed']}/{self.limits.max_tools_per_turn}"
            )
            return False

        # Check total execution time
        if stats["total_execution_time"] >= self.limits.max_execution_time_seconds:
            logger.warning(
                f"Execution time limit exceeded: {stats['total_execution_time']:.1f}s"
            )
            return False

        # Check row count limit
        if stats["total_rows_returned"] >= self.limits.max_total_rows:
            logger.warning(
                f"Row count limit exceeded: {stats['total_rows_returned']}/{self.limits.max_total_rows}"
            )
            return False

        return True

    def _update_execution_stats(self, result: ToolResult) -> None:
        """Update execution statistics after tool execution."""
        self._current_turn_stats["tools_executed"] += 1
        self._current_turn_stats["total_execution_time"] += result.execution_time

        # Count rows if data is a list
        if result.success and isinstance(result.data, list):
            self._current_turn_stats["total_rows_returned"] += len(result.data)
        elif result.success and result.metadata:
            # Check for row count in metadata
            row_count = result.metadata.get("row_count", 0)
            self._current_turn_stats["total_rows_returned"] += row_count

    def reset_turn_stats(self) -> None:
        """Reset execution statistics for a new turn."""
        self._current_turn_stats = {
            "tools_executed": 0,
            "total_rows_returned": 0,
            "total_execution_time": 0.0,
        }

    def get_execution_stats(self) -> Dict[str, Any]:
        """Get current execution statistics."""
        return self._current_turn_stats.copy()


# Factory function for creating tool registries
async def create_tool_registry(
    session_id: UUID,
    sqlite_manager: SQLiteManager,
    duckdb_manager: DuckDBManager,
    limits: Optional[ExecutionLimits] = None,
) -> ToolRegistry:
    """
    Create and initialize a tool registry for a session.

    Args:
        session_id: Flight session to analyze
        sqlite_manager: Database manager for session metadata
        duckdb_manager: Database manager for telemetry data
        limits: Optional execution limits

    Returns:
        ToolRegistry: Initialized registry ready for use
    """
    registry = ToolRegistry(session_id, sqlite_manager, duckdb_manager, limits)
    await registry.initialize()
    return registry
