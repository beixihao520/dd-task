
import sys
from pathlib import Path
import json
import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add src to path relative to this script
sys.path.append(str(Path(__file__).parent.parent / "src"))

from dd_agent.orchestrator.pipeline import Pipeline
from dd_agent.contracts.specs import CutSpec

console = Console()

def main():
    console.print(Panel.fit(
        "[bold blue]DD Analytics Agent - E2E Validation Suite[/bold blue]\n"
        "Testing full pipeline logic (run_single and run_autoplan)",
        border_style="blue",
    ))

    demo_dir = Path(__file__).parent.parent / "data/demo"
    if not demo_dir.exists():
        console.print("[red]❌ Demo data not found at data/demo/[/red]")
        return

    pipeline = Pipeline(data_dir=demo_dir)
    
    # 1. Test run_single
    console.print("\n[bold]Checking run_single...[/bold]")
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
        "Compare NPS between promoters and detractors (Wait, this is nonsensical as a cut, but good to test handling)"
    ]
    
    single_results = []
    for prompt in test_prompts:
        console.print(f"Testing: \"{prompt}\"")
        try:
            result = pipeline.run_single(prompt, save_run=False)
            if result.success and result.execution_result:
                status = "[green]PASS[/green]"
                details = f"Base N: {result.execution_result.tables[0].base_n}"
            else:
                status = "[red]FAIL[/red]"
                details = ", ".join(result.errors) if result.errors else "No output produced"
        except NotImplementedError:
            status = "[yellow]CRASH[/yellow]"
            details = "Not implemented"
        except Exception as e:
            status = "[red]CRASH[/red]"
            details = str(e)
            
        single_results.append((prompt, status, details))

    # 2. Test run_autoplan
    console.print("\n[bold]Checking run_autoplan...[/bold]")
    try:
        auto_result = pipeline.run_autoplan(save_run=False)
        if auto_result.success:
            auto_status = "[green]PASS[/green]"
            auto_details = f"Intents: {len(auto_result.plan.intents) if auto_result.plan else 0}, Cuts: {len(auto_result.cuts_planned)}"
        else:
            auto_status = "[red]FAIL[/red]"
            auto_details = ", ".join(auto_result.errors) if auto_result.errors else "Execution failed"
    except NotImplementedError:
        auto_status = "[yellow]CRASH[/yellow]"
        auto_details = "Not implemented"
    except Exception as e:
        auto_status = "[red]CRASH[/red]"
        auto_details = str(e)

    # Summary Table
    table = Table(title="E2E Validation Scorecard")
    table.add_column("Feature")
    table.add_column("Status")
    table.add_column("Details")

    for prompt, status, details in single_results:
        table.add_row(f"run_single: {prompt}", status, details)
        
    table.add_row("run_autoplan", auto_status, auto_details)

    console.print("\n")
    console.print(table)
    
    if "[yellow]CRASH[/yellow]" in [r[1] for r in single_results] or auto_status == "[yellow]CRASH[/yellow]":
        console.print("\n[yellow]💡 Candidates need to implement the pipeline methods in src/dd_agent/orchestrator/pipeline.py[/yellow]")

if __name__ == "__main__":
    main()
