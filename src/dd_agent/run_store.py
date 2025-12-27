"""Run storage for persisting execution artifacts."""

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from dd_agent.util.hashing import hash_dataset


class RunStore:
    """Storage manager for run artifacts.

    Creates and manages run directories with the structure:
    runs/<timestamp>_<short_id>/
      inputs/
        questions.json
        responses.csv
        scope.md
        user_prompt.txt
      artifacts/
        high_level_plan.json
        segments.json
        cuts.json
        results.json
        validation.json
      report.md
    """

    def __init__(self, runs_dir: Path):
        """Initialize the run store.

        Args:
            runs_dir: Base directory for all runs
        """
        self.runs_dir = Path(runs_dir)
        self.runs_dir.mkdir(parents=True, exist_ok=True)

        self.run_id: Optional[str] = None
        self.run_dir: Optional[Path] = None
        self.inputs_dir: Optional[Path] = None
        self.artifacts_dir: Optional[Path] = None
        self.dataset_hash: Optional[str] = None

    def new_run(self, prompt: Optional[str] = None) -> str:
        """Create a new run directory.

        Args:
            prompt: Optional prompt to include in metadata

        Returns:
            The run ID
        """
        # Generate run ID
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
        short_id = uuid4().hex[:8]
        self.run_id = f"{timestamp}_{short_id}"

        # Create directories
        self.run_dir = self.runs_dir / self.run_id
        self.inputs_dir = self.run_dir / "inputs"
        self.artifacts_dir = self.run_dir / "artifacts"

        self.run_dir.mkdir(parents=True)
        self.inputs_dir.mkdir()
        self.artifacts_dir.mkdir()

        # Save initial metadata
        metadata = {
            "run_id": self.run_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "prompt": prompt,
        }
        self._save_json(self.run_dir / "metadata.json", metadata)

        return self.run_id

    def save_input(self, name: str, source_path: Path) -> None:
        """Copy an input file to the run's inputs directory.

        Args:
            name: Name to save the file as
            source_path: Path to the source file
        """
        if self.inputs_dir is None:
            raise RuntimeError("No active run. Call new_run() first.")

        dest = self.inputs_dir / name
        shutil.copy(source_path, dest)

    def save_input_text(self, name: str, content: str) -> None:
        """Save text content as an input file.

        Args:
            name: Name of the file
            content: Text content to save
        """
        if self.inputs_dir is None:
            raise RuntimeError("No active run. Call new_run() first.")

        dest = self.inputs_dir / name
        dest.write_text(content)

    def save_artifact(self, name: str, data: Any) -> None:
        """Save an artifact to the run's artifacts directory.

        Args:
            name: Name of the artifact file
            data: Data to save (will be JSON serialized if dict/list)
        """
        if self.artifacts_dir is None:
            raise RuntimeError("No active run. Call new_run() first.")

        dest = self.artifacts_dir / name

        if isinstance(data, (dict, list)):
            self._save_json(dest, data)
        elif isinstance(data, str):
            dest.write_text(data)
        else:
            # Try to convert to dict
            if hasattr(data, "model_dump"):
                self._save_json(dest, data.model_dump())
            else:
                self._save_json(dest, {"data": str(data)})

    def compute_dataset_hash(
        self,
        questions_path: Path,
        responses_path: Path,
        scope_path: Optional[Path] = None,
    ) -> str:
        """Compute and store the dataset hash.

        Args:
            questions_path: Path to questions.json
            responses_path: Path to responses.csv
            scope_path: Optional path to scope.md

        Returns:
            The computed hash
        """
        self.dataset_hash = hash_dataset(questions_path, responses_path, scope_path)

        # Update metadata
        if self.run_dir:
            metadata_path = self.run_dir / "metadata.json"
            if metadata_path.exists():
                with open(metadata_path) as f:
                    metadata = json.load(f)
                metadata["dataset_hash"] = self.dataset_hash
                self._save_json(metadata_path, metadata)

        return self.dataset_hash

    def save_report(self, result: Any) -> None:
        """Generate and save a human-readable report.

        Args:
            result: PipelineResult or similar result object
        """
        if self.run_dir is None:
            raise RuntimeError("No active run. Call new_run() first.")

        report_lines = [
            "# Analysis Run Report",
            "",
            f"**Run ID:** {self.run_id}",
            f"**Timestamp:** {datetime.now(timezone.utc).isoformat()}",
        ]

        if self.dataset_hash:
            report_lines.append(f"**Dataset Hash:** {self.dataset_hash[:16]}...")

        report_lines.append("")

        # Add result summary
        if hasattr(result, "success"):
            status = "✅ Success" if result.success else "❌ Failed"
            report_lines.append(f"## Status: {status}")
            report_lines.append("")

        if hasattr(result, "plan") and result.plan:
            report_lines.append("## Analysis Plan")
            report_lines.append(f"**Intents:** {len(result.plan.intents)}")
            report_lines.append(f"**Rationale:** {result.plan.rationale}")
            report_lines.append("")

        if hasattr(result, "cuts_planned"):
            report_lines.append(f"## Cuts Executed: {len(result.cuts_planned)}")
            for cut in result.cuts_planned:
                report_lines.append(
                    f"- **{cut.cut_id}**: {cut.metric.type} on {cut.metric.question_id}"
                )
            report_lines.append("")

        if hasattr(result, "cuts_failed") and result.cuts_failed:
            report_lines.append(f"## Failed Cuts: {len(result.cuts_failed)}")
            for fc in result.cuts_failed:
                report_lines.append(f"- **{fc['intent_id']}**: {fc['description'][:50]}...")
            report_lines.append("")

        if hasattr(result, "execution_result") and result.execution_result:
            exec_result = result.execution_result
            report_lines.append("## Execution Results")
            report_lines.append(f"**Tables Generated:** {len(exec_result.tables)}")

            if exec_result.errors:
                report_lines.append(f"**Execution Errors:** {len(exec_result.errors)}")

            report_lines.append("")

            for table in exec_result.tables:
                report_lines.append(f"### {table.cut_id}")
                report_lines.append(f"- Metric: {table.metric_type}")
                report_lines.append(f"- Question: {table.question_id}")
                report_lines.append(f"- Base N: {table.base_n}")

                if table.warnings:
                    for warn in table.warnings:
                        report_lines.append(f"- ⚠️ {warn}")

                report_lines.append("")

        if hasattr(result, "errors") and result.errors:
            report_lines.append("## Errors")
            for error in result.errors:
                report_lines.append(f"- {error}")
            report_lines.append("")

        report_content = "\n".join(report_lines)
        (self.run_dir / "report.md").write_text(report_content)

    def _save_json(self, path: Path, data: Any) -> None:
        """Save data as JSON."""
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def list_runs(self) -> list[dict[str, Any]]:
        """List all runs in the runs directory.

        Returns:
            List of run metadata dicts
        """
        runs = []
        for run_dir in sorted(self.runs_dir.iterdir(), reverse=True):
            if run_dir.is_dir():
                metadata_path = run_dir / "metadata.json"
                if metadata_path.exists():
                    with open(metadata_path) as f:
                        metadata = json.load(f)
                    metadata["run_dir"] = str(run_dir)
                    runs.append(metadata)
        return runs
