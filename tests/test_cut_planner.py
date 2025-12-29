# tests/test_cut_planner.py - FIXED
import pytest
from unittest.mock import Mock, patch, MagicMock
import json
from dd_agent.tools.cut_planner import CutPlanner, CutPlanResult
from dd_agent.contracts.specs import CutSpec, MetricSpec, DimensionSpec
from dd_agent.contracts.questions import Question, QuestionType, Option
from dd_agent.tools.base import ToolContext

def test_cut_planner_with_nps_request():
    """Test CutPlanner with a simple NPS request."""
    # Create test questions
    questions = [
        Question(
            question_id="Q_NPS",
            label="How likely are you to recommend our product?",
            type=QuestionType.nps_0_10
        ),
        Question(
            question_id="Q_REGION",
            label="Which region are you from?",
            type=QuestionType.single_choice,
            options=[
                Option(code="north", label="North"),
                Option(code="south", label="South"),
                Option(code="east", label="East"),
                Option(code="west", label="West")
            ]
        )
    ]
    
    # Create expected LLM response - Use DimensionSpec objects, not dicts
    expected_cut = CutSpec(
        cut_id="test_cut_001",
        metric=MetricSpec(type="nps", question_id="Q_NPS"),
        dimensions=[DimensionSpec(kind="question", id="Q_REGION")],  # FIXED: Use DimensionSpec
        filter=None
    )
    
    expected_response = CutPlanResult(
        ok=True,
        cut=expected_cut,
        resolution_map={"nps": "Q_NPS", "region": "Q_REGION"},
        ambiguity_options=[],
        errors=[]
    )
    
    # Mock the chat_structured_pydantic function
    with patch('dd_agent.tools.cut_planner.chat_structured_pydantic') as mock_llm:
        # Create a proper mock ToolOutput
        mock_tool_output = MagicMock()
        mock_tool_output.ok = True
        mock_tool_output.data = expected_response
        mock_tool_output.errors = []
        mock_tool_output.warnings = []
        mock_tool_output.trace = {}
        
        mock_llm.return_value = mock_tool_output
        
        # Create CutPlanner
        planner = CutPlanner()
        
        # Create a mock ToolContext object with all required attributes
        ctx = MagicMock()
        ctx.prompt = "Show NPS by region"
        ctx.questions = questions
        ctx.segments = []
        ctx.llm_client = MagicMock()
        
        # Run the planner
        result = planner.run(ctx)
        
        # Assertions
        assert result.ok, f"Expected success but got errors: {result.errors}"
        assert result.data is not None
        assert result.data.metric.type == "nps"
        assert result.data.metric.question_id == "Q_NPS"
        assert len(result.data.dimensions) == 1
        # FIXED: Access id attribute of DimensionSpec object
        assert result.data.dimensions[0].id == "Q_REGION"

def test_cut_planner_with_dimension_specs():
    """Test to understand DimensionSpec structure."""
    # Quick check of what DimensionSpec looks like
    from dd_agent.contracts.specs import DimensionSpec
    
    dim = DimensionSpec(kind="question", id="Q_REGION")
    print(f"DimensionSpec attributes: kind={dim.kind}, id={dim.id}")
    
    # This should work
    assert dim.kind == "question"
    assert dim.id == "Q_REGION"
    
    # This should fail (it's an object, not a dict)
    try:
        value = dim["id"]
        print(f"ERROR: DimensionSpec is subscriptable: {value}")
    except TypeError:
        print("CORRECT: DimensionSpec is not subscriptable")

def test_minimal_cut_planner():
    """Minimal test to check basic functionality."""
    planner = CutPlanner()
    
    # Just test that it initializes
    assert planner.name == "cut_planner"
    assert "natural language" in planner.description.lower()
    
    # Test with minimal context
    ctx = MagicMock()
    ctx.prompt = "test"
    ctx.questions = []
    ctx.segments = []
    ctx.llm_client = None
    
    result = planner.run(ctx)
    # Should fail with missing prompt or similar, but not crash

def test_cut_planner_missing_prompt():
    """Test CutPlanner with missing prompt."""
    planner = CutPlanner()
    
    ctx = MagicMock()
    ctx.prompt = ""  # Empty prompt
    ctx.questions = []
    ctx.segments = []
    ctx.llm_client = None
    
    result = planner.run(ctx)
    assert not result.ok
    assert "missing_prompt" in str(result.errors[0]).lower()

def test_cut_planner_basic():
    """Basic test without mocks."""
    planner = CutPlanner()
    assert planner.name == "cut_planner"
    assert planner.description
    
    # Test the prompt builder methods
    ctx = MagicMock()
    ctx.prompt = "test"
    ctx.questions = []
    ctx.segments = []
    
    # These should work without needing llm_client
    system_prompt = planner._build_system_prompt(ctx)
    user_content = planner._build_user_content(ctx)
    
    assert "data analysis expert" in system_prompt
    assert "test" in user_content

# Add this test to run the dimension spec check
if __name__ == "__main__":
    # Run the dimension spec test
    test_cut_planner_with_dimension_specs()
    
    # Run other tests
    test_minimal_cut_planner()
    print("✓ Minimal test passed")
    
    test_cut_planner_missing_prompt()
    print("✓ Missing prompt test passed")
    
    test_cut_planner_basic()
    print("✓ Basic test passed")