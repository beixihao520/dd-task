"""Tests for domain validation logic."""

import pytest

from dd_agent.contracts.filters import (
    And,
    PredicateContainsAny,
    PredicateEq,
    PredicateIn,
    PredicateRange,
)
from dd_agent.contracts.questions import Option, Question, QuestionType
from dd_agent.contracts.specs import CutSpec, DimensionSpec, MetricSpec, SegmentSpec
from dd_agent.contracts.validate import (
    check_metric_compatibility,
    validate_cut_spec,
    validate_filter_expr,
    validate_segment_spec,
)


class TestMetricCompatibility:
    """Tests for metric/question type compatibility checking."""

    def test_nps_requires_nps_question(self):
        """NPS metric should only work with nps_0_10 questions."""
        # Valid
        assert check_metric_compatibility("nps", QuestionType.nps_0_10) is None
        
        # Invalid
        result = check_metric_compatibility("nps", QuestionType.likert_1_5)
        assert result is not None
        assert result.code == "metric_incompatible"

    def test_top2box_requires_likert(self):
        """Top2box should only work with Likert scales."""
        # Valid
        assert check_metric_compatibility("top2box", QuestionType.likert_1_5) is None
        assert check_metric_compatibility("top2box", QuestionType.likert_1_7) is None
        
        # Invalid
        result = check_metric_compatibility("top2box", QuestionType.single_choice)
        assert result is not None
        assert result.code == "metric_incompatible"

    def test_mean_works_with_numeric_types(self):
        """Mean should work with numeric-compatible types."""
        assert check_metric_compatibility("mean", QuestionType.numeric) is None
        assert check_metric_compatibility("mean", QuestionType.likert_1_5) is None
        assert check_metric_compatibility("mean", QuestionType.nps_0_10) is None

    def test_frequency_works_with_choice_types(self):
        """Frequency should work with choice-type questions."""
        assert check_metric_compatibility("frequency", QuestionType.single_choice) is None
        assert check_metric_compatibility("frequency", QuestionType.multi_choice) is None


class TestFilterExprValidation:
    """Tests for filter expression validation."""

    @pytest.fixture
    def questions_by_id(self) -> dict[str, Question]:
        return {
            "Q_REGION": Question(
                question_id="Q_REGION",
                label="Region",
                type=QuestionType.single_choice,
                options=[
                    Option(code="NORTH", label="North"),
                    Option(code="SOUTH", label="South"),
                ],
            ),
            "Q_AGE": Question(
                question_id="Q_AGE",
                label="Age",
                type=QuestionType.numeric,
            ),
            "Q_FEATURES": Question(
                question_id="Q_FEATURES",
                label="Features",
                type=QuestionType.multi_choice,
                options=[
                    Option(code="A", label="Feature A"),
                    Option(code="B", label="Feature B"),
                ],
            ),
        }

    def test_valid_eq_predicate(self, questions_by_id):
        """Valid eq predicate should pass."""
        expr = PredicateEq(question_id="Q_REGION", value="NORTH")
        errors = validate_filter_expr(expr, questions_by_id)
        assert len(errors) == 0

    def test_unknown_question_in_predicate(self, questions_by_id):
        """Unknown question should fail validation."""
        expr = PredicateEq(question_id="Q_UNKNOWN", value="X")
        errors = validate_filter_expr(expr, questions_by_id)
        assert len(errors) == 1
        assert errors[0].code == "unknown_question"

    def test_invalid_option_value(self, questions_by_id):
        """Invalid option value should fail validation."""
        expr = PredicateEq(question_id="Q_REGION", value="INVALID")
        errors = validate_filter_expr(expr, questions_by_id)
        assert len(errors) == 1
        assert errors[0].code == "invalid_option"

    def test_valid_range_predicate(self, questions_by_id):
        """Valid range predicate should pass."""
        expr = PredicateRange(question_id="Q_AGE", min=18, max=65)
        errors = validate_filter_expr(expr, questions_by_id)
        assert len(errors) == 0

    def test_range_on_non_numeric(self, questions_by_id):
        """Range predicate on non-numeric question should fail."""
        expr = PredicateRange(question_id="Q_REGION", min=1, max=10)
        errors = validate_filter_expr(expr, questions_by_id)
        assert len(errors) == 1
        assert errors[0].code == "predicate_incompatible"

    def test_contains_any_on_multi_choice(self, questions_by_id):
        """ContainsAny on multi-choice should pass."""
        expr = PredicateContainsAny(question_id="Q_FEATURES", values=["A", "B"])
        errors = validate_filter_expr(expr, questions_by_id)
        assert len(errors) == 0

    def test_contains_any_on_single_choice(self, questions_by_id):
        """ContainsAny on single-choice should fail."""
        expr = PredicateContainsAny(question_id="Q_REGION", values=["NORTH"])
        errors = validate_filter_expr(expr, questions_by_id)
        assert len(errors) == 1
        assert errors[0].code == "predicate_incompatible"

    def test_nested_and_expression(self, questions_by_id):
        """Nested AND expression should validate all children."""
        expr = And(
            children=[
                PredicateEq(question_id="Q_REGION", value="NORTH"),
                PredicateRange(question_id="Q_AGE", min=18, max=65),
            ]
        )
        errors = validate_filter_expr(expr, questions_by_id)
        assert len(errors) == 0

    def test_nested_and_with_error(self, questions_by_id):
        """Nested AND with invalid child should fail."""
        expr = And(
            children=[
                PredicateEq(question_id="Q_REGION", value="NORTH"),
                PredicateEq(question_id="Q_UNKNOWN", value="X"),
            ]
        )
        errors = validate_filter_expr(expr, questions_by_id)
        assert len(errors) == 1


class TestCutSpecValidation:
    """Tests for CutSpec validation."""

    @pytest.fixture
    def questions_by_id(self) -> dict[str, Question]:
        return {
            "Q_NPS": Question(
                question_id="Q_NPS",
                label="NPS",
                type=QuestionType.nps_0_10,
            ),
            "Q_REGION": Question(
                question_id="Q_REGION",
                label="Region",
                type=QuestionType.single_choice,
                options=[Option(code="NORTH", label="North")],
            ),
        }

    @pytest.fixture
    def segments_by_id(self, questions_by_id) -> dict[str, SegmentSpec]:
        return {
            "promoters": SegmentSpec(
                segment_id="promoters",
                name="Promoters",
                definition=PredicateRange(question_id="Q_NPS", min=9, max=10),
            ),
        }

    def test_valid_cut_spec(self, questions_by_id, segments_by_id):
        """Valid cut spec should pass."""
        cut = CutSpec(
            cut_id="test",
            metric=MetricSpec(type="nps", question_id="Q_NPS"),
            dimensions=[DimensionSpec(kind="question", id="Q_REGION")],
        )
        errors = validate_cut_spec(cut, questions_by_id, segments_by_id)
        assert len(errors) == 0

    def test_unknown_metric_question(self, questions_by_id, segments_by_id):
        """Unknown metric question should fail."""
        cut = CutSpec(
            cut_id="test",
            metric=MetricSpec(type="nps", question_id="Q_UNKNOWN"),
        )
        errors = validate_cut_spec(cut, questions_by_id, segments_by_id)
        assert len(errors) == 1
        assert errors[0].code == "unknown_question"

    def test_incompatible_metric(self, questions_by_id, segments_by_id):
        """Incompatible metric should fail."""
        cut = CutSpec(
            cut_id="test",
            metric=MetricSpec(type="nps", question_id="Q_REGION"),  # NPS on non-NPS
        )
        errors = validate_cut_spec(cut, questions_by_id, segments_by_id)
        assert len(errors) == 1
        assert errors[0].code == "metric_incompatible"

    def test_unknown_dimension_question(self, questions_by_id, segments_by_id):
        """Unknown dimension question should fail."""
        cut = CutSpec(
            cut_id="test",
            metric=MetricSpec(type="nps", question_id="Q_NPS"),
            dimensions=[DimensionSpec(kind="question", id="Q_UNKNOWN")],
        )
        errors = validate_cut_spec(cut, questions_by_id, segments_by_id)
        assert len(errors) == 1
        assert errors[0].code == "unknown_dimension"

    def test_unknown_dimension_segment(self, questions_by_id, segments_by_id):
        """Unknown dimension segment should fail."""
        cut = CutSpec(
            cut_id="test",
            metric=MetricSpec(type="nps", question_id="Q_NPS"),
            dimensions=[DimensionSpec(kind="segment", id="unknown_segment")],
        )
        errors = validate_cut_spec(cut, questions_by_id, segments_by_id)
        assert len(errors) == 1
        assert errors[0].code == "unknown_dimension"

    def test_valid_segment_dimension(self, questions_by_id, segments_by_id):
        """Valid segment dimension should pass."""
        cut = CutSpec(
            cut_id="test",
            metric=MetricSpec(type="nps", question_id="Q_NPS"),
            dimensions=[DimensionSpec(kind="segment", id="promoters")],
        )
        errors = validate_cut_spec(cut, questions_by_id, segments_by_id)
        assert len(errors) == 0


class TestSegmentSpecValidation:
    """Tests for SegmentSpec validation."""

    @pytest.fixture
    def questions_by_id(self) -> dict[str, Question]:
        return {
            "Q_AGE": Question(
                question_id="Q_AGE",
                label="Age",
                type=QuestionType.numeric,
            ),
        }

    def test_valid_segment(self, questions_by_id):
        """Valid segment should pass."""
        segment = SegmentSpec(
            segment_id="young_adults",
            name="Young Adults",
            definition=PredicateRange(question_id="Q_AGE", min=18, max=35),
        )
        errors = validate_segment_spec(segment, questions_by_id)
        assert len(errors) == 0

    def test_segment_with_unknown_question(self, questions_by_id):
        """Segment with unknown question should fail."""
        segment = SegmentSpec(
            segment_id="test",
            name="Test",
            definition=PredicateEq(question_id="Q_UNKNOWN", value="X"),
        )
        errors = validate_segment_spec(segment, questions_by_id)
        assert len(errors) == 1
        assert errors[0].code == "unknown_question"
