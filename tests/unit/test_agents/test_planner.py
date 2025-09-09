"""Tests for the planning agent."""

from unittest.mock import Mock, patch

import pytest

from local_agents.agents.planner import PlanningAgent
from local_agents.base import TaskResult
from local_agents.ollama_client import OllamaClient


class TestPlanningAgent:
    """Test PlanningAgent class."""

    @pytest.fixture
    def mock_ollama_client(self):
        """Create a mock Ollama client."""
        client = Mock(spec=OllamaClient)
        client.is_model_available.return_value = True
        client.generate.return_value = "Generated plan content"
        return client

    @pytest.fixture
    def planner_agent(self, mock_ollama_client):
        """Create a PlanningAgent instance for testing."""
        return PlanningAgent(
            model="test:model", ollama_client=mock_ollama_client
        )

    def test_agent_initialization(self, planner_agent):
        """Test planning agent initialization."""
        assert planner_agent.agent_type == "plan"
        assert (
            planner_agent.role
            == "Senior Software Architect and Project Planner"
        )
        assert "implementation plans" in planner_agent.goal
        assert planner_agent.model == "test:model"

    def test_execute_success(self, planner_agent):
        """Test successful execution of planning task."""
        task = "Create a user authentication system"
        context = {"file_content": "existing code"}

        result = planner_agent.execute(task, context)

        assert isinstance(result, TaskResult)
        assert result.success is True
        assert result.output == "Generated plan content"
        assert result.agent_type == "plan"
        assert result.task == task
        assert result.context == context
        assert result.error is None

    def test_execute_failure(self, planner_agent):
        """Test execution failure handling."""
        planner_agent.ollama_client.generate.side_effect = Exception(
            "Connection error"
        )

        task = "Create a plan"
        result = planner_agent.execute(task)

        assert isinstance(result, TaskResult)
        assert result.success is False
        assert result.output == ""
        assert result.error == "Connection error"

    def test_build_planning_prompt_basic(self, planner_agent):
        """Test building basic planning prompt."""
        task = "Add user authentication"
        context = {}

        prompt = planner_agent._build_planning_prompt(task, context)

        assert "# Implementation Planning Task" in prompt
        assert task in prompt
        assert "## Planning Instructions" in prompt
        assert "Analysis & Requirements" in prompt
        assert "Architecture & Design" in prompt
        assert "Implementation Steps" in prompt

    def test_build_planning_prompt_with_context(self, planner_agent):
        """Test building planning prompt with context."""
        task = "Add user authentication"
        context = {
            "file_content": "class User:\n    pass",
            "directory": "/app/src",
            "specification": "Use JWT tokens",
        }

        prompt = planner_agent._build_planning_prompt(task, context)

        assert "## Context File Content" in prompt
        assert "class User:" in prompt
        assert "## Working Directory" in prompt
        assert "/app/src" in prompt
        assert "## Additional Specifications" in prompt
        assert "Use JWT tokens" in prompt

    def test_plan_feature(self, planner_agent):
        """Test planning a feature."""
        feature_description = "User dashboard with analytics"

        result = planner_agent.plan_feature(feature_description)

        assert result.success is True
        assert (
            "Plan implementation of new feature: User dashboard with analytics"
            in result.task
        )
        planner_agent.ollama_client.generate.assert_called_once()

    def test_plan_bugfix(self, planner_agent):
        """Test planning a bug fix."""
        bug_description = "Memory leak in data processor"

        result = planner_agent.plan_bugfix(bug_description)

        assert result.success is True
        assert "Plan bug fix for: Memory leak in data processor" in result.task
        planner_agent.ollama_client.generate.assert_called_once()

    def test_plan_refactor(self, planner_agent):
        """Test planning a refactor."""
        refactor_description = "Extract common utilities to shared module"

        result = planner_agent.plan_refactor(refactor_description)

        assert result.success is True
        assert (
            "Plan refactoring: Extract common utilities to shared module"
            in result.task
        )
        planner_agent.ollama_client.generate.assert_called_once()

    def test_execute_with_stream(self, planner_agent):
        """Test execution with streaming."""
        task = "Create a plan"

        result = planner_agent.execute(task, stream=True)

        assert result.success is True
        planner_agent.ollama_client.generate.assert_called_once()
        call_args = planner_agent.ollama_client.generate.call_args
        assert call_args.kwargs["stream"] is True

    @patch("local_agents.base.get_model_for_agent")
    def test_default_model_selection(self, mock_get_model, mock_ollama_client):
        """Test default model selection for planning agent."""
        mock_get_model.return_value = "llama3.1:8b"

        agent = PlanningAgent(ollama_client=mock_ollama_client)

        mock_get_model.assert_called_with("plan")
        assert agent.model == "llama3.1:8b"

    def test_context_types_in_prompt(self, planner_agent):
        """Test different context types are handled in prompt."""
        contexts = [
            {"plan_type": "feature"},
            {"plan_type": "bugfix"},
            {"plan_type": "refactor"},
        ]

        for context in contexts:
            task = "Test task"
            result = planner_agent.execute(task, context)
            assert result.success is True
            assert result.context == context
