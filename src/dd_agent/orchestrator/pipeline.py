"""Pipeline for running analysis flows."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from dd_agent.contracts.questions import Question
from dd_agent.contracts.specs import CutSpec, HighLevelPlan, SegmentSpec
from dd_agent.contracts.tool_output import ToolOutput
from dd_agent.engine.executor import ExecutionResult
from dd_agent.orchestrator.agent import Agent
from dd_agent.run_store import RunStore
from dd_agent.util.logging import get_logger

logger = get_logger("pipeline")


@dataclass
class PipelineResult:
    """Result of a pipeline execution."""

    success: bool
    run_id: str
    run_dir: Path
    plan: Optional[HighLevelPlan] = None
    cuts_planned: list[CutSpec] = field(default_factory=list)
    cuts_failed: list[dict[str, Any]] = field(default_factory=list)
    execution_result: Optional[ExecutionResult] = None
    errors: list[str] = field(default_factory=list)


class Pipeline:
    """Pipeline for running analysis flows.

    Provides two main flows:
    1. run_single: Execute a single analysis request
    2. run_autoplan: Generate and execute a full analysis plan
    """

    def __init__(
        self,
        data_dir: Path,
        runs_dir: Optional[Path] = None,
    ):
        """Initialize the pipeline.

        Args:
            data_dir: Directory containing questions.json, responses.csv, scope.md
            runs_dir: Directory for saving run artifacts (defaults to data_dir/runs)
        """
        self.data_dir = Path(data_dir)
        self.runs_dir = runs_dir or self.data_dir / "runs"

        # Load data
        self.questions = self._load_questions()
        self.responses_df = self._load_responses()
        self.scope = self._load_scope()

        # Create agent
        self.agent = Agent(
            questions=self.questions,
            responses_df=self.responses_df,
            scope=self.scope,
            data_dir=self.data_dir,
        )

    def _load_questions(self) -> list[Question]:
        """Load questions from questions.json."""
        questions_path = self.data_dir / "questions.json"
        if not questions_path.exists():
            raise FileNotFoundError(f"Questions file not found: {questions_path}")

        with open(questions_path) as f:
            data = json.load(f)

        # Handle both list and dict formats
        if isinstance(data, list):
            return [Question.model_validate(q) for q in data]
        elif isinstance(data, dict) and "questions" in data:
            return [Question.model_validate(q) for q in data["questions"]]
        else:
            raise ValueError("Invalid questions.json format")

    def _load_responses(self) -> pd.DataFrame:
        """Load responses from responses.csv."""
        responses_path = self.data_dir / "responses.csv"
        if not responses_path.exists():
            raise FileNotFoundError(f"Responses file not found: {responses_path}")

        return pd.read_csv(responses_path)

    def _load_scope(self) -> Optional[str]:
        """Load scope from scope.md if it exists."""
        scope_path = self.data_dir / "scope.md"
        if scope_path.exists():
            return scope_path.read_text()
        return None

    def run_single(
        self,
        prompt: str,
        save_run: bool = True,
    ) -> PipelineResult:
        """Execute a single analysis request.

        Args:
            prompt: Natural language analysis request
            save_run: Whether to save run artifacts

        Returns:
            PipelineResult with execution details
        """
        # TODO: Implement the single-request pipeline
        # 1. Initialize RunStore
        # 2. Plan the cut via agent
        # 3. Execute the cut
        # 4. Save artifacts and generate report
        raise NotImplementedError("Candidates must implement run_single")

    def run_autoplan(
        self,
        save_run: bool = True,
        max_cuts: int = 20,
    ) -> PipelineResult:
        """Generate and execute a full analysis plan.

        Args:
            save_run: Whether to save run artifacts
            max_cuts: Maximum number of cuts to execute

        Returns:
            PipelineResult with execution details
        """
        # TODO: Implement the autoplan pipeline
        # 1. Initialize RunStore
        # 2. Generate high-level plan via agent
        # 3. For each intent, plan a cut
        # 4. Execute all planned cuts
        # 5. Save all artifacts and generate report
        raise NotImplementedError("Candidates must implement run_autoplan")
