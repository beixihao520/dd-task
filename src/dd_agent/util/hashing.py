"""Dataset hashing utilities for reproducibility."""

import hashlib
from pathlib import Path
from typing import Optional


def hash_file(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def hash_dataset(
    questions_path: Path,
    responses_path: Path,
    scope_path: Optional[Path] = None,
) -> str:
    """Compute a combined hash of the dataset files.

    This creates a reproducible hash that can be used to verify that
    the same dataset was used across runs.

    Args:
        questions_path: Path to questions.json
        responses_path: Path to responses.csv
        scope_path: Optional path to scope.md

    Returns:
        SHA-256 hash of the combined file contents
    """
    sha256 = hashlib.sha256()

    # Hash questions file
    with open(questions_path, "rb") as f:
        sha256.update(f.read())

    # Hash responses file
    with open(responses_path, "rb") as f:
        sha256.update(f.read())

    # Hash scope file if provided
    if scope_path and scope_path.exists():
        with open(scope_path, "rb") as f:
            sha256.update(f.read())

    return sha256.hexdigest()


def hash_string(content: str) -> str:
    """Compute SHA-256 hash of a string."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
