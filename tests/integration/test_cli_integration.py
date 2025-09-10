"""Integration tests for CLI functionality."""

from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from local_agents.base import TaskResult
from local_agents.cli import code, main, plan, review, test, workflow
from local_agents.workflows.orchestrator import WorkflowResult


@pytest.fixture
def cli_runner():
    """Create a Click CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_successful_agent():
    """Mock agent that returns successful results."""
    mock_agent = Mock()
    mock_agent.agent_type = "mock"
    mock_agent.execute.return_value = TaskResult(
        success=True,
        output="Mock successful output",
        agent_type="mock",
        task="Mock task",
    )
    mock_agent.display_info.return_value = None
    return mock_agent


@pytest.fixture
def mock_failed_agent():
    """Mock agent that returns failed results."""
    mock_agent = Mock()
    mock_agent.agent_type = "mock"
    mock_agent.execute.return_value = TaskResult(
        success=False,
        output="",
        agent_type="mock",
        task="Mock task",
        error="Mock error occurred",
    )
    mock_agent.display_info.return_value = None
    return mock_agent


class TestCLIBasicCommands:
    """Test basic CLI command functionality."""

    def test_main_help(self, cli_runner):
        """Test main help command."""
        result = cli_runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "Local Agents" in result.output
        assert "plan" in result.output
        assert "code" in result.output
        assert "test" in result.output
        assert "review" in result.output
        assert "workflow" in result.output

    def test_main_version(self, cli_runner):
        """Test version display."""
        result = cli_runner.invoke(main, ["--version"])

        assert result.exit_code == 0
        assert "version" in result.output.lower()

    def test_main_without_command(self, cli_runner):
        """Test main command without subcommand shows welcome."""
        result = cli_runner.invoke(main, [])

        assert result.exit_code == 0
        assert "Local Agents" in result.output
        assert "Welcome" in result.output or "Available Commands" in result.output

    @patch("local_agents.cli.PlanningAgent")
    def test_plan_command_success(self, mock_agent_class, cli_runner, mock_successful_agent):
        """Test successful plan command execution."""
        mock_agent_class.return_value = mock_successful_agent

        result = cli_runner.invoke(plan, ["Create a calculator app"])

        assert result.exit_code == 0
        mock_agent_class.assert_called_once()
        mock_successful_agent.execute.assert_called_once()
        mock_successful_agent.display_info.assert_called_once()

    @patch("local_agents.cli.CodingAgent")
    def test_code_command_success(self, mock_agent_class, cli_runner, mock_successful_agent):
        """Test successful code command execution."""
        mock_agent_class.return_value = mock_successful_agent

        result = cli_runner.invoke(code, ["Implement calculator function"])

        assert result.exit_code == 0
        mock_agent_class.assert_called_once()
        mock_successful_agent.execute.assert_called_once()

    @patch("local_agents.cli.TestingAgent")
    def test_test_command_success(self, mock_agent_class, cli_runner, mock_successful_agent):
        """Test successful test command execution."""
        mock_agent_class.return_value = mock_successful_agent

        result = cli_runner.invoke(test, ["calculator.py"])

        assert result.exit_code == 0
        mock_agent_class.assert_called_once()
        mock_successful_agent.execute.assert_called_once()

    @patch("local_agents.cli.ReviewAgent")
    def test_review_command_success(
        self,
        mock_agent_class,
        cli_runner,
        mock_successful_agent,
        temp_directory,
    ):
        """Test successful review command execution."""
        mock_agent_class.return_value = mock_successful_agent

        # Create a temporary file to review
        test_file = temp_directory / "test.py"
        test_file.write_text("def hello(): pass")

        result = cli_runner.invoke(review, [str(test_file)])

        assert result.exit_code == 0
        mock_agent_class.assert_called_once()
        mock_successful_agent.execute.assert_called_once()


class TestCLICommandOptions:
    """Test CLI command options and parameters."""

    @patch("local_agents.cli.PlanningAgent")
    def test_plan_with_output_file(
        self,
        mock_agent_class,
        cli_runner,
        mock_successful_agent,
        temp_directory,
    ):
        """Test plan command with output file option."""
        mock_agent_class.return_value = mock_successful_agent
        output_file = temp_directory / "plan.md"

        result = cli_runner.invoke(plan, ["Create a web app", "--output", str(output_file)])

        assert result.exit_code == 0
        assert output_file.exists()
        assert output_file.read_text() == "Mock successful output"

    @patch("local_agents.cli.PlanningAgent")
    def test_plan_with_context_file(
        self,
        mock_agent_class,
        cli_runner,
        mock_successful_agent,
        sample_python_file,
    ):
        """Test plan command with context file."""
        mock_agent_class.return_value = mock_successful_agent

        result = cli_runner.invoke(
            plan, ["Improve this code", "--context", str(sample_python_file)]
        )

        assert result.exit_code == 0
        # Verify context was passed to agent
        call_args = mock_successful_agent.execute.call_args
        context = call_args[0][1]  # Second argument is context
        assert "file_content" in context

    @patch("local_agents.cli.CodingAgent")
    def test_code_with_file_option(self, mock_agent_class, cli_runner, mock_successful_agent):
        """Test code command with file option."""
        mock_agent_class.return_value = mock_successful_agent

        result = cli_runner.invoke(code, ["Add error handling", "--file", "calculator.py"])

        assert result.exit_code == 0
        # Verify file context was passed
        call_args = mock_successful_agent.execute.call_args
        context = call_args[0][1]
        assert "target_file" in context
        assert context["target_file"] == "calculator.py"

    @patch("local_agents.cli.TestingAgent")
    def test_test_with_framework_option(self, mock_agent_class, cli_runner, mock_successful_agent):
        """Test test command with framework option."""
        mock_agent_class.return_value = mock_successful_agent

        result = cli_runner.invoke(test, ["calculator.py", "--framework", "pytest"])

        assert result.exit_code == 0
        # Verify framework was passed in context
        call_args = mock_successful_agent.execute.call_args
        context = call_args[0][1]
        assert "framework" in context
        assert context["framework"] == "pytest"

    @patch("local_agents.cli.ReviewAgent")
    def test_review_with_focus_option(
        self,
        mock_agent_class,
        cli_runner,
        mock_successful_agent,
        sample_python_file,
    ):
        """Test review command with focus option."""
        mock_agent_class.return_value = mock_successful_agent

        result = cli_runner.invoke(review, [str(sample_python_file), "--focus", "security"])

        assert result.exit_code == 0
        # Verify focus area was passed in context
        call_args = mock_successful_agent.execute.call_args
        context = call_args[0][1]
        assert "focus_area" in context
        assert context["focus_area"] == "security"

    @patch("local_agents.cli.PlanningAgent")
    def test_streaming_option(self, mock_agent_class, cli_runner, mock_successful_agent):
        """Test streaming option is passed to agents."""
        mock_agent_class.return_value = mock_successful_agent

        result = cli_runner.invoke(plan, ["Create app", "--stream"])

        assert result.exit_code == 0
        # Verify streaming was passed to agent
        call_args = mock_successful_agent.execute.call_args
        assert call_args[1]["stream"] is True  # stream is keyword arg


class TestCLIErrorHandling:
    """Test CLI error handling scenarios."""

    @patch("local_agents.cli.PlanningAgent")
    def test_agent_failure_handling(self, mock_agent_class, cli_runner, mock_failed_agent):
        """Test CLI handles agent failures gracefully."""
        mock_agent_class.return_value = mock_failed_agent

        result = cli_runner.invoke(plan, ["Create a plan"])

        # CLI should not crash but should show error
        assert result.exit_code == 0  # CLI itself doesn't exit with error
        # Error should be displayed through agent's error handling
        mock_failed_agent.execute.assert_called_once()

    @patch("local_agents.cli.PlanningAgent")
    def test_connection_error_handling(self, mock_agent_class, cli_runner):
        """Test CLI handles connection errors gracefully."""
        # Mock agent that raises ConnectionError
        mock_agent = Mock()
        mock_agent.display_info.return_value = None
        mock_agent.execute.side_effect = ConnectionError("Cannot connect to Ollama")
        mock_agent_class.return_value = mock_agent

        result = cli_runner.invoke(plan, ["Test connection error"])

        assert result.exit_code == 0
        # Should display connection error panel
        assert "Connection Error" in result.output or "Connection Failed" in result.output

    @patch("local_agents.cli.PlanningAgent")
    def test_timeout_error_handling(self, mock_agent_class, cli_runner):
        """Test CLI handles timeout errors gracefully."""
        mock_agent = Mock()
        mock_agent.display_info.return_value = None
        mock_agent.execute.side_effect = TimeoutError("Request timed out")
        mock_agent_class.return_value = mock_agent

        result = cli_runner.invoke(plan, ["Test timeout"])

        assert result.exit_code == 0
        assert "Timeout" in result.output or "timed out" in result.output

    def test_review_nonexistent_file(self, cli_runner):
        """Test review command with nonexistent file."""
        result = cli_runner.invoke(review, ["/nonexistent/file.py"])

        assert result.exit_code == 0
        assert "does not exist" in result.output


class TestWorkflowCLI:
    """Test workflow CLI functionality."""

    @patch("local_agents.cli.Workflow")
    def test_workflow_command_success(self, mock_workflow_class, cli_runner):
        """Test successful workflow command execution."""
        mock_workflow = Mock()

        # Create a proper WorkflowResult object
        mock_task_result = TaskResult(
            success=True,
            output="Mock output",
            agent_type="plan",
            task="Create calculator",
        )

        mock_workflow_result = WorkflowResult(
            success=True,
            results=[mock_task_result],
            workflow_name="feature-dev",
            task="Create calculator",
            total_steps=1,
            completed_steps=1,
            execution_time=1.0,
        )

        mock_workflow.execute_workflow.return_value = mock_workflow_result
        mock_workflow_class.return_value = mock_workflow

        result = cli_runner.invoke(workflow, ["feature-dev", "Create calculator"])

        assert result.exit_code == 0
        # Check that execute_workflow was called with output_directory set to PWD
        mock_workflow.execute_workflow.assert_called_once()
        call_args = mock_workflow.execute_workflow.call_args
        assert call_args[0][0] == "feature-dev"
        assert call_args[0][1] == "Create calculator"
        assert "output_directory" in call_args[0][2]  # Should have output_directory
        assert call_args[1]["stream"] is False

    @patch("local_agents.cli.Workflow")
    def test_workflow_with_context(self, mock_workflow_class, cli_runner, sample_python_file):
        """Test workflow command with context file."""
        mock_workflow = Mock()
        mock_workflow.execute_workflow.return_value = {
            "workflow_name": "code-review",
            "success": True,
            "steps": [{"agent_type": "review", "success": True}],
        }
        mock_workflow_class.return_value = mock_workflow

        result = cli_runner.invoke(
            workflow,
            [
                "code-review",
                "Review this code",
                "--context",
                str(sample_python_file),
            ],
        )

        assert result.exit_code == 0
        # Verify context was passed
        call_args = mock_workflow.execute_workflow.call_args
        context = call_args[0][2]  # Third argument is context
        assert "file_content" in context

    @patch("local_agents.cli.Workflow")
    def test_workflow_with_output_dir(self, mock_workflow_class, cli_runner, temp_directory):
        """Test workflow command with output directory."""
        mock_workflow = Mock()
        mock_workflow.execute_workflow.return_value = {
            "workflow_name": "feature-dev",
            "success": True,
            "steps": [],
        }
        mock_workflow_class.return_value = mock_workflow

        output_dir = temp_directory / "workflow_output"

        result = cli_runner.invoke(
            workflow,
            ["feature-dev", "Create feature", "--output-dir", str(output_dir)],
        )

        assert result.exit_code == 0
        # Output directory should be created
        assert output_dir.exists()

    @patch("local_agents.cli.Workflow")
    def test_workflow_error_handling(self, mock_workflow_class, cli_runner):
        """Test workflow error handling."""
        mock_workflow = Mock()
        mock_workflow.execute_workflow.side_effect = ValueError("Unknown workflow: invalid")
        mock_workflow_class.return_value = mock_workflow

        result = cli_runner.invoke(workflow, ["invalid", "Test task"])

        assert result.exit_code == 0
        assert "Error" in result.output


class TestConfigCLI:
    """Test configuration CLI functionality."""

    @patch("local_agents.cli.config_manager")
    def test_config_show(self, mock_config_manager, cli_runner):
        """Test config show command."""
        # Mock config object
        mock_config = Mock()
        mock_config.default_model = "llama3.1:8b"
        mock_config.ollama_host = "http://localhost:11434"
        mock_config.temperature = 0.7
        mock_config.max_tokens = 4096
        mock_config.agents.planning = "llama3.1:8b"
        mock_config.agents.coding = "codellama:7b"
        mock_config.agents.testing = "deepseek-coder:6.7b"
        mock_config.agents.reviewing = "llama3.1:8b"

        # Mock plan output config
        mock_config.plan_output.enable_file_output = True
        mock_config.plan_output.output_directory = "./plans"
        mock_config.plan_output.filename_format = "plan_{timestamp}_{task_hash}.md"

        mock_config_manager.config_path = "/test/config.yml"
        mock_config_manager.load_config.return_value = mock_config

        # Import config command
        from local_agents.cli import config as config_command

        result = cli_runner.invoke(config_command, ["show"])

        assert result.exit_code == 0
        assert "Configuration" in result.output
        assert "llama3.1:8b" in result.output
        assert "localhost:11434" in result.output
        # Check plan output configuration is displayed
        assert "Plan Output" in result.output
        assert "True" in result.output  # enable_file_output
        assert "./plans" in result.output  # output_directory

    @patch("local_agents.cli.config_manager")
    def test_config_set(self, mock_config_manager, cli_runner):
        """Test config set command."""
        mock_config = Mock()
        mock_config.temperature = 0.7
        mock_config_manager.load_config.return_value = mock_config

        from local_agents.cli import config as config_command

        result = cli_runner.invoke(config_command, ["set", "temperature", "0.8"])

        assert result.exit_code == 0
        # Verify set operation was attempted
        mock_config_manager.load_config.assert_called()

    @patch("local_agents.cli.config_manager")
    def test_config_reset(self, mock_config_manager, cli_runner):
        """Test config reset command."""
        from local_agents.cli import config as config_command

        result = cli_runner.invoke(config_command, ["reset", "--force"])

        assert result.exit_code == 0
        assert "reset" in result.output.lower()
        mock_config_manager.save_config.assert_called_once()


class TestCLIInputOutput:
    """Test CLI input/output handling."""

    @patch("local_agents.cli.PlanningAgent")
    def test_output_file_creation(
        self,
        mock_agent_class,
        cli_runner,
        mock_successful_agent,
        temp_directory,
    ):
        """Test that output files are created correctly."""
        mock_agent_class.return_value = mock_successful_agent
        output_file = temp_directory / "subdir" / "output.txt"

        result = cli_runner.invoke(plan, ["Create plan", "--output", str(output_file)])

        assert result.exit_code == 0
        assert output_file.exists()
        assert output_file.parent.exists()  # Directory should be created
        assert output_file.read_text() == "Mock successful output"

    @patch("local_agents.cli.PlanningAgent")
    def test_context_directory_handling(
        self,
        mock_agent_class,
        cli_runner,
        mock_successful_agent,
        sample_project_directory,
    ):
        """Test context directory handling."""
        mock_agent_class.return_value = mock_successful_agent

        result = cli_runner.invoke(
            plan,
            [
                "Analyze this project",
                "--context",
                str(sample_project_directory),
            ],
        )

        assert result.exit_code == 0
        # Verify directory context was passed
        call_args = mock_successful_agent.execute.call_args
        context = call_args[0][1]
        assert "directory" in context
        assert context["directory"] == str(sample_project_directory)
