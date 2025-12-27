# DD Analytics Agent - Validation Suite

This directory contains the automated validation tools for the DD Analytics Agent. These tools are used to verify the performance and accuracy of various agent components against "Golden Data" (ground truth).

## 📂 Directory Structure

- `golden_data/`: Contains the JSON ground-truth files for each component.
- `validate_all.py`: The master script that runs all 176+ test cases across all components.
- `validate_cut_planning.py`: Validates the `CutPlanner` (NL -> CutSpec).
- `validate_segment_builder.py`: Validates the `SegmentBuilder` (NL -> SegmentSpec).
- `validate_high_level_planner.py`: Validates the `HighLevelPlanner` across multiple business scenarios.
- `validate_e2e.py`: Validates the full `Pipeline` orchestration.

## 🚀 How to Run

You can run the comprehensive validation suite from the project root using `uv`:

```bash
# Run everything
uv run validation/validate_all.py

# Run individual components
uv run validation/validate_cut_planning.py
uv run validation/validate_segment_builder.py
uv run validation/validate_e2e.py
```

## 📊 Key Metrics

The validation suite checks for:
1.  **Planning Accuracy**: Does the LLM understand the user's intent?
2.  **Domain Correctness**: Are the correct Question IDs and Metric types selected?
3.  **Execution Precision**: Does the code produce the exact same `Base N` (respondent count) as the golden data?
4.  **Strategic Alignment**: Does the High-Level Planner identify the key research objectives described in the project scope?

---
*Note: These tests require access to the LLM (Azure OpenAI) as they test the agentic reasoning layers.*
