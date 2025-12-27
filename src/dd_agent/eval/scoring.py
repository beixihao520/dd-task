"""Scoring utilities for evaluation results."""

from dataclasses import dataclass, field
from typing import Any, Optional

from dd_agent.engine.tables import TableResult


@dataclass
class EvalResult:
    """Result of evaluating a single test case."""

    name: str
    passed: bool
    message: str
    expected: Optional[dict[str, Any]] = None
    actual: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    details: dict[str, Any] = field(default_factory=dict)


def score_executor_result(
    case_name: str,
    table: TableResult,
    expected: dict[str, Any],
) -> EvalResult:
    """Score an executor result against expected values.

    Args:
        case_name: Name of the test case
        table: The table result from executor
        expected: Expected values dictionary

    Returns:
        EvalResult with pass/fail
    """
    checks_passed = []
    checks_failed = []

    # Check NPS range
    if "nps_range" in expected:
        nps_min, nps_max = expected["nps_range"]
        nps_value = table.result_data.get("nps")
        if nps_value is not None:
            if nps_min <= nps_value <= nps_max:
                checks_passed.append(f"NPS {nps_value} in range [{nps_min}, {nps_max}]")
            else:
                checks_failed.append(f"NPS {nps_value} not in range [{nps_min}, {nps_max}]")
        else:
            checks_failed.append("NPS value is None")

    # Check base_n minimum
    if "base_n_min" in expected:
        if table.base_n >= expected["base_n_min"]:
            checks_passed.append(f"Base N {table.base_n} >= {expected['base_n_min']}")
        else:
            checks_failed.append(f"Base N {table.base_n} < {expected['base_n_min']}")

    # Check mean range
    if "mean_range" in expected:
        mean_min, mean_max = expected["mean_range"]
        mean_value = table.result_data.get("mean")
        if mean_value is not None:
            if mean_min <= mean_value <= mean_max:
                checks_passed.append(f"Mean {mean_value} in range [{mean_min}, {mean_max}]")
            else:
                checks_failed.append(f"Mean {mean_value} not in range [{mean_min}, {mean_max}]")
        else:
            checks_failed.append("Mean value is None")

    # Check percentage range
    if "percentage_range" in expected:
        pct_min, pct_max = expected["percentage_range"]
        pct_value = table.result_data.get("top2box_pct")
        if pct_value is not None:
            if pct_min <= pct_value <= pct_max:
                checks_passed.append(f"Percentage {pct_value} in range [{pct_min}, {pct_max}]")
            else:
                checks_failed.append(f"Percentage {pct_value} not in range [{pct_min}, {pct_max}]")

    # Check total percentage for frequency
    if "total_percentage" in expected:
        distribution = table.result_data.get("distribution", [])
        total_pct = sum(item.get("percentage", 0) for item in distribution)
        if abs(total_pct - expected["total_percentage"]) < 0.1:
            checks_passed.append(f"Total percentage {total_pct} ≈ {expected['total_percentage']}")
        else:
            checks_failed.append(f"Total percentage {total_pct} != {expected['total_percentage']}")

    # Check categories presence
    if "categories" in expected:
        distribution = table.result_data.get("distribution", [])
        actual_categories = {str(item.get("value")) for item in distribution}
        expected_categories = set(expected["categories"])
        if expected_categories <= actual_categories:
            checks_passed.append(f"Categories {expected_categories} present")
        else:
            missing = expected_categories - actual_categories
            checks_failed.append(f"Missing categories: {missing}")

    # Check categories_present (looser check)
    if "categories_present" in expected:
        distribution = table.result_data.get("distribution", [])
        actual_categories = {str(item.get("value")) for item in distribution}
        for cat in expected["categories_present"]:
            if cat in actual_categories:
                checks_passed.append(f"Category '{cat}' present")
            else:
                checks_failed.append(f"Category '{cat}' not present")

    # Check dimensions_present
    if "dimensions_present" in expected:
        by_dimension = table.result_data.get("by_dimension", {})
        actual_dims = set(by_dimension.keys())
        for dim in expected["dimensions_present"]:
            if dim in actual_dims:
                checks_passed.append(f"Dimension '{dim}' present")
            else:
                checks_failed.append(f"Dimension '{dim}' not present")

    # Determine overall pass/fail
    passed = len(checks_failed) == 0 and len(checks_passed) > 0

    message = ""
    if passed:
        message = f"All {len(checks_passed)} checks passed"
    else:
        message = f"Failed: {'; '.join(checks_failed)}"

    return EvalResult(
        name=case_name,
        passed=passed,
        message=message,
        expected=expected,
        actual=table.result_data,
        details={
            "checks_passed": checks_passed,
            "checks_failed": checks_failed,
            "base_n": table.base_n,
        },
    )
