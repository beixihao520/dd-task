"""Cut planner tool for converting NL requests to CutSpecs."""

from typing import Any, Optional

from pydantic import BaseModel, Field

from dd_agent.contracts.specs import CutSpec
from dd_agent.contracts.tool_output import ToolMessage, ToolOutput, err
from dd_agent.contracts.validate import validate_cut_spec
from dd_agent.llm.structured import build_messages, chat_structured_pydantic
from dd_agent.tools.base import Tool, ToolContext


class CutPlanResult(BaseModel):
    """Result of the cut planner tool."""

    ok: bool = Field(..., description="Whether planning succeeded")
    cut: Optional[CutSpec] = Field(
        default=None, description="The planned cut specification"
    )
    resolution_map: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of NL terms to question/segment IDs",
    )
    ambiguity_options: list[str] = Field(
        default_factory=list,
        description="Possible interpretations if ambiguous",
    )
    errors: list[dict[str, Any]] = Field(
        default_factory=list, description="Any errors from the LLM"
    )


class CutPlanner(Tool):
    """Tool for converting natural language requests to CutSpecs.

    Takes a natural language analysis request (e.g., "Show NPS by region")
    and produces a validated CutSpec that can be executed deterministically.
    """

    @property
    def name(self) -> str:
        return "cut_planner"

    @property
    def description(self) -> str:
        return "Converts natural language analysis requests to executable CutSpecs"

    def run(self, ctx: ToolContext) -> ToolOutput[CutSpec]:
        """Execute the cut planner tool.

        Args:
            ctx: Tool context with questions, segments, and the prompt

        Returns:
            ToolOutput containing a validated CutSpec or errors
        """
        if not ctx.prompt:
            return ToolOutput.failure(
                errors=[err("missing_prompt", "No analysis request provided")]
            )

        # TODO: Implement tool logic
        raise NotImplementedError("Candidates must implement the CutPlanner logic")

    def _build_user_content(self, ctx: ToolContext) -> str:
        """Build the user message content."""
        # TODO: Implement context formatting
        return ""
