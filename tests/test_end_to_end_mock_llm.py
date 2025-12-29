"""End-to-end tests with mock LLM backend."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from dd_agent.contracts.questions import Question
from dd_agent.contracts.specs import CutSpec, MetricSpec, SegmentSpec
from dd_agent.contracts.filters import PredicateRange
from dd_agent.engine.executor import Executor
from dd_agent.tools.base import ToolContext


class TestExecutorEndToEnd:
    """End-to-end tests for the executor (no LLM needed)."""

    def test_nps_calculation(self, sample_questions, sample_responses_df):
        """Test NPS calculation end-to-end."""
        questions_by_id = {q.question_id: q for q in sample_questions}
        
        executor = Executor(
            df=sample_responses_df,
            questions_by_id=questions_by_id,
        )
        
        cut = CutSpec(
            cut_id="test_nps",
            metric=MetricSpec(type="nps", question_id="Q_NPS"),
        )
        
        result = executor.execute_cuts([cut])
        
        assert len(result.tables) == 1
        table = result.tables[0]
        assert table.cut_id == "test_nps"
        assert table.metric_type == "nps"
        assert table.base_n > 0
        assert "nps" in table.result_data

    def test_frequency_calculation(self, sample_questions, sample_responses_df):
        """Test frequency distribution end-to-end."""
        questions_by_id = {q.question_id: q for q in sample_questions}
        
        executor = Executor(
            df=sample_responses_df,
            questions_by_id=questions_by_id,
        )
        
        cut = CutSpec(
            cut_id="test_freq",
            metric=MetricSpec(type="frequency", question_id="Q_REGION"),
        )
        
        result = executor.execute_cuts([cut])
        
        assert len(result.tables) == 1
        table = result.tables[0]
        assert table.metric_type == "frequency"
        assert "distribution" in table.result_data

    def test_with_segment_filter(self, sample_questions, sample_responses_df):
        """Test execution with segment-based filter."""
        questions_by_id = {q.question_id: q for q in sample_questions}
        
        segment = SegmentSpec(
            segment_id="promoters",
            name="Promoters",
            definition=PredicateRange(question_id="Q_NPS", min=9, max=10),
        )
        segments_by_id = {"promoters": segment}
        
        executor = Executor(
            df=sample_responses_df,
            questions_by_id=questions_by_id,
            segments_by_id=segments_by_id,
        )
        
        # Materialize segments
        segment_bases = executor.materialize_segments()
        assert "promoters" in segment_bases
        assert segment_bases["promoters"] > 0

    def test_dimension_crosstab(self, sample_questions, sample_responses_df):
        """Test cross-tabulation by dimension."""
        questions_by_id = {q.question_id: q for q in sample_questions}
        
        executor = Executor(
            df=sample_responses_df,
            questions_by_id=questions_by_id,
        )
        
        cut = CutSpec(
            cut_id="test_crosstab",
            metric=MetricSpec(type="mean", question_id="Q_SATISFACTION"),
            dimensions=[{"kind": "question", "id": "Q_REGION"}],
        )
        
        result = executor.execute_cuts([cut])
        
        assert len(result.tables) == 1
        table = result.tables[0]
        assert "by_dimension" in table.result_data

    def test_multiple_cuts(self, sample_questions, sample_responses_df):
        """Test executing multiple cuts."""
        questions_by_id = {q.question_id: q for q in sample_questions}
        
        executor = Executor(
            df=sample_responses_df,
            questions_by_id=questions_by_id,
        )
        
        cuts = [
            CutSpec(
                cut_id="cut1",
                metric=MetricSpec(type="nps", question_id="Q_NPS"),
            ),
            CutSpec(
                cut_id="cut2",
                metric=MetricSpec(type="mean", question_id="Q_SATISFACTION"),
            ),
            CutSpec(
                cut_id="cut3",
                metric=MetricSpec(type="frequency", question_id="Q_REGION"),
            ),
        ]
        
        result = executor.execute_cuts(cuts)
        
        assert len(result.tables) == 3
        assert {t.cut_id for t in result.tables} == {"cut1", "cut2", "cut3"}


class TestToolContextBuilding:
    """Tests for ToolContext construction."""

    def test_context_from_questions(self, sample_questions):
        """Test creating context from questions."""
        ctx = ToolContext(questions=sample_questions)
        
        assert len(ctx.questions) == len(sample_questions)
        assert len(ctx.questions_by_id) == len(sample_questions)
        assert "Q_NPS" in ctx.questions_by_id

    def test_context_with_prompt(self, sample_questions):
        """Test adding prompt to context."""
        ctx = ToolContext(questions=sample_questions)
        new_ctx = ctx.with_prompt("Calculate NPS by region")
        
        assert new_ctx.prompt == "Calculate NPS by region"
        assert ctx.prompt is None  # Original unchanged

    def test_context_summary(self, sample_questions):
        """Test question summary generation."""
        ctx = ToolContext(questions=sample_questions)
        summary = ctx.get_questions_summary()
        
        assert "Q_NPS" in summary
        assert "nps_0_10" in summary


class TestMockLLMIntegration:
    """Tests with mocked LLM responses."""

    def test_cut_planner_with_mock(self, sample_questions):
        """Test cut planner with mocked LLM response."""
        from dd_agent.tools.cut_planner import CutPlanner, CutPlanResult
        
        # Create mock response
        mock_result = CutPlanResult(
            ok=True,
            cut=CutSpec(
                cut_id="mock_cut",
                metric=MetricSpec(type="nps", question_id="Q_NPS"),
            ),
            resolution_map={"NPS": "Q_NPS"},
        )
        
        # Mock the LLM call
        with patch("dd_agent.tools.cut_planner.chat_structured_pydantic") as mock_llm:
            mock_llm.return_value = (mock_result, {"model": "mock"})
            
            planner = CutPlanner()
            ctx = ToolContext(
                questions=sample_questions,
                prompt="Calculate NPS",
            )
            
            result = planner.run(ctx)
            
            assert result.ok
            assert result.data.cut_id == "mock_cut"
            assert result.data.metric.type == "nps"

    def test_segment_builder_with_mock(self, sample_questions):
        """Test segment builder with mocked LLM response."""
        from dd_agent.tools.segment_builder import SegmentBuilder
        
        # Create mock response
        mock_segment = SegmentSpec(
            segment_id="young_users",
            name="Young Users",
            definition=PredicateRange(question_id="Q_AGE", min=18, max=30),
        )
        
        with patch("dd_agent.tools.segment_builder.chat_structured_pydantic") as mock_llm:
            mock_llm.return_value = (mock_segment, {"model": "mock"})
            
            builder = SegmentBuilder()
            ctx = ToolContext(
                questions=sample_questions,
                prompt="Users aged 18-30",
            )
            
            result = builder.run(ctx)
            
            assert result.ok
            assert result.data.segment_id == "young_users"


class TestDataLoading:
    """Tests for data loading functionality."""

    def test_load_questions_from_json(self, demo_data_dir):
        """Test loading questions from JSON file."""
        questions_path = demo_data_dir / "questions.json"
        
        with open(questions_path) as f:
            data = json.load(f)
        
        questions = [Question.model_validate(q) for q in data]
        
        assert len(questions) > 0
        assert all(isinstance(q, Question) for q in questions)

    def test_load_responses_csv(self, demo_data_dir):
        """Test loading responses from CSV."""
        responses_path = demo_data_dir / "responses.csv"
        
        df = pd.read_csv(responses_path)
        
        assert len(df) > 0
        assert "Q_NPS" in df.columns
