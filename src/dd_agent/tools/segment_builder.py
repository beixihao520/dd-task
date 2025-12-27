"""Segment builder tool for converting NL definitions to SegmentSpecs."""

from dd_agent.contracts.specs import SegmentSpec
from dd_agent.contracts.tool_output import ToolOutput, err
from dd_agent.contracts.validate import validate_segment_spec
from dd_agent.llm.structured import build_messages, chat_structured_pydantic
from dd_agent.tools.base import Tool, ToolContext


class SegmentBuilder(Tool):
    """Tool for converting natural language segment definitions to SegmentSpecs.

    Takes a natural language segment description (e.g., "Young professionals
    aged 25-34 in urban areas") and produces a validated SegmentSpec with
    a filter expression.
    """

    @property
    def name(self) -> str:
        return "segment_builder"

    @property
    def description(self) -> str:
        return "Converts natural language segment definitions to executable SegmentSpecs"

    def run(self, ctx: ToolContext) -> ToolOutput[SegmentSpec]:
        """Execute the segment builder tool.

        Args:
            ctx: Tool context with questions and the segment definition prompt

        Returns:
            ToolOutput containing a validated SegmentSpec or errors
        """
        if not ctx.prompt:
            return ToolOutput.failure(
                errors=[err("missing_prompt", "No segment definition provided")]
            )

        # TODO: Implement segment logic
        raise NotImplementedError("Candidates must implement the SegmentBuilder logic")

    def _build_user_content(self, ctx: ToolContext) -> str:
        """Build the user message content."""
        # TODO: Implement segment formatting
        return ""
