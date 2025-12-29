"""Tool output envelope and message types."""

from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ToolMessage(BaseModel):
    """A message (error or warning) from a tool."""

    code: str = Field(..., description="Machine-readable error/warning code")
    message: str = Field(..., description="Human-readable message")
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context for debugging",
    )


class ToolOutput(BaseModel, Generic[T]):
    """Standard output envelope for all tools.

    This provides a consistent interface for tool results, making it easy
    to handle success/failure cases and trace execution.
    """

    ok: bool = Field(..., description="Whether the tool execution was successful")
    data: Optional[T] = Field(
        default=None, description="The result data (if successful)"
    )
    errors: list[ToolMessage] = Field(
        default_factory=list, description="List of errors (if any)"
    )
    warnings: list[ToolMessage] = Field(
        default_factory=list, description="List of warnings (if any)"
    )
    trace: dict[str, Any] = Field(
        default_factory=dict,
        description="Trace information (prompts, model, latency, mappings, etc.)",
    )

    @classmethod
    def success(
        cls,
        data: T,
        warnings: Optional[list[ToolMessage]] = None,
        trace: Optional[dict[str, Any]] = None,
    ) -> "ToolOutput[T]":
        """Create a successful tool output."""
        return cls(
            ok=True,
            data=data,
            warnings=warnings or [],
            trace=trace or {},
        )

    @classmethod
    def failure(
        cls,
        errors: list[ToolMessage],
        warnings: Optional[list[ToolMessage]] = None,
        trace: Optional[dict[str, Any]] = None,
    ) -> "ToolOutput[T]":
        """Create a failed tool output."""
        return cls(
            ok=False,
            data=None,
            errors=errors,
            warnings=warnings or [],
            trace=trace or {},
        )


def err(code: str, message: str, **context: Any) -> ToolMessage:
    """Helper to create an error message."""
    return ToolMessage(code=code, message=message, context=context)


def warn(code: str, message: str, **context: Any) -> ToolMessage:
    """Helper to create a warning message."""
    return ToolMessage(code=code, message=message, context=context)
