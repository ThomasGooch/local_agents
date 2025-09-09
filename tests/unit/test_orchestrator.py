"""Tests for workflow orchestrator."""

from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import pytest

from local_agents.agents.coder import CodingAgent
from local_agents.agents.planner import PlanningAgent
from local_agents.agents.reviewer import ReviewAgent
from local_agents.agents.tester import TestingAgent

# Avoid direct imports to prevent class pollution in other tests
from local_agents.base import TaskResult
from local_agents.workflows.orchestrator import Workflow, WorkflowResult, WorkflowStep


class TestWorkflowOrchestrator:
    """Test Workflow orchestrator functionality."""

    @pytest.fixture
    def mock_agents(self):
        """Create mock agents for testing."""
        agents = {}

        # Mock planning agent
        mock_planner = Mock()
        mock_planner.agent_type = "plan"
        mock_planner.execute.return_value = TaskResult(
            success=True,
            output="## Implementation Plan\n\n1. Create main function\n2. Add error handling",
            agent_type="plan",
            task="Create implementation plan",
            context={},
        )
        agents["planner"] = mock_planner

        # Mock coding agent
        mock_coder = Mock()
        mock_coder.agent_type = "code"
        mock_coder.execute.return_value = TaskResult(
            success=True,
            output="```python\ndef main():\n    try:\n        print('Hello World')\n    except Exception as e:\n        print(f'Error: {e}')\n```",
            agent_type="code",
            task="Generate code",
            context={},
        )
        agents["coder"] = mock_coder

        # Mock testing agent
        mock_tester = Mock()
        mock_tester.agent_type = "test"
        mock_tester.execute.return_value = TaskResult(
            success=True,
            output="```python\ndef test_main():\n    assert main() is None\n```",
            agent_type="test",
            task="Generate tests",
            context={},
        )
        agents["tester"] = mock_tester

        # Mock review agent
        mock_reviewer = Mock()
        mock_reviewer.agent_type = "review"
        mock_reviewer.execute.return_value = TaskResult(
            success=True,
            output="## Code Review\n\n### Summary\nCode is well-structured.\n\n### Issues\nNone found.",
            agent_type="review",
            task="Review code",
            context={},
        )
        agents["reviewer"] = mock_reviewer

        return agents

    @pytest.fixture
    def workflow(self, mock_agents):
        """Create workflow with mocked agents."""
        workflow = Workflow()

        # Replace agent creation with mocked instances using string-based patching
        with patch(
            "local_agents.agents.planner.PlanningAgent",
            return_value=mock_agents["planner"],
        ):
            with patch(
                "local_agents.agents.coder.CodingAgent",
                return_value=mock_agents["coder"],
            ):
                with patch(
                    "local_agents.agents.tester.TestingAgent",
                    return_value=mock_agents["tester"],
                ):
                    with patch(
                        "local_agents.agents.reviewer.ReviewAgent",
                        return_value=mock_agents["reviewer"],
                    ):
                        yield workflow

    def test_workflow_initialization(self):
        """Test workflow initialization."""
        workflow = Workflow()

        assert hasattr(workflow, "current_context")
        assert workflow.current_context == {}
        assert hasattr(workflow, "workflow_definitions")
        assert "feature-dev" in workflow.workflow_definitions
        assert "bug-fix" in workflow.workflow_definitions
        assert "code-review" in workflow.workflow_definitions

    def test_predefined_workflow_definitions(self, workflow):
        """Test that predefined workflows are correctly defined."""
        # Feature development workflow
        feature_dev = workflow.workflow_definitions["feature-dev"]
        assert feature_dev["steps"] == ["plan", "code", "test", "review"]
        assert (
            feature_dev["description"]
            == "Complete feature development workflow"
        )

        # Bug fix workflow
        bug_fix = workflow.workflow_definitions["bug-fix"]
        assert bug_fix["steps"] == ["plan", "code", "test"]

        # Code review workflow
        code_review = workflow.workflow_definitions["code-review"]
        assert code_review["steps"] == ["review"]

        # Refactoring workflow
        refactor = workflow.workflow_definitions["refactor"]
        assert refactor["steps"] == ["plan", "code", "test", "review"]

    def test_agent_factory_creation(self, workflow, mock_agents):
        """Test agent factory creates correct agent types."""
        with patch.object(
            PlanningAgent, "__new__", return_value=mock_agents["planner"]
        ):
            agent = workflow._create_agent("plan")
            assert agent.agent_type == "plan"

        with patch.object(
            CodingAgent, "__new__", return_value=mock_agents["coder"]
        ):
            agent = workflow._create_agent("code")
            assert agent.agent_type == "code"

        with patch.object(
            TestingAgent, "__new__", return_value=mock_agents["tester"]
        ):
            agent = workflow._create_agent("test")
            assert agent.agent_type == "test"

        with patch.object(
            ReviewAgent, "__new__", return_value=mock_agents["reviewer"]
        ):
            agent = workflow._create_agent("review")
            assert agent.agent_type == "review"

    def test_agent_factory_invalid_type(self, workflow):
        """Test agent factory raises error for invalid agent type."""
        with pytest.raises(ValueError, match="Unknown agent type: invalid"):
            workflow._create_agent("invalid")

    def test_execute_single_step(self, workflow, mock_agents):
        """Test executing a single workflow step."""
        with patch.object(
            PlanningAgent, "__new__", return_value=mock_agents["planner"]
        ):
            step_result = workflow._execute_step(
                "plan", "Create implementation plan", {"language": "python"}
            )

        assert isinstance(step_result, WorkflowStep)
        assert step_result.agent_type == "plan"
        assert step_result.success is True
        assert step_result.output is not None
        assert step_result.execution_time > 0
        mock_agents["planner"].execute.assert_called_once()

    def test_execute_step_with_streaming(self, workflow, mock_agents):
        """Test executing step with streaming enabled."""
        with patch.object(
            PlanningAgent, "__new__", return_value=mock_agents["planner"]
        ):
            step_result = workflow._execute_step(
                "plan", "Create plan", {}, stream=True
            )

        assert step_result.success is True
        # Verify streaming parameter was passed
        call_args = mock_agents["planner"].execute.call_args
        assert call_args[1]["stream"] is True

    def test_context_passing_between_steps(self, workflow, mock_agents):
        """Test context is properly passed between workflow steps."""
        with patch.object(
            PlanningAgent, "__new__", return_value=mock_agents["planner"]
        ):
            with patch.object(
                CodingAgent, "__new__", return_value=mock_agents["coder"]
            ):
                # Execute planning step
                workflow._execute_step(
                    "plan", "Create plan", {"language": "python"}
                )

                # Verify context was updated
                assert "plan_output" in workflow.current_context

                # Execute coding step
                workflow._execute_step("code", "Generate code", {})

                # Verify coder received context from planner
                coder_call_args = mock_agents["coder"].execute.call_args
                context = coder_call_args[0][1]  # Second argument is context
                assert "plan_output" in context
                assert "language" in context

    def test_dependency_checking(self, workflow, mock_agents):
        """Test workflow step dependency checking."""
        # Mock dependencies
        workflow.step_dependencies = {
            "code": ["plan"],
            "test": ["code"],
            "review": ["code"],
        }

        # Test that dependencies are checked
        with patch.object(workflow, "_check_dependencies") as mock_check:
            mock_check.return_value = True

            with patch.object(
                CodingAgent, "__new__", return_value=mock_agents["coder"]
            ):
                workflow._execute_step("code", "Generate code", {})

            mock_check.assert_called_once_with("code", [])

    def test_dependency_failure_handling(self, workflow, mock_agents):
        """Test handling of dependency failures."""
        # Set up failed dependency
        workflow.completed_steps = {"plan": False}  # Plan failed
        workflow.step_dependencies = {"code": ["plan"]}

        with patch.object(
            CodingAgent, "__new__", return_value=mock_agents["coder"]
        ):
            step_result = workflow._execute_step("code", "Generate code", {})

        # Step should be skipped due to dependency failure
        assert step_result.success is False
        assert "dependency" in step_result.error.lower()

    def test_step_execution_failure_handling(self, workflow, mock_agents):
        """Test handling of individual step execution failures."""
        # Make planner fail
        mock_agents["planner"].execute.return_value = TaskResult(
            success=False,
            output="",
            agent_type="plan",
            task="Create plan",
            error="Planning failed",
        )

        with patch.object(
            PlanningAgent, "__new__", return_value=mock_agents["planner"]
        ):
            step_result = workflow._execute_step("plan", "Create plan", {})

        assert step_result.success is False
        assert step_result.error == "Planning failed"
        assert step_result.execution_time > 0

    def test_full_workflow_execution_success(self, workflow, mock_agents):
        """Test successful execution of complete workflow."""
        with patch.object(
            PlanningAgent, "__new__", return_value=mock_agents["planner"]
        ):
            with patch.object(
                CodingAgent, "__new__", return_value=mock_agents["coder"]
            ):
                with patch.object(
                    TestingAgent, "__new__", return_value=mock_agents["tester"]
                ):
                    with patch.object(
                        ReviewAgent,
                        "__new__",
                        return_value=mock_agents["reviewer"],
                    ):
                        result = workflow.execute_workflow(
                            "feature-dev",
                            "Create a hello world function",
                            {"language": "python"},
                        )

        assert isinstance(result, WorkflowResult)
        assert result.workflow_name == "feature-dev"
        assert result.success is True
        assert len(result.steps) == 4  # plan, code, test, review
        assert result.task == "Create a hello world function"
        assert result.total_execution_time > 0

        # Verify all steps were successful
        for step in result.steps:
            assert step.success is True

        # Verify agents were called in correct order
        mock_agents["planner"].execute.assert_called_once()
        mock_agents["coder"].execute.assert_called_once()
        mock_agents["tester"].execute.assert_called_once()
        mock_agents["reviewer"].execute.assert_called_once()

    def test_workflow_execution_with_failures(self, workflow, mock_agents):
        """Test workflow execution with some step failures."""
        # Make coding step fail
        mock_agents["coder"].execute.return_value = TaskResult(
            success=False,
            output="",
            agent_type="code",
            task="Generate code",
            error="Code generation failed",
        )

        with patch.object(
            PlanningAgent, "__new__", return_value=mock_agents["planner"]
        ):
            with patch.object(
                CodingAgent, "__new__", return_value=mock_agents["coder"]
            ):
                with patch.object(
                    TestingAgent, "__new__", return_value=mock_agents["tester"]
                ):
                    with patch.object(
                        ReviewAgent,
                        "__new__",
                        return_value=mock_agents["reviewer"],
                    ):
                        result = workflow.execute_workflow(
                            "feature-dev", "Create a function"
                        )

        assert result.success is False
        assert len(result.steps) == 4  # All steps should be attempted

        # Check specific step results
        plan_step, code_step, test_step, review_step = result.steps
        assert plan_step.success is True
        assert code_step.success is False
        assert (
            test_step.success is True
        )  # Should continue after non-critical failure
        assert review_step.success is True

        assert result.successful_steps == 3
        assert result.failed_steps == 1

    def test_workflow_summary_generation(self, workflow, mock_agents):
        """Test workflow summary generation."""
        with patch.object(
            PlanningAgent, "__new__", return_value=mock_agents["planner"]
        ):
            with patch.object(
                ReviewAgent, "__new__", return_value=mock_agents["reviewer"]
            ):
                result = workflow.execute_workflow(
                    "code-review", "Review authentication module"
                )

        assert "summary" in result.summary
        assert "Code-Review Workflow Summary" in result.summary
        assert "Review authentication module" in result.summary
        assert "1/1 steps successful" in result.summary
        assert result.execution_time_formatted in result.summary

    def test_custom_workflow_creation(self, workflow, mock_agents):
        """Test creation and execution of custom workflows."""
        with patch.object(
            PlanningAgent, "__new__", return_value=mock_agents["planner"]
        ):
            with patch.object(
                TestingAgent, "__new__", return_value=mock_agents["tester"]
            ):
                result = workflow.create_custom_workflow(
                    steps=["plan", "test"],
                    task="Test-driven development workflow",
                    context={"approach": "TDD"},
                )

        assert result.workflow_name == "custom"
        assert result.success is True
        assert len(result.steps) == 2
        assert result.task == "Test-driven development workflow"

        # Verify correct agents were called
        mock_agents["planner"].execute.assert_called_once()
        mock_agents["tester"].execute.assert_called_once()
        # These agents should not be called
        assert mock_agents["coder"].execute.call_count == 0
        assert mock_agents["reviewer"].execute.call_count == 0

    def test_custom_workflow_invalid_steps(self, workflow):
        """Test custom workflow with invalid step names."""
        with pytest.raises(ValueError, match="Unknown agent type: invalid"):
            workflow.create_custom_workflow(
                steps=["plan", "invalid", "test"], task="Invalid workflow"
            )

    def test_workflow_state_management(self, workflow, mock_agents):
        """Test workflow state management during execution."""
        with patch.object(
            PlanningAgent, "__new__", return_value=mock_agents["planner"]
        ):
            with patch.object(
                CodingAgent, "__new__", return_value=mock_agents["coder"]
            ):
                # Execute partial workflow
                workflow._execute_step(
                    "plan", "Create plan", {"language": "python"}
                )

                # Check workflow state
                assert "plan" in workflow.completed_steps
                assert workflow.completed_steps["plan"] is True
                assert "plan_output" in workflow.current_context

                # Continue workflow
                workflow._execute_step("code", "Generate code", {})

                # Check updated state
                assert "code" in workflow.completed_steps
                assert workflow.completed_steps["code"] is True
                assert "code_output" in workflow.current_context

    @patch("local_agents.base.OllamaClient")
    def test_workflow_execution_time_tracking(
        self, mock_ollama_class, workflow, mock_agents
    ):
        """Test that execution times are properly tracked."""
        # Set up mock OllamaClient
        mock_client = Mock()
        mock_client.is_model_available.return_value = True
        mock_client.pull_model.return_value = True
        mock_client.generate.return_value = "Mock review output"
        mock_ollama_class.return_value = mock_client

        result = workflow.execute_workflow("code-review", "Review code")

        assert result.total_execution_time > 0
        assert result.execution_time_formatted is not None
        assert (
            "seconds" in result.execution_time_formatted
            or "ms" in result.execution_time_formatted
        )

        # Check individual step timing
        for step in result.steps:
            assert step.execution_time >= 0

    @patch("local_agents.base.OllamaClient")
    def test_workflow_continuation_after_non_critical_failures(
        self, mock_ollama_class, workflow, mock_agents
    ):
        """Test workflow continues after non-critical step failures."""
        # Set up mock OllamaClient
        mock_client = Mock()
        mock_client.is_model_available.return_value = True
        mock_client.pull_model.return_value = True
        mock_client.generate.return_value = "Mock output"
        mock_ollama_class.return_value = mock_client

        # Configure failure behavior
        workflow.critical_steps = ["plan"]  # Only plan is critical

        # Make coding step fail (non-critical)
        mock_agents["coder"].execute.return_value = TaskResult(
            success=False,
            output="",
            agent_type="code",
            task="Generate code",
            error="Non-critical failure",
        )

        with patch.object(
            PlanningAgent, "__new__", return_value=mock_agents["planner"]
        ):
            with patch.object(
                CodingAgent, "__new__", return_value=mock_agents["coder"]
            ):
                with patch.object(
                    TestingAgent, "__new__", return_value=mock_agents["tester"]
                ):
                    result = workflow.execute_workflow(
                        "feature-dev", "Create feature despite coding failure"
                    )

        # Workflow should complete despite coding failure
        assert (
            len(result.steps) >= 3
        )  # Plan, code (failed), test should all run
        assert result.steps[0].success is True  # Plan
        assert result.steps[1].success is False  # Code (failed)
        assert result.steps[2].success is True  # Test (continues)

    def test_workflow_stops_on_critical_failures(self, workflow, mock_agents):
        """Test workflow stops on critical step failures."""
        # Configure critical steps
        workflow.critical_steps = ["plan"]

        # Make planning step fail (critical)
        mock_agents["planner"].execute.return_value = TaskResult(
            success=False,
            output="",
            agent_type="plan",
            task="Create plan",
            error="Critical planning failure",
        )

        with patch.object(
            PlanningAgent, "__new__", return_value=mock_agents["planner"]
        ):
            with patch.object(
                CodingAgent, "__new__", return_value=mock_agents["coder"]
            ):
                result = workflow.execute_workflow(
                    "feature-dev", "Create feature with critical failure"
                )

        # Workflow should stop after planning failure
        assert result.success is False
        assert len(result.steps) == 1  # Only planning step should have run
        assert result.steps[0].success is False

        # Coding step should not have been called
        mock_agents["coder"].execute.assert_not_called()

    def test_unknown_workflow_handling(self, workflow):
        """Test handling of unknown workflow names."""
        with pytest.raises(ValueError, match="Unknown workflow: nonexistent"):
            workflow.execute_workflow("nonexistent", "Test unknown workflow")

    def test_workflow_context_isolation(self, workflow, mock_agents):
        """Test that workflow contexts are properly isolated between executions."""
        with patch.object(
            ReviewAgent, "__new__", return_value=mock_agents["reviewer"]
        ):
            # Execute first workflow
            result1 = workflow.execute_workflow(
                "code-review", "First review", {"file": "test1.py"}
            )

            # Execute second workflow
            result2 = workflow.execute_workflow(
                "code-review", "Second review", {"file": "test2.py"}
            )

        # Results should be independent
        assert result1.task != result2.task
        assert result1.initial_context != result2.initial_context

    def test_workflow_result_serialization(self, workflow, mock_agents):
        """Test that workflow results can be serialized to dict."""
        with patch.object(
            ReviewAgent, "__new__", return_value=mock_agents["reviewer"]
        ):
            result = workflow.execute_workflow(
                "code-review", "Test serialization"
            )

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert "workflow_name" in result_dict
        assert "success" in result_dict
        assert "steps" in result_dict
        assert "task" in result_dict
        assert "total_execution_time" in result_dict
        assert isinstance(result_dict["steps"], list)

        # Check step serialization
        for step_dict in result_dict["steps"]:
            assert isinstance(step_dict, dict)
            assert "agent_type" in step_dict
            assert "success" in step_dict
            assert "execution_time" in step_dict
