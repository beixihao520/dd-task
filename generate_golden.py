
import json
import random
import pandas as pd
import numpy as np
from typing import Any, Optional
from pathlib import Path

from dd_agent.engine.executor import Executor
from dd_agent.contracts.questions import Question, QuestionType
from dd_agent.contracts.specs import SegmentSpec, CutSpec
from dd_agent.tools.cut_planner import CutPlanner
from dd_agent.tools.base import ToolContext

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

def main():
    questions = [Question(**q) for q in json.load(open("data/demo/questions.json"))]
    questions_by_id = {q.question_id: q for q in questions}
    df = generate_dummy_data(questions)
    
    segments = [
        SegmentSpec(segment_id="SEG_YOUNG", name="Young Respondents", definition={"kind": "range", "question_id": "Q_AGE", "min": 18, "max": 35}),
        SegmentSpec(segment_id="SEG_HIGH_INCOME", name="High Income", definition={"kind": "in", "question_id": "Q_INCOME", "values": ["HIGH", "VHIGH"]}),
        SegmentSpec(segment_id="SEG_MALE_NORTH", name="Males in the North", definition={"kind": "and", "children": [{"kind": "eq", "question_id": "Q_GENDER", "value": "M"}, {"kind": "eq", "question_id": "Q_REGION", "value": "NORTH"}]}),
        SegmentSpec(segment_id="SEG_TECH_ACTIVE", name="Active Tech Users", definition={"kind": "contains_any", "question_id": "Q_FEATURES_USED", "values": ["API", "MOBILE"]}),
        SegmentSpec(segment_id="SEG_NOT_LOW_INCOME", name="Excluded Low Income", definition={"kind": "not", "child": {"kind": "eq", "question_id": "Q_INCOME", "value": "LOW"}}),
        SegmentSpec(segment_id="SEG_OR_CONDITION", name="Young OR High Income", definition={"kind": "or", "children": [{"kind": "range", "question_id": "Q_AGE", "min": 18, "max": 25}, {"kind": "in", "question_id": "Q_INCOME", "values": ["VHIGH"]}]})
    ]
    segments_by_id = {s.segment_id: s for s in segments}

    planner = CutPlanner()
    executor = Executor(df, questions_by_id, segments_by_id=segments_by_id)
    
    # 50 high-confidence prompts
    prompts = [
        # --- Basic Metrics ---
        "Frequency of gender", "Average age", "NPS score for the product", "Top 2 box for overall satisfaction",
        "Bottom 2 box for ease of use", "Value for money frequency", "Purchase intent distribution",
        "Tenure distribution among customers", "Support satisfaction mean score", "How many people use each feature?",

        # --- Question Dimensions ---
        "Show the average age broken down by income", "Performance of NPS by region", "Frequency of features used by gender",
        "Top 2 box for support satisfaction by plan type", "Bottom 2 box for ease of use by region",
        "Overall satisfaction by tenure", "Purchase intent across different usage frequencies",
        "Value for money by plan type", "Gender distribution by region", "Average age by usage frequency",

        # --- Segment Dimensions ---
        "Compare overall satisfaction for regular 'Young Respondents' vs others",
        "Break down purchase intent by the 'High Income' segment",
        "Support satisfaction for 'Active Tech Users' compared to others",
        "Value for money rating by 'Males in the North' vs everyone else",
        "Plan frequency for the 'Excluded Low Income' segment",
        "NPS performance for 'Young OR High Income' respondents",

        # --- Simple Filters ---
        "Average NPS for respondents aged 18 to 30", "Overall satisfaction for people in the North or South regions",
        "Mean age for Female respondents", "Top 2 box for satisfaction among 'Enterprise' plan users",
        "Frequency of features used for respondents with 'Low' income",
        "NPS score for users in the 'West' region who are 'Monthly' users",
        "How many 'Daily' users recommend the product?",

        # --- Logical Operator Filters ---
        "NPS score for 'Males in the North'",
        "Average support satisfaction for people who use the API feature",
        "Show the income distribution for 'Active Tech Users'",
        "Purchase intent for respondents who are NOT 'Very Satisfied' with support",
        "Mean age for respondents who use either 'Data Export' OR 'Dashboard'",
        "Check NPS for respondents who use 'Reporting' but live in the 'South'",

        # --- Edge Cases (Expected Rejections) ---
        "Calculate the mean of Region", "What is the average Gender?", "NPS score for Age",
        "What is the capital of France?", "Show the stock price of Microsoft",
        "Satisfaction for respondents who live on Mars", "Average of features used",
        "Show me the weather in San Francisco", "Minimum salary of the CEO",
        "Distribution of the color blue", "Top 5 box for age"
    ]

    golden_results = []
    print(f"Generating Golden Metadata for {len(prompts)} cases...")
    for prompt in prompts:
        ctx = ToolContext(questions=questions, questions_by_id=questions_by_id, segments=segments, segments_by_id=segments_by_id, prompt=prompt, responses_df=df)
        plan_output = planner.run(ctx)
        
        case_data = {"prompt": prompt, "expected_ok": plan_output.ok, "expected_plan": None, "expected_results": None}

        if plan_output.ok and plan_output.data:
            cut_spec = plan_output.data
            exec_result = executor.execute_cuts([cut_spec])
            case_data["expected_plan"] = {"metric_type": cut_spec.metric.type, "question_id": cut_spec.metric.question_id, "dimension_ids": [d.id for d in cut_spec.dimensions]}
            if not exec_result.errors:
                table = exec_result.tables[0]
                res_df = table.get_dataframe()
                primary_value = None
                if res_df is not None and not res_df.empty:
                    if "mean" in res_df.columns: primary_value = float(res_df["mean"].iloc[0])
                    elif "nps" in res_df.columns: primary_value = float(res_df["nps"].iloc[0])
                    elif "metric" in res_df.columns: 
                        val = res_df["metric"].iloc[0]
                        primary_value = float(val) if isinstance(val, (int, float)) else None
                case_data["expected_results"] = {"base_n": table.base_n, "primary_value": primary_value}

        golden_results.append(case_data)

    output_path = "tests/golden_validation.json"
    Path("tests").mkdir(exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(golden_results, f, indent=2)
    print(f"Golden metadata saved to {output_path}")

if __name__ == "__main__":
    main()
