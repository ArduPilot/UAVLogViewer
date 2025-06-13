"""
LLM Client for UAV Log Viewer chatbot.
Provides async wrapper around LLM providers (default: OpenAI).
"""

import asyncio
import logging
import os
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dataclasses import dataclass

try:
    import openai
    from openai import AsyncOpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Response from LLM completion."""

    content: str
    model: str
    usage: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    tool_calls: Optional[list] = None  # For function calling responses


class LLMClientError(Exception):
    """Base exception for LLM client errors."""

    pass


class LLMConfigurationError(LLMClientError):
    """Raised when LLM client is misconfigured."""

    pass


class LLMServiceError(LLMClientError):
    """Raised when LLM service is unavailable or returns an error."""

    pass


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    async def complete(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate completion for the given prompt."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the LLM service is available."""
        pass


class LegacyChatCompletionClient(LLMClient):
    """OpenAI Chat Completions client (legacy)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-3.5-turbo",
        max_tokens: int = 500,
        temperature: float = 0.7,
    ):
        """
        Initialize OpenAI client.

        Parameters
        ----------
        api_key : Optional[str]
            OpenAI API key. If None, will try to get from OPENAI_API_KEY env var.
        model : str
            OpenAI model to use (default: gpt-3.5-turbo)
        max_tokens : int
            Maximum tokens in response
        temperature : float
            Sampling temperature
        """
        if not OPENAI_AVAILABLE:
            raise LLMConfigurationError(
                "OpenAI package not available. Install with: pip install openai"
            )

        # Get API key from parameter or environment
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise LLMConfigurationError(
                "OpenAI API key not provided. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

        # Initialize async client
        self.client = AsyncOpenAI(api_key=self.api_key)

        logger.info(f"OpenAI Chat Completions client initialized with model: {model}")

    async def complete(self, prompt: str, **kwargs) -> LLMResponse:
        """
        Generate completion using OpenAI API.

        Parameters
        ----------
        prompt : str
            The prompt to send to the model
        **kwargs
            Additional parameters to override defaults

        Returns
        -------
        LLMResponse
            The completion response

        Raises
        ------
        LLMServiceError
            If the OpenAI API returns an error
        """
        try:
            # Prepare messages
            messages = kwargs.get("messages", [{"role": "user", "content": prompt}])

            # Prepare request parameters
            request_params = {
                "model": kwargs.get("model", self.model),
                "messages": messages,
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "temperature": kwargs.get("temperature", self.temperature),
            }

            # Add tool calling support
            tools = kwargs.get("tools")
            if tools:
                request_params["tools"] = tools
                request_params["tool_choice"] = kwargs.get("tool_choice", "auto")

            logger.debug(f"Sending OpenAI Chat request: {request_params['model']}")

            # Make API call
            response = await self.client.chat.completions.create(**request_params)

            message = response.choices[0].message

            # Extract response content (may be None for tool calls)
            content = message.content or ""

            # Extract tool calls if present
            tool_calls = None
            if message.tool_calls:
                tool_calls = []
                for tc in message.tool_calls:
                    tool_calls.append(
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                    )

            # Build response object
            usage = None
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            metadata = {
                "response_id": response.id,
                "created": response.created,
                "model": response.model,
                "finish_reason": response.choices[0].finish_reason,
            }

            logger.debug(
                f"OpenAI response received: {len(content)} chars, {len(tool_calls) if tool_calls else 0} tool calls"
            )

            return LLMResponse(
                content=content.strip(),
                model=response.model,
                usage=usage,
                metadata=metadata,
                tool_calls=tool_calls,
            )

        except openai.AuthenticationError as e:
            logger.error(f"OpenAI authentication error: {e}")
            raise LLMConfigurationError(f"Invalid OpenAI API key: {e}")
        except openai.RateLimitError as e:
            logger.error(f"OpenAI rate limit error: {e}")
            raise LLMServiceError(f"OpenAI rate limit exceeded: {e}")
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise LLMServiceError(f"OpenAI API error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in OpenAI completion: {e}")
            raise LLMServiceError(f"Unexpected error: {e}")

    async def health_check(self) -> bool:
        """
        Check if OpenAI API is accessible.

        Returns
        -------
        bool
            True if API is accessible, False otherwise
        """
        try:
            # Simple test request
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=1,
            )
            return response.choices[0].message.content is not None
        except Exception as e:
            logger.warning(f"OpenAI health check failed: {e}")
            return False


class MockLLMClient(LLMClient):
    """Mock LLM client for testing/development."""

    def __init__(self, model: str = "mock-gpt"):
        self.model = model
        logger.info("Mock LLM client initialized")

    async def complete(self, prompt: str, **kwargs) -> LLMResponse:
        """Return a mock response that echoes the prompt."""
        # Simulate API delay
        await asyncio.sleep(0.1)

        mock_content = f"Mock LLM response to: '{prompt}'. This is a simulated response for testing purposes."

        return LLMResponse(
            content=mock_content,
            model=self.model,
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            metadata={"mock": True},
        )

    async def health_check(self) -> bool:
        """Mock health check always returns True."""
        return True


def create_llm_client(
    provider: str = "openai", api_key: Optional[str] = None, **kwargs
) -> LLMClient:
    """
    Factory function to create LLM client.

    Parameters
    ----------
    provider : str
        LLM provider ("openai"/"openai-responses", "openai-chat"/"openai-legacy", or "mock")
    api_key : Optional[str]
        API key for the provider
    **kwargs
        Additional configuration for the client

    Returns
    -------
    LLMClient
        Configured LLM client instance

    Raises
    ------
    LLMConfigurationError
        If provider is not supported or configuration is invalid
    """
    provider_lc = provider.lower()
    if provider_lc in {"openai", "openai-responses"}:
        return OpenAIResponsesClient(api_key=api_key, **kwargs)
    # elif provider_lc in {"openai-chat", "openai-legacy"}:
    #     return LegacyChatCompletionClient(api_key=api_key, **kwargs)
    # elif provider.lower() == "mock":
    #     return MockLLMClient(**kwargs)
    else:
        raise LLMConfigurationError(f"Unsupported LLM provider: {provider}")


# Global client instance (will be initialized in main.py)
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """
    Get the global LLM client instance.

    Returns
    -------
    LLMClient
        The configured LLM client

    Raises
    ------
    LLMConfigurationError
        If no client has been configured
    """
    if _llm_client is None:
        raise LLMConfigurationError(
            "LLM client not initialized. Call set_llm_client() first."
        )
    return _llm_client


def set_llm_client(client: LLMClient) -> None:
    """
    Set the global LLM client instance.

    Parameters
    ----------
    client : LLMClient
        The LLM client to use globally
    """
    global _llm_client
    _llm_client = client
    logger.info(f"Global LLM client set: {type(client).__name__}")


async def initialize_default_llm_client() -> LLMClient:
    """
    Initialize default LLM client based on environment.

    Returns
    -------
    LLMClient
        Initialized client instance
    """
    # Try OpenAI first if API key is available
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key and OPENAI_AVAILABLE:
        try:
            client = create_llm_client("openai", api_key=openai_key)
            # Test connectivity
            if await client.health_check():
                logger.info("OpenAI client initialized and verified")
                return client
            else:
                logger.warning(
                    "OpenAI client failed health check, falling back to mock"
                )
        except Exception as e:
            logger.warning(
                f"Failed to initialize OpenAI client: {e}, falling back to mock"
            )

    # Fall back to mock client
    logger.info("Using mock LLM client")
    return create_llm_client("mock")


# -------------------------------------------------------------
# New Responses API client
# -------------------------------------------------------------


class OpenAIResponsesClient(LLMClient):
    """OpenAI Responses API client - Real Responses API implementation."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        max_completion_tokens: int = 500,
        temperature: float = 0.7,
    ):
        if not OPENAI_AVAILABLE:
            raise LLMConfigurationError(
                "OpenAI package not available. Install with: pip install openai"
            )

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise LLMConfigurationError(
                "OpenAI API key not provided. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.model = model
        self.max_completion_tokens = max_completion_tokens
        self.temperature = temperature

        self.client = AsyncOpenAI(api_key=self.api_key)

        logger.info(f"OpenAI Responses API client initialized with model: {model}")

    async def complete(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate completion using the real OpenAI Responses API."""
        try:
            # Build input - can be string or array
            input_data = kwargs.get("messages")
            if input_data is None:
                input_data = prompt

            request_params = {
                "model": kwargs.get("model", self.model),
                "input": input_data,
                "temperature": kwargs.get("temperature", self.temperature),
            }

            # Add optional parameters - use max_output_tokens for Responses API
            if "max_tokens" in kwargs or self.max_completion_tokens:
                request_params["max_output_tokens"] = kwargs.get(
                    "max_tokens", self.max_completion_tokens
                )

            # Support tools for function calling
            tools = kwargs.get("tools")
            if tools:
                request_params["tools"] = tools
                request_params["tool_choice"] = kwargs.get("tool_choice", "auto")

            # Support stateful conversation
            if "previous_response_id" in kwargs and kwargs["previous_response_id"]:
                request_params["previous_response_id"] = kwargs["previous_response_id"]

            if "instructions" in kwargs and kwargs["instructions"]:
                request_params["instructions"] = kwargs["instructions"]

            logger.debug(
                f"Sending OpenAI Responses API request: {request_params['model']}"
            )

            response = await self.client.responses.create(**request_params)

            # Extract content from response output
            content = ""
            tool_calls = None

            if hasattr(response, "output_text") and response.output_text:
                # Some responses have direct output_text
                content = response.output_text
            elif hasattr(response, "output") and response.output:
                # Parse the output array
                for output_item in response.output:
                    if hasattr(output_item, "type"):
                        if output_item.type == "message" and hasattr(
                            output_item, "content"
                        ):
                            # Message output with content
                            for content_item in output_item.content:
                                if hasattr(content_item, "text"):
                                    content += content_item.text
                                elif (
                                    hasattr(content_item, "type")
                                    and content_item.type == "output_text"
                                ):
                                    content += content_item.text
                        elif (
                            output_item.type.endswith("_call")
                            and "function" in output_item.type
                        ):
                            # Function call output
                            if tool_calls is None:
                                tool_calls = []
                            # Parse tool call information
                            tool_calls.append(
                                {
                                    "id": getattr(output_item, "id", ""),
                                    "call_id": getattr(
                                        output_item,
                                        "call_id",
                                        getattr(output_item, "id", ""),
                                    ),
                                    "type": "function",
                                    "function": {
                                        "name": getattr(output_item, "name", ""),
                                        "arguments": getattr(
                                            output_item, "arguments", "{}"
                                        ),
                                    },
                                }
                            )

            # Build usage info
            usage = None
            if hasattr(response, "usage") and response.usage:
                usage = {
                    "prompt_tokens": getattr(response.usage, "input_tokens", None),
                    "completion_tokens": getattr(response.usage, "output_tokens", None),
                    "total_tokens": getattr(response.usage, "total_tokens", None),
                }

            # Build metadata
            metadata = {
                "response_id": getattr(response, "id", None),
                "created": getattr(response, "created_at", None),
                "model": getattr(response, "model", self.model),
                "status": getattr(response, "status", None),
            }

            logger.debug(f"OpenAI Responses API received: {len(content)} chars")

            return LLMResponse(
                content=content.strip() if content else "",
                model=getattr(response, "model", self.model),
                usage=usage,
                metadata=metadata,
                tool_calls=tool_calls,
            )

        except openai.AuthenticationError as e:
            logger.error(f"OpenAI authentication error: {e}")
            raise LLMConfigurationError(f"Invalid OpenAI API key: {e}")
        except openai.RateLimitError as e:
            logger.error(f"OpenAI rate limit error: {e}")
            raise LLMServiceError(f"OpenAI rate limit exceeded: {e}")
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise LLMServiceError(f"OpenAI API error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in OpenAI Responses API completion: {e}")
            raise LLMServiceError(f"Unexpected error: {e}")

    async def health_check(self) -> bool:
        """Simple health check using a trivial request."""
        try:
            response = await self.client.responses.create(
                model=self.model,
                input="ping",
            )
            return hasattr(response, "output") and bool(response.output)
        except Exception as e:
            logger.warning(f"OpenAI Responses API health check failed: {e}")
            return False
