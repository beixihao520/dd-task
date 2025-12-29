"""High-level analysis planner tool."""

from typing import Any

from dd_agent.contracts.specs import HighLevelPlan
from dd_agent.contracts.tool_output import ToolOutput, err
from dd_agent.llm.structured import build_messages, chat_structured_pydantic
from dd_agent.tools.base import Tool, ToolContext


class HighLevelPlanner(Tool):
    """Tool for generating high-level analysis plans.

    Given a question catalog and optional scope document, this tool
    proposes a comprehensive set of analysis intents that would
    provide valuable insights from the survey data.
    """

    @property
    def name(self) -> str:
        return "high_level_planner"

    @property
    def description(self) -> str:
        return "Generates a high-level analysis plan with intents and suggested segments"

    def run(self, ctx: ToolContext) -> ToolOutput[HighLevelPlan]:
        """Execute the high-level planning tool.

        Args:
            ctx: Tool context with questions and optional scope

        Returns:
            ToolOutput containing a HighLevelPlan or errors
        """
        # TODO: Implement architectural planning logic
        raise NotImplementedError("Candidates must implement the HighLevelPlanner logic")

    def _build_user_content(self, ctx: ToolContext) -> str:
        """Build the user message content."""
        # TODO: Implement data presentation for LLM
        return ""

    def _validate_plan(
        self, plan: HighLevelPlan, ctx: ToolContext
    ) -> list[Any]:
        """Validate the generated plan."""
        # TODO: Implement plan verification
        return []
