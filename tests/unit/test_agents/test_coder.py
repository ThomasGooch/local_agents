"""Tests for the coding agent."""

from unittest.mock import Mock, patch

import pytest

from local_agents.agents.coder import CodingAgent
from local_agents.base import TaskResult
from local_agents.ollama_client import OllamaClient


class TestCodingAgent:
    """Test CodingAgent class."""

    @pytest.fixture
    def mock_ollama_client(self):
        """Create a mock Ollama client."""
        client = Mock(spec=OllamaClient)
        client.is_model_available.return_value = True
        client.generate.return_value = (
            "```python\ndef hello():\n    return 'Hello, World!'\n```"
        )
        return client

    @pytest.fixture
    def coder_agent(self, mock_ollama_client):
        """Create a CodingAgent instance for testing."""
        return CodingAgent(model="test:model", ollama_client=mock_ollama_client)

    def test_agent_initialization(self, coder_agent):
        """Test coding agent initialization."""
        assert coder_agent.agent_type == "code"
        assert coder_agent.role == "Senior Software Engineer and Code Generator"
        assert "high-quality" in coder_agent.goal
        assert coder_agent.model == "test:model"

    def test_execute_success(self, coder_agent):
        """Test successful execution of coding task."""
        task = "Create a hello world function"
        context = {"language": "python", "style": "functional"}

        result = coder_agent.execute(task, context)

        assert isinstance(result, TaskResult)
        assert result.success is True
        assert "def hello" in result.output
        assert "Hello, World!" in result.output
        assert result.agent_type == "code"
        assert result.task == task
        assert result.context == context
        assert result.error is None

    def test_execute_failure(self, coder_agent):
        """Test execution failure handling."""
        coder_agent.ollama_client.generate.side_effect = Exception("Model error")

        task = "Generate code"
        result = coder_agent.execute(task)

        assert isinstance(result, TaskResult)
        assert result.success is False
        assert result.output == ""
        assert result.error == "Model error"

    def test_build_coding_prompt_basic(self, coder_agent):
        """Test building basic coding prompt."""
        task = "Create a calculator function"
        context = {"language": "python"}

        prompt = coder_agent._build_coding_prompt(task, context)

        assert "# Code Generation Task" in prompt
        assert task in prompt
        assert "## Coding Instructions" in prompt
        assert "Language: python" in prompt
        assert "Code Quality" in prompt
        assert "Best Practices" in prompt

    def test_build_coding_prompt_with_implementation_plan(self, coder_agent):
        """Test building coding prompt with implementation plan."""
        task = "Implement user authentication"
        context = {
            "language": "python",
            "implementation_plan": "1. Create User class\n2. Add authentication methods",
            "target_file": "auth.py",
        }

        prompt = coder_agent._build_coding_prompt(task, context)

        assert "## Implementation Plan" in prompt
        assert "Create User class" in prompt
        assert "## Target File" in prompt
        assert "auth.py" in prompt
        assert "Language: python" in prompt

    def test_build_coding_prompt_with_existing_code(self, coder_agent):
        """Test building coding prompt with existing code context."""
        task = "Add error handling to existing function"
        context = {
            "language": "python",
            "existing_code": "def divide(a, b):\n    return a / b",
            "requirements": "Add division by zero protection",
        }

        prompt = coder_agent._build_coding_prompt(task, context)

        assert "## Existing Code" in prompt
        assert "def divide(a, b)" in prompt
        assert "## Requirements" in prompt
        assert "division by zero protection" in prompt

    def test_generate_function(self, coder_agent):
        """Test generating a function."""
        function_spec = "Calculate factorial of a number"
        language = "python"

        result = coder_agent.generate_function(function_spec, language)

        assert result.success is True
        assert f"Generate function: {function_spec}" in result.task
        coder_agent.ollama_client.generate.assert_called_once()

        # Verify context contains language
        call_args = coder_agent.ollama_client.generate.call_args
        prompt = call_args.kwargs["prompt"]  # Second argument is prompt
        assert "Language: python" in prompt

    def test_generate_class(self, coder_agent):
        """Test generating a class."""
        class_spec = "User model with authentication methods"
        language = "python"

        result = coder_agent.generate_class(class_spec, language)

        assert result.success is True
        assert f"Generate class: {class_spec}" in result.task

    def test_implement_feature(self, coder_agent):
        """Test implementing a feature."""
        feature_description = "Shopping cart functionality"
        context = {"language": "python", "framework": "flask", "database": "postgresql"}

        result = coder_agent.implement_feature(feature_description, context)

        assert result.success is True
        assert f"Implement feature: {feature_description}" in result.task
        assert result.context == context

    def test_fix_bug(self, coder_agent):
        """Test fixing a bug."""
        bug_description = "Memory leak in data processing loop"
        context = {
            "language": "python",
            "buggy_code": "while True:\n    data = load_data()\n    process(data)",
            "error_message": "Memory usage keeps growing",
        }

        result = coder_agent.fix_bug(bug_description, context)

        assert result.success is True
        assert f"Fix bug: {bug_description}" in result.task

    def test_refactor_code(self, coder_agent):
        """Test refactoring code."""
        refactor_description = "Extract common utilities to shared module"
        context = {
            "language": "python",
            "code_to_refactor": "def util1():\n    pass\ndef util2():\n    pass",
            "target_structure": "utils.py module",
        }

        result = coder_agent.refactor_code(refactor_description, context)

        assert result.success is True
        assert f"Refactor code: {refactor_description}" in result.task

    def test_multiple_language_support(self, coder_agent):
        """Test support for multiple programming languages."""
        languages = ["python", "javascript", "java", "go", "rust"]

        for language in languages:
            task = f"Create hello world in {language}"
            context = {"language": language}

            result = coder_agent.execute(task, context)

            assert result.success is True
            # Verify language appears in the prompt
            call_args = coder_agent.ollama_client.generate.call_args
            prompt = call_args.kwargs["prompt"]
            assert f"Language: {language}" in prompt

    def test_code_style_guidelines(self, coder_agent):
        """Test that coding prompts include style guidelines."""
        task = "Create a data structure"
        context = {
            "language": "python",
            "style_guide": "PEP 8",
            "docstring_style": "Google",
        }

        result = coder_agent.execute(task, context)

        assert result.success is True
        call_args = coder_agent.ollama_client.generate.call_args
        prompt = call_args.kwargs["prompt"]
        assert "PEP 8" in prompt
        assert "Google" in prompt

    def test_execute_with_stream(self, coder_agent):
        """Test execution with streaming."""
        task = "Generate streaming code"

        result = coder_agent.execute(task, stream=True)

        assert result.success is True
        coder_agent.ollama_client.generate.assert_called_once()
        call_args = coder_agent.ollama_client.generate.call_args
        assert call_args.kwargs["stream"] is True

    @patch("local_agents.base.get_model_for_agent")
    def test_default_model_selection(self, mock_get_model, mock_ollama_client):
        """Test default model selection for coding agent."""
        mock_get_model.return_value = "codellama:7b"

        agent = CodingAgent(ollama_client=mock_ollama_client)

        mock_get_model.assert_called_with("code")
        assert agent.model == "codellama:7b"

    def test_framework_specific_prompts(self, coder_agent):
        """Test framework-specific prompt generation."""
        frameworks = [
            {"language": "python", "framework": "django"},
            {"language": "javascript", "framework": "react"},
            {"language": "java", "framework": "spring"},
        ]

        for context in frameworks:
            task = f"Create API endpoint using {context['framework']}"
            result = coder_agent.execute(task, context)

            assert result.success is True
            call_args = coder_agent.ollama_client.generate.call_args
            prompt = call_args.kwargs["prompt"]
            assert context["framework"] in prompt.lower()

    def test_code_review_integration_context(self, coder_agent):
        """Test that coding agent can use code review feedback."""
        task = "Improve code based on review feedback"
        context = {
            "language": "python",
            "existing_code": "def calc(x, y): return x/y",
            "review_feedback": "Add error handling for division by zero",
            "suggestions": ["Use try-except", "Validate inputs"],
        }

        result = coder_agent.execute(task, context)

        assert result.success is True
        call_args = coder_agent.ollama_client.generate.call_args
        prompt = call_args.kwargs["prompt"]
        assert "review_feedback" in prompt.lower() or "review feedback" in prompt
        assert "division by zero" in prompt
