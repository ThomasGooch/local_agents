"""Workflow orchestrator for managing multi-agent workflows."""

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn, TimeElapsedColumn
from rich.table import Table

from ..agents.coder import CodingAgent
from ..agents.planner import PlanningAgent
from ..agents.reviewer import ReviewAgent
from ..agents.tester import TestingAgent
from ..base import BaseAgent, TaskResult
from ..config import config_manager

console = Console()


@dataclass
class WorkflowResult:
    """Result of a workflow execution."""

    success: bool
    results: List[TaskResult]
    workflow_name: str
    task: str
    total_steps: int
    completed_steps: int
    execution_time: float
    error: Optional[str] = None
    initial_context: Optional[Dict[str, Any]] = None
    final_context: Optional[Dict[str, Any]] = None

    @property
    def steps(self) -> List[TaskResult]:
        """Alias for results to match test expectations."""
        return self.results

    @property
    def total_execution_time(self) -> float:
        """Alias for execution_time to match test expectations."""
        return self.execution_time

    @property
    def successful_steps(self) -> int:
        """Number of successfully completed steps."""
        return self.completed_steps

    @property
    def failed_steps(self) -> int:
        """Number of failed steps."""
        return len(self.results) - self.completed_steps

    @property
    def execution_time_formatted(self) -> str:
        """Formatted execution time string."""
        if self.execution_time >= 1.0:
            return f"{self.execution_time:.2f} seconds"
        else:
            return f"{self.execution_time*1000:.0f}ms"

    @property
    def summary(self) -> str:
        """Generate workflow execution summary."""
        successful_steps = sum(1 for r in self.results if r.success)
        total_steps = len(self.results)

        summary_parts = [
            f"# {self.workflow_name.title()} Workflow Summary",
            f"\n**Task**: {self.task}",
            f"**Completion**: {successful_steps}/{total_steps} steps successful",
            f"\n**Execution Time**: {self.execution_time_formatted}",
            ("\nThis workflow execution summary provides an overview of the " "completed tasks."),
        ]

        if successful_steps == total_steps:
            summary_parts.append("\n✅ **Status**: Workflow completed successfully")
        else:
            summary_parts.append(
                f"\n⚠️ **Status**: Workflow completed with "
                f"{total_steps - successful_steps} failures"
            )

        summary_parts.append("\n## Step Results:")
        for i, result in enumerate(self.results, 1):
            status = "✅" if result.success else "❌"
            summary_parts.append(f"{i}. {status} {result.agent_type.title()} Agent")
            if not result.success and result.error:
                summary_parts.append(f"   Error: {result.error}")

        return "\n".join(summary_parts)

    def to_dict(self) -> Dict[str, Any]:
        """Convert WorkflowResult to dictionary."""
        return {
            "success": self.success,
            "results": [r.to_dict() for r in self.results],
            "steps": [r.to_dict() for r in self.results],  # Compatibility alias
            "workflow_name": self.workflow_name,
            "task": self.task,
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "execution_time": self.execution_time,
            "total_execution_time": self.execution_time,  # Compatibility alias
            "error": self.error,
        }

    def display(self) -> None:
        """Display workflow results using rich console."""
        # Create a summary table
        table = Table(title=f"{self.workflow_name.title()} Workflow Results")
        table.add_column("Step", style="cyan")
        table.add_column("Agent", style="magenta")
        table.add_column("Status", style="green" if self.success else "red")
        table.add_column("Details")

        for i, result in enumerate(self.results, 1):
            status = "✅ Success" if result.success else "❌ Failed"
            details = result.error if not result.success and result.error else "Completed"
            table.add_row(
                str(i),
                result.agent_type.title(),
                status,
                details[:50] + "..." if len(details) > 50 else details,
            )

        console.print(table)

        # Display overall status
        if self.success:
            console.print(
                Panel(
                    f"[bold green]Workflow completed successfully![/bold green]\n\n"
                    f"Steps: {self.completed_steps}/{self.total_steps}\n"
                    f"Execution time: {self.execution_time:.2f}s",
                    title="✅ Success",
                    border_style="green",
                )
            )
        else:
            console.print(
                Panel(
                    f"[bold red]Workflow failed[/bold red]\n\n"
                    f"Steps: {self.completed_steps}/{self.total_steps}\n"
                    f"Execution time: {self.execution_time:.2f}s\n"
                    f"Error: {self.error or 'Unknown error'}",
                    title="❌ Failed",
                    border_style="red",
                )
            )


class WorkflowStep:
    """Represents a single step in a workflow."""

    def __init__(
        self,
        agent_type: str,
        description: str,
        depends_on: Optional[List[str]] = None,
        context_mapping: Optional[Dict[str, str]] = None,
    ) -> None:
        self.agent_type = agent_type
        self.description = description
        self.depends_on = depends_on or []
        self.context_mapping = context_mapping or {}
        self.result: Optional[TaskResult] = None
        self.completed = False

        # Additional attributes for test compatibility
        self.success: bool = False
        self.output: str = ""
        self.execution_time: float = 0.0
        self.error: Optional[str] = None


class Workflow:
    """Orchestrates multi-agent workflows with performance optimization."""

    def __init__(self, max_concurrent_agents: int = 2) -> None:
        self.max_concurrent_agents = max_concurrent_agents
        self.agents: Dict[str, Type[BaseAgent]] = {
            "plan": PlanningAgent,
            "code": CodingAgent,
            "test": TestingAgent,
            "review": ReviewAgent,
        }
        self.current_context: Dict[str, Any] = {}
        self.completed_steps: Dict[str, bool] = {}

        # Performance monitoring
        self.execution_stats: Dict[str, Any] = {
            "total_workflows": 0,
            "successful_workflows": 0,
            "average_execution_time": 0.0,
            "concurrent_executions": 0,
            "cache_hits": 0,
            "total_steps": 0,
        }

        # Workflow definitions for tests compatibility
        self.workflow_definitions = {
            "feature-dev": {
                "steps": ["plan", "code", "test", "review"],
                "description": "Complete feature development workflow",
            },
            "bug-fix": {
                "steps": ["plan", "code", "test"],
                "description": "Bug fix workflow",
            },
            "code-review": {"steps": ["review"], "description": "Code review workflow"},
            "refactor": {
                "steps": ["plan", "code", "test", "review"],
                "description": "Code refactoring workflow",
            },
        }

    def _create_agent(self, agent_type: str) -> BaseAgent:
        """Create an agent instance of the specified type."""
        agent_class = self.agents.get(agent_type)
        if not agent_class:
            raise ValueError(f"Unknown agent type: {agent_type}")
        return agent_class()

    def execute_workflow(
        self,
        workflow_name: str,
        task: str,
        initial_context: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        enable_parallel: bool = True,
    ) -> WorkflowResult:
        """Execute a predefined workflow."""
        start_time = time.time()

        # Store initial context copy for result
        initial_context_copy = (initial_context or {}).copy()

        self.current_context = initial_context or {}
        self.current_context["main_task"] = task
        # Pass current working directory to agents
        if "directory" not in self.current_context:
            self.current_context["directory"] = str(Path.cwd())

        workflow_steps = self._get_workflow_definition(workflow_name)
        if not workflow_steps:
            raise ValueError(f"Unknown workflow: {workflow_name}")

        console.print(
            Panel(
                f"[bold blue]Starting Workflow: {workflow_name.title()}[/bold blue]\n\n"
                f"Task: {task}\n"
                f"Steps: {len(workflow_steps)}",
                title="Workflow Execution",
                border_style="blue",
            )
        )

        results = []

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
        ) as progress:
            workflow_task = progress.add_task(
                f"[cyan]{workflow_name.title()} Workflow", total=len(workflow_steps)
            )

            for i, step in enumerate(workflow_steps, 1):
                console.print(f"\n[bold]Step {i}/{len(workflow_steps)}: {step.description}[/bold]")

                # Check dependencies
                if not self._check_dependencies(step, results):
                    console.print("[red]Skipping step due to failed dependencies[/red]")
                    continue

                # Execute step
                result = self._execute_step(step, task, None, stream)
                results.append(result)

                # Update context with results
                self._update_context_from_result(step, result)

                # Track completed steps
                if result.success:
                    self.completed_steps[step.agent_type] = True

                if result.success:
                    console.print(f"[green]✓ Step {i} completed successfully[/green]")
                else:
                    console.print(f"[red]✗ Step {i} failed: {result.error}[/red]")

                    # Decide whether to continue or abort
                    if not self._should_continue_after_failure(step, result):
                        console.print("[red]Workflow aborted due to critical failure[/red]")
                        break

                progress.advance(workflow_task)

        # Calculate execution time
        execution_time = time.time() - start_time

        # Count completed successful steps
        successful_results = [r for r in results if r.success]

        return WorkflowResult(
            success=all(r.success for r in results) if results else False,
            results=results,
            workflow_name=workflow_name,
            task=task,
            total_steps=len(workflow_steps),
            completed_steps=len(successful_results),
            execution_time=execution_time,
            error=None
            if all(r.success for r in results) or not results
            else f"Failed steps: {len(results) - len(successful_results)}",
            initial_context=initial_context_copy,
            final_context=self.current_context.copy(),
        )

    def _get_workflow_definition(self, workflow_name: str) -> List[WorkflowStep]:
        """Get the definition for a predefined workflow."""
        workflows = {
            "feature-dev": [
                WorkflowStep("plan", "Create implementation plan"),
                WorkflowStep(
                    "code",
                    "Generate code implementation",
                    depends_on=["plan"],
                    context_mapping={"plan_output": "implementation_plan"},
                ),
                WorkflowStep(
                    "test",
                    "Create and run tests",
                    depends_on=["code"],
                    context_mapping={"code_output": "code_to_test"},
                ),
                WorkflowStep(
                    "review",
                    "Review implementation",
                    depends_on=["code"],
                    context_mapping={"code_output": "code_to_review"},
                ),
            ],
            "bug-fix": [
                WorkflowStep("plan", "Analyze bug and create fix plan"),
                WorkflowStep(
                    "code",
                    "Implement bug fix",
                    depends_on=["plan"],
                    context_mapping={"plan_output": "fix_plan"},
                ),
                WorkflowStep(
                    "test",
                    "Test bug fix",
                    depends_on=["code"],
                    context_mapping={"code_output": "fixed_code"},
                ),
            ],
            "code-review": [WorkflowStep("review", "Comprehensive code review")],
            "refactor": [
                WorkflowStep("plan", "Create refactoring plan"),
                WorkflowStep(
                    "code",
                    "Implement refactoring",
                    depends_on=["plan"],
                    context_mapping={"plan_output": "refactor_plan"},
                ),
                WorkflowStep(
                    "test",
                    "Test refactored code",
                    depends_on=["code"],
                    context_mapping={"code_output": "refactored_code"},
                ),
                WorkflowStep(
                    "review",
                    "Review refactored implementation",
                    depends_on=["code"],
                    context_mapping={"code_output": "code_to_review"},
                ),
            ],
        }

        # Also check user-configured workflows
        config_workflows = config_manager.get_workflow_steps(workflow_name)
        if config_workflows:
            return [WorkflowStep(step, f"Execute {step} agent") for step in config_workflows]

        return workflows.get(workflow_name, [])

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get workflow execution performance statistics."""
        from ..ollama_client import OllamaClient

        # Get cache statistics
        cache_stats = OllamaClient.get_cache_stats()

        return {
            **self.execution_stats,
            "cache_stats": cache_stats,
            "max_concurrent_agents": self.max_concurrent_agents,
            "success_rate": (
                self.execution_stats["successful_workflows"]
                / max(1, self.execution_stats["total_workflows"])
            )
            * 100,
        }

    def optimize_for_hardware(self, ram_gb: int = 16, cpu_cores: int = 6) -> None:
        """Optimize workflow settings for specific hardware configuration."""
        if ram_gb >= 16:
            # High memory - can run more concurrent agents
            self.max_concurrent_agents = min(cpu_cores // 2, 4)
        elif ram_gb >= 8:
            # Medium memory - limited concurrency
            self.max_concurrent_agents = 2
        else:
            # Low memory - sequential execution only
            self.max_concurrent_agents = 1

        opt_msg = (
            f"Optimized for {ram_gb}GB RAM, {cpu_cores} cores: "
            f"max {self.max_concurrent_agents} concurrent agents"
        )
        console.print(f"[blue]{opt_msg}[/blue]")

    def clear_performance_stats(self) -> None:
        """Reset performance statistics."""
        self.execution_stats = {
            "total_workflows": 0,
            "successful_workflows": 0,
            "average_execution_time": 0.0,
            "concurrent_executions": 0,
            "cache_hits": 0,
            "total_steps": 0,
        }

    def _execute_step(
        self,
        step: Union[WorkflowStep, str],
        main_task: str,
        context: Optional[Dict[str, Any]] = None,
        stream: bool = False,
    ) -> Union[TaskResult, WorkflowStep]:
        """Execute a single workflow step.

        Args:
            step: Either a WorkflowStep object or agent type string
            main_task: The main task description
            context: Optional context dict (for backward compatibility)
            stream: Whether to stream the response

        Returns:
            TaskResult when called with WorkflowStep, WorkflowStep when called
            with string
        """
        step_start_time = time.time()

        # Handle both call styles for backward compatibility
        if isinstance(step, str):
            # Legacy test API: _execute_step(agent_type, task, context, stream)
            agent_type = step
            task_description = main_task
            step_context = context or {}

            # Check dependencies for legacy API
            if not self._check_dependencies(agent_type, []):
                # Return failed step for dependency failure
                temp_step = WorkflowStep(agent_type, f"Execute {agent_type} agent")
                task_result = TaskResult(
                    success=False,
                    output="",
                    agent_type=agent_type,
                    task=task_description,
                    error="Dependency not satisfied",
                    execution_time=0.0,
                )
                temp_step.result = task_result
                temp_step.completed = False
                temp_step.success = False
                temp_step.output = ""
                temp_step.execution_time = 0.0
                temp_step.error = "Dependency not satisfied"
                return temp_step

            # Create a temporary WorkflowStep for processing
            temp_step = WorkflowStep(agent_type, f"Execute {agent_type} agent")

            try:
                # Get the appropriate agent
                agent_class = self.agents.get(agent_type)
                if not agent_class:
                    task_result = TaskResult(
                        success=False,
                        output="",
                        agent_type=agent_type,
                        task=task_description,
                        error=f"Unknown agent type: {agent_type}",
                        execution_time=time.time() - step_start_time,
                    )
                    # Return WorkflowStep with result for test compatibility
                    temp_step.result = task_result
                    temp_step.completed = False
                    temp_step.success = False
                    temp_step.output = task_result.output
                    temp_step.execution_time = task_result.execution_time
                    return temp_step

                agent = agent_class()

                # Merge current context with provided context for legacy calls
                # Update current context first with provided context
                if step_context:
                    self.current_context.update(step_context)
                merged_context = self.current_context.copy()

                # Execute the agent
                result = agent.execute(task_description, merged_context, stream=stream)
                result.execution_time = time.time() - step_start_time

                # Update context with results
                if result.success:
                    self.current_context[f"{agent_type}_output"] = result.output
                    self.current_context[f"{agent_type}_result"] = result.to_dict()
                    # Track completed steps
                    self.completed_steps[agent_type] = True

                # Return WorkflowStep with result for test compatibility
                temp_step.result = result
                temp_step.completed = result.success
                temp_step.success = result.success
                temp_step.output = result.output
                temp_step.execution_time = result.execution_time
                temp_step.error = result.error
                return temp_step

            except Exception as e:
                task_result = TaskResult(
                    success=False,
                    output="",
                    agent_type=agent_type,
                    task=task_description,
                    error=str(e),
                    execution_time=time.time() - step_start_time,
                )
                temp_step.result = task_result
                temp_step.completed = False
                temp_step.success = False
                temp_step.output = task_result.output
                temp_step.execution_time = task_result.execution_time
                temp_step.error = str(e)
                return temp_step

        # Original workflow API: _execute_step(WorkflowStep, main_task, stream)
        try:
            # Get the appropriate agent
            agent_class = self.agents.get(step.agent_type)
            if not agent_class:
                return TaskResult(
                    success=False,
                    output="",
                    agent_type=step.agent_type,
                    task=step.description,
                    error=f"Unknown agent type: {step.agent_type}",
                    execution_time=time.time() - step_start_time,
                )

            agent = agent_class()

            # Prepare context for this step
            step_context = self.current_context.copy()

            # Apply context mapping
            for src, dst in step.context_mapping.items():
                if src in self.current_context:
                    step_context[dst] = self.current_context[src]

            # Customize task based on step and main task
            task_description = self._customize_task_for_step(step, main_task)

            # Execute the agent
            result = agent.execute(task_description, step_context, stream=stream)

            # Update result with execution time
            result.execution_time = time.time() - step_start_time

            step.result = result
            step.completed = True

            return result

        except Exception as e:
            return TaskResult(
                success=False,
                output="",
                agent_type=step.agent_type,
                task=step.description,
                error=str(e),
                execution_time=time.time() - step_start_time,
            )

    def _customize_task_for_step(self, step: WorkflowStep, main_task: str) -> str:
        """Customize the task description for a specific step."""
        task_templates = {
            "plan": f"Create a detailed plan for: {main_task}",
            "code": f"Implement the following: {main_task}",
            "test": f"Create comprehensive tests for: {main_task}",
            "review": f"Review the implementation of: {main_task}",
        }

        return task_templates.get(step.agent_type, f"{step.description}: {main_task}")

    def _check_dependencies(
        self,
        step: Union[WorkflowStep, str],
        completed_results: Optional[List[TaskResult]] = None,
    ) -> bool:
        """Check if all dependencies for a step are satisfied."""
        # Handle legacy API where just agent type string is passed
        if isinstance(step, str):
            agent_type = step
            # Check if workflow has step_dependencies attribute (set by tests)
            if hasattr(self, "step_dependencies") and agent_type in self.step_dependencies:
                required_deps = self.step_dependencies[agent_type]
                # Check against completed_steps dictionary
                return all(
                    dep in self.completed_steps and self.completed_steps[dep]
                    for dep in required_deps
                )
            return True  # No dependencies defined

        # Original WorkflowStep API
        if not step.depends_on:
            return True

        completed_types = {result.agent_type for result in completed_results if result.success}
        return all(dep in completed_types for dep in step.depends_on)

    def _update_context_from_result(self, step: WorkflowStep, result: TaskResult) -> None:
        """Update the workflow context with results from a step."""
        if result.success:
            # Store the output with a key based on the agent type
            self.current_context[f"{step.agent_type}_output"] = result.output
            self.current_context[f"{step.agent_type}_result"] = result.to_dict()

            # Also update any context from the result itself
            if result.context:
                for key, value in result.context.items():
                    if not key.startswith("_"):  # Skip private context keys
                        self.current_context[key] = value

    def _should_continue_after_failure(self, step: WorkflowStep, result: TaskResult) -> bool:
        """Determine whether to continue the workflow after a step failure."""
        # For now, continue unless it's a planning step failure
        # This could be made more sophisticated based on step criticality
        return step.agent_type != "plan"

    def _generate_workflow_summary(
        self, workflow_name: str, task: str, results: List[TaskResult]
    ) -> str:
        """Generate a summary of the workflow execution."""
        successful_steps = sum(1 for r in results if r.success)
        total_steps = len(results)

        summary_parts = [
            f"# {workflow_name.title()} Workflow Summary",
            f"\n**Task**: {task}",
            f"**Completion**: {successful_steps}/{total_steps} steps successful",
        ]

        if successful_steps == total_steps:
            summary_parts.append("\n✅ **Status**: Workflow completed successfully")
        else:
            summary_parts.append(
                f"\n⚠️ **Status**: Workflow completed with "
                f"{total_steps - successful_steps} failures"
            )

        summary_parts.append("\n## Step Results:")
        for i, result in enumerate(results, 1):
            status = "✅" if result.success else "❌"
            summary_parts.append(f"{i}. {status} {result.agent_type.title()} Agent")
            if not result.success and result.error:
                summary_parts.append(f"   Error: {result.error}")

        return "\n".join(summary_parts)

    def create_custom_workflow(
        self,
        steps: List[str],
        task: str,
        context: Optional[Dict[str, Any]] = None,
        stream: bool = False,
    ) -> WorkflowResult:
        """Create and execute a custom workflow from a list of agent types."""
        start_time = time.time()
        workflow_steps = []

        for i, agent_type in enumerate(steps):
            if agent_type not in self.agents:
                raise ValueError(f"Unknown agent type: {agent_type}")

            # Simple dependency: each step depends on the previous one
            depends_on = [steps[i - 1]] if i > 0 else []

            workflow_steps.append(
                WorkflowStep(
                    agent_type=agent_type,
                    description=f"Execute {agent_type} agent",
                    depends_on=depends_on,
                )
            )

        # Execute the custom workflow
        initial_context_copy = (context or {}).copy()
        self.current_context = context or {}
        self.current_context["main_task"] = task

        console.print(
            Panel(
                f"[bold blue]Custom Workflow[/bold blue]\n\n"
                f"Task: {task}\n"
                f"Steps: {' → '.join(steps)}",
                title="Custom Workflow Execution",
                border_style="blue",
            )
        )

        results = []

        for i, step in enumerate(workflow_steps, 1):
            console.print(f"\n[bold]Step {i}/{len(workflow_steps)}: {step.description}[/bold]")

            result = self._execute_step(step, task, stream)
            results.append(result)

            self._update_context_from_result(step, result)

            if result.success:
                console.print(f"[green]✓ Step {i} completed successfully[/green]")
            else:
                console.print(f"[red]✗ Step {i} failed: {result.error}[/red]")

        # Calculate execution time
        execution_time = time.time() - start_time

        # Count completed successful steps
        successful_results = [r for r in results if r.success]

        return WorkflowResult(
            success=all(r.success for r in results) if results else False,
            results=results,
            workflow_name="custom",
            task=task,
            total_steps=len(workflow_steps),
            completed_steps=len(successful_results),
            execution_time=execution_time,
            error=None
            if all(r.success for r in results) or not results
            else f"Failed steps: {len(results) - len(successful_results)}",
            initial_context=initial_context_copy,
            final_context=self.current_context.copy(),
        )
