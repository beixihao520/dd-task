"""Specification contracts for analysis definitions."""

from typing import Literal, Optional

from pydantic import BaseModel, Field

from dd_agent.contracts.filters import FilterExpr


class SegmentSpec(BaseModel):
    """Specification for a respondent segment."""

    segment_id: str = Field(..., description="Unique identifier for this segment")
    name: str = Field(..., description="Human-readable name for the segment")
    definition: FilterExpr = Field(
        ..., description="Filter expression defining segment membership"
    )
    intended_partition: bool = Field(
        default=False,
        description="If true, this segment is part of a mutually exclusive partition",
    )
    notes: Optional[str] = Field(
        default=None, description="Optional notes about the segment"
    )


class MetricSpec(BaseModel):
    """Specification for a metric to compute."""

    type: Literal["frequency", "mean", "top2box", "bottom2box", "nps"] = Field(
        ..., description="The type of metric to compute"
    )
    question_id: str = Field(..., description="The question to compute the metric on")
    params: dict = Field(
        default_factory=dict,
        description="Additional parameters for the metric (e.g., top_values for top2box)",
    )


class DimensionSpec(BaseModel):
    """Specification for a dimension in cross-tabulation."""

    kind: Literal["question", "segment"] = Field(
        ..., description="Whether this dimension is a question or segment"
    )
    id: str = Field(..., description="The question_id or segment_id")


class CutSpec(BaseModel):
    """Specification for an analysis cut (a single table/computation)."""

    cut_id: str = Field(..., description="Unique identifier for this cut")
    metric: MetricSpec = Field(..., description="The metric to compute")
    dimensions: list[DimensionSpec] = Field(
        default_factory=list,
        description="Dimensions for cross-tabulation (row/column breaks)",
    )
    filter: Optional[FilterExpr] = Field(
        default=None, description="Optional filter to apply before computation"
    )
    weight_column: Optional[str] = Field(
        default=None, description="Column name for weighting"
    )
    output: dict = Field(
        default_factory=dict,
        description="Output configuration (e.g., format preferences)",
    )


class AnalysisIntent(BaseModel):
    """A high-level analysis intent from the planner."""

    intent_id: str = Field(..., description="Unique identifier for this intent")
    description: str = Field(
        ..., description="Natural language description of the analysis"
    )
    segments_needed: list[str] = Field(
        default_factory=list,
        description="Hints about segments that might be needed",
    )
    priority: int = Field(
        default=1, description="Priority level (1=high, 3=low)"
    )


class HighLevelPlan(BaseModel):
    """The output of the high-level planner."""

    intents: list[AnalysisIntent] = Field(
        ..., description="List of analysis intents to execute"
    )
    rationale: str = Field(
        ..., description="Explanation of the planning decisions"
    )
    suggested_segments: list[SegmentSpec] = Field(
        default_factory=list,
        description="Segments suggested for use across multiple intents",
    )
