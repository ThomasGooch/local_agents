"""Tests for the planning agent."""

import tempfile
from pathlib import Path
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
        return PlanningAgent(model="test:model", ollama_client=mock_ollama_client)

    def test_agent_initialization(self, planner_agent):
        """Test planning agent initialization."""
        assert planner_agent.agent_type == "plan"
        assert planner_agent.role == "Senior Software Architect and Project Planner"
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
        # Context should contain original context plus plan file info
        assert result.context["file_content"] == context["file_content"]
        assert "plan_file" in result.context
        assert "plan_content" in result.context
        assert result.error is None

    def test_execute_failure(self, planner_agent):
        """Test execution failure handling."""
        planner_agent.ollama_client.generate.side_effect = Exception("Connection error")

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
        assert "Plan implementation of new feature: User dashboard with analytics" in result.task
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
        assert "Plan refactoring: Extract common utilities to shared module" in result.task
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
            # Context should contain original context plus plan file info
            assert result.context["plan_type"] == context["plan_type"]
            assert "plan_file" in result.context
            assert "plan_content" in result.context

    def test_plan_file_output_disabled(self, planner_agent):
        """Test plan execution when file output is disabled."""
        task = "Create a test plan"
        context = {"file_content": "test content"}

        with patch("local_agents.config.get_config") as mock_config:
            mock_plan_config = Mock()
            mock_plan_config.enable_file_output = False
            mock_config.return_value.plan_output = mock_plan_config

            result = planner_agent.execute(task, context)

            assert result.success is True
            assert "plan_file" not in result.context
            assert "plan_content" not in result.context

    def test_plan_file_output_enabled(self, planner_agent):
        """Test plan execution when file output is enabled."""
        task = "Create a test plan"
        context = {"file_content": "test content"}

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("local_agents.config.get_config") as mock_config:
                mock_plan_config = Mock()
                mock_plan_config.enable_file_output = True
                mock_plan_config.output_directory = temp_dir
                mock_plan_config.filename_format = "plan_{timestamp}_{task_hash}.md"
                mock_plan_config.include_context_in_filename = False
                mock_plan_config.max_filename_length = 255
                mock_plan_config.preserve_plans = True
                mock_config.return_value.plan_output = mock_plan_config

                result = planner_agent.execute(task, context)

                assert result.success is True
                assert "plan_file" in result.context
                assert "plan_content" in result.context
                assert result.context["plan_content"] == "Generated plan content"

                # Check that the file was actually created
                plan_file_path = Path(result.context["plan_file"])
                assert plan_file_path.exists()
                assert plan_file_path.suffix == ".md"

    def test_plan_file_content_format(self, planner_agent):
        """Test the format of the generated plan file."""
        task = "Create a test plan"
        context = {"plan_type": "feature", "directory": "/test/dir"}

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("local_agents.config.get_config") as mock_config:
                mock_plan_config = Mock()
                mock_plan_config.enable_file_output = True
                mock_plan_config.output_directory = temp_dir
                mock_plan_config.filename_format = "plan_{timestamp}_{task_hash}.md"
                mock_plan_config.include_context_in_filename = False
                mock_plan_config.max_filename_length = 255
                mock_plan_config.preserve_plans = True
                mock_config.return_value.plan_output = mock_plan_config

                result = planner_agent.execute(task, context)
                plan_file_path = Path(result.context["plan_file"])
                file_content = plan_file_path.read_text(encoding='utf-8')

                # Check metadata section
                assert "# Planning Session Metadata" in file_content
                assert f"- **Task**: {task}" in file_content
                assert f"- **Model**: {planner_agent.model}" in file_content
                assert "- **Plan Type**: feature" in file_content
                assert "- **Working Directory**: /test/dir" in file_content

                # Check plan section
                assert "# Implementation Plan" in file_content
                assert "Generated plan content" in file_content

    def test_plan_filename_with_context(self, planner_agent):
        """Test plan filename generation with context information."""
        task = "Create a feature plan"
        context = {"plan_type": "feature"}

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("local_agents.config.get_config") as mock_config:
                mock_plan_config = Mock()
                mock_plan_config.enable_file_output = True
                mock_plan_config.output_directory = temp_dir
                mock_plan_config.filename_format = "plan_{timestamp}_{task_hash}.md"
                mock_plan_config.include_context_in_filename = True
                mock_plan_config.max_filename_length = 255
                mock_plan_config.preserve_plans = True
                mock_config.return_value.plan_output = mock_plan_config

                result = planner_agent.execute(task, context)
                plan_file_path = Path(result.context["plan_file"])

                assert "_feature.md" in plan_file_path.name

    def test_plan_filename_length_limitation(self, planner_agent):
        """Test plan filename length is properly limited."""
        task = "Create a very long task description that might exceed the filename length limit" * 5
        context = {"plan_type": "feature"}

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("local_agents.config.get_config") as mock_config:
                mock_plan_config = Mock()
                mock_plan_config.enable_file_output = True
                mock_plan_config.output_directory = temp_dir
                mock_plan_config.filename_format = "plan_{timestamp}_{task_hash}.md"
                mock_plan_config.include_context_in_filename = False
                mock_plan_config.max_filename_length = 50
                mock_plan_config.preserve_plans = True
                mock_config.return_value.plan_output = mock_plan_config

                result = planner_agent.execute(task, context)
                plan_file_path = Path(result.context["plan_file"])

                assert len(plan_file_path.name) <= 50

    def test_plan_file_creation_error_handling(self, planner_agent):
        """Test error handling when plan file creation fails."""
        task = "Create a test plan"
        context = {}

        with patch("local_agents.config.get_config") as mock_config:
            mock_plan_config = Mock()
            mock_plan_config.enable_file_output = True
            mock_plan_config.output_directory = "/invalid/path/that/does/not/exist"
            mock_plan_config.filename_format = "plan_{timestamp}_{task_hash}.md"
            mock_plan_config.include_context_in_filename = False
            mock_plan_config.max_filename_length = 255
            mock_plan_config.preserve_plans = True
            mock_config.return_value.plan_output = mock_plan_config

            # Should not crash, but should not include plan_file in result
            result = planner_agent.execute(task, context)

            assert result.success is True
            # File creation failed, so these should not be in context
            assert "plan_file" not in result.context or result.context["plan_file"] is None
