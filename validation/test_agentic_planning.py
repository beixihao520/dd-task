
import json
import random
import pandas as pd
from typing import Any
from pathlib import Path

from dd_agent.engine.executor import Executor
from dd_agent.contracts.questions import Question, QuestionType
from dd_agent.contracts.specs import SegmentSpec
from dd_agent.tools.cut_planner import CutPlanner
from dd_agent.tools.base import ToolContext

def load_questions(json_path: str) -> list[Question]:
    with open(json_path, 'r') as f:
        data = json.load(f)
    return [Question(**q_data) for q_data in data]

def generate_dummy_data(questions: list[Question], n_rows=100) -> pd.DataFrame:
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

def main():
    questions_path = "data/demo/questions.json"
    print(f"Loading questions from {questions_path}...")
    questions = load_questions(questions_path)
    questions_by_id = {q.question_id: q for q in questions}
    
    print("Generating dummy data...")
    df = generate_dummy_data(questions)
    
    segments = [
        SegmentSpec(
            segment_id="SEG_YOUNG",
            name="Young Respondents",
            definition={"kind": "range", "question_id": "Q_AGE", "min": 18, "max": 35}
        ),
        SegmentSpec(
            segment_id="SEG_HIGH_INCOME",
            name="High Income",
            definition={"kind": "in", "question_id": "Q_INCOME", "values": ["HIGH", "VHIGH"]}
        ),
        SegmentSpec(
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
        SegmentSpec(
            segment_id="SEG_TECH_ACTIVE",
            name="Active Tech Users",
            definition={
                "kind": "contains_any",
                "question_id": "Q_FEATURES_USED",
                "values": ["API", "MOBILE"]
            }
        ),
        SegmentSpec(
            segment_id="SEG_NOT_LOW_INCOME",
            name="Excluded Low Income",
            definition={
                "kind": "not",
                "child": {"kind": "eq", "question_id": "Q_INCOME", "value": "LOW"}
            }
        )
    ]
    segments_by_id = {s.segment_id: s for s in segments}

    planner = CutPlanner()
    executor = Executor(df, questions_by_id, segments_by_id=segments_by_id)
    
    # NL Requests to test full coverage:
    # 1. All Metric Types
    # 2. Both Dimension Kinds (Question, Segment)
    # 3. All Filter Logic (And, Or, Not, Range, In, Eq, ContainsAny)
    requests = [
        # --- Core Metrics & Question Dimensions ---
        "Show the average age broken down by income",
        "Performance of NPS by region",
        "Frequency of features used by gender",
        "Top 2 box for support satisfaction by plan type",
        "Bottom 2 box for ease of use by region",
        
        # --- Segment Dimensions (The 'Split by' Case) ---
        "Compare overall satisfaction for regular 'Young Respondents' vs others",
        "Break down purchase intent by the 'High Income' segment",
        
        # --- Filter Logic: Range, In, Eq ---
        "Average NPS for respondents aged 18 to 30",
        "Overall satisfaction for people in the North or South regions",
        "Mean age for Female respondents",
        
        # --- Filter Logic: Logical Operators (And, Or, Not) ---
        "NPS for 'Males in the North'",
        "Frequency of plans for people who are NOT in the 'High Income' segment",
        "Mean satisfaction for users who are either Young Respondents OR have High Income",
        
        # --- Multi-Choice Logic (ContainsAny) ---
        "Average support satisfaction for people who use the API feature",
        "Show the income distribution for 'Active Tech Users'"
    ]
    # Edge Case Requests
    edge_cases = [
        # --- Ambiguity ---
        "Show satisfaction",  # Ambiguous between Overall and Support
        "Breakdown by region", # No metric specified
        
        # --- Nonsensical / Out of Scope ---
        "What is the capital of France?",
        "Show the stock price of Microsoft",
        "How is the weather?",
        
        # --- Invalid Analyses (Math errors) ---
        "Calculate the mean of Region",      # Categorical cannot have mean
        "What is the average Gender?",       # Categorical cannot have mean
        "NPS score for Age",                 # Age is numeric, not NPS
        
        # --- Empty Results / Out of Bounds ---
        "NPS for people older than 200",     # No respondents match
        "Satisfaction for respondents who live on Mars", # Invalid option value
        
        # --- Multi-Choice Invalid ---
        "Average of features used"           # Mean on multi-choice
    ]
    
    # Combined list for processing
    all_tests = [("Standard", requests), ("Edge Case", edge_cases)]


    md_output_path = "agentic_analysis_results.md"
    print(f"Executing agentic tests and exporting to {md_output_path}...")
    
    with open(md_output_path, "w") as f:
        f.write("# Agentic Planning & Execution Results\n\n")
        f.write("This file validates both standard success paths and edge-case error handling.\n\n")
        
        for section_name, test_requests in all_tests:
            f.write(f"# Section: {section_name}\n\n")
            for nl_request in test_requests:
                print(f"Processing ({section_name}): \"{nl_request}\"")
                f.write(f"## Request: \"{nl_request}\"\n")
                
                # 1. Plan the cut
                ctx = ToolContext(
                    questions=questions,
                    questions_by_id=questions_by_id,
                    segments=segments,
                    segments_by_id=segments_by_id,
                    prompt=nl_request,
                    responses_df=df
                )
                
                plan_output = planner.run(ctx)
                
                if not plan_output.ok or plan_output.data is None:
                    f.write(f"### ❌ Planning Failed (Expected for some Edge Cases)\n")
                    f.write("Errors:\n")
                    if plan_output.errors:
                        for err in plan_output.errors:
                            f.write(f"- `{err.code}`: {err.message}\n")
                    else:
                        f.write("- Unknown error (no cut produced)\n")
                    f.write("\n---\n\n")
                    continue
                
                cut_spec = plan_output.data
                f.write(f"### ✅ Planning Succeeded\n")

                f.write(f"- **Planned Cut ID**: `{cut_spec.cut_id}`\n")
                f.write(f"- **Metric**: `{cut_spec.metric.type}` on `{cut_spec.metric.question_id}`\n")
                
                if cut_spec.dimensions:
                    dims = [f"{d.kind}: {d.id}" for d in cut_spec.dimensions]
                    f.write(f"- **Dimensions**: {', '.join(dims)}\n")
                
                if cut_spec.filter:
                    f.write(f"- **Filter Applied**: `{cut_spec.filter['kind'] if isinstance(cut_spec.filter, dict) else 'Complex'}`\n")
                
                # 2. Execute the cut
                print(f"Executing planned cut: {cut_spec.cut_id}")
                try:
                    exec_result = executor.execute_cuts([cut_spec])
                    
                    if exec_result.errors:
                        f.write(f"### ❌ Execution Failed\n")
                        f.write(f"Error: {exec_result.errors[0]['error']}\n")
                    else:
                        table = exec_result.tables[0]
                        f.write(f"### ✅ Execution Succeeded\n")
                        f.write(f"- **Base N**: {table.base_n}\n")
                        
                        res_df = table.get_dataframe()
                        if res_df is not None:
                            f.write("\n```text\n")
                            f.write(res_df.to_string())
                            f.write("\n```\n")
                        else:
                            f.write("\n*No DataFrame in result*\n")
                except Exception as e:
                    f.write(f"### ❌ Execution Errored\n")
                    f.write(f"Exception: {str(e)}\n")
                
                f.write("\n---\n\n")

    print(f"Agentic tests completed. Results in {md_output_path}")

if __name__ == "__main__":
    main()
