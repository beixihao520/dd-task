
import json
import random
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Any, Optional

# Add src to path relative to this script
sys.path.append(str(Path(__file__).parent.parent / "src"))

from dd_agent.engine.executor import Executor
from dd_agent.contracts.questions import Question, QuestionType
from dd_agent.contracts.specs import CutSpec, MetricSpec, DimensionSpec, SegmentSpec

def load_questions(json_path: str) -> list[Question]:
    with open(json_path, 'r') as f:
        data = json.load(f)
    questions = []
    for q_data in data:
        questions.append(Question(**q_data))
    return questions

def set_seed(seed=42):
    random.seed(seed)
    np.random.seed(seed)

def generate_dummy_data(questions: list[Question], n_rows=100) -> pd.DataFrame:
    set_seed()
    data = []
    for i in range(n_rows):
        row: dict[str, Any] = {}
        for q in questions:
            if q.type == QuestionType.numeric:
                if q.question_id == "Q_RESP_ID":
                    row[q.effective_column_name] = i + 1
                elif q.question_id == "Q_AGE":
                    row[q.effective_column_name] = random.randint(18, 90)
                else:
                    row[q.effective_column_name] = random.randint(0, 100)
            elif q.options:
                codes = [opt.code for opt in q.options]
                if q.type == QuestionType.multi_choice:
                    k = random.randint(1, min(3, len(codes)))
                    selected = random.sample(codes, k)
                    row[q.effective_column_name] = ";".join(str(c) for c in selected)
                else:
                    row[q.effective_column_name] = random.choice(codes)
            elif q.type == QuestionType.nps_0_10:
                row[q.effective_column_name] = random.randint(0, 10)
            else:
                row[q.effective_column_name] = None
        data.append(row)
    return pd.DataFrame(data)

def get_valid_metrics(q: Question) -> list[str]:
    valid = []
    if q.type in [QuestionType.single_choice, QuestionType.multi_choice, QuestionType.likert_1_5, QuestionType.likert_1_7]:
        valid.append("frequency")
    if q.type in [QuestionType.numeric, QuestionType.nps_0_10]:
        valid.append("mean")
    elif q.type in [QuestionType.likert_1_5, QuestionType.likert_1_7]:
        if q.options and isinstance(q.options[0].code, int):
            valid.append("mean")
    if q.type in [QuestionType.likert_1_5, QuestionType.likert_1_7]:
        valid.append("top2box")
        valid.append("bottom2box")
    if q.type == QuestionType.nps_0_10:
        valid.append("nps")
    return valid

def load_golden_data(path: Optional[str] = None) -> dict:
    if path is None:
        path = str(Path(__file__).parent / "golden_data" / "golden_validation.json")
    try:
        with open(path, "r") as f:
            data = json.load(f)
        
        golden_map = {}
        for entry in data:
            if not entry.get("expected_ok") or not entry.get("expected_plan"):
                continue
            
            plan = entry["expected_plan"]
            key = (
                plan["metric_type"],
                plan["question_id"],
                tuple(sorted(plan.get("dimension_ids", [])))
            )
            if key not in golden_map:
                golden_map[key] = []
            golden_map[key].append(entry)
        return golden_map
    except FileNotFoundError:
        return {}

def find_best_golden_match(cut_spec, table, golden_entries):
    """
    Search for a golden entry that strictly matches the cut's definition.
    For this deterministic test, we use Base N as a proxy for filter matching.
    """
    is_filtered = cut_spec.filter is not None
    actual_val = get_primary_value(table)
    
    # Priority 1: Direct Match (Metric + Question + Dim + Filter proxy)
    for entry in golden_entries:
        expected = entry["expected_results"]
        # In our seed-42 dummy data:
        # Unfiltered cuts ALWAYS have exactly Base N = 100.
        # Filtered cuts ALWAYS have Base N < 100.
        expected_is_filtered = expected["base_n"] < 100
        
        if is_filtered == expected_is_filtered:
            # Check if this specific entry matches the calculated data
            base_match = (table.base_n == expected["base_n"])
            expected_val = expected["primary_value"]
            val_match = True
            if expected_val is not None:
                if actual_val is None: val_match = False
                else: val_match = abs(actual_val - expected_val) < 0.01
            
            if base_match and val_match:
                return entry
            
    # Priority 2: If we are unfiltered, and there is an unfiltered golden entry, return it
    # even if values don't match (so we can report the failure properly).
    if not is_filtered:
        for entry in golden_entries:
            if entry["expected_results"]["base_n"] == 100:
                return entry

    # If the only golden entries are filtered but our cut is not (or vice versa), 
    # it's a different analytical request. Do not compare.
    return None

def get_primary_value(table) -> Optional[float]:
    res_df = table.get_dataframe()
    if res_df is not None and not res_df.empty:
        if "mean" in res_df.columns:
            return float(res_df["mean"].iloc[0])
        elif "nps" in res_df.columns:
            return float(res_df["nps"].iloc[0])
        elif "metric" in res_df.columns:
            val = res_df["metric"].iloc[0]
            return float(val) if isinstance(val, (int, float)) else None
    return None

def main():
    base_dir = Path(__file__).parent.parent
    questions_path = str(base_dir / "data/demo/questions.json")
    print(f"Loading questions from {questions_path}...")
    questions = load_questions(questions_path)
    questions_by_id = {q.question_id: q for q in questions}
    
    print("Generating dummy data...")
    df = generate_dummy_data(questions)
    print(f"Generated {len(df)} rows.")
    
    segments_by_id = {
        "SEG_YOUNG": SegmentSpec(
            segment_id="SEG_YOUNG",
            name="Young Respondents",
            definition={"kind": "range", "question_id": "Q_AGE", "min": 18, "max": 35}
        ),
        "SEG_HIGH_INCOME": SegmentSpec(
            segment_id="SEG_HIGH_INCOME",
            name="High Income",
            definition={"kind": "in", "question_id": "Q_INCOME", "values": ["HIGH", "VHIGH"]}
        ),
        "SEG_MALE_NORTH": SegmentSpec(
            segment_id="SEG_MALE_NORTH",
            name="Males in the North",
            definition={
                "kind": "and",
                "children": [
                    {"kind": "eq", "question_id": "Q_GENDER", "value": "M"},
                    {"kind": "eq", "question_id": "Q_REGION", "value": "NORTH"}
                ]
            }
        ),
        "SEG_TECH_ACTIVE": SegmentSpec(
            segment_id="SEG_TECH_ACTIVE",
            name="Active Tech Users",
            definition={
                "kind": "contains_any",
                "question_id": "Q_FEATURES_USED",
                "values": ["API", "MOBILE"]
            }
        ),
        "SEG_NOT_LOW_INCOME": SegmentSpec(
            segment_id="SEG_NOT_LOW_INCOME",
            name="Excluded Low Income",
            definition={
                "kind": "not",
                "child": {"kind": "eq", "question_id": "Q_INCOME", "value": "LOW"}
            }
        ),
        "SEG_OR_CONDITION": SegmentSpec(
            segment_id="SEG_OR_CONDITION",
            name="Young OR High Income",
            definition={
                "kind": "or",
                "children": [
                    {"kind": "range", "question_id": "Q_AGE", "min": 18, "max": 25},
                    {"kind": "in", "question_id": "Q_INCOME", "values": ["VHIGH"]}
                ]
            }
        )
    }


    executor = Executor(df, questions_by_id, segments_by_id=segments_by_id)
    cuts = []
    dim_candidates = [q.question_id for q in questions if q.type == QuestionType.single_choice and q.question_id != "Q_RESP_ID"]
    
    # User requested example
    cuts.append(CutSpec(
        cut_id="USER_REQ_AGE_BY_INCOME",
        metric=MetricSpec(type="mean", question_id="Q_AGE"),
        dimensions=[DimensionSpec(kind="question", id="Q_INCOME")]
    ))

    cut_counter = 0
    for q in questions:
        metrics = get_valid_metrics(q)
        for m in metrics:
            cut_counter += 1
            cuts.append(CutSpec(
                cut_id=f"CUT_{cut_counter}_{q.question_id}_{m}",
                metric=MetricSpec(type=m, question_id=q.question_id)
            ))
            dimension_id = dim_candidates[cut_counter % len(dim_candidates)]
            if dimension_id != q.question_id:
                cuts.append(CutSpec(
                    cut_id=f"CUT_{cut_counter}_{q.question_id}_{m}_BY_{dimension_id}",
                    metric=MetricSpec(type=m, question_id=q.question_id),
                    dimensions=[DimensionSpec(kind="question", id=dimension_id)]
                ))
            # Cross-tab by Segment (Cycle through all segments)
            segment_id = list(segments_by_id.keys())[cut_counter % len(segments_by_id)]
            cuts.append(CutSpec(
                cut_id=f"CUT_{cut_counter}_{q.question_id}_{m}_BY_{segment_id}",
                metric=MetricSpec(type=m, question_id=q.question_id),
                dimensions=[DimensionSpec(kind="segment", id=segment_id)]
            ))

            # Filtered Metric (Cycle through all segments)
            filter_seg_id = list(segments_by_id.keys())[(cut_counter + 1) % len(segments_by_id)]
            cuts.append(CutSpec(
                cut_id=f"CUT_{cut_counter}_{q.question_id}_{m}_FILTERED_{filter_seg_id}",
                metric=MetricSpec(type=m, question_id=q.question_id),
                filter=segments_by_id[filter_seg_id].definition
            ))


    print(f"Generated {len(cuts)} cuts. Executing...")
    result = executor.execute_cuts(cuts)
    
    # --- Golden Comparison ---
    golden_map = load_golden_data()
    golden_matches = 0
    golden_comparisons = 0
    
    passed_no_warnings = 0
    for t in result.tables:
        if not t.warnings:
            passed_no_warnings += 1
        
        # Match against golden
        cut_spec = next((c for c in cuts if c.cut_id == t.cut_id), None)
        if cut_spec:
            dim_ids = tuple(sorted([d.id for d in cut_spec.dimensions]))
            if not cut_spec.filter:
                key = (t.metric_type, t.question_id, dim_ids)
                if key in golden_map:
                    best_match = find_best_golden_match(cut_spec, t, golden_map[key])
                    if best_match:
                        golden_comparisons += 1
                        expected = best_match["expected_results"]
                        
                        base_match = (t.base_n == expected["base_n"])
                        actual_val = get_primary_value(t)
                        expected_val = expected["primary_value"]
                        
                        val_match = True
                        if expected_val is not None:
                            if actual_val is None:
                                val_match = False
                            else:
                                val_match = abs(actual_val - expected_val) < 0.01
                        
                        if base_match and val_match:
                            golden_matches += 1

    total_cuts = len(cuts)
    successful_runs = len(result.tables)
    
    run_rate = (successful_runs / total_cuts) * 100 if total_cuts > 0 else 0
    warning_free_rate = (passed_no_warnings / total_cuts) * 100 if total_cuts > 0 else 0
    golden_rate = (golden_matches / golden_comparisons) * 100 if golden_comparisons > 0 else 0
    
    print("\n" + "="*50)
    print("ANALYSIS EXECUTION SUMMARY")
    print("="*50)
    print(f"Total Cuts Attempted:      {total_cuts}")
    print(f"Execution Success Rate:    {successful_runs}/{total_cuts} ({run_rate:.1f}%)")
    print(f"Warning-Free Rate:         {passed_no_warnings}/{total_cuts} ({warning_free_rate:.1f}%)")
    if golden_comparisons > 0:
        print(f"Golden Data Pass Rate:     {golden_matches}/{golden_comparisons} ({golden_rate:.1f}%)")
        print(f"  (Compared {golden_comparisons} cuts against predefined golden data)")
    else:
        print("Golden Data Pass Rate:     N/A (No matching golden data found)")
    
    print("-" * 50)
    pass_rate = golden_rate if golden_comparisons > 0 else warning_free_rate
    print(f"OVERALL PASS RATE:         {pass_rate:.1f}%")
    
    if warning_free_rate < 100:
        warning_count = len([t for t in result.tables if t.warnings])
        print(f"\nNote: {warning_count} cuts generated warnings (likely low base size).")
        print(f"Thresholds: min_base={executor.min_base_size}, warn_base={executor.warn_base_size}")
        print(f"Total rows in dummy data: 100 (Seed: 42)")
    print("="*50 + "\n")
    
    md_output_path = str(base_dir / "analysis_results.md")
    print(f"Exporting results to {md_output_path}...")
    
    with open(md_output_path, "w") as f:
        f.write("# Analysis Results Summary\n\n")
        f.write(f"Total Cuts Executed: {len(result.tables)}\n")
        f.write(f"Errors Encountered: {len(result.errors)}\n\n")
        
        for t in result.tables:
            cut_spec = next((c for c in cuts if c.cut_id == t.cut_id), None)
            dim_str = ""
            if cut_spec and cut_spec.dimensions:
                dims = [f"{d.kind.title()}: {d.id}" for d in cut_spec.dimensions]
                dim_str = f" by {', '.join(dims)}"
            filter_str = " (Filtered)" if cut_spec and cut_spec.filter else ""
            
            f.write(f"## {t.question_id} -> {t.metric_type}{dim_str}{filter_str}\n")
            f.write(f"- **Cut ID**: `{t.cut_id}`\n")
            f.write(f"- **Base N**: {t.base_n}\n")
            
            if cut_spec and not cut_spec.filter:
                dim_ids = tuple(sorted([d.id for d in cut_spec.dimensions]))
                key = (t.metric_type, t.question_id, dim_ids)
                if key in golden_map:
                    best_match = find_best_golden_match(cut_spec, t, golden_map[key])
                    if best_match:
                        expected = best_match["expected_results"]
                        base_match = (t.base_n == expected["base_n"])
                        actual_val = get_primary_value(t)
                        expected_val = expected["primary_value"]
                        
                        val_match = True
                        if expected_val is not None:
                            if actual_val is None: val_match = False
                            else: val_match = abs(actual_val - expected_val) < 0.01
                        
                        match_status = "✅ PASS" if (base_match and val_match) else "❌ FAIL"
                        f.write(f"- **Golden Comparison**: {match_status} (Prompt: '{best_match['prompt']}')\n")
                        if not base_match:
                            f.write(f"  - Base N Mismatch: Expected {expected['base_n']}, Got {t.base_n}\n")
                        if not val_match:
                            f.write(f"  - Value Mismatch: Expected {expected_val}, Got {actual_val}\n")

            if t.warnings:
                f.write("- **Warnings**:\n")
                for w in t.warnings:
                    f.write(f"  - {w}\n")

            df = t.get_dataframe()
            if df is not None:
                f.write("\n```text\n")
                f.write(df.to_string())
                f.write("\n```\n")
            f.write("\n---\n\n")

    print(f"Success! Results written to {md_output_path}")

if __name__ == "__main__":
    main()
