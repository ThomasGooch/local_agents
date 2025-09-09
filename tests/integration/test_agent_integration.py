"""Integration tests for agent interactions."""

from unittest.mock import Mock, patch

import pytest

from local_agents.agents.coder import CodingAgent
from local_agents.agents.planner import PlanningAgent
from local_agents.agents.reviewer import ReviewAgent
from local_agents.agents.tester import TestingAgent
from local_agents.ollama_client import OllamaClient


@pytest.fixture
def mock_ollama_response():
    """Mock Ollama responses for different agents."""
    responses = {
        "plan": """# Implementation Plan

## Requirements Analysis
- Create a simple calculator function
- Support basic arithmetic operations
- Include input validation

## Implementation Steps
1. Define function signature
2. Implement arithmetic operations
3. Add input validation
4. Handle edge cases
5. Create comprehensive tests

## Architecture Decisions
- Use functional approach for simplicity
- Implement type hints for better code quality
- Include comprehensive error handling""",
        "code": """```python
def calculator(operation: str, a: float, b: float) -> float:
    \"\"\"Perform basic arithmetic operations.

    Args:
        operation: The operation to perform (+, -, *, /)
        a: First operand
        b: Second operand

    Returns:
        Result of the arithmetic operation

    Raises:
        ValueError: If operation is not supported or division by zero
    \"\"\"
    if operation == '+':
        return a + b
    elif operation == '-':
        return a - b
    elif operation == '*':
        return a * b
    elif operation == '/':
        if b == 0:
            raise ValueError("Division by zero is not allowed")
        return a / b
    else:
        raise ValueError(f"Unsupported operation: {operation}")
```""",
        "test": """```python
import pytest
from calculator import calculator


def test_calculator_addition():
    \"\"\"Test addition operation.\"\"\"
    assert calculator('+', 2, 3) == 5
    assert calculator('+', -1, 1) == 0
    assert calculator('+', 0, 0) == 0


def test_calculator_subtraction():
    \"\"\"Test subtraction operation.\"\"\"
    assert calculator('-', 5, 3) == 2
    assert calculator('-', 0, 5) == -5


def test_calculator_multiplication():
    \"\"\"Test multiplication operation.\"\"\"
    assert calculator('*', 4, 3) == 12
    assert calculator('*', -2, 3) == -6


def test_calculator_division():
    \"\"\"Test division operation.\"\"\"
    assert calculator('/', 10, 2) == 5
    assert calculator('/', 7, 2) == 3.5


def test_calculator_division_by_zero():
    \"\"\"Test division by zero raises error.\"\"\"
    with pytest.raises(ValueError, match="Division by zero"):
        calculator('/', 10, 0)


def test_calculator_invalid_operation():
    \"\"\"Test invalid operation raises error.\"\"\"
    with pytest.raises(ValueError, match="Unsupported operation"):
        calculator('%', 10, 3)
```""",
        "review": """# Code Review Report

## Summary
The calculator function is well-implemented with proper error handling,
type hints, and comprehensive documentation. The code follows Python
best practices.

## Positive Aspects
- Excellent type hints usage
- Comprehensive error handling for edge cases
- Clear and descriptive docstring
- Simple and readable implementation
- Proper exception types and messages

## Issues Found
### Medium Priority Issues
- Consider using an Enum for operations instead of string literals
- Could benefit from input type validation

## Recommendations
1. Create an Operation enum for better type safety
2. Add input type validation for non-numeric inputs
3. Consider adding logging for debugging purposes

## Security Considerations
- No security issues identified
- Input validation helps prevent unexpected behavior

## Performance Notes
- Performance is optimal for the use case
- No optimization needed for this simple function""",
    }

    def mock_generate(model, prompt, **kwargs):
        # Determine response based on prompt content first (more reliable)
        if "Test Generation Task" in prompt or "QA Engineer" in prompt or "test suites" in prompt:
            return responses["test"]
        elif "Code Generation Task" in prompt:
            return responses["code"]
        elif "Code Review Task" in prompt or "Code Review" in prompt:
            return responses["review"]
        elif "Planning" in prompt:
            return responses["plan"]
        # Fallback to model name matching
        elif "planner" in model.lower():
            return responses["plan"]
        elif "codellama" in model.lower():
            return responses["code"]
        elif "review" in model.lower():
            return responses["review"]
        else:
            return responses["plan"]  # Default

    return mock_generate


@pytest.fixture
def mock_ollama_client_with_responses(mock_ollama_response):
    """Create mock Ollama client with realistic responses."""
    client = Mock(spec=OllamaClient)
    client.is_model_available.return_value = True
    client.pull_model.return_value = True
    client.generate.side_effect = mock_ollama_response
    client.chat.side_effect = mock_ollama_response
    client.list_models.return_value = ["llama3.1:8b", "codellama:7b"]
    return client


class TestingAgentChaining:
    """Test chaining agents together with realistic scenarios."""

    @patch("local_agents.base.OllamaClient")
    def test_plan_to_code_integration(self, mock_ollama_class, mock_ollama_client_with_responses):
        """Test integrating planning and coding agents."""
        mock_ollama_class.return_value = mock_ollama_client_with_responses

        # Create agents
        planner = PlanningAgent()
        coder = CodingAgent()

        # Execute planning
        plan_result = planner.execute(
            "Create a simple calculator function",
            {"language": "python", "style": "functional"},
        )

        assert plan_result.success
        assert "Implementation Plan" in plan_result.output
        assert "calculator function" in plan_result.output.lower()

        # Use planning output for coding
        code_context = {
            "implementation_plan": plan_result.output,
            "language": "python",
            "target_file": "calculator.py",
        }

        code_result = coder.execute("Implement the calculator based on the plan", code_context)

        assert code_result.success
        assert "def calculator" in code_result.output
        assert "operation: str" in code_result.output
        assert "float" in code_result.output

    @patch("local_agents.base.OllamaClient")
    def test_code_to_test_integration(self, mock_ollama_class, mock_ollama_client_with_responses):
        """Test integrating coding and testing agents."""
        mock_ollama_class.return_value = mock_ollama_client_with_responses

        # Create agents
        coder = CodingAgent()
        tester = TestingAgent()

        # Generate code first
        code_result = coder.execute("Create a calculator function", {"language": "python"})

        assert code_result.success

        # Generate tests for the code
        test_context = {
            "code_to_test": code_result.output,
            "framework": "pytest",
            "target_file": "calculator.py",
        }

        test_result = tester.execute(
            "Generate comprehensive tests for the calculator function", test_context
        )

        assert test_result.success
        assert "def test_" in test_result.output
        assert "pytest" in test_result.output.lower()
        assert "calculator" in test_result.output

    @patch("local_agents.base.OllamaClient")
    def test_code_to_review_integration(self, mock_ollama_class, mock_ollama_client_with_responses):
        """Test integrating coding and review agents."""
        mock_ollama_class.return_value = mock_ollama_client_with_responses

        # Create agents
        coder = CodingAgent()
        reviewer = ReviewAgent()

        # Generate code first
        code_result = coder.execute("Create a calculator function", {"language": "python"})

        assert code_result.success

        # Review the generated code
        review_context = {
            "code_content": code_result.output,
            "focus_area": "security",
            "target_file": "calculator.py",
        }

        review_result = reviewer.execute("Review the calculator implementation", review_context)

        assert review_result.success
        assert "Code Review" in review_result.output
        assert "Summary" in review_result.output
        assert any(
            word in review_result.output.lower()
            for word in ["positive", "issues", "recommendations"]
        )

    @patch("local_agents.base.OllamaClient")
    def test_full_agent_chain(self, mock_ollama_class, mock_ollama_client_with_responses):
        """Test full chain: Plan -> Code -> Test -> Review."""
        mock_ollama_class.return_value = mock_ollama_client_with_responses

        # Create all agents
        planner = PlanningAgent()
        coder = CodingAgent()
        tester = TestingAgent()
        reviewer = ReviewAgent()

        task = "Create a robust calculator function"
        context = {"language": "python", "requirements": "basic arithmetic operations"}

        # Step 1: Planning
        plan_result = planner.execute(task, context)
        assert plan_result.success

        # Step 2: Coding (using plan output)
        code_context = context.copy()
        code_context["implementation_plan"] = plan_result.output

        code_result = coder.execute("Implement calculator based on the plan", code_context)
        assert code_result.success

        # Step 3: Testing (using code output)
        test_context = context.copy()
        test_context["code_to_test"] = code_result.output
        test_context["framework"] = "pytest"

        test_result = tester.execute("Generate tests for the calculator", test_context)
        assert test_result.success

        # Step 4: Review (using code output)
        review_context = context.copy()
        review_context["code_content"] = code_result.output
        review_context["focus_area"] = "all"

        review_result = reviewer.execute("Review the complete implementation", review_context)
        assert review_result.success

        # Verify all results contain expected content
        assert "calculator" in plan_result.output.lower()
        assert "def calculator" in code_result.output
        assert "def test_" in test_result.output
        assert "review" in review_result.output.lower()


class TestingAgentErrorHandling:
    """Test error handling in agent integration scenarios."""

    @patch("local_agents.base.OllamaClient")
    def test_agent_handles_ollama_failure(self, mock_ollama_class):
        """Test agent handles Ollama client failures gracefully."""
        # Create mock that raises exception
        mock_client = Mock(spec=OllamaClient)
        mock_client.is_model_available.return_value = True
        mock_client.pull_model.return_value = True
        mock_client.generate.side_effect = Exception("Connection failed")
        mock_ollama_class.return_value = mock_client

        planner = PlanningAgent()

        result = planner.execute("Create a plan", {"language": "python"})

        assert not result.success
        assert "Connection failed" in result.error
        assert result.agent_type == "plan"

    @patch("local_agents.base.OllamaClient")
    def test_agent_handles_model_unavailable(self, mock_ollama_class):
        """Test agent handles unavailable model."""
        mock_client = Mock(spec=OllamaClient)
        mock_client.is_model_available.return_value = False
        mock_client.pull_model.return_value = False
        mock_ollama_class.return_value = mock_client

        with pytest.raises(RuntimeError, match="Failed to pull model"):
            PlanningAgent(model="nonexistent:model")


class TestingAgentContextHandling:
    """Test how agents handle different context scenarios."""

    @patch("local_agents.base.OllamaClient")
    def test_agent_handles_empty_context(
        self, mock_ollama_class, mock_ollama_client_with_responses
    ):
        """Test agent handles empty or None context."""
        mock_ollama_class.return_value = mock_ollama_client_with_responses

        planner = PlanningAgent()

        # Test with None context
        result1 = planner.execute("Create a plan", None)
        assert result1.success

        # Test with empty context
        result2 = planner.execute("Create a plan", {})
        assert result2.success

    @patch("local_agents.base.OllamaClient")
    def test_agent_handles_rich_context(
        self, mock_ollama_class, mock_ollama_client_with_responses, sample_python_file
    ):
        """Test agent handles context with file content."""
        mock_ollama_class.return_value = mock_ollama_client_with_responses

        reviewer = ReviewAgent()

        context = {
            "target_file": str(sample_python_file),
            "code_content": sample_python_file.read_text(),
            "focus_area": "performance",
            "project_type": "library",
        }

        result = reviewer.execute("Review this Python file", context)

        assert result.success
        assert "review" in result.output.lower()
        # Verify the agent received and can work with rich context
        assert result.context == context

    @patch("local_agents.base.OllamaClient")
    def test_agent_context_propagation(self, mock_ollama_class, mock_ollama_client_with_responses):
        """Test that context is properly propagated through agent execution."""
        mock_ollama_class.return_value = mock_ollama_client_with_responses

        coder = CodingAgent()

        initial_context = {
            "language": "python",
            "style": "functional",
            "version": "3.9+",
        }

        result = coder.execute("Generate a function", initial_context)

        assert result.success
        assert result.context == initial_context
        # Context should be preserved in the result
        assert result.context["language"] == "python"
        assert result.context["style"] == "functional"


class TestingAgentStreamingSupport:
    """Test streaming functionality across agents."""

    @patch("local_agents.base.OllamaClient")
    def test_agent_streaming_mode(self, mock_ollama_class, mock_ollama_client_with_responses):
        """Test that agents properly support streaming mode."""
        mock_ollama_class.return_value = mock_ollama_client_with_responses

        planner = PlanningAgent()

        # Test with streaming enabled
        result = planner.execute(
            "Create implementation plan", {"project": "calculator"}, stream=True
        )

        assert result.success
        # Verify streaming parameter was passed to Ollama client
        mock_ollama_client_with_responses.generate.assert_called()
        call_args = mock_ollama_client_with_responses.generate.call_args
        assert call_args[1]["stream"] is True

    @patch("local_agents.base.OllamaClient")
    def test_agent_non_streaming_mode(self, mock_ollama_class, mock_ollama_client_with_responses):
        """Test that agents work in non-streaming mode."""
        mock_ollama_class.return_value = mock_ollama_client_with_responses

        planner = PlanningAgent()

        # Test with streaming disabled (default)
        result = planner.execute("Create implementation plan", {"project": "calculator"})

        assert result.success
        # Verify streaming parameter was passed as False
        call_args = mock_ollama_client_with_responses.generate.call_args
        assert call_args[1]["stream"] is False
