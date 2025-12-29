"""Evaluation harness for running test cases."""

from pathlib import Path
from typing import Any, Optional

import yaml

from dd_agent.contracts.questions import Question
from dd_agent.contracts.specs import CutSpec
from dd_agent.engine.executor import Executor
from dd_agent.eval.scoring import EvalResult, score_executor_result


class EvalHarness:
    """Harness for running evaluation cases.

    Loads test cases from YAML and runs them against the executor,
    comparing results to expected values.
    """

    def __init__(
        self,
        questions: list[Question],
        responses_df: "pd.DataFrame",
    ):
        """Initialize the evaluation harness.

        Args:
            questions: Question catalog
            responses_df: Responses DataFrame
        """
        self.questions = questions
        self.questions_by_id = {q.question_id: q for q in questions}
        self.responses_df = responses_df
        self.executor = Executor(
            df=responses_df,
            questions_by_id=self.questions_by_id,
        )

    def load_cases(self, cases_path: Path) -> list[dict[str, Any]]:
        """Load test cases from YAML file.

        Args:
            cases_path: Path to eval_cases.yaml

        Returns:
            List of test case dictionaries
        """
        with open(cases_path) as f:
            content = f.read()

        # Parse YAML documents (separated by ---)
        cases = []
        for doc in yaml.safe_load_all(content):
            if doc and isinstance(doc, list):
                cases.extend(doc)
            elif doc:
                cases.append(doc)

        return [c for c in cases if c]  # Filter None entries

    def run_case(self, case: dict[str, Any]) -> EvalResult:
        """Run a single test case.

        Args:
            case: Test case dictionary

        Returns:
            EvalResult with pass/fail and details
        """
        case_name = case.get("name", "unnamed")
        case_type = case.get("type", "executor")

        try:
            if case_type == "executor":
                return self._run_executor_case(case)
            elif case_type == "validation":
                return self._run_validation_case(case)
            else:
                return EvalResult(
                    name=case_name,
                    passed=False,
                    message=f"Unknown case type: {case_type}",
                )
        except Exception as e:
            return EvalResult(
                name=case_name,
                passed=False,
                message=f"Error: {str(e)}",
                error=str(e),
            )

    def _run_executor_case(self, case: dict[str, Any]) -> EvalResult:
        """Run an executor test case."""
        case_name = case.get("name", "unnamed")
        cut_data = case.get("input", {}).get("cut_spec", {})
        expected = case.get("expected", {})

        # Parse cut spec
        cut = CutSpec.model_validate(cut_data)

        # Execute
        exec_result = self.executor.execute_cuts([cut])

        if exec_result.errors:
            return EvalResult(
                name=case_name,
                passed=False,
                message=f"Execution errors: {exec_result.errors}",
            )

        if not exec_result.tables:
            return EvalResult(
                name=case_name,
                passed=False,
                message="No tables returned",
            )

        table = exec_result.tables[0]
        return score_executor_result(case_name, table, expected)

    def _run_validation_case(self, case: dict[str, Any]) -> EvalResult:
        """Run a validation test case."""
        from dd_agent.contracts.validate import validate_cut_spec

        case_name = case.get("name", "unnamed")
        cut_data = case.get("input", {}).get("cut_spec", {})
        expected = case.get("expected", {})

        try:
            cut = CutSpec.model_validate(cut_data)
        except Exception as e:
            # Parsing error counts as validation failure
            expected_errors = expected.get("validation_errors", [])
            if expected_errors:
                return EvalResult(
                    name=case_name,
                    passed=True,
                    message=f"Validation correctly failed: {e}",
                )
            return EvalResult(
                name=case_name,
                passed=False,
                message=f"Unexpected parsing error: {e}",
            )

        errors = validate_cut_spec(cut, self.questions_by_id)
        expected_errors = expected.get("validation_errors", [])

        if expected_errors:
            # We expect errors
            if not errors:
                return EvalResult(
                    name=case_name,
                    passed=False,
                    message="Expected validation errors but got none",
                )

            # Check that expected error codes are present
            error_codes = {e.code for e in errors}
            expected_codes = {e.get("code") for e in expected_errors}

            if expected_codes <= error_codes:
                return EvalResult(
                    name=case_name,
                    passed=True,
                    message=f"Validation correctly failed with: {error_codes}",
                )
            else:
                return EvalResult(
                    name=case_name,
                    passed=False,
                    message=f"Expected {expected_codes} but got {error_codes}",
                )
        else:
            # We expect no errors
            if errors:
                return EvalResult(
                    name=case_name,
                    passed=False,
                    message=f"Unexpected validation errors: {[e.code for e in errors]}",
                )
            return EvalResult(
                name=case_name,
                passed=True,
                message="Validation passed as expected",
            )

    def run_all(self, cases_path: Path) -> list[EvalResult]:
        """Run all test cases from a file.

        Args:
            cases_path: Path to eval_cases.yaml

        Returns:
            List of EvalResult for each case
        """
        cases = self.load_cases(cases_path)
        results = []

        for case in cases:
            result = self.run_case(case)
            results.append(result)

        return results

    def summary(self, results: list[EvalResult]) -> dict[str, Any]:
        """Generate a summary of evaluation results.

        Args:
            results: List of EvalResult

        Returns:
            Summary dictionary
        """
        passed = sum(1 for r in results if r.passed)
        failed = len(results) - passed

        return {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / len(results) if results else 0,
            "failures": [
                {"name": r.name, "message": r.message}
                for r in results
                if not r.passed
            ],
        }
