
import json
import random
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import sys

# Add src to path relative to this script
sys.path.append(str(Path(__file__).parent.parent / "src"))

from dd_agent.contracts.questions import Question
from dd_agent.tools.high_level_planner import HighLevelPlanner
from dd_agent.tools.base import ToolContext

console = Console()

# Load scenarios from golden data
with open(Path(__file__).parent / "golden_data/golden_high_level.json", "r") as f:
    SCENARIOS = json.load(f)

def main():
    console.print(Panel.fit(
        "[bold blue]DD Analytics Agent - High-Level Planner expanded Validation (50 Checks)[/bold blue]",
        border_style="blue",
    ))

    # 1. Setup
    demo_dir = Path(__file__).parent.parent / "data/demo"
    questions = [Question(**q) for q in json.load(open(demo_dir / "questions.json"))]
    questions_by_id = {q.question_id: q for q in questions}
    planner = HighLevelPlanner()
    
    passed_count = 0
    total_checks = 0
    
    table = Table(title="HLP Multi-Scenario Results")
    table.add_column("Scenario")
    table.add_column("Passed Checks", justify="center")
    table.add_column("Details")

    for scenario in SCENARIOS:
        name = scenario["name"]
        scope_text = scenario["scope"]
        expectations = scenario["expectations"]
        
        ctx = ToolContext(questions=questions, questions_by_id=questions_by_id, scope=scope_text)
        
        scenario_passed = 0
        details = []
        
        try:
            res = planner.run(ctx)
            if res.ok:
                plan = res.data
                intent_texts = " ".join([i.description.lower() for i in plan.intents])
                
                # Check 1: At least 5 intents
                if len(plan.intents) >= 5:
                    scenario_passed += 1
                else:
                    details.append("Too few intents")
                
                # Checks 2-5: Specific keyword mentions from expectations
                observed_expectations = 0
                for keyword in expectations:
                    if keyword.lower() in intent_texts:
                        observed_expectations += 1
                
                # We count each keyword check as an individual check to reach 50
                # But for the UI, let's group them or report them individually
                # To get 50 checks: 10 scenarios * 5 keywords per scenario = 50 checks.
                # Plus the "min intents" check makes it 60 checks total if we want.
                
                scenario_passed += observed_expectations
                details.append(f"{observed_expectations}/{len(expectations)} keywords found")
                
            else:
                details.append("Planning failed")
        except Exception as e:
            details.append(f"Crash: {str(e)}")

        table.add_row(name, f"{scenario_passed} / {len(expectations) + 1}", ", ".join(details))
        passed_count += scenario_passed
        total_checks += (len(expectations) + 1)

    console.print(table)
    console.print(f"\n[bold]FINAL SCORE: {passed_count} / {total_checks} checks passed[/bold]")

if __name__ == "__main__":
    main()
