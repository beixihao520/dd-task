"""Cut planner tool for converting NL requests to CutSpecs."""

import json
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
            # Use correct parameter names for build_messages
            messages = build_messages(
                system_prompt=system_prompt,
                user_content=user_content
            )
            
            result = chat_structured_pydantic(
                client=ctx.llm_client,
                messages=messages,
                response_model=CutPlanResult,
                temperature=0.1  # Low temperature for determinism
            )
            
            # 4. Process LLM response
            if not result.ok:
                return ToolOutput.failure(
                    errors=[err("llm_failed", f"LLM failed to produce valid plan: {result.errors}")]
                )
            
            cut_plan = result.data
            
            # 5. Check for ambiguity requiring user clarification
            if cut_plan.ambiguity_options and len(cut_plan.ambiguity_options) > 1:
                return ToolOutput.partial(
                    data=None,
                    warnings=[warn("ambiguity_detected", 
                                   f"Multiple interpretations found: {', '.join(cut_plan.ambiguity_options)}")],
                    trace={
                        "prompt": ctx.prompt,
                        "ambiguity_options": cut_plan.ambiguity_options,
                        "resolution_map": cut_plan.resolution_map
                    }
                )
            
            # 6. Validate the generated CutSpec
            if cut_plan.cut:
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
                options_str = ", ".join([f"'{opt.code}': '{opt.label}'" for opt in q.options])
                question_desc += f", Options: {{{options_str}}}"
            questions_info.append(question_desc)
        
        questions_str = "\n".join(questions_info)
        
        # Build segment catalog (if available)
        segments_str = ""
        if ctx.segments:
            segments_info = [f"- ID: {s.segment_id}, Name: '{s.name}'" 
                           for s in ctx.segments]
            segments_str = "\nAvailable Segments:\n" + "\n".join(segments_info)
        
        return f"""You are a data analysis expert responsible for converting natural language analysis requests into precise CutSpec specifications.

# Available Data
Here are the questions in the dataset:
{questions_str}
{segments_str}

# Task
Parse the user's natural language request into a CutSpec containing:
1. metric: The metric to compute (MetricSpec object with 'type' and 'question_id')
2. dimensions: List of dimensions to group by (each dimension is an object with 'kind' and 'id')
3. filter: Optional filter condition (can be null)

# Important Rules
## 1. Metric Compatibility
- 'nps' metric can only be used with questions of type 'nps_0_10'
- 'top2box' and 'bottom2box' can only be used with 'likert_1_5' or 'likert_1_7' questions
- 'mean' can be used with 'likert_1_5', 'likert_1_7', 'numeric', 'nps_0_10'
- 'frequency' can be used with all question types

## 2. Dimension Matching
- Find the question ID that best matches the user's description
- Example: "country" → look for questions with "country" or "region" in the label
- If multiple matches, record them in ambiguity_options
- For segments: use 'kind': 'segment' and the segment ID

## 3. Output Format
You must return a CutPlanResult object with this exact structure:
{{
    "ok": true,
    "cut": {{
        "cut_id": "auto_generated_unique_id",
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
1. Generate a unique cut_id like "cut_nps_by_region_001"
2. Ensure metric compatibility (check question type)
3. Map user terms to actual question/segment IDs in resolution_map
4. If unsure about which question to use, add options to ambiguity_options
5. Return ONLY valid JSON, no other text

# Examples
Example 1:
User: "Show NPS by country"
Available: Q_NPS (nps_0_10), Q_COUNTRY (single_choice)
Response: {{
    "ok": true,
    "cut": {{
        "cut_id": "cut_nps_by_country_001",
        "metric": {{"type": "nps", "question_id": "Q_NPS"}},
        "dimensions": [{{"kind": "question", "id": "Q_COUNTRY"}}],
        "filter": null
    }},
    "resolution_map": {{"nps": "Q_NPS", "country": "Q_COUNTRY"}},
    "ambiguity_options": [],
    "errors": []
}}

Example 2:
User: "Top 2 box satisfaction by region"
Available: Q_SAT (likert_1_7), Q_REGION (single_choice)
Response: {{
    "ok": true,
    "cut": {{
        "cut_id": "cut_top2box_by_region_001",
        "metric": {{"type": "top2box", "question_id": "Q_SAT"}},
        "dimensions": [{{"kind": "question", "id": "Q_REGION"}}],
        "filter": null
    }},
    "resolution_map": {{"satisfaction": "Q_SAT", "region": "Q_REGION"}},
    "ambiguity_options": [],
    "errors": []
}}

Now process the user request."""

    def _build_user_content(self, ctx: ToolContext) -> str:
        """Build the user message content."""
        return f"""Analysis request: "{ctx.prompt}"

Based on the available questions and segments shown in the system prompt, generate the appropriate CutSpec.

Remember:
1. Check metric compatibility with question type
2. Generate a unique cut_id
3. Map user terms to actual IDs in resolution_map
4. Return ONLY valid JSON matching the CutPlanResult schema

JSON Output:"""