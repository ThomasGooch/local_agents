"""Tests for the review agent."""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from local_agents.agents.reviewer import ReviewAgent
from local_agents.base import TaskResult
from local_agents.ollama_client import OllamaClient


class TestReviewAgent:
    """Test ReviewAgent class."""

    @pytest.fixture
    def mock_ollama_client(self):
        """Create a mock Ollama client."""
        client = Mock(spec=OllamaClient)
        client.is_model_available.return_value = True
        client.generate.return_value = """# Code Review Report

## Summary
The code is well-structured with good error handling practices.

## Issues Found
### High Priority
- Potential SQL injection vulnerability in user_query function
- Missing input validation on user data

### Medium Priority  
- Code complexity could be reduced in calculate_metrics function
- Consider adding more comprehensive logging

## Recommendations
1. Use parameterized queries for database operations
2. Add input sanitization and validation
3. Refactor complex functions for better readability"""
        return client

    @pytest.fixture
    def reviewer_agent(self, mock_ollama_client):
        """Create a ReviewAgent instance for testing."""
        return ReviewAgent(
            model="test:model", ollama_client=mock_ollama_client
        )

    def test_agent_initialization(self, reviewer_agent):
        """Test review agent initialization."""
        assert reviewer_agent.agent_type == "review"
        assert (
            reviewer_agent.role == "Senior Code Reviewer and Quality Analyst"
        )
        assert "quality" in reviewer_agent.goal
        assert reviewer_agent.model == "test:model"

    def test_execute_success(self, reviewer_agent):
        """Test successful execution of review task."""
        task = "Review user authentication module"
        context = {
            "code_content": "def authenticate(username, password): return True",
            "focus_area": "security",
        }

        result = reviewer_agent.execute(task, context)

        assert isinstance(result, TaskResult)
        assert result.success is True
        assert "Code Review Report" in result.output
        assert "Issues Found" in result.output
        assert result.agent_type == "review"
        assert result.task == task
        assert result.context == context
        assert result.error is None

    def test_execute_failure(self, reviewer_agent):
        """Test execution failure handling."""
        reviewer_agent.ollama_client.generate.side_effect = Exception(
            "Review error"
        )

        task = "Review code"
        result = reviewer_agent.execute(task)

        assert isinstance(result, TaskResult)
        assert result.success is False
        assert result.output == ""
        assert result.error == "Review error"

    def test_build_review_prompt_basic(self, reviewer_agent):
        """Test building basic review prompt."""
        task = "Review payment processing module"
        context = {"focus_area": "security", "language": "python"}

        prompt = reviewer_agent._build_review_prompt(task, context)

        assert "# Code Review Task" in prompt
        assert task in prompt
        assert "## Review Instructions" in prompt
        assert "Focus Area: security" in prompt
        assert "Language: python" in prompt
        assert "## Review Criteria" in prompt
        assert "Security vulnerabilities" in prompt
        assert "Code quality" in prompt
        assert "Performance considerations" in prompt

    def test_build_review_prompt_with_code_content(self, reviewer_agent):
        """Test building review prompt with code content."""
        task = "Review database connection module"
        context = {
            "code_content": "import sqlite3\ndef connect(): return sqlite3.connect('db.sqlite')",
            "target_file": "database.py",
            "focus_area": "all",
        }

        prompt = reviewer_agent._build_review_prompt(task, context)

        assert "## Code to Review" in prompt
        assert "import sqlite3" in prompt
        assert "## Target File" in prompt
        assert "database.py" in prompt
        assert "Focus Area: all" in prompt

    def test_build_review_prompt_with_static_analysis(self, reviewer_agent):
        """Test building review prompt with static analysis results."""
        task = "Review with static analysis"
        context = {
            "code_content": "def test(): pass",
            "static_analysis_results": {
                "flake8": ["E302: expected 2 blank lines"],
                "pylint": ["C0111: Missing function docstring"],
                "bandit": ["B101: Use of assert detected"],
            },
        }

        prompt = reviewer_agent._build_review_prompt(task, context)

        assert "## Static Analysis Results" in prompt
        assert "flake8" in prompt
        assert "E302" in prompt
        assert "Missing function docstring" in prompt
        assert "Use of assert detected" in prompt

    @patch("os.path.exists", return_value=True)
    @patch("subprocess.run")
    def test_run_static_analysis_success(
        self, mock_run, mock_exists, reviewer_agent
    ):
        """Test successful static analysis execution."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="test.py:1:1: E302 expected 2 blank lines",
            stderr="",
        )

        result = reviewer_agent._run_static_analysis("test.py", "flake8")

        assert "E302" in result
        mock_run.assert_called_once()

    @patch("os.path.exists", return_value=True)
    @patch("subprocess.run")
    def test_run_static_analysis_timeout(
        self, mock_run, mock_exists, reviewer_agent
    ):
        """Test static analysis timeout handling."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("flake8", 30)

        result = reviewer_agent._run_static_analysis("test.py", "flake8")

        assert "timeout" in result.lower()
        assert len(result) > 0  # Should return error message

    @patch("os.path.exists", return_value=True)
    @patch("subprocess.run")
    def test_run_static_analysis_not_found(
        self, mock_run, mock_exists, reviewer_agent
    ):
        """Test static analysis tool not found."""
        mock_run.side_effect = FileNotFoundError("flake8 not found")

        result = reviewer_agent._run_static_analysis("test.py", "flake8")

        assert "not available" in result.lower()

    def test_review_for_security(self, reviewer_agent):
        """Test security-focused code review."""
        code = "SELECT * FROM users WHERE id = " + str(123)

        result = reviewer_agent.review_for_security(code)

        assert result.success is True
        assert "Review this code for security vulnerabilities" in result.task

        # Verify security focus in prompt
        call_args = reviewer_agent.ollama_client.generate.call_args
        prompt = call_args.kwargs["prompt"]
        assert "security" in prompt.lower()
        assert "SELECT * FROM users" in prompt

    def test_review_for_performance(self, reviewer_agent):
        """Test performance-focused code review."""
        code = "for i in range(1000000): result.append(expensive_operation(i))"

        result = reviewer_agent.review_for_performance(code)

        assert result.success is True
        assert "Review this code for performance issues" in result.task

        # Verify performance focus in prompt
        call_args = reviewer_agent.ollama_client.generate.call_args
        prompt = call_args.kwargs["prompt"]
        assert "performance" in prompt.lower()

    def test_review_for_maintainability(self, reviewer_agent):
        """Test maintainability-focused code review."""
        code = "def complex_function(a,b,c,d,e,f,g,h): return a+b+c+d+e+f+g+h if a else b"

        result = reviewer_agent.review_for_maintainability(code)

        assert result.success is True
        assert "Review this code for maintainability" in result.task

    def test_comprehensive_review(self, reviewer_agent):
        """Test comprehensive code review."""
        code = "def authenticate(user, pwd): return user == 'admin' and pwd == 'password'"
        target_file = "auth.py"

        result = reviewer_agent.comprehensive_review(code, target_file)

        assert result.success is True
        assert "Perform a comprehensive code review" in result.task

        # Verify comprehensive review includes all areas
        call_args = reviewer_agent.ollama_client.generate.call_args
        prompt = call_args.kwargs["prompt"]
        assert "security" in prompt.lower()
        assert "performance" in prompt.lower()
        assert "maintainability" in prompt.lower()

    @patch("local_agents.agents.reviewer.ReviewAgent._run_static_analysis")
    def test_static_analysis_integration(
        self, mock_static_analysis, reviewer_agent, temp_directory
    ):
        """Test static analysis integration."""
        # Create test file
        test_file = temp_directory / "test_code.py"
        test_file.write_text("def test(): pass")

        # Mock static analysis results
        mock_static_analysis.return_value = (
            "test_code.py:1:1: C0111 Missing function docstring"
        )

        task = "Review with static analysis"
        context = {
            "target_file": str(test_file),
            "enable_static_analysis": True,
            "analysis_tools": ["pylint"],
        }

        result = reviewer_agent.execute(task, context)

        assert result.success is True
        mock_static_analysis.assert_called()

    def test_multi_language_support(self, reviewer_agent):
        """Test review support for multiple languages."""
        languages = [
            {"language": "python", "code": "def hello(): print('Hello')"},
            {
                "language": "javascript",
                "code": "function hello() { console.log('Hello'); }",
            },
            {
                "language": "java",
                "code": "public void hello() { System.out.println('Hello'); }",
            },
            {
                "language": "go",
                "code": "func hello() { fmt.Println('Hello') }",
            },
        ]

        for lang_context in languages:
            task = f"Review {lang_context['language']} code"
            context = {
                "language": lang_context["language"],
                "code_content": lang_context["code"],
            }

            result = reviewer_agent.execute(task, context)

            assert result.success is True
            call_args = reviewer_agent.ollama_client.generate.call_args
            prompt = call_args.kwargs["prompt"]
            assert lang_context["language"] in prompt.lower()

    def test_severity_categorization(self, reviewer_agent):
        """Test that review results are categorized by severity."""
        task = "Review code with severity categorization"
        context = {
            "code_content": "def vulnerable_function(user_input): exec(user_input)",
            "categorize_findings": True,
        }

        result = reviewer_agent.execute(task, context)

        assert result.success is True
        call_args = reviewer_agent.ollama_client.generate.call_args
        prompt = call_args.kwargs["prompt"]
        assert "severity" in prompt.lower()
        assert "critical" in prompt.lower() or "high" in prompt.lower()

    def test_framework_specific_review(self, reviewer_agent):
        """Test framework-specific review guidelines."""
        frameworks = [
            {"framework": "django", "language": "python"},
            {"framework": "react", "language": "javascript"},
            {"framework": "spring", "language": "java"},
        ]

        for context in frameworks:
            task = f"Review {context['framework']} application code"
            context["code_content"] = "sample code"

            result = reviewer_agent.execute(task, context)

            assert result.success is True
            call_args = reviewer_agent.ollama_client.generate.call_args
            prompt = call_args.kwargs["prompt"]
            assert context["framework"] in prompt.lower()

    def test_execute_with_stream(self, reviewer_agent):
        """Test execution with streaming."""
        task = "Stream review process"

        result = reviewer_agent.execute(task, stream=True)

        assert result.success is True
        reviewer_agent.ollama_client.generate.assert_called_once()
        call_args = reviewer_agent.ollama_client.generate.call_args
        assert call_args.kwargs["stream"] is True

    @patch("local_agents.base.get_model_for_agent")
    def test_default_model_selection(self, mock_get_model, mock_ollama_client):
        """Test default model selection for review agent."""
        mock_get_model.return_value = "llama3.1:8b"

        agent = ReviewAgent(ollama_client=mock_ollama_client)

        mock_get_model.assert_called_with("review")
        assert agent.model == "llama3.1:8b"

    def test_review_metrics_extraction(self, reviewer_agent):
        """Test extraction of review metrics."""
        task = "Extract metrics from code review"
        context = {
            "code_content": "def complex_func(a,b,c,d): return a+b+c+d",
            "extract_metrics": True,
        }

        result = reviewer_agent.execute(task, context)

        assert result.success is True
        call_args = reviewer_agent.ollama_client.generate.call_args
        prompt = call_args.kwargs["prompt"]
        assert "metrics" in prompt.lower()

    @patch("local_agents.agents.reviewer.ReviewAgent._run_static_analysis")
    def test_fallback_analysis_when_tools_unavailable(
        self, mock_static_analysis, reviewer_agent
    ):
        """Test fallback analysis when static analysis tools are unavailable."""
        # Mock all tools as unavailable
        mock_static_analysis.side_effect = [
            "Tool not available",
            "Tool not available",
            "Tool not available",
        ]

        task = "Review with fallback analysis"
        context = {
            "code_content": "def test(): pass",
            "enable_static_analysis": True,
        }

        result = reviewer_agent.execute(task, context)

        # Should still succeed with manual analysis
        assert result.success is True
        # Static analysis should have been attempted
        assert mock_static_analysis.called

    def test_code_review_with_context_history(self, reviewer_agent):
        """Test code review with historical context."""
        task = "Review code with historical context"
        context = {
            "code_content": "def improved_function(): return 'better'",
            "previous_reviews": [
                "Previous issue: Function was too complex",
                "Previous recommendation: Simplify return logic",
            ],
            "changes_made": "Simplified function implementation",
        }

        result = reviewer_agent.execute(task, context)

        assert result.success is True
        call_args = reviewer_agent.ollama_client.generate.call_args
        prompt = call_args.kwargs["prompt"]
        assert "previous reviews" in prompt.lower()
        assert "changes made" in prompt.lower()
