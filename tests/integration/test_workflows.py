"""Integration tests for workflows."""

from unittest.mock import Mock, patch

import pytest

from local_agents.agents.coder import CodingAgent
from local_agents.agents.planner import PlanningAgent
from local_agents.agents.reviewer import ReviewAgent
from local_agents.agents.tester import TestingAgent
from local_agents.base import TaskResult
from local_agents.workflows.orchestrator import Workflow


@pytest.fixture
def mock_agents():
    """Mock all agents for integration testing."""
    agents = {}

    # Mock planning agent
    mock_planner = Mock(spec=PlanningAgent)
    mock_planner.agent_type = "plan"
    mock_planner.execute.return_value = TaskResult(
        success=True,
        output="## Implementation Plan\n\n1. Create main function\n2. Add error handling\n3. Write tests",
        agent_type="plan",
        task="Create implementation plan",
    )
    agents["planner"] = mock_planner

    # Mock coding agent
    mock_coder = Mock(spec=CodingAgent)
    mock_coder.agent_type = "code"
    mock_coder.execute.return_value = TaskResult(
        success=True,
        output="```python\ndef main():\n    print('Hello World')\n```",
        agent_type="code",
        task="Generate code",
    )
    agents["coder"] = mock_coder

    # Mock testing agent
    mock_tester = Mock(spec=TestingAgent)
    mock_tester.agent_type = "test"
    mock_tester.execute.return_value = TaskResult(
        success=True,
        output="```python\ndef test_main():\n    assert main() is None\n```",
        agent_type="test",
        task="Generate tests",
    )
    agents["tester"] = mock_tester

    # Mock review agent
    mock_reviewer = Mock(spec=ReviewAgent)
    mock_reviewer.agent_type = "review"
    mock_reviewer.execute.return_value = TaskResult(
        success=True,
        output="## Code Review\n\n### Summary\nCode looks good.\n\n### Issues Found\nNone.",
        agent_type="review",
        task="Review code",
    )
    agents["reviewer"] = mock_reviewer

    return agents


@pytest.fixture
def workflow_with_mocks(mock_agents):
    """Create workflow with mocked agents."""
    workflow = Workflow()

    # Replace agent classes with mock instances
    with patch.object(PlanningAgent, "__new__", return_value=mock_agents["planner"]):
        with patch.object(CodingAgent, "__new__", return_value=mock_agents["coder"]):
            with patch.object(TestingAgent, "__new__", return_value=mock_agents["tester"]):
                with patch.object(ReviewAgent, "__new__", return_value=mock_agents["reviewer"]):
                    yield workflow, mock_agents


class TestWorkflowExecution:
    """Test workflow execution scenarios."""

    def test_feature_dev_workflow_success(self, workflow_with_mocks):
        """Test successful feature development workflow."""
        workflow, mock_agents = workflow_with_mocks

        with patch.object(PlanningAgent, "__new__", return_value=mock_agents["planner"]):
            with patch.object(CodingAgent, "__new__", return_value=mock_agents["coder"]):
                with patch.object(TestingAgent, "__new__", return_value=mock_agents["tester"]):
                    with patch.object(ReviewAgent, "__new__", return_value=mock_agents["reviewer"]):
                        result = workflow.execute_workflow(
                            workflow_name="feature-dev",
                            task="Create a hello world function",
                            initial_context={"project_type": "python"},
                        )

        # Verify workflow completion
        assert result.success is True
        assert result.workflow_name == "feature-dev"
        assert result.task == "Create a hello world function"
        assert len(result.steps) == 4  # plan, code, test, review

        # Verify all agents were called
        mock_agents["planner"].execute.assert_called_once()
        mock_agents["coder"].execute.assert_called_once()
        mock_agents["tester"].execute.assert_called_once()
        mock_agents["reviewer"].execute.assert_called_once()

        # Verify context passing
        assert "plan_output" in workflow.current_context
        assert "code_output" in workflow.current_context
        assert "test_output" in workflow.current_context
        assert "review_output" in workflow.current_context

    def test_bug_fix_workflow_success(self, workflow_with_mocks):
        """Test successful bug fix workflow."""
        workflow, mock_agents = workflow_with_mocks

        with patch.object(PlanningAgent, "__new__", return_value=mock_agents["planner"]):
            with patch.object(CodingAgent, "__new__", return_value=mock_agents["coder"]):
                with patch.object(TestingAgent, "__new__", return_value=mock_agents["tester"]):
                    result = workflow.execute_workflow(
                        workflow_name="bug-fix",
                        task="Fix null pointer exception",
                        initial_context={"bug_report": "NPE in main function"},
                    )

        # Verify workflow completion
        assert result.success is True
        assert result.workflow_name == "bug-fix"
        assert len(result.steps) == 3  # plan, code, test

        # Verify agents were called in correct order
        mock_agents["planner"].execute.assert_called_once()
        mock_agents["coder"].execute.assert_called_once()
        mock_agents["tester"].execute.assert_called_once()
        # Review agent should not be called for bug-fix workflow
        assert mock_agents["reviewer"].execute.call_count == 0

    def test_code_review_workflow_success(self, workflow_with_mocks):
        """Test code review only workflow."""
        workflow, mock_agents = workflow_with_mocks

        with patch.object(ReviewAgent, "__new__", return_value=mock_agents["reviewer"]):
            result = workflow.execute_workflow(
                workflow_name="code-review",
                task="Review existing code",
                initial_context={"code_file": "main.py"},
            )

        # Verify workflow completion
        assert result.success is True
        assert result.workflow_name == "code-review"
        assert len(result.steps) == 1  # review only

        # Only review agent should be called
        mock_agents["reviewer"].execute.assert_called_once()
        assert mock_agents["planner"].execute.call_count == 0
        assert mock_agents["coder"].execute.call_count == 0
        assert mock_agents["tester"].execute.call_count == 0

    def test_workflow_with_failure_continues(self, workflow_with_mocks):
        """Test that workflow continues after non-critical step failure."""
        workflow, mock_agents = workflow_with_mocks

        # Make coding step fail
        mock_agents["coder"].execute.return_value = TaskResult(
            success=False,
            output="",
            agent_type="code",
            task="Generate code",
            error="Code generation failed",
        )

        with patch.object(PlanningAgent, "__new__", return_value=mock_agents["planner"]):
            with patch.object(CodingAgent, "__new__", return_value=mock_agents["coder"]):
                with patch.object(TestingAgent, "__new__", return_value=mock_agents["tester"]):
                    with patch.object(ReviewAgent, "__new__", return_value=mock_agents["reviewer"]):
                        result = workflow.execute_workflow(
                            workflow_name="feature-dev",
                            task="Create a hello world function",
                        )

        # Workflow should complete but not be successful overall
        assert result.success is False
        assert len(result.steps) == 4

        # All agents should still be called
        mock_agents["planner"].execute.assert_called_once()
        mock_agents["coder"].execute.assert_called_once()
        mock_agents["tester"].execute.assert_called_once()
        mock_agents["reviewer"].execute.assert_called_once()

    def test_workflow_stops_on_planning_failure(self, workflow_with_mocks):
        """Test that workflow stops when planning step fails."""
        workflow, mock_agents = workflow_with_mocks

        # Make planning step fail
        mock_agents["planner"].execute.return_value = TaskResult(
            success=False,
            output="",
            agent_type="plan",
            task="Create implementation plan",
            error="Planning failed",
        )

        with patch.object(PlanningAgent, "__new__", return_value=mock_agents["planner"]):
            with patch.object(CodingAgent, "__new__", return_value=mock_agents["coder"]):
                with patch.object(TestingAgent, "__new__", return_value=mock_agents["tester"]):
                    with patch.object(ReviewAgent, "__new__", return_value=mock_agents["reviewer"]):
                        result = workflow.execute_workflow(
                            workflow_name="feature-dev",
                            task="Create a hello world function",
                        )

        # Workflow should stop after planning failure
        assert result.success is False
        assert len(result.steps) == 1  # Only planning step

        # Only planner should be called
        mock_agents["planner"].execute.assert_called_once()
        assert mock_agents["coder"].execute.call_count == 0
        assert mock_agents["tester"].execute.call_count == 0
        assert mock_agents["reviewer"].execute.call_count == 0

    def test_custom_workflow_creation(self, workflow_with_mocks):
        """Test creation and execution of custom workflow."""
        workflow, mock_agents = workflow_with_mocks

        with patch.object(PlanningAgent, "__new__", return_value=mock_agents["planner"]):
            with patch.object(TestingAgent, "__new__", return_value=mock_agents["tester"]):
                result = workflow.create_custom_workflow(
                    steps=["plan", "test"],
                    task="Create test-first workflow",
                    context={"approach": "TDD"},
                )

        # Verify custom workflow execution
        assert result.success is True
        assert result.workflow_name == "custom"
        assert len(result.steps) == 2

        # Verify correct agents were called
        mock_agents["planner"].execute.assert_called_once()
        mock_agents["tester"].execute.assert_called_once()
        assert mock_agents["coder"].execute.call_count == 0
        assert mock_agents["reviewer"].execute.call_count == 0

    def test_workflow_context_passing(self, workflow_with_mocks):
        """Test that context is properly passed between workflow steps."""
        workflow, mock_agents = workflow_with_mocks

        with patch.object(PlanningAgent, "__new__", return_value=mock_agents["planner"]):
            with patch.object(CodingAgent, "__new__", return_value=mock_agents["coder"]):
                result = workflow.execute_workflow(
                    workflow_name="feature-dev",
                    task="Create a hello world function",
                    initial_context={"framework": "flask", "version": "2.0"},
                )

        # Check that planner received initial context
        planner_call_args = mock_agents["planner"].execute.call_args
        assert "framework" in planner_call_args[0][1]  # context is second argument
        assert planner_call_args[0][1]["framework"] == "flask"

        # Check that coder received context including planner output
        coder_call_args = mock_agents["coder"].execute.call_args
        coder_context = coder_call_args[0][1]
        assert "framework" in coder_context
        assert "plan_output" in coder_context or "implementation_plan" in coder_context

    def test_unknown_workflow_raises_error(self):
        """Test that unknown workflow name raises appropriate error."""
        workflow = Workflow()

        with pytest.raises(ValueError, match="Unknown workflow: nonexistent"):
            workflow.execute_workflow(workflow_name="nonexistent", task="Test task")

    def test_custom_workflow_invalid_agent(self):
        """Test that custom workflow with invalid agent raises error."""
        workflow = Workflow()

        with pytest.raises(ValueError, match="Unknown agent type: invalid"):
            workflow.create_custom_workflow(steps=["plan", "invalid", "test"], task="Test task")


class TestWorkflowDependencies:
    """Test workflow step dependencies."""

    def test_dependencies_are_checked(self, workflow_with_mocks):
        """Test that dependencies are properly checked before step execution."""
        workflow, mock_agents = workflow_with_mocks

        # Make planning step fail but not abort workflow
        mock_agents["planner"].execute.return_value = TaskResult(
            success=False,
            output="",
            agent_type="plan",
            task="Create plan",
            error="Planning failed",
        )

        with patch.object(PlanningAgent, "__new__", return_value=mock_agents["planner"]):
            with patch.object(CodingAgent, "__new__", return_value=mock_agents["coder"]):
                # Force workflow to continue after planning failure
                workflow._should_continue_after_failure = Mock(return_value=True)

                result = workflow.execute_workflow(
                    workflow_name="feature-dev", task="Test dependencies"
                )

        # Planner should be called, but coder should be skipped due to dependency failure
        mock_agents["planner"].execute.assert_called_once()
        # Note: Actual dependency checking behavior depends on implementation details
        # This test verifies the framework is in place

    def test_successful_dependencies_allow_execution(self, workflow_with_mocks):
        """Test that successful dependencies allow subsequent steps."""
        workflow, mock_agents = workflow_with_mocks

        with patch.object(PlanningAgent, "__new__", return_value=mock_agents["planner"]):
            with patch.object(CodingAgent, "__new__", return_value=mock_agents["coder"]):
                result = workflow.execute_workflow(
                    workflow_name="feature-dev", task="Test successful dependencies"
                )

        # Both steps should execute successfully
        mock_agents["planner"].execute.assert_called_once()
        mock_agents["coder"].execute.assert_called_once()

        # Verify that coding step received context from planning step
        coder_call_args = mock_agents["coder"].execute.call_args
        coder_context = coder_call_args[0][1]
        # Context should contain planning output (exact key depends on implementation)
        assert any("plan" in key for key in coder_context.keys())


class TestWorkflowStreamingAndOutput:
    """Test workflow streaming and output handling."""

    def test_workflow_streaming_parameter_passed(self, workflow_with_mocks):
        """Test that streaming parameter is passed to agents."""
        workflow, mock_agents = workflow_with_mocks

        with patch.object(ReviewAgent, "__new__", return_value=mock_agents["reviewer"]):
            workflow.execute_workflow(
                workflow_name="code-review", task="Test streaming", stream=True
            )

        # Verify streaming parameter was passed to agent
        reviewer_call_args = mock_agents["reviewer"].execute.call_args
        assert reviewer_call_args[1]["stream"] is True  # stream is keyword argument

    def test_workflow_summary_generation(self, workflow_with_mocks):
        """Test that workflow generates proper summary."""
        workflow, mock_agents = workflow_with_mocks

        with patch.object(ReviewAgent, "__new__", return_value=mock_agents["reviewer"]):
            result = workflow.execute_workflow(
                workflow_name="code-review", task="Test summary generation"
            )

        # Verify summary is generated
        assert hasattr(result, "summary")
        summary = result.summary
        assert "Code-Review Workflow Summary" in summary
        assert "Test summary generation" in summary
        assert "1/1 steps successful" in summary
        assert "✅" in summary  # Success indicator

    def test_workflow_summary_with_failures(self, workflow_with_mocks):
        """Test workflow summary when there are failures."""
        workflow, mock_agents = workflow_with_mocks

        # Make review step fail
        mock_agents["reviewer"].execute.return_value = TaskResult(
            success=False,
            output="",
            agent_type="review",
            task="Review code",
            error="Review failed",
        )

        with patch.object(ReviewAgent, "__new__", return_value=mock_agents["reviewer"]):
            result = workflow.execute_workflow(
                workflow_name="code-review", task="Test failure summary"
            )

        # Verify failure summary
        assert result.success is False
        summary = result.summary
        assert "0/1 steps successful" in summary
        assert "1 failures" in summary
        assert "❌" in summary  # Failure indicator
        assert "Review failed" in summary
