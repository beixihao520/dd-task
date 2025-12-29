"""Agent for coordinating tools and execution."""

from pathlib import Path
from typing import Optional

import pandas as pd

from dd_agent.contracts.questions import Question
from dd_agent.contracts.specs import CutSpec, SegmentSpec
from dd_agent.contracts.tool_output import ToolOutput
from dd_agent.engine.executor import ExecutionResult, Executor
from dd_agent.tools.base import ToolContext
from dd_agent.tools.cut_planner import CutPlanner
from dd_agent.tools.high_level_planner import HighLevelPlanner
from dd_agent.tools.segment_builder import SegmentBuilder


class Agent:
    """Agent that coordinates tools and execution.

    The agent provides a high-level interface for:
    - Planning analyses (high-level and cut-level)
    - Building segments
    - Executing validated specifications
    """

    def __init__(
        self,
        questions: list[Question],
        responses_df: pd.DataFrame,
        scope: Optional[str] = None,
        data_dir: Optional[Path] = None,
    ):
        """Initialize the agent.

        Args:
            questions: List of question definitions
            responses_df: DataFrame with survey responses
            scope: Optional project scope document
            data_dir: Optional data directory path
        """
        self.questions = questions
        self.questions_by_id = {q.question_id: q for q in questions}
        self.responses_df = responses_df
        self.scope = scope
        self.data_dir = data_dir

        # Segments built during the session
        self.segments: list[SegmentSpec] = []
        self.segments_by_id: dict[str, SegmentSpec] = {}

        # Initialize tools
        self.high_level_planner = HighLevelPlanner()
        self.cut_planner = CutPlanner()
        self.segment_builder = SegmentBuilder()

    def _get_context(self, prompt: Optional[str] = None) -> ToolContext:
        """Get a tool context with current state."""
        return ToolContext(
            questions=self.questions,
            questions_by_id=self.questions_by_id,
            segments=self.segments,
            segments_by_id=self.segments_by_id,
            scope=self.scope,
            prompt=prompt,
            responses_df=self.responses_df,
            data_dir=self.data_dir,
        )

    def plan_analysis(self) -> ToolOutput:
        """Generate a high-level analysis plan.

        Uses the high-level planner to propose analysis intents
        based on the available questions and project scope.

        Returns:
            ToolOutput with HighLevelPlan or errors
        """
        # TODO: Implement orchestration for high-level planning
        # 1. Use high_level_planner tool
        # 2. Add any suggested segments to the current session
        raise NotImplementedError("Candidates must implement plan_analysis")

    def plan_cut(self, request: str) -> ToolOutput[CutSpec]:
        """Plan a single cut from a natural language request.

        Args:
            request: Natural language analysis request

        Returns:
            ToolOutput with CutSpec or errors
        """
        # TODO: Implement orchestration for cut planning
        raise NotImplementedError("Candidates must implement plan_cut")

    def build_segment(self, definition: str) -> ToolOutput[SegmentSpec]:
        """Build a segment from a natural language definition.

        Args:
            definition: Natural language segment definition

        Returns:
            ToolOutput with SegmentSpec or errors
        """
        # TODO: Implement orchestration for segment building
        raise NotImplementedError("Candidates must implement build_segment")

    def add_segment(self, segment: SegmentSpec) -> None:
        """Add a segment to the session.

        Args:
            segment: The segment to add
        """
        # Replace if exists
        self.segments = [s for s in self.segments if s.segment_id != segment.segment_id]
        self.segments.append(segment)
        self.segments_by_id[segment.segment_id] = segment

    def execute_cuts(self, cuts: list[CutSpec]) -> ExecutionResult:
        """Execute a list of validated cut specifications.

        Args:
            cuts: List of CutSpec objects to execute

        Returns:
            ExecutionResult with tables and any errors
        """
        # TODO: Initialize the Executor and call execute_cuts
        raise NotImplementedError("Candidates must implement execute_cuts")

    def execute_single_cut(self, cut: CutSpec) -> ExecutionResult:
        """Execute a single cut specification.

        Args:
            cut: The CutSpec to execute

        Returns:
            ExecutionResult with the table
        """
        return self.execute_cuts([cut])
