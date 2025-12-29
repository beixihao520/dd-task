"""Pytest fixtures for DD Agent tests."""

import json
from pathlib import Path

import pandas as pd
import pytest

from dd_agent.contracts.questions import Option, Question, QuestionType
from dd_agent.contracts.specs import CutSpec, MetricSpec, SegmentSpec
from dd_agent.contracts.filters import PredicateEq, PredicateRange


@pytest.fixture
def sample_questions() -> list[Question]:
    """Create sample questions for testing."""
    return [
        Question(
            question_id="Q_NPS",
            label="How likely to recommend?",
            type=QuestionType.nps_0_10,
        ),
        Question(
            question_id="Q_SATISFACTION",
            label="Overall satisfaction",
            type=QuestionType.likert_1_5,
            options=[
                Option(code=1, label="Very Dissatisfied"),
                Option(code=2, label="Dissatisfied"),
                Option(code=3, label="Neutral"),
                Option(code=4, label="Satisfied"),
                Option(code=5, label="Very Satisfied"),
            ],
        ),
        Question(
            question_id="Q_REGION",
            label="Region",
            type=QuestionType.single_choice,
            options=[
                Option(code="NORTH", label="North"),
                Option(code="SOUTH", label="South"),
                Option(code="EAST", label="East"),
                Option(code="WEST", label="West"),
            ],
        ),
        Question(
            question_id="Q_AGE",
            label="Age",
            type=QuestionType.numeric,
        ),
        Question(
            question_id="Q_FEATURES",
            label="Features used",
            type=QuestionType.multi_choice,
            options=[
                Option(code="A", label="Feature A"),
                Option(code="B", label="Feature B"),
                Option(code="C", label="Feature C"),
            ],
        ),
    ]


@pytest.fixture
def questions_by_id(sample_questions: list[Question]) -> dict[str, Question]:
    """Create question lookup dictionary."""
    return {q.question_id: q for q in sample_questions}


@pytest.fixture
def sample_responses_df() -> pd.DataFrame:
    """Create sample responses DataFrame."""
    return pd.DataFrame({
        "Q_NPS": [10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0, 9, 10, 8, 7],
        "Q_SATISFACTION": [5, 4, 4, 3, 3, 2, 1, 2, 1, 2, 1, 5, 5, 4, 3],
        "Q_REGION": ["NORTH", "SOUTH", "EAST", "WEST", "NORTH", 
                     "SOUTH", "EAST", "WEST", "NORTH", "SOUTH",
                     "EAST", "WEST", "NORTH", "SOUTH", "EAST"],
        "Q_AGE": [25, 35, 45, 28, 32, 41, 55, 23, 38, 47, 29, 33, 42, 27, 36],
        "Q_FEATURES": ["A;B", "B;C", "A", "A;B;C", "B", 
                       "C", "A;C", "B", "A;B", "C",
                       "A;B;C", "B;C", "A", "A;B", "C"],
    })


@pytest.fixture
def sample_segment() -> SegmentSpec:
    """Create a sample segment."""
    return SegmentSpec(
        segment_id="promoters",
        name="Promoters",
        definition=PredicateRange(
            question_id="Q_NPS",
            min=9,
            max=10,
            inclusive=True,
        ),
    )


@pytest.fixture
def sample_cut_spec() -> CutSpec:
    """Create a sample cut specification."""
    return CutSpec(
        cut_id="test_cut",
        metric=MetricSpec(
            type="nps",
            question_id="Q_NPS",
        ),
        dimensions=[],
        filter=None,
    )


@pytest.fixture
def demo_data_dir(tmp_path: Path, sample_questions: list[Question]) -> Path:
    """Create a temporary demo data directory."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    
    # Write questions
    questions_data = [q.model_dump() for q in sample_questions]
    with open(data_dir / "questions.json", "w") as f:
        json.dump(questions_data, f)
    
    # Write responses
    df = pd.DataFrame({
        "Q_NPS": [10, 9, 8, 7, 6, 5, 4, 3, 2, 1],
        "Q_SATISFACTION": [5, 4, 4, 3, 3, 2, 1, 2, 1, 2],
        "Q_REGION": ["NORTH", "SOUTH", "EAST", "WEST", "NORTH", 
                     "SOUTH", "EAST", "WEST", "NORTH", "SOUTH"],
        "Q_AGE": [25, 35, 45, 28, 32, 41, 55, 23, 38, 47],
        "Q_FEATURES": ["A;B", "B;C", "A", "A;B;C", "B", 
                       "C", "A;C", "B", "A;B", "C"],
    })
    df.to_csv(data_dir / "responses.csv", index=False)
    
    # Write scope
    (data_dir / "scope.md").write_text("# Test Scope\nThis is a test.")
    
    return data_dir
