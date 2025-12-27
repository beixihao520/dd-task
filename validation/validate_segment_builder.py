
import json
import random
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Any
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import sys
from pathlib import Path
# Add src to path relative to this script
sys.path.append(str(Path(__file__).parent.parent / "src"))

from dd_agent.engine.executor import Executor
from dd_agent.contracts.questions import Question, QuestionType
from dd_agent.contracts.specs import SegmentSpec
from dd_agent.tools.segment_builder import SegmentBuilder
from dd_agent.tools.base import ToolContext
from dd_agent.engine.masks import build_mask

# --- REPRODUCIBILITY ---
RANDOM_SEED = 42
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

console = Console()

def main():
    console.print(Panel.fit(
        "[bold blue]DD Analytics Agent - Segment Builder Validation[/bold blue]",
        border_style="blue",
    ))

    # 1. Setup
    demo_dir = Path(__file__).parent.parent / "data/demo"
    questions = [Question(**q) for q in json.load(open(demo_dir / "questions.json"))]
    questions_by_id = {q.question_id: q for q in questions}
    df = generate_dummy_data(questions)
    
    builder = SegmentBuilder()
    
    # 2. Load Golden Rules
    # 2. Load Golden Rules
    with open(Path(__file__).parent / "golden_data/golden_segments.json", "r") as f:
        golden_cases = json.load(f)

    passed_count = 0
    table = Table(title="Segment Builder Results")
    table.add_column("Prompt", ratio=2)
    table.add_column("Status")
    table.add_column("Details", ratio=3)

    for case in golden_cases:
        prompt = case["prompt"]
        expected_ok = case["expected_ok"]
        expected_base_n = case.get("expected_base_n")
        
        ctx = ToolContext(questions=questions, questions_by_id=questions_by_id, prompt=prompt, responses_df=df)
        
        status = "FAIL"
        reason = ""
        try:
            res = builder.run(ctx)
            if res.ok != expected_ok:
                reason = f"Outcome mismatch (Expected OK: {expected_ok}, Got: {res.ok})"
            elif not res.ok:
                status = "PASS"
            else:
                # Execution check
                mask = build_mask(df, res.data.definition, questions_by_id)
                actual_base_n = int(mask.sum())
                if actual_base_n != expected_base_n:
                    reason = f"Data mismatch (Base N: {actual_base_n}, Expected: {expected_base_n})"
                else:
                    status = "PASS"
        except NotImplementedError:
            status = "CRASH"
            reason = "Not implemented"
        except Exception as e:
            status = "CRASH"
            reason = str(e)

        if status == "PASS":
            passed_count += 1
            table.add_row(prompt, "[green]PASS[/green]", "")
        else:
            table.add_row(prompt, f"[red]{status}[/red]", reason)

    console.print(table)
    console.print(f"\n[bold]FINAL SCORE: {passed_count} / {len(golden_cases)} passed[/bold]")

if __name__ == "__main__":
    main()
