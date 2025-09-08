"""Command-line interface for Local Agents."""

import click
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .agents.planner import PlanningAgent
from .agents.coder import CodingAgent
from .agents.tester import TestingAgent
from .agents.reviewer import ReviewAgent
from .workflows.orchestrator import Workflow
from .config import config_manager
from .exceptions import (
    ModelNotAvailableError,
    ConfigurationError,
    FileOperationError,
    WorkflowError,
    AgentExecutionError,
)

console = Console()


def handle_common_errors(e: Exception) -> None:
    """Handle common exceptions with user-friendly error messages."""
    if isinstance(e, ConnectionError):
        console.print(Panel(
            "[red]Connection Error[/red]\n\n"
            "Cannot connect to Ollama. Please ensure:\n"
            "• Ollama is installed and running\n"
            "• The service is accessible at the configured host\n"
            "• No firewall is blocking the connection\n\n"
            "Run: [cyan]ollama serve[/cyan] to start Ollama",
            title="Connection Failed",
            border_style="red"
        ))
    elif isinstance(e, TimeoutError):
        console.print(Panel(
            "[red]Request Timeout[/red]\n\n"
            "The request to Ollama timed out. This might be because:\n"
            "• The model is too large for your system\n"
            "• Ollama is busy with other requests\n"
            "• Your task is very complex\n\n"
            "Try using a smaller model or breaking down the task.",
            title="Timeout Error",
            border_style="red"
        ))
    elif isinstance(e, ModelNotAvailableError):
        console.print(Panel(
            f"[red]Model Not Available[/red]\n\n"
            f"{e}\n\n"
            "Use: [cyan]ollama pull <model-name>[/cyan] to download the model",
            title="Model Error",
            border_style="red"
        ))
    elif isinstance(e, FileOperationError):
        console.print(Panel(
            f"[red]File Operation Failed[/red]\n\n"
            f"{e}\n\n"
            "Please check file permissions and paths.",
            title="File Error",
            border_style="red"
        ))
    elif isinstance(e, WorkflowError):
        console.print(Panel(
            f"[red]Workflow Error[/red]\n\n"
            f"{e}\n\n"
            "Please check your workflow configuration and try again.",
            title="Workflow Failed",
            border_style="red"
        ))
    elif isinstance(e, AgentExecutionError):
        console.print(Panel(
            f"[red]Agent Execution Error[/red]\n\n"
            f"{e}\n\n"
            "The agent encountered an error during execution.",
            title="Agent Error",
            border_style="red"
        ))
    else:
        console.print(Panel(
            f"[red]Unexpected Error[/red]\n\n"
            f"{e}\n\n"
            "If this problem persists, please check your configuration and try again.",
            title="Error",
            border_style="red"
        ))


@click.group(invoke_without_command=True)
@click.option('--version', is_flag=True, help='Show version information')
@click.pass_context
def main(ctx: click.Context, version: bool) -> None:
    """Local Agents - A suite of AI agents for software development."""
    if version:
        from . import __version__
        console.print(f"Local Agents version {__version__}")
        return
    
    if ctx.invoked_subcommand is None:
        console.print(Panel(
            "[bold blue]Local Agents[/bold blue]\n\n"
            "A local-only suite of AI agents for software development.\n\n"
            "[bold]Available Commands:[/bold]\n"
            "• [cyan]plan[/cyan] - Create implementation plans\n"
            "• [cyan]code[/cyan] - Generate or modify code\n"
            "• [cyan]test[/cyan] - Create and run tests\n"
            "• [cyan]review[/cyan] - Analyze and review code\n"
            "• [cyan]workflow[/cyan] - Execute multi-agent workflows\n"
            "• [cyan]config[/cyan] - Manage configuration\n\n"
            "[dim]Use --help with any command for more information.[/dim]",
            title="Welcome to Local Agents",
            border_style="blue",
        ))


@main.command()
@click.argument('task', required=True)
@click.option('--model', '-m', help='Override model for this task')
@click.option('--output', '-o', type=click.Path(), help='Save plan to file')
@click.option('--context', '-c', type=click.Path(exists=True), help='Context file or directory')
@click.option('--stream', is_flag=True, help='Stream output in real-time')
def plan(task: str, model: Optional[str], output: Optional[str], context: Optional[str], stream: bool) -> None:
    """Create an implementation plan for a task."""
    try:
        agent = PlanningAgent(model=model)
        agent.display_info()
        
        context_data = {}
        if context:
            context_path = Path(context)
            if context_path.is_file():
                context_data['file_content'] = context_path.read_text()
            elif context_path.is_dir():
                context_data['directory'] = str(context_path)
        
        result = agent.execute(task, context_data, stream=stream)
        result.display()
        
        if output and result.success:
            output_path = Path(output)
            output_path.write_text(result.output)
            console.print(f"[green]Plan saved to {output_path}[/green]")
        
    except Exception as e:
        handle_common_errors(e)


@main.command()
@click.argument('task', required=True)
@click.option('--file', '-f', type=click.Path(), help='File to modify or create')
@click.option('--spec', '-s', help='Detailed specification or requirements')
@click.option('--model', '-m', help='Override model for this task')
@click.option('--output', '-o', type=click.Path(), help='Save code to file')
@click.option('--context', '-c', type=click.Path(exists=True), help='Context file or directory')
@click.option('--stream', is_flag=True, help='Stream output in real-time')
def code(
    task: str,
    file: Optional[str],
    spec: Optional[str],
    model: Optional[str],
    output: Optional[str],
    context: Optional[str],
    stream: bool
) -> None:
    """Generate or modify code."""
    try:
        agent = CodingAgent(model=model)
        agent.display_info()
        
        context_data = {}
        if context:
            context_path = Path(context)
            if context_path.is_file():
                context_data['file_content'] = context_path.read_text()
            elif context_path.is_dir():
                context_data['directory'] = str(context_path)
        
        if file:
            context_data['target_file'] = file
            if Path(file).exists():
                context_data['existing_code'] = Path(file).read_text()
        
        if spec:
            context_data['specification'] = spec
        
        result = agent.execute(task, context_data, stream=stream)
        result.display()
        
        if output and result.success:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(result.output)
            console.print(f"[green]Code saved to {output_path}[/green]")
        
    except Exception as e:
        handle_common_errors(e)


@main.command()
@click.argument('target', required=True)
@click.option('--framework', help='Testing framework to use (pytest, unittest, jest, etc.)')
@click.option('--model', '-m', help='Override model for this task')
@click.option('--output', '-o', type=click.Path(), help='Save tests to file')
@click.option('--run', is_flag=True, help='Run tests after generation')
@click.option('--stream', is_flag=True, help='Stream output in real-time')
def test(
    target: str,
    framework: Optional[str],
    model: Optional[str],
    output: Optional[str],
    run: bool,
    stream: bool
) -> None:
    """Generate and optionally run tests."""
    try:
        agent = TestingAgent(model=model)
        agent.display_info()
        
        context_data = {}
        target_path = Path(target)
        
        if target_path.exists():
            if target_path.is_file():
                context_data['target_file'] = target
                context_data['code_content'] = target_path.read_text()
            else:
                context_data['target_directory'] = target
        else:
            context_data['target_description'] = target
        
        if framework:
            context_data['framework'] = framework
        
        context_data['run_tests'] = run
        
        result = agent.execute(f"Generate tests for {target}", context_data, stream=stream)
        result.display()
        
        if output and result.success:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(result.output)
            console.print(f"[green]Tests saved to {output_path}[/green]")
        
    except Exception as e:
        handle_common_errors(e)


@main.command()
@click.argument('target', required=True)
@click.option('--focus', help='Focus area (security, performance, style, etc.)')
@click.option('--model', '-m', help='Override model for this task')
@click.option('--output', '-o', type=click.Path(), help='Save review to file')
@click.option('--stream', is_flag=True, help='Stream output in real-time')
def review(
    target: str,
    focus: Optional[str],
    model: Optional[str],
    output: Optional[str],
    stream: bool
) -> None:
    """Analyze and review code."""
    try:
        agent = ReviewAgent(model=model)
        agent.display_info()
        
        context_data = {}
        target_path = Path(target)
        
        if target_path.exists():
            if target_path.is_file():
                context_data['target_file'] = target
                context_data['code_content'] = target_path.read_text()
            else:
                context_data['target_directory'] = target
        else:
            console.print(f"[red]Error: Target {target} does not exist[/red]")
            return
        
        if focus:
            context_data['focus_area'] = focus
        
        result = agent.execute(f"Review {target}", context_data, stream=stream)
        result.display()
        
        if output and result.success:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(result.output)
            console.print(f"[green]Review saved to {output_path}[/green]")
        
    except Exception as e:
        handle_common_errors(e)


@main.command()
@click.argument('workflow_name', required=True)
@click.argument('task', required=True)
@click.option('--context', '-c', type=click.Path(exists=True), help='Context file or directory')
@click.option('--output-dir', '-o', type=click.Path(), help='Output directory for results')
@click.option('--stream', is_flag=True, help='Stream output in real-time')
def workflow(
    workflow_name: str,
    task: str,
    context: Optional[str],
    output_dir: Optional[str],
    stream: bool
) -> None:
    """Execute a multi-agent workflow."""
    try:
        wf = Workflow()
        
        context_data = {}
        if context:
            context_path = Path(context)
            if context_path.is_file():
                context_data['file_content'] = context_path.read_text()
            elif context_path.is_dir():
                context_data['directory'] = str(context_path)
        
        if output_dir:
            context_data['output_directory'] = output_dir
            Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        result = wf.execute_workflow(workflow_name, task, context_data, stream=stream)
        
        console.print(Panel(
            f"[bold green]Workflow Complete![/bold green]\n\n"
            f"Executed {len(result.get('steps', []))} steps successfully.",
            title=f"{workflow_name.title()} Workflow",
            border_style="green",
        ))
        
    except Exception as e:
        handle_common_errors(e)


@main.command()
@click.option('--show', is_flag=True, help='Show current configuration')
@click.option('--set', nargs=2, metavar=('<key>', '<value>'), help='Set configuration value')
@click.option('--reset', is_flag=True, help='Reset to default configuration')
def config(show: bool, set: Optional[tuple], reset: bool) -> None:
    """Manage configuration."""
    if reset:
        config_manager._config = None
        config_manager.save_config()
        console.print("[green]Configuration reset to defaults[/green]")
        return
    
    if set:
        key, value = set
        config_obj = config_manager.load_config()
        # Simple key setting - could be enhanced for nested keys
        if hasattr(config_obj, key):
            setattr(config_obj, key, value)
            config_manager._config = config_obj
            config_manager.save_config()
            console.print(f"[green]Set {key} = {value}[/green]")
        else:
            console.print(f"[red]Unknown configuration key: {key}[/red]")
        return
    
    # Show configuration
    config_obj = config_manager.load_config()
    
    table = Table(title="Local Agents Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Config File", str(config_manager.config_path))
    table.add_row("Default Model", config_obj.default_model)
    table.add_row("Ollama Host", config_obj.ollama_host)
    table.add_row("Temperature", str(config_obj.temperature))
    table.add_row("Max Tokens", str(config_obj.max_tokens))
    table.add_row("Planning Model", config_obj.agents.planning)
    table.add_row("Coding Model", config_obj.agents.coding)
    table.add_row("Testing Model", config_obj.agents.testing)
    table.add_row("Review Model", config_obj.agents.reviewing)
    
    console.print(table)


# Individual command functions for direct script access
def plan_command() -> None:
    """Entry point for la-plan script."""
    import sys
    plan.main(sys.argv[1:], standalone_mode=False)


def code_command() -> None:
    """Entry point for la-code script."""
    import sys
    code.main(sys.argv[1:], standalone_mode=False)


def test_command() -> None:
    """Entry point for la-test script."""
    import sys
    test.main(sys.argv[1:], standalone_mode=False)


def review_command() -> None:
    """Entry point for la-review script."""
    import sys
    review.main(sys.argv[1:], standalone_mode=False)


if __name__ == '__main__':
    main()