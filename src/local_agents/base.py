"""Base agent classes and utilities."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, TypeVar
from rich.console import Console
from rich.panel import Panel
from functools import wraps

from .ollama_client import OllamaClient
from .config import get_config, get_model_for_agent

T = TypeVar('T', bound='BaseAgent')

console = Console()


def handle_agent_execution(func: Callable) -> Callable:
    """Decorator to handle common agent execution error patterns."""
    @wraps(func)
    def wrapper(self: 'BaseAgent', task: str, context: Optional[Dict[str, Any]] = None, stream: bool = False) -> 'TaskResult':
        try:
            context = context or {}
            return func(self, task, context, stream)
        except Exception as e:
            return TaskResult(
                success=False,
                output="",
                agent_type=self.agent_type,
                task=task,
                context=context,
                error=str(e)
            )
    return wrapper


class BaseAgent(ABC):
    """Base class for all agents."""
    
    def __init__(
        self,
        agent_type: str,
        role: str,
        goal: str,
        model: Optional[str] = None,
        ollama_client: Optional[OllamaClient] = None,
    ):
        self.agent_type = agent_type
        self.role = role
        self.goal = goal
        
        config = get_config()
        self.model = model or get_model_for_agent(agent_type)
        self.temperature = config.temperature
        self.max_tokens = config.max_tokens
        
        self.ollama_client = ollama_client or OllamaClient(config.ollama_host)
        
        # Ensure model is available
        if not self.ollama_client.is_model_available(self.model):
            console.print(f"[yellow]Model {self.model} not found. Attempting to pull...[/yellow]")
            if not self.ollama_client.pull_model(self.model):
                raise RuntimeError(f"Failed to pull model {self.model}")
    
    @abstractmethod
    def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute the agent's task."""
        pass
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for this agent."""
        return f"""You are a {self.role}.

Goal: {self.goal}

You should provide clear, actionable, and well-structured responses. Always consider the context provided and maintain consistency with existing patterns and conventions."""
    
    def _call_ollama(
        self,
        prompt: str,
        system: Optional[str] = None,
        stream: bool = False,
    ) -> str:
        """Call Ollama with the given prompt."""
        system_prompt = system or self._build_system_prompt()
        
        try:
            return self.ollama_client.generate(
                model=self.model,
                prompt=prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                system=system_prompt,
                stream=stream,
            )
        except Exception as e:
            console.print(f"[red]Error calling Ollama: {e}[/red]")
            raise
    
    def _call_ollama_chat(
        self,
        messages: list[Dict[str, str]],
        stream: bool = False,
    ) -> str:
        """Call Ollama using chat format."""
        try:
            return self.ollama_client.chat(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=stream,
            )
        except Exception as e:
            console.print(f"[red]Error calling Ollama chat: {e}[/red]")
            raise
    
    def display_info(self) -> None:
        """Display agent information."""
        info_panel = Panel(
            f"[bold blue]{self.role}[/bold blue]\n\n"
            f"[bold]Goal:[/bold] {self.goal}\n"
            f"[bold]Model:[/bold] {self.model}\n"
            f"[bold]Type:[/bold] {self.agent_type}",
            title=f"{self.agent_type.title()} Agent",
            border_style="blue",
        )
        console.print(info_panel)
    
    def _create_success_result(
        self,
        output: str,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> 'TaskResult':
        """Helper method to create a successful TaskResult."""
        return TaskResult(
            success=True,
            output=output,
            agent_type=self.agent_type,
            task=task,
            context=context or {}
        )


class TaskResult:
    """Represents the result of an agent task execution."""
    
    def __init__(
        self,
        success: bool,
        output: str,
        agent_type: str,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ):
        self.success = success
        self.output = output
        self.agent_type = agent_type
        self.task = task
        self.context = context or {}
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "output": self.output,
            "agent_type": self.agent_type,
            "task": self.task,
            "context": self.context,
            "error": self.error,
        }
    
    def display(self) -> None:
        """Display the task result."""
        if self.success:
            result_panel = Panel(
                self.output,
                title=f"[green]{self.agent_type.title()} Agent Result[/green]",
                border_style="green",
            )
        else:
            result_panel = Panel(
                f"[red]Error:[/red] {self.error}\n\n[yellow]Output:[/yellow] {self.output}",
                title=f"[red]{self.agent_type.title()} Agent Failed[/red]",
                border_style="red",
            )
        
        console.print(result_panel)