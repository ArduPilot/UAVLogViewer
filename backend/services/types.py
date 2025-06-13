"""
Shared Types for Chat and Tool System

This module contains shared dataclasses used across the chat orchestrator
and tool registry to avoid circular imports.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional


@dataclass
class ToolCall:
    """Represents a tool call request from the LLM."""

    tool_name: str
    parameters: Dict[str, Any]
    call_id: Optional[str] = None  # For tracking in conversation


@dataclass
class ToolResult:
    """Result from executing a tool."""

    tool_name: str
    call_id: Optional[str]
    success: bool
    data: Any
    metadata: Dict[str, Any]
    execution_time: float
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
