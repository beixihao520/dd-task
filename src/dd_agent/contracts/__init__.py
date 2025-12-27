"""Contracts package - Pydantic models for the DD Agent."""

from dd_agent.contracts.questions import Option, Question, QuestionType
from dd_agent.contracts.filters import (
    And,
    FilterExpr,
    Not,
    Or,
    Predicate,
    PredicateContainsAny,
    PredicateEq,
    PredicateIn,
    PredicateRange,
)
from dd_agent.contracts.specs import (
    AnalysisIntent,
    CutSpec,
    DimensionSpec,
    MetricSpec,
    SegmentSpec,
)
from dd_agent.contracts.tool_output import ToolMessage, ToolOutput

__all__ = [
    # Questions
    "Option",
    "Question",
    "QuestionType",
    # Filters
    "And",
    "FilterExpr",
    "Not",
    "Or",
    "Predicate",
    "PredicateContainsAny",
    "PredicateEq",
    "PredicateIn",
    "PredicateRange",
    # Specs
    "AnalysisIntent",
    "CutSpec",
    "DimensionSpec",
    "MetricSpec",
    "SegmentSpec",
    # Tool Output
    "ToolMessage",
    "ToolOutput",
]
