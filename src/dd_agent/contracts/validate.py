"""Domain validation for specs and expressions.

This module implements strict validation that refuses to execute if specs
don't validate - unknown question IDs, incompatible metric/question type,
invalid option values, ambiguous mappings, etc.
"""

from typing import Optional

from dd_agent.contracts.filters import (
    And,
    FilterExpr,
    Not,
    Or,
    PredicateContainsAny,
    PredicateEq,
    PredicateIn,
    PredicateRange,
)
from dd_agent.contracts.questions import Question, QuestionType
from dd_agent.contracts.specs import CutSpec, MetricSpec, SegmentSpec
from dd_agent.contracts.tool_output import ToolMessage, err


# ============================================================================
# Metric/Question Type Compatibility
# ============================================================================

# Define which metrics are compatible with which question types
METRIC_TYPE_COMPATIBILITY: dict[str, set[QuestionType]] = {
    "frequency": {
        QuestionType.single_choice,
        QuestionType.multi_choice,
        QuestionType.likert_1_5,
        QuestionType.likert_1_7,
        QuestionType.nps_0_10,
    },
    "mean": {
        QuestionType.likert_1_5,
        QuestionType.likert_1_7,
        QuestionType.numeric,
        QuestionType.nps_0_10,
    },
    "top2box": {
        QuestionType.likert_1_5,
        QuestionType.likert_1_7,
    },
    "bottom2box": {
        QuestionType.likert_1_5,
        QuestionType.likert_1_7,
    },
    "nps": {
        QuestionType.nps_0_10,
    },
}


def check_metric_compatibility(
    metric_type: str, question_type: QuestionType
) -> Optional[ToolMessage]:
    """Check if a metric type is compatible with a question type."""
    compatible_types = METRIC_TYPE_COMPATIBILITY.get(metric_type)
    if compatible_types is None:
        return err(
            "unknown_metric_type",
            f"Unknown metric type: {metric_type}",
            metric_type=metric_type,
        )
    if question_type not in compatible_types:
        return err(
            "metric_incompatible",
            f"Metric '{metric_type}' is not compatible with question type '{question_type.value}'",
            metric_type=metric_type,
            question_type=question_type.value,
            compatible_types=[t.value for t in compatible_types],
        )
    return None


# ============================================================================
# Filter Expression Validation
# ============================================================================


def validate_filter_expr(
    expr: Optional[FilterExpr],
    questions_by_id: dict[str, Question],
) -> list[ToolMessage]:
    """Validate a filter expression against the question catalog.

    Checks:
    - All referenced question IDs exist
    - All option values are valid for the referenced questions
    - Range predicates are only used with numeric-compatible questions
    - ContainsAny predicates are only used with multi-choice questions
    """
    if expr is None:
        return []

    errors: list[ToolMessage] = []

    if isinstance(expr, PredicateEq):
        errors.extend(_validate_predicate_eq(expr, questions_by_id))
    elif isinstance(expr, PredicateIn):
        errors.extend(_validate_predicate_in(expr, questions_by_id))
    elif isinstance(expr, PredicateRange):
        errors.extend(_validate_predicate_range(expr, questions_by_id))
    elif isinstance(expr, PredicateContainsAny):
        errors.extend(_validate_predicate_contains_any(expr, questions_by_id))
    elif isinstance(expr, And):
        for child in expr.children:
            errors.extend(validate_filter_expr(child, questions_by_id))
    elif isinstance(expr, Or):
        for child in expr.children:
            errors.extend(validate_filter_expr(child, questions_by_id))
    elif isinstance(expr, Not):
        errors.extend(validate_filter_expr(expr.child, questions_by_id))

    return errors


def _validate_predicate_eq(
    pred: PredicateEq, questions_by_id: dict[str, Question]
) -> list[ToolMessage]:
    """Validate an equality predicate."""
    errors: list[ToolMessage] = []

    question = questions_by_id.get(pred.question_id)
    if question is None:
        errors.append(
            err(
                "unknown_question",
                f"Question '{pred.question_id}' not found in catalog",
                question_id=pred.question_id,
            )
        )
        return errors

    # Check option validity for choice-type questions
    if question.type in {
        QuestionType.single_choice,
        QuestionType.multi_choice,
        QuestionType.likert_1_5,
        QuestionType.likert_1_7,
    }:
        valid_codes = question.get_option_codes()
        if valid_codes and pred.value not in valid_codes:
            # Try string/int coercion
            str_value = str(pred.value)
            if str_value not in {str(c) for c in valid_codes}:
                errors.append(
                    err(
                        "invalid_option",
                        f"Option value '{pred.value}' is not valid for question '{pred.question_id}'",
                        question_id=pred.question_id,
                        value=pred.value,
                        valid_codes=list(valid_codes),
                    )
                )

    return errors


def _validate_predicate_in(
    pred: PredicateIn, questions_by_id: dict[str, Question]
) -> list[ToolMessage]:
    """Validate an 'in' predicate."""
    errors: list[ToolMessage] = []

    question = questions_by_id.get(pred.question_id)
    if question is None:
        errors.append(
            err(
                "unknown_question",
                f"Question '{pred.question_id}' not found in catalog",
                question_id=pred.question_id,
            )
        )
        return errors

    # Check option validity for choice-type questions
    if question.type in {
        QuestionType.single_choice,
        QuestionType.multi_choice,
        QuestionType.likert_1_5,
        QuestionType.likert_1_7,
    }:
        valid_codes = question.get_option_codes()
        if valid_codes:
            str_valid = {str(c) for c in valid_codes}
            for value in pred.values:
                if value not in valid_codes and str(value) not in str_valid:
                    errors.append(
                        err(
                            "invalid_option",
                            f"Option value '{value}' is not valid for question '{pred.question_id}'",
                            question_id=pred.question_id,
                            value=value,
                            valid_codes=list(valid_codes),
                        )
                    )

    return errors


def _validate_predicate_range(
    pred: PredicateRange, questions_by_id: dict[str, Question]
) -> list[ToolMessage]:
    """Validate a range predicate."""
    errors: list[ToolMessage] = []

    question = questions_by_id.get(pred.question_id)
    if question is None:
        errors.append(
            err(
                "unknown_question",
                f"Question '{pred.question_id}' not found in catalog",
                question_id=pred.question_id,
            )
        )
        return errors

    # Range predicates only work with numeric-compatible types
    numeric_types = {
        QuestionType.numeric,
        QuestionType.likert_1_5,
        QuestionType.likert_1_7,
        QuestionType.nps_0_10,
    }
    if question.type not in numeric_types:
        errors.append(
            err(
                "predicate_incompatible",
                f"Range predicate cannot be used with question type '{question.type.value}'",
                question_id=pred.question_id,
                question_type=question.type.value,
            )
        )

    # Validate range bounds
    if pred.min > pred.max:
        errors.append(
            err(
                "invalid_range",
                f"Range min ({pred.min}) is greater than max ({pred.max})",
                question_id=pred.question_id,
                min=pred.min,
                max=pred.max,
            )
        )

    return errors


def _validate_predicate_contains_any(
    pred: PredicateContainsAny, questions_by_id: dict[str, Question]
) -> list[ToolMessage]:
    """Validate a 'contains any' predicate."""
    errors: list[ToolMessage] = []

    question = questions_by_id.get(pred.question_id)
    if question is None:
        errors.append(
            err(
                "unknown_question",
                f"Question '{pred.question_id}' not found in catalog",
                question_id=pred.question_id,
            )
        )
        return errors

    # ContainsAny is specifically for multi-choice questions
    if question.type != QuestionType.multi_choice:
        errors.append(
            err(
                "predicate_incompatible",
                f"ContainsAny predicate can only be used with multi_choice questions, "
                f"but '{pred.question_id}' is '{question.type.value}'",
                question_id=pred.question_id,
                question_type=question.type.value,
            )
        )

    # Check option validity
    valid_codes = question.get_option_codes()
    if valid_codes:
        str_valid = {str(c) for c in valid_codes}
        for value in pred.values:
            if value not in valid_codes and str(value) not in str_valid:
                errors.append(
                    err(
                        "invalid_option",
                        f"Option value '{value}' is not valid for question '{pred.question_id}'",
                        question_id=pred.question_id,
                        value=value,
                        valid_codes=list(valid_codes),
                    )
                )

    return errors


# ============================================================================
# Segment Validation
# ============================================================================


def validate_segment_spec(
    segment: SegmentSpec,
    questions_by_id: dict[str, Question],
) -> list[ToolMessage]:
    """Validate a segment specification."""
    errors: list[ToolMessage] = []

    # Validate the filter expression
    errors.extend(validate_filter_expr(segment.definition, questions_by_id))

    return errors


# ============================================================================
# Cut Validation
# ============================================================================


def validate_cut_spec(
    cut: CutSpec,
    questions_by_id: dict[str, Question],
    segments_by_id: Optional[dict[str, SegmentSpec]] = None,
) -> list[ToolMessage]:
    """Validate a cut specification.

    Checks:
    - Metric question exists and is compatible
    - All dimension questions/segments exist
    - Filter expression is valid
    """
    if segments_by_id is None:
        segments_by_id = {}

    errors: list[ToolMessage] = []

    # Validate metric
    errors.extend(_validate_metric_spec(cut.metric, questions_by_id))

    # Validate dimensions
    for dim in cut.dimensions:
        if dim.kind == "question":
            if dim.id not in questions_by_id:
                errors.append(
                    err(
                        "unknown_dimension",
                        f"Dimension question '{dim.id}' not found",
                        dimension_id=dim.id,
                        dimension_kind="question",
                    )
                )
        elif dim.kind == "segment":
            if dim.id not in segments_by_id:
                errors.append(
                    err(
                        "unknown_dimension",
                        f"Dimension segment '{dim.id}' not found",
                        dimension_id=dim.id,
                        dimension_kind="segment",
                    )
                )

    # Validate filter
    errors.extend(validate_filter_expr(cut.filter, questions_by_id))

    return errors


def _validate_metric_spec(
    metric: MetricSpec,
    questions_by_id: dict[str, Question],
) -> list[ToolMessage]:
    """Validate a metric specification."""
    errors: list[ToolMessage] = []

    question = questions_by_id.get(metric.question_id)
    if question is None:
        errors.append(
            err(
                "unknown_question",
                f"Metric question_id '{metric.question_id}' not found in catalog",
                question_id=metric.question_id,
            )
        )
        return errors

    # Check metric/type compatibility
    compat_error = check_metric_compatibility(metric.type, question.type)
    if compat_error:
        errors.append(compat_error)

    return errors


# ============================================================================
# Batch Validation
# ============================================================================


def validate_all_segments(
    segments: list[SegmentSpec],
    questions_by_id: dict[str, Question],
) -> dict[str, list[ToolMessage]]:
    """Validate all segments, returning errors by segment_id."""
    result = {}
    for segment in segments:
        errors = validate_segment_spec(segment, questions_by_id)
        if errors:
            result[segment.segment_id] = errors
    return result


def validate_all_cuts(
    cuts: list[CutSpec],
    questions_by_id: dict[str, Question],
    segments_by_id: Optional[dict[str, SegmentSpec]] = None,
) -> dict[str, list[ToolMessage]]:
    """Validate all cuts, returning errors by cut_id."""
    result = {}
    for cut in cuts:
        errors = validate_cut_spec(cut, questions_by_id, segments_by_id)
        if errors:
            result[cut.cut_id] = errors
    return result
