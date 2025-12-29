"""Cut planner tool for converting NL requests to CutSpecs."""

import json
import uuid
from typing import Any, Optional
from pydantic import BaseModel, Field

from dd_agent.contracts.specs import CutSpec, MetricSpec
from dd_agent.contracts.tool_output import ToolMessage, ToolOutput, err, warn
from dd_agent.contracts.validate import validate_cut_spec
from dd_agent.llm.structured import build_messages, chat_structured_pydantic
from dd_agent.tools.base import Tool, ToolContext


class CutPlanResult(BaseModel):
    """Result of the cut planner tool."""

    ok: bool = Field(..., description="Whether planning succeeded")
    cut: Optional[CutSpec] = Field(
        default=None, description="The planned cut specification"
    )
    resolution_map: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of NL terms to question/segment IDs",
    )
    ambiguity_options: list[str] = Field(
        default_factory=list,
        description="Possible interpretations if ambiguous",
    )
    errors: list[dict[str, Any]] = Field(
        default_factory=list, description="Any errors from the LLM"
    )


class CutPlanner(Tool):
    """Tool for converting natural language requests to CutSpecs.

    Takes a natural language analysis request (e.g., "Show NPS by region")
    and produces a validated CutSpec that can be executed deterministically.
    """

    @property
    def name(self) -> str:
        return "cut_planner"

    @property
    def description(self) -> str:
        return "Converts natural language analysis requests to executable CutSpecs"

    def run(self, ctx: ToolContext) -> ToolOutput[CutSpec]:
        """Execute the cut planner tool.

        Args:
            ctx: Tool context with questions, segments, and the prompt

        Returns:
            ToolOutput containing a validated CutSpec or errors
        """
        if not ctx.prompt:
            return ToolOutput.failure(
                errors=[err("missing_prompt", "No analysis request provided")]
            )

        try:
            # 1. Prepare context information
            user_content = self._build_user_content(ctx)
            
            # 2. Build system prompt
            system_prompt = self._build_system_prompt(ctx)
            
            # 3. Call LLM to generate structured output
            # FIX: Correct parameter name
            messages = build_messages(
                system_prompt=system_prompt,
                user_content=user_content
            )
            
            # FIX: chat_structured_pydantic returns tuple (instance, trace)
            cut_plan, llm_trace = chat_structured_pydantic(
                messages=messages,
                model=CutPlanResult,
                temperature=0.1
            )
            
            # 4. Process LLM response
            if not cut_plan.ok:
                return ToolOutput.failure(
                    errors=[err("llm_failed", f"LLM failed to produce valid plan: {cut_plan.errors}")]
                )
            
            # 5. Check for ambiguity requiring user clarification
            if cut_plan.ambiguity_options and len(cut_plan.ambiguity_options) > 1:
                return ToolOutput.partial(
                    data=None,
                    warnings=[warn("ambiguity_detected", 
                                   f"Multiple interpretations found: {', '.join(cut_plan.ambiguity_options)}")],
                    trace={
                        "prompt": ctx.prompt,
                        "ambiguity_options": cut_plan.ambiguity_options,
                        "resolution_map": cut_plan.resolution_map,
                        "llm_trace": llm_trace
                    }
                )
            
            # 6. Validate the generated CutSpec
            if cut_plan.cut:
                # Generate cut_id if missing
                if not cut_plan.cut.cut_id:
                    cut_plan.cut.cut_id = f"cut_{uuid.uuid4().hex[:8]}"
                
                # Convert questions and segments to dictionaries for validation
                questions_by_id = {q.question_id: q for q in ctx.questions}
                segments_by_id = {s.segment_id: s for s in (ctx.segments or [])}
                
                # Validate using the existing validate_cut_spec function
                validation_errors = validate_cut_spec(
                    cut_plan.cut, 
                    questions_by_id, 
                    segments_by_id
                )
                
                if validation_errors:
                    return ToolOutput.failure(
                        errors=validation_errors
                    )
                
                return ToolOutput.success(
                    data=cut_plan.cut,
                    warnings=[ToolMessage(
                        code="resolution_mapped", 
                        message=f"Mapped terms: {cut_plan.resolution_map}"
                    )] if cut_plan.resolution_map else [],
                    trace={
                        "prompt": ctx.prompt,
                        "resolution_map": cut_plan.resolution_map,
                        "llm_response": cut_plan.model_dump(),
                        "llm_trace": llm_trace,
                        "validation_passed": True
                    }
                )
            else:
                return ToolOutput.failure(
                    errors=[err("no_cut_generated", "LLM did not generate a CutSpec")]
                )
                
        except Exception as e:
            return ToolOutput.failure(
                errors=[err("unexpected_error", f"Unexpected error: {str(e)}")]
            )

    def _build_system_prompt(self, ctx: ToolContext) -> str:
        """Build the system prompt to guide LLM reasoning."""
        
        # Build string representation of question catalog
        questions_info = []
        for q in ctx.questions:
            # Use question_id from the Question class
            question_desc = f"- ID: {q.question_id}, Label: '{q.label}', Type: {q.type.value}"
            if q.options:
                # Handle numeric option codes for Likert
                option_strings = []
                for opt in q.options:
                    # Show both code and label
                    option_strings.append(f"'{opt.code}': '{opt.label}'")
                options_str = ", ".join(option_strings)
                question_desc += f", Options: {{{options_str}}}"
            questions_info.append(question_desc)
        
        questions_str = "\n".join(questions_info)
        
        # Build segment catalog (if available)
        segments_str = ""
        if ctx.segments:
            segments_info = []
            for s in ctx.segments:
                segment_desc = f"- ID: {s.segment_id}, Name: '{s.name}'"
                # Add filter description if available
                if hasattr(s, 'filter') and s.filter:
                    segment_desc += f", Filter: {s.filter}"
                segments_info.append(segment_desc)
            segments_str = "\nAvailable Segments:\n" + "\n".join(segments_info)
        
        # FIX: Improved metric compatibility table
        return f"""You are a data analysis expert responsible for converting natural language analysis requests into precise CutSpec specifications.

# Available Data
Here are the questions in the dataset:
{questions_str}
{segments_str}

# Task
Parse the user's natural language request into a CutSpec containing:
1. cut_id: Unique identifier (you can suggest, but system will generate if missing)
2. metric: The metric to compute (MetricSpec object with 'type' and 'question_id')
3. dimensions: List of dimensions to group by (each dimension is an object with 'kind' and 'id')
4. filter: Optional filter condition (can be null)

# Important Rules
## 1. Metric Compatibility
TYPE          | COMPATIBLE METRICS
--------------|-------------------
nps_0_10      | 'nps', 'mean', 'frequency'
likert_1_5    | 'mean', 'top2box', 'bottom2box', 'frequency'
likert_1_7    | 'mean', 'top2box', 'bottom2box', 'frequency'
numeric       | 'mean', 'frequency'
single_choice | 'frequency'
multi_choice  | 'frequency'

Key constraints:
- 'nps' metric can ONLY be used with questions of type 'nps_0_10'
- 'top2box' and 'bottom2box' can ONLY be used with 'likert_1_5' or 'likert_1_7' questions
- If user says "NPS", you MUST use the nps_0_10 question
- If user says "top-2-box" or "top2box", find Likert questions

## 2. Dimension Matching
- Find the question ID that best matches the user's description
- Example: "country" → look for questions with "country", "region", "location" in the label
- If multiple matches, record them in ambiguity_options
- For segments: use 'kind': 'segment' and the segment ID

## 3. Automatic Term Mapping
Common mappings:
- "NPS" or "Net Promoter Score" → Q_NPS (if exists)
- "satisfaction" or "sat" → Q_OVERALL_SAT (if exists)
- "country", "region", "geography" → Q_REGION (if exists)
- "age" → Q_AGE (if exists)
- "income" → Q_INCOME (if exists)
- "gender" → Q_GENDER (if exists)
- "plan" or "subscription" → Q_PLAN (if exists)

## 4. Output Format
You must return a CutPlanResult object with this exact structure:
{{
    "ok": true,
    "cut": {{
        "cut_id": "suggested_id_here",
        "metric": {{
            "type": "metric_type",
            "question_id": "QUESTION_ID"
        }},
        "dimensions": [
            {{"kind": "question", "id": "QUESTION_ID"}}
        ],
        "filter": null
    }},
    "resolution_map": {{"user_term": "actual_id"}},
    "ambiguity_options": [],
    "errors": []
}}

# Critical Instructions
1. Suggest a cut_id based on metric and dimension (e.g., "cut_nps_by_region")
2. Ensure metric compatibility (check question type)
3. Map user terms to actual question/segment IDs in resolution_map
4. If unsure about which question to use, add options to ambiguity_options
5. Return ONLY valid JSON, no other text

# Examples
Example 1: "Show NPS by region"
Available: Q_NPS (nps_0_10), Q_REGION (single_choice)
Response: {{
    "ok": true,
    "cut": {{
        "cut_id": "cut_nps_by_region",
        "metric": {{"type": "nps", "question_id": "Q_NPS"}},
        "dimensions": [{{"kind": "question", "id": "Q_REGION"}}],
        "filter": null
    }},
    "resolution_map": {{"nps": "Q_NPS", "region": "Q_REGION"}},
    "ambiguity_options": [],
    "errors": []
}}

Example 2: "Top 2 box overall satisfaction by income level"
Available: Q_OVERALL_SAT (likert_1_5), Q_INCOME (single_choice)
Response: {{
    "ok": true,
    "cut": {{
        "cut_id": "cut_top2box_sat_by_income",
        "metric": {{"type": "top2box", "question_id": "Q_OVERALL_SAT"}},
        "dimensions": [{{"kind": "question", "id": "Q_INCOME"}}],
        "filter": null
    }},
    "resolution_map": {{"overall satisfaction": "Q_OVERALL_SAT", "income": "Q_INCOME"}},
    "ambiguity_options": [],
    "errors": []
}}

Example 3: "Compare ease of use mean between subscription plans"
Available: Q_EASE_OF_USE (likert_1_5), Q_PLAN (single_choice)
Response: {{
    "ok": true,
    "cut": {{
        "cut_id": "cut_ease_mean_by_plan",
        "metric": {{"type": "mean", "question_id": "Q_EASE_OF_USE"}},
        "dimensions": [{{"kind": "question", "id": "Q_PLAN"}}],
        "filter": null
    }},
    "resolution_map": {{"ease of use": "Q_EASE_OF_USE", "subscription plans": "Q_PLAN"}},
    "ambiguity_options": [],
    "errors": []
}}

Now process the user request below."""

    def _build_user_content(self, ctx: ToolContext) -> str:
        """Build the user message content."""
        return f"""Analysis request: "{ctx.prompt}"

Based on the available questions and segments shown above, generate the appropriate CutSpec.

Remember:
1. Check metric compatibility with question type
2. Suggest a cut_id (system will finalize it)
3. Map user terms to actual IDs in resolution_map
4. If ambiguous, add options to ambiguity_options
5. Return ONLY valid JSON matching the CutPlanResult schema

JSON Output:"""