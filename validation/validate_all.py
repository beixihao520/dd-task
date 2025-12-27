
import json
import random
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add src to path relative to this script
sys.path.append(str(Path(__file__).parent.parent / "src"))

from dd_agent.contracts.questions import Question, QuestionType
from dd_agent.contracts.specs import CutSpec, SegmentSpec, HighLevelPlan
from dd_agent.engine.executor import Executor
from dd_agent.engine.masks import build_mask
from dd_agent.orchestrator.pipeline import Pipeline
from dd_agent.tools.base import ToolContext
from dd_agent.tools.cut_planner import CutPlanner
from dd_agent.tools.high_level_planner import HighLevelPlanner
from dd_agent.tools.segment_builder import SegmentBuilder

# --- CONSTANTS & SETUP ---
RANDOM_SEED = 42
console = Console()

def set_seed(seed=RANDOM_SEED):
    random.seed(seed)
    np.random.seed(seed)

def generate_dummy_data(questions: list[Question], n_rows=100) -> pd.DataFrame:
    set_seed()
    data = []
    for i in range(n_rows):
        row: dict[str, Any] = {}
        for q in questions:
            if q.type == QuestionType.numeric:
                if q.question_id == "Q_RESP_ID": row[q.effective_column_name] = i + 1
                elif q.question_id == "Q_AGE": row[q.effective_column_name] = random.randint(18, 90)
                else: row[q.effective_column_name] = random.randint(0, 100)
            elif q.options:
                codes = [opt.code for opt in q.options]
                if q.type == QuestionType.multi_choice:
                    k = random.randint(1, min(3, len(codes))); selected = random.sample(codes, k)
                    row[q.effective_column_name] = ";".join(str(c) for c in selected)
                else: row[q.effective_column_name] = random.choice(codes)
            elif q.type == QuestionType.nps_0_10: row[q.effective_column_name] = random.randint(0, 10)
            else: row[q.effective_column_name] = None
        data.append(row)
    return pd.DataFrame(data)

def run_cut_planning_tests(questions, questions_by_id, df, planner, executor):
    with open(Path(__file__).parent / "golden_data/golden_validation.json", "r") as f:
        cases = json.load(f)
    
    passed = 0
    results = []
    
    for case in cases:
        prompt = case["prompt"]
        expected_ok = case["expected_ok"]
        expected_plan = case.get("expected_plan")
        expected_res = case.get("expected_results")
        
        ctx = ToolContext(questions=questions, questions_by_id=questions_by_id, prompt=prompt, responses_df=df)
        status, reason = "FAIL", ""
        
        try:
            res = planner.run(ctx)
            if res.ok != expected_ok:
                reason = f"Outcome mismatch (Expected OK: {expected_ok}, Got: {res.ok})"
            elif not res.ok:
                status = "PASS"
            else:
                cut_spec = res.data
                plan_match = (
                    cut_spec.metric.type == expected_plan["metric_type"] and
                    cut_spec.metric.question_id == expected_plan["question_id"]
                )
                if not plan_match:
                    reason = f"Plan mismatch (Got {cut_spec.metric.type} on {cut_spec.metric.question_id})"
                else:
                    exec_res = executor.execute_cuts([cut_spec])
                    if exec_res.errors:
                        reason = f"Execution error: {exec_res.errors[0]['error']}"
                    else:
                        table_res = exec_res.tables[0]
                        if table_res.base_n != expected_res["base_n"]:
                            reason = f"Data mismatch (Base N: {table_res.base_n}, Expected: {expected_res['base_n']})"
                        else:
                            status = "PASS"
        except NotImplementedError:
            status, reason = "CRASH", "Not implemented"
        except Exception as e:
            status, reason = "CRASH", str(e)
            
        if status == "PASS": passed += 1
        results.append((prompt, status, reason))
        
    return passed, len(cases), results

def run_segment_builder_tests(questions, questions_by_id, df, builder):
    with open(Path(__file__).parent / "golden_data/golden_segments.json", "r") as f:
        cases = json.load(f)
        
    passed = 0
    results = []
    
    for case in cases:
        prompt = case["prompt"]
        expected_ok = case["expected_ok"]
        expected_base_n = case.get("expected_base_n")
        
        ctx = ToolContext(questions=questions, questions_by_id=questions_by_id, prompt=prompt, responses_df=df)
        status, reason = "FAIL", ""
        
        try:
            res = builder.run(ctx)
            if res.ok != expected_ok:
                reason = f"Outcome mismatch (Expected OK: {expected_ok}, Got: {res.ok})"
            elif not res.ok:
                status = "PASS"
            else:
                mask = build_mask(df, res.data.definition, questions_by_id)
                actual_base_n = int(mask.sum())
                if actual_base_n != expected_base_n:
                    reason = f"Data mismatch (Base N: {actual_base_n}, Expected: {expected_base_n})"
                else:
                    status = "PASS"
        except NotImplementedError:
            status, reason = "CRASH", "Not implemented"
        except Exception as e:
            status, reason = "CRASH", str(e)
            
        if status == "PASS": passed += 1
        results.append((prompt, status, reason))
        
    return passed, len(cases), results

def run_hlp_tests(questions, questions_by_id, planner):
    # Load scenarios from golden data
    with open(Path(__file__).parent / "golden_data/golden_high_level.json", "r") as f:
        SCENARIOS = json.load(f)
    
    passed_checks = 0
    total_checks = 0
    results = []
    
    for sc in SCENARIOS:
        ctx = ToolContext(questions=questions, questions_by_id=questions_by_id, scope=sc["scope"])
        sc_passed = 0
        details = []
        try:
            res = planner.run(ctx)
            if res.ok:
                plan = res.data
                intent_texts = " ".join([i.description.lower() for i in plan.intents])
                if len(plan.intents) >= 5: sc_passed += 1
                else: details.append("Low intent count")
                
                obs = 0
                for k in sc["expectations"]:
                    if k.lower() in intent_texts: obs += 1
                sc_passed += obs
                details.append(f"{obs}/{len(sc['expectations'])} keywords")
            else:
                details.append("Planning failed")
        except NotImplementedError: details.append("Not implemented")
        except Exception as e: details.append(str(e))
        
        results.append((sc["name"], sc_passed, len(sc["expectations"]) + 1, ", ".join(details)))
        passed_checks += sc_passed
        total_checks += (len(sc["expectations"]) + 1)
        
    return passed_checks, total_checks, results

def run_e2e_tests():
    demo_dir = Path(__file__).parent.parent / "data/demo"
    pipeline = Pipeline(data_dir=demo_dir)
    
    test_prompts = [
        "Show average age by income",
        "Performance of NPS by region",
        "Top 2 box for support satisfaction by plan",
        "Frequency of gender for Daily users",
        "Bottom 2 box for ease of use by tenure",
        "Mean satisfaction for Enterprise customers in the West",
        "NPS distribution for high income respondents",
        "Top 2 box for value for money by product usage frequency",
        "Average purchase intent for new customers",
        "Compare NPS between promoters and detractors"
    ]
    
    passed = 0
    results = []
    
    for prompt in test_prompts:
        try:
            result = pipeline.run_single(prompt, save_run=False)
            if result.success and result.execution_result:
                status, details = "PASS", f"Base N: {result.execution_result.tables[0].base_n}"
            else:
                status, details = "FAIL", ", ".join(result.errors) if result.errors else "Failure"
        except NotImplementedError: status, details = "CRASH", "Not implemented"
        except Exception as e: status, details = "CRASH", str(e)
        if status == "PASS": passed += 1
        results.append((f"single: {prompt}", status, details))
        
    # Autoplan
    try:
        res = pipeline.run_autoplan(save_run=False)
        if res.success:
            status, details = "PASS", f"Cuts: {len(res.cuts_planned)}"
        else:
            status, details = "FAIL", "Autoplan failed"
    except NotImplementedError: status, details = "CRASH", "Not implemented"
    except Exception as e: status, details = "CRASH", str(e)
    if status == "PASS": passed += 1
    results.append(("autoplan", status, details))
    
    return passed, len(test_prompts) + 1, results

def run_engine_stress_tests(questions, questions_by_id, df):
    sys.path.append(str(Path(__file__).parent))
    import validate_engine
    
    segments_by_id = {
        "SEG_YOUNG": SegmentSpec(segment_id="SEG_YOUNG", name="Young Respondents", definition={"kind": "range", "question_id": "Q_AGE", "min": 18, "max": 35}),
        "SEG_HIGH_INCOME": SegmentSpec(segment_id="SEG_HIGH_INCOME", name="High Income", definition={"kind": "in", "question_id": "Q_INCOME", "values": ["HIGH", "VHIGH"]}),
        "SEG_MALE_NORTH": SegmentSpec(segment_id="SEG_MALE_NORTH", name="Males in the North", definition={"kind": "and", "children": [{"kind": "eq", "question_id": "Q_GENDER", "value": "M"}, {"kind": "eq", "question_id": "Q_REGION", "value": "NORTH"}]}),
        "SEG_TECH_ACTIVE": SegmentSpec(segment_id="SEG_TECH_ACTIVE", name="Active Tech Users", definition={"kind": "contains_any", "question_id": "Q_FEATURES_USED", "values": ["API", "MOBILE"]}),
        "SEG_NOT_LOW_INCOME": SegmentSpec(segment_id="SEG_NOT_LOW_INCOME", name="Excluded Low Income", definition={"kind": "not", "child": {"kind": "eq", "question_id": "Q_INCOME", "value": "LOW"}}),
        "SEG_OR_CONDITION": SegmentSpec(segment_id="SEG_OR_CONDITION", name="Young OR High Income", definition={"kind": "or", "children": [{"kind": "range", "question_id": "Q_AGE", "min": 18, "max": 25}, {"kind": "in", "question_id": "Q_INCOME", "values": ["VHIGH"]}]})
    }
    
    executor = Executor(df, questions_by_id, segments_by_id=segments_by_id)
    cuts = []
    dim_candidates = [q.question_id for q in questions if q.type == QuestionType.single_choice and q.question_id != "Q_RESP_ID"]
    
    cut_counter = 0
    for q in questions:
        metrics = validate_engine.get_valid_metrics(q)
        for m in metrics:
            cut_counter += 1
            cuts.append(CutSpec(cut_id=f"STRESS_{cut_counter}_{q.question_id}_{m}", metric={"type": m, "question_id": q.question_id}))
            dimension_id = dim_candidates[cut_counter % len(dim_candidates)]
            if dimension_id != q.question_id:
                cuts.append(CutSpec(cut_id=f"STRESS_{cut_counter}_{q.question_id}_{m}_BY_{dimension_id}", metric={"type": m, "question_id": q.question_id}, dimensions=[{"kind": "question", "id": dimension_id}]))
            
            # Segment & Filtered (Comprehensive matches)
            segment_id = list(segments_by_id.keys())[cut_counter % len(segments_by_id)]
            cuts.append(CutSpec(cut_id=f"STRESS_{cut_counter}_{q.question_id}_{m}_BY_{segment_id}", metric={"type": m, "question_id": q.question_id}, dimensions=[{"kind": "segment", "id": segment_id}]))
            filter_seg_id = list(segments_by_id.keys())[(cut_counter + 1) % len(segments_by_id)]
            cuts.append(CutSpec(cut_id=f"STRESS_{cut_counter}_{q.question_id}_{m}_FILTERED_{filter_seg_id}", metric={"type": m, "question_id": q.question_id}, filter=segments_by_id[filter_seg_id].definition))

    result = executor.execute_cuts(cuts)
    golden_map = validate_engine.load_golden_data()
    
    passed = 0
    total_comparisons = 0
    results = []
    
    for t in result.tables:
        cut_spec = next((c for c in cuts if c.cut_id == t.cut_id), None)
        if cut_spec:
            dim_ids = tuple(sorted([d.id for d in cut_spec.dimensions]))
            key = (t.metric_type, t.question_id, dim_ids)
            if key in golden_map:
                best_match = validate_engine.find_best_golden_match(cut_spec, t, golden_map[key])
                if best_match:
                    total_comparisons += 1
                    expected = best_match["expected_results"]
                    base_match = (t.base_n == expected["base_n"])
                    actual_val = validate_engine.get_primary_value(t)
                    expected_val = expected["primary_value"]
                    val_match = True
                    if expected_val is not None:
                        if actual_val is None: val_match = False
                        else: val_match = abs(actual_val - expected_val) < 0.01
                    
                    if base_match and val_match:
                        passed += 1
                        results.append((f"stress: {key}", "PASS", ""))
                    else:
                        results.append((f"stress: {key}", "FAIL", f"Base: {t.base_n} vs {expected['base_n']}, Val: {actual_val} vs {expected_val}"))
    
    return passed, total_comparisons, results

def main():
    console.print(Panel(
        "[bold blue]DD Analytics Agent: COMPREHENSIVE VALIDATION SUITE[/bold blue]\n"
        "Executing all tool and integration tests...",
        border_style="blue",
    ))

    # General Setup
    demo_dir = Path(__file__).parent.parent / "data/demo"
    questions = [Question(**q) for q in json.load(open(demo_dir / "questions.json"))]
    questions_by_id = {q.question_id: q for q in questions}
    df = generate_dummy_data(questions)
    
    cut_p = CutPlanner()
    seg_b = SegmentBuilder()
    hlp_p = HighLevelPlanner()
    exec_e = Executor(df, questions_by_id)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        t1 = progress.add_task("[cyan]Testing Cut Planner...", total=1)
        cp_score, cp_total, cp_details = run_cut_planning_tests(questions, questions_by_id, df, cut_p, exec_e)
        progress.update(t1, advance=1)
        
        t2 = progress.add_task("[magenta]Testing Segment Builder...", total=1)
        sb_score, sb_total, sb_details = run_segment_builder_tests(questions, questions_by_id, df, seg_b)
        progress.update(t2, advance=1)
        
        t3 = progress.add_task("[green]Testing High-Level Planner...", total=1)
        hlp_score, hlp_total, hlp_details = run_hlp_tests(questions, questions_by_id, hlp_p)
        progress.update(t3, advance=1)
        
        t4 = progress.add_task("[yellow]Testing E2E Pipeline...", total=1)
        e2e_score, e2e_total, e2e_details = run_e2e_tests()
        progress.update(t4, advance=1)

        t5 = progress.add_task("[blue]Testing Execution Engine Stress...", total=1)
        ee_score, ee_total, ee_details = run_engine_stress_tests(questions, questions_by_id, df)
        progress.update(t5, advance=1)

    # Output detailed tables
    # 1. Cut Planner & Segment Builder (Summarized top 5 failures)
    def print_failures(title, details):
        fails = [d for d in details if d[1] != "PASS"]
        if fails:
            t = Table(title=f"{title} - Top Failures", border_style="red")
            t.add_column("Prompt")
            t.add_column("Status")
            t.add_column("Reason")
            for f in fails[:10]:
                t.add_row(f[0], f[1], f[2])
            console.print(t)

    print_failures("Cut Planner", cp_details)
    print_failures("Segment Builder", sb_details)

    # 2. HLP Scenario Table
    hlp_table = Table(title="High-Level Planner Scenarios")
    hlp_table.add_column("Scenario")
    hlp_table.add_column("Score")
    hlp_table.add_column("Details")
    for row in hlp_details:
        hlp_table.add_row(row[0], f"{row[1]}/{row[2]}", row[3])
    console.print(hlp_table)

    # 3. E2E Summary
    e2e_table = Table(title="E2E Pipeline Results")
    e2e_table.add_column("Feature")
    e2e_table.add_column("Status")
    e2e_table.add_column("Result")
    for row in e2e_details:
        color = "green" if row[1] == "PASS" else "red"
        e2e_table.add_row(row[0], f"[{color}]{row[1]}[/]", row[2])
    console.print(e2e_table)

    # FINAL REPORT PANEL
    summary = (
        f"[bold cyan]Cut Planning:[/] {cp_score} / {cp_total} passed\n"
        f"[bold magenta]Segment Builder:[/] {sb_score} / {sb_total} passed\n"
        f"[bold blue]Execution Engine:[/] {ee_score} / {ee_total} passed\n"
        f"[bold green]Strategic Planning:[/] {hlp_score} / {hlp_total} passed\n"
        f"[bold yellow]E2E Integration:[/] {e2e_score} / {e2e_total} passed\n"
    )
    
    overall_total = cp_total + sb_total + hlp_total + e2e_total + ee_total
    overall_passed = cp_score + sb_score + hlp_score + e2e_score + ee_score
    pct = (overall_passed / overall_total) * 100
    
    console.print(Panel(
        summary + f"\n[bold white]OVERALL ACCURACY: {pct:.1f}% ({overall_passed} / {overall_total})[/bold white]",
        title="[bold green]FINAL VALIDATION SUMMARY[/bold green]",
        border_style="green",
        expand=False
    ))

if __name__ == "__main__":
    main()
