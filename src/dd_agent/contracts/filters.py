"""Boolean expression AST for filter definitions."""

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


# ============================================================================
# Predicates (leaf nodes)
# ============================================================================


class PredicateEq(BaseModel):
    """Equality predicate: question value equals a specific value."""

    kind: Literal["eq"] = "eq"
    question_id: str = Field(..., description="The question to filter on")
    value: str | int = Field(..., description="The value to match")


class PredicateIn(BaseModel):
    """In predicate: question value is one of the specified values."""

    kind: Literal["in"] = "in"
    question_id: str = Field(..., description="The question to filter on")
    values: list[str | int] = Field(..., description="The values to match (any of)")


class PredicateRange(BaseModel):
    """Range predicate: question value is within a numeric range."""

    kind: Literal["range"] = "range"
    question_id: str = Field(..., description="The question to filter on")
    min: float | int = Field(..., description="Minimum value")
    max: float | int = Field(..., description="Maximum value")
    inclusive: bool = Field(default=True, description="Whether bounds are inclusive")


class PredicateContainsAny(BaseModel):
    """Contains any predicate: for multi-choice, at least one value matches.

    This is specifically for multi-choice questions where the response
    contains multiple selected options (stored as semicolon-separated codes).
    """

    kind: Literal["contains_any"] = "contains_any"
    question_id: str = Field(..., description="The question to filter on")
    values: list[str | int] = Field(
        ..., description="At least one of these values must be present"
    )


# Union of all predicate types
Predicate = Union[PredicateEq, PredicateIn, PredicateRange, PredicateContainsAny]


# ============================================================================
# Logical operators (composite nodes)
# ============================================================================


class And(BaseModel):
    """Logical AND: all children must be true."""

    kind: Literal["and"] = "and"
    children: list["FilterExpr"] = Field(
        ..., description="Child expressions (all must be true)"
    )


class Or(BaseModel):
    """Logical OR: at least one child must be true."""

    kind: Literal["or"] = "or"
    children: list["FilterExpr"] = Field(
        ..., description="Child expressions (at least one must be true)"
    )


class Not(BaseModel):
    """Logical NOT: inverts the child expression."""

    kind: Literal["not"] = "not"
    child: "FilterExpr" = Field(..., description="Child expression to negate")


# ============================================================================
# FilterExpr union type
# ============================================================================

# The complete filter expression type - either a predicate or a logical operator
FilterExpr = Annotated[
    Union[PredicateEq, PredicateIn, PredicateRange, PredicateContainsAny, And, Or, Not],
    Field(discriminator="kind"),
]

# Rebuild models to resolve forward references
And.model_rebuild()
Or.model_rebuild()
Not.model_rebuild()
