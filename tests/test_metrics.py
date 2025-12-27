"""Tests for metric computation functions."""

import pandas as pd
import pytest

from dd_agent.contracts.questions import Option, Question, QuestionType
from dd_agent.engine.metrics import (
    compute_frequency,
    compute_mean,
    compute_multi_choice_frequency,
    compute_nps,
    compute_top2box,
    compute_bottom2box,
)


class TestComputeNPS:
    """Tests for NPS calculation."""

    def test_all_promoters(self):
        """All 9s and 10s should give NPS of 100."""
        series = pd.Series([9, 10, 9, 10, 9, 10])
        result = compute_nps(series)
        
        assert result["nps"] == 100.0
        assert result["promoters_count"] == 6
        assert result["detractors_count"] == 0
        assert result["passives_count"] == 0

    def test_all_detractors(self):
        """All 0-6 should give NPS of -100."""
        series = pd.Series([0, 1, 2, 3, 4, 5, 6])
        result = compute_nps(series)
        
        assert result["nps"] == -100.0
        assert result["promoters_count"] == 0
        assert result["detractors_count"] == 7

    def test_mixed_nps(self):
        """Mixed responses should calculate correctly."""
        # 2 promoters (10, 9), 2 passives (8, 7), 2 detractors (6, 5)
        series = pd.Series([10, 9, 8, 7, 6, 5])
        result = compute_nps(series)
        
        # (2/6 - 2/6) * 100 = 0
        assert result["nps"] == 0.0
        assert result["promoters_count"] == 2
        assert result["passives_count"] == 2
        assert result["detractors_count"] == 2
        assert result["total"] == 6

    def test_empty_series(self):
        """Empty series should return None NPS."""
        series = pd.Series([], dtype=float)
        result = compute_nps(series)
        
        assert result["nps"] is None
        assert result["total"] == 0

    def test_with_nan_values(self):
        """NaN values should be excluded."""
        series = pd.Series([10, 9, None, 5, None, 8])
        result = compute_nps(series)
        
        assert result["total"] == 4  # Only 4 valid values
        assert result["promoters_count"] == 2  # 10, 9


class TestComputeMean:
    """Tests for mean calculation."""

    def test_simple_mean(self):
        """Test basic mean calculation."""
        series = pd.Series([1, 2, 3, 4, 5])
        result = compute_mean(series)
        
        assert result["mean"] == 3.0
        assert result["count"] == 5
        assert result["min"] == 1.0
        assert result["max"] == 5.0

    def test_with_nan(self):
        """NaN values should be excluded from mean."""
        series = pd.Series([1, 2, None, 4, 5])
        result = compute_mean(series)
        
        assert result["mean"] == 3.0
        assert result["count"] == 4


class TestComputeTop2Box:
    """Tests for top 2 box calculation."""

    def test_likert_1_5(self):
        """Test top 2 box for 1-5 Likert scale."""
        series = pd.Series([1, 2, 3, 4, 5, 4, 5, 3])
        question = Question(
            question_id="Q1",
            label="Test",
            type=QuestionType.likert_1_5,
        )
        result = compute_top2box(series, question)
        
        # 4 values are 4 or 5 out of 8
        assert result["top2box_pct"] == 50.0
        assert result["top2box_count"] == 4
        assert result["total"] == 8

    def test_likert_1_7(self):
        """Test top 2 box for 1-7 Likert scale."""
        series = pd.Series([1, 2, 3, 4, 5, 6, 7, 6])
        question = Question(
            question_id="Q1",
            label="Test",
            type=QuestionType.likert_1_7,
        )
        result = compute_top2box(series, question)
        
        # 3 values are 6 or 7 out of 8
        assert result["top2box_pct"] == 37.5
        assert result["top2box_count"] == 3

    def test_custom_top_values(self):
        """Test with custom top values."""
        series = pd.Series([1, 2, 3, 4, 5])
        result = compute_top2box(series, top_values=[3, 4, 5])
        
        # 3 values are 3, 4, or 5 out of 5
        assert result["top2box_pct"] == 60.0


class TestComputeBottom2Box:
    """Tests for bottom 2 box calculation."""

    def test_likert_1_5(self):
        """Test bottom 2 box for 1-5 Likert scale."""
        series = pd.Series([1, 2, 3, 4, 5, 1, 2, 3])
        question = Question(
            question_id="Q1",
            label="Test",
            type=QuestionType.likert_1_5,
        )
        result = compute_bottom2box(series, question)
        
        # 4 values are 1 or 2 out of 8
        assert result["bottom2box_pct"] == 50.0
        assert result["bottom2box_count"] == 4


class TestComputeFrequency:
    """Tests for frequency distribution calculation."""

    def test_simple_frequency(self):
        """Test basic frequency distribution."""
        series = pd.Series(["A", "B", "A", "C", "A", "B"])
        result = compute_frequency(series)
        
        assert len(result) == 3
        
        # A appears 3 times (50%)
        a_row = result[result["value"] == "A"].iloc[0]
        assert a_row["count"] == 3
        assert a_row["percentage"] == 50.0

    def test_with_question_labels(self):
        """Test frequency uses question labels."""
        series = pd.Series([1, 2, 1, 1, 2])
        question = Question(
            question_id="Q1",
            label="Test",
            type=QuestionType.single_choice,
            options=[
                Option(code=1, label="Option One"),
                Option(code=2, label="Option Two"),
            ],
        )
        result = compute_frequency(series, question)
        
        assert result[result["value"] == 1]["label"].iloc[0] == "Option One"


class TestComputeMultiChoiceFrequency:
    """Tests for multi-choice frequency calculation."""

    def test_multi_choice_frequency(self):
        """Test multi-choice frequency with semicolon separated values."""
        series = pd.Series(["A;B", "B;C", "A", "A;B;C", "B"])
        question = Question(
            question_id="Q1",
            label="Test",
            type=QuestionType.multi_choice,
            options=[
                Option(code="A", label="Feature A"),
                Option(code="B", label="Feature B"),
                Option(code="C", label="Feature C"),
            ],
        )
        result = compute_multi_choice_frequency(series, question)
        
        # Check counts (A appears in 3 responses, B in 4, C in 2)
        assert result[result["value"] == "A"]["count"].iloc[0] == 3
        assert result[result["value"] == "B"]["count"].iloc[0] == 4
        assert result[result["value"] == "C"]["count"].iloc[0] == 2
        
        # Percentages are of respondents (5 total)
        assert result[result["value"] == "B"]["percentage"].iloc[0] == 80.0  # 4/5
