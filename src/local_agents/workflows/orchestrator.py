"""Workflow orchestrator for managing multi-agent workflows."""

from typing import Dict, Any, List, Optional, Type, Union
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, TaskID

from ..agents.planner import PlanningAgent
from ..agents.coder import CodingAgent
from ..agents.tester import TestingAgent
from ..agents.reviewer import ReviewAgent
from ..base import BaseAgent, TaskResult
from ..config import config_manager

console = Console()


class WorkflowStep:
    """Represents a single step in a workflow."""
    
    def __init__(
        self,
        agent_type: str,
        description: str,
        depends_on: Optional[List[str]] = None,
        context_mapping: Optional[Dict[str, str]] = None
    ) -> None:
        self.agent_type = agent_type
        self.description = description
        self.depends_on = depends_on or []
        self.context_mapping = context_mapping or {}
        self.result: Optional[TaskResult] = None
        self.completed = False


class Workflow:
    """Orchestrates multi-agent workflows."""
    
    def __init__(self) -> None:
        self.agents: Dict[str, Type[BaseAgent]] = {
            'plan': PlanningAgent,
            'code': CodingAgent,
            'test': TestingAgent,
            'review': ReviewAgent,
        }
        self.current_context: Dict[str, Any] = {}
    
    def execute_workflow(
        self,
        workflow_name: str,
        task: str,
        initial_context: Optional[Dict[str, Any]] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """Execute a predefined workflow."""
        self.current_context = initial_context or {}
        self.current_context['main_task'] = task
        
        workflow_steps = self._get_workflow_definition(workflow_name)
        if not workflow_steps:
            raise ValueError(f"Unknown workflow: {workflow_name}")
        
        console.print(Panel(
            f"[bold blue]Starting Workflow: {workflow_name.title()}[/bold blue]\n\n"
            f"Task: {task}\n"
            f"Steps: {len(workflow_steps)}",
            title="Workflow Execution",
            border_style="blue",
        ))
        
        results = []
        
        with Progress() as progress:
            workflow_task = progress.add_task(
                f"[cyan]{workflow_name.title()} Workflow",
                total=len(workflow_steps)
            )
            
            for i, step in enumerate(workflow_steps, 1):
                console.print(f"\n[bold]Step {i}/{len(workflow_steps)}: {step.description}[/bold]")
                
                # Check dependencies
                if not self._check_dependencies(step, results):
                    console.print(f"[red]Skipping step due to failed dependencies[/red]")
                    continue
                
                # Execute step
                result = self._execute_step(step, task, stream)
                results.append(result)
                
                # Update context with results
                self._update_context_from_result(step, result)
                
                if result.success:
                    console.print(f"[green]✓ Step {i} completed successfully[/green]")
                else:
                    console.print(f"[red]✗ Step {i} failed: {result.error}[/red]")
                    
                    # Decide whether to continue or abort
                    if not self._should_continue_after_failure(step, result):
                        console.print("[red]Workflow aborted due to critical failure[/red]")
                        break
                
                progress.advance(workflow_task)
        
        # Generate workflow summary
        summary = self._generate_workflow_summary(workflow_name, task, results)
        
        return {
            'workflow_name': workflow_name,
            'task': task,
            'steps': [result.to_dict() for result in results],
            'success': all(r.success for r in results),
            'summary': summary,
            'context': self.current_context
        }
    
    def _get_workflow_definition(self, workflow_name: str) -> List[WorkflowStep]:
        """Get the definition for a predefined workflow."""
        workflows = {
            'feature-dev': [
                WorkflowStep('plan', 'Create implementation plan'),
                WorkflowStep('code', 'Generate code implementation', 
                           depends_on=['plan'],
                           context_mapping={'plan_output': 'implementation_plan'}),
                WorkflowStep('test', 'Create and run tests',
                           depends_on=['code'],
                           context_mapping={'code_output': 'code_to_test'}),
                WorkflowStep('review', 'Review implementation',
                           depends_on=['code'],
                           context_mapping={'code_output': 'code_to_review'})
            ],
            'bug-fix': [
                WorkflowStep('plan', 'Analyze bug and create fix plan'),
                WorkflowStep('code', 'Implement bug fix',
                           depends_on=['plan'],
                           context_mapping={'plan_output': 'fix_plan'}),
                WorkflowStep('test', 'Test bug fix',
                           depends_on=['code'],
                           context_mapping={'code_output': 'fixed_code'})
            ],
            'code-review': [
                WorkflowStep('review', 'Comprehensive code review')
            ],
            'refactor': [
                WorkflowStep('plan', 'Create refactoring plan'),
                WorkflowStep('code', 'Implement refactoring',
                           depends_on=['plan'],
                           context_mapping={'plan_output': 'refactor_plan'}),
                WorkflowStep('test', 'Test refactored code',
                           depends_on=['code'],
                           context_mapping={'code_output': 'refactored_code'}),
                WorkflowStep('review', 'Review refactored implementation',
                           depends_on=['code'],
                           context_mapping={'code_output': 'code_to_review'})
            ]
        }
        
        # Also check user-configured workflows
        config_workflows = config_manager.get_workflow_steps(workflow_name)
        if config_workflows:
            return [WorkflowStep(step, f"Execute {step} agent") for step in config_workflows]
        
        return workflows.get(workflow_name, [])
    
    def _execute_step(self, step: WorkflowStep, main_task: str, stream: bool = False) -> TaskResult:
        """Execute a single workflow step."""
        try:
            # Get the appropriate agent
            agent_class = self.agents.get(step.agent_type)
            if not agent_class:
                return TaskResult(
                    success=False,
                    output="",
                    agent_type=step.agent_type,
                    task=step.description,
                    error=f"Unknown agent type: {step.agent_type}"
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
            step.result = result
            step.completed = True
            
            return result
            
        except Exception as e:
            return TaskResult(
                success=False,
                output="",
                agent_type=step.agent_type,
                task=step.description,
                error=str(e)
            )
    
    def _customize_task_for_step(self, step: WorkflowStep, main_task: str) -> str:
        """Customize the task description for a specific step."""
        task_templates = {
            'plan': f"Create a detailed plan for: {main_task}",
            'code': f"Implement the following: {main_task}",
            'test': f"Create comprehensive tests for: {main_task}",
            'review': f"Review the implementation of: {main_task}"
        }
        
        return task_templates.get(step.agent_type, f"{step.description}: {main_task}")
    
    def _check_dependencies(self, step: WorkflowStep, completed_results: List[TaskResult]) -> bool:
        """Check if all dependencies for a step are satisfied."""
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
                    if not key.startswith('_'):  # Skip private context keys
                        self.current_context[key] = value
    
    def _should_continue_after_failure(self, step: WorkflowStep, result: TaskResult) -> bool:
        """Determine whether to continue the workflow after a step failure."""
        # For now, continue unless it's a planning step failure
        # This could be made more sophisticated based on step criticality
        return step.agent_type != 'plan'
    
    def _generate_workflow_summary(
        self,
        workflow_name: str,
        task: str,
        results: List[TaskResult]
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
            summary_parts.append(f"\n⚠️ **Status**: Workflow completed with {total_steps - successful_steps} failures")
        
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
        stream: bool = False
    ) -> Dict[str, Any]:
        """Create and execute a custom workflow from a list of agent types."""
        workflow_steps = []
        
        for i, agent_type in enumerate(steps):
            if agent_type not in self.agents:
                raise ValueError(f"Unknown agent type: {agent_type}")
            
            # Simple dependency: each step depends on the previous one
            depends_on = [steps[i-1]] if i > 0 else []
            
            workflow_steps.append(WorkflowStep(
                agent_type=agent_type,
                description=f"Execute {agent_type} agent",
                depends_on=depends_on
            ))
        
        # Execute the custom workflow
        self.current_context = context or {}
        self.current_context['main_task'] = task
        
        console.print(Panel(
            f"[bold blue]Custom Workflow[/bold blue]\n\n"
            f"Task: {task}\n"
            f"Steps: {' → '.join(steps)}",
            title="Custom Workflow Execution",
            border_style="blue",
        ))
        
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
        
        summary = self._generate_workflow_summary("custom", task, results)
        
        return {
            'workflow_name': 'custom',
            'task': task,
            'steps': [result.to_dict() for result in results],
            'success': all(r.success for r in results),
            'summary': summary,
            'context': self.current_context
        }