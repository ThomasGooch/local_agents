"""Command-line interface for Local Agents."""

from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .agents.coder import CodingAgent
from .agents.planner import PlanningAgent
from .agents.reviewer import ReviewAgent
from .agents.tester import TestingAgent
from .benchmarks import benchmark_system
from .config import config_manager
from .exceptions import (
    AgentExecutionError,
    FileOperationError,
    ModelNotAvailableError,
    WorkflowError,
)
from .hardware import hardware_optimizer
from .performance import performance_monitor
from .workflows.orchestrator import Workflow

console = Console()


def handle_common_errors(e: Exception) -> None:
    """Handle common exceptions with user-friendly error messages."""
    if isinstance(e, ConnectionError):
        console.print(
            Panel(
                "[red]Connection Error[/red]\n\n"
                "Cannot connect to Ollama. Please ensure:\n"
                "• Ollama is installed and running\n"
                "• The service is accessible at the configured host\n"
                "• No firewall is blocking the connection\n\n"
                "Run: [cyan]ollama serve[/cyan] to start Ollama",
                title="Connection Failed",
                border_style="red",
            )
        )
    elif isinstance(e, TimeoutError):
        console.print(
            Panel(
                "[red]Request Timeout[/red]\n\n"
                "The request to Ollama timed out. This might be because:\n"
                "• The model is too large for your system\n"
                "• Ollama is busy with other requests\n"
                "• Your task is very complex\n\n"
                "Try using a smaller model or breaking down the task.",
                title="Timeout Error",
                border_style="red",
            )
        )
    elif isinstance(e, ModelNotAvailableError):
        console.print(
            Panel(
                f"[red]Model Not Available[/red]\n\n"
                f"{e}\n\n"
                "Use: [cyan]ollama pull <model-name>[/cyan] to download the model",
                title="Model Error",
                border_style="red",
            )
        )
    elif isinstance(e, FileOperationError):
        console.print(
            Panel(
                f"[red]File Operation Failed[/red]\n\n"
                f"{e}\n\n"
                "Please check file permissions and paths.",
                title="File Error",
                border_style="red",
            )
        )
    elif isinstance(e, WorkflowError):
        console.print(
            Panel(
                f"[red]Workflow Error[/red]\n\n"
                f"{e}\n\n"
                "Please check your workflow configuration and try again.",
                title="Workflow Failed",
                border_style="red",
            )
        )
    elif isinstance(e, AgentExecutionError):
        console.print(
            Panel(
                f"[red]Agent Execution Error[/red]\n\n"
                f"{e}\n\n"
                "The agent encountered an error during execution.",
                title="Agent Error",
                border_style="red",
            )
        )
    else:
        console.print(
            Panel(
                f"[red]Unexpected Error[/red]\n\n"
                f"{e}\n\n"
                + ("If this problem persists, please check your configuration " "and try again."),
                title="Error",
                border_style="red",
            )
        )


@click.group(invoke_without_command=True)
@click.option("--version", is_flag=True, help="Show version information")
@click.pass_context
def main(ctx: click.Context, version: bool) -> None:
    """Local Agents - A suite of AI agents for software development."""
    if version:
        from . import __version__

        console.print(f"Local Agents version {__version__}")
        return

    if ctx.invoked_subcommand is None:
        console.print(
            Panel(
                "[bold blue]Local Agents[/bold blue]\n\n"
                "A local-only suite of AI agents for software development.\n\n"
                "[bold]Available Commands:[/bold]\n"
                "• [cyan]plan[/cyan] - Create implementation plans\n"
                "• [cyan]code[/cyan] - Generate or modify code\n"
                "• [cyan]test[/cyan] - Create and run tests\n"
                "• [cyan]review[/cyan] - Analyze and review code\n"
                "• [cyan]workflow[/cyan] - Execute multi-agent workflows\n"
                "• [cyan]config[/cyan] - Manage configuration\n"
                "• [cyan]model[/cyan] - Manage AI models\n\n"
                "[dim]Use --help with any command for more information.[/dim]",
                title="Welcome to Local Agents",
                border_style="blue",
            )
        )


@main.command()
@click.argument("task", required=True)
@click.option("--model", "-m", help="Override model for this task")
@click.option("--output", "-o", type=click.Path(), help="Save plan to file")
@click.option("--context", "-c", type=click.Path(exists=True), help="Context file or directory")
@click.option("--stream/--no-stream", default=True, help="Stream output in real-time")
def plan(
    task: str,
    model: Optional[str],
    output: Optional[str],
    context: Optional[str],
    stream: bool,
) -> None:
    """Create an implementation plan for a task."""
    try:
        console.print(
            Panel(
                f"[bold blue]Planning Task[/bold blue]\n\n"
                f"Task: {task}\n"
                f"Model: {model or 'default'}\n"
                f"Context: {context or 'none'}\n"
                f"Streaming: {'enabled' if stream else 'disabled'}",
                title="Planning Agent",
                border_style="blue",
            )
        )

        agent = PlanningAgent(model=model)
        agent.display_info()

        context_data = {}
        if context:
            context_path = Path(context)
            if context_path.is_file():
                context_data["file_content"] = context_path.read_text()
                console.print(f"[dim]Loaded context from file: {context_path}[/dim]")
            elif context_path.is_dir():
                context_data["directory"] = str(context_path)
                console.print(f"[dim]Using directory context: {context_path}[/dim]")

        if not stream:
            with console.status("[cyan]Planning in progress..."):
                result = agent.execute(task, context_data, stream=False)
        else:
            result = agent.execute(task, context_data, stream=True)

        result.display()

        if output and result.success:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(result.output)
            console.print(f"[green]✓ Plan saved to {output_path}[/green]")

    except Exception as e:
        handle_common_errors(e)


@main.command()
@click.argument("task", required=True)
@click.option("--file", "-f", type=click.Path(), help="File to modify or create")
@click.option("--spec", "-s", help="Detailed specification or requirements")
@click.option("--model", "-m", help="Override model for this task")
@click.option("--output", "-o", type=click.Path(), help="Save code to file")
@click.option("--context", "-c", type=click.Path(exists=True), help="Context file or directory")
@click.option("--stream/--no-stream", default=True, help="Stream output in real-time")
def code(
    task: str,
    file: Optional[str],
    spec: Optional[str],
    model: Optional[str],
    output: Optional[str],
    context: Optional[str],
    stream: bool,
) -> None:
    """Generate or modify code."""
    try:
        console.print(
            Panel(
                f"[bold green]Coding Task[/bold green]\n\n"
                f"Task: {task}\n"
                f"Target file: {file or 'new code'}\n"
                f"Model: {model or 'default'}\n"
                f"Specification: {spec or 'none'}\n"
                f"Context: {context or 'none'}\n"
                f"Streaming: {'enabled' if stream else 'disabled'}",
                title="Coding Agent",
                border_style="green",
            )
        )

        agent = CodingAgent(model=model)
        agent.display_info()

        context_data = {}
        if context:
            context_path = Path(context)
            if context_path.is_file():
                context_data["file_content"] = context_path.read_text()
                console.print(f"[dim]Loaded context from file: {context_path}[/dim]")
            elif context_path.is_dir():
                context_data["directory"] = str(context_path)
                console.print(f"[dim]Using directory context: {context_path}[/dim]")

        if file:
            context_data["target_file"] = file
            if Path(file).exists():
                context_data["existing_code"] = Path(file).read_text()
                console.print(f"[dim]Loaded existing code from: {file}[/dim]")
            else:
                console.print(f"[dim]Will create new file: {file}[/dim]")

        if spec:
            context_data["specification"] = spec

        if not stream:
            with console.status("[cyan]Generating code..."):
                result = agent.execute(task, context_data, stream=False)
        else:
            result = agent.execute(task, context_data, stream=True)

        result.display()

        if output and result.success:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(result.output)
            console.print(f"[green]✓ Code saved to {output_path}[/green]")

    except Exception as e:
        handle_common_errors(e)


@main.command()
@click.argument("target", required=True)
@click.option("--framework", help="Testing framework to use (pytest, unittest, jest, etc.)")
@click.option("--model", "-m", help="Override model for this task")
@click.option("--output", "-o", type=click.Path(), help="Save tests to file")
@click.option("--run", is_flag=True, help="Run tests after generation")
@click.option("--stream/--no-stream", default=True, help="Stream output in real-time")
def test(
    target: str,
    framework: Optional[str],
    model: Optional[str],
    output: Optional[str],
    run: bool,
    stream: bool,
) -> None:
    """Generate and optionally run tests."""
    try:
        target_path = Path(target)
        target_type = (
            "file"
            if target_path.is_file()
            else "directory"
            if target_path.is_dir()
            else "description"
        )

        console.print(
            Panel(
                f"[bold yellow]Testing Task[/bold yellow]\n\n"
                f"Target: {target} ({target_type})\n"
                f"Framework: {framework or 'auto-detect'}\n"
                f"Model: {model or 'default'}\n"
                f"Run tests: {'yes' if run else 'no'}\n"
                f"Streaming: {'enabled' if stream else 'disabled'}",
                title="Testing Agent",
                border_style="yellow",
            )
        )

        agent = TestingAgent(model=model)
        agent.display_info()

        context_data = {}

        if target_path.exists():
            if target_path.is_file():
                context_data["target_file"] = target
                context_data["code_content"] = target_path.read_text()
                console.print(f"[dim]Loaded code from file: {target}[/dim]")
            else:
                context_data["target_directory"] = target
                console.print(f"[dim]Using directory: {target}[/dim]")
        else:
            context_data["target_description"] = target
            console.print(f"[dim]Using description: {target}[/dim]")

        if framework:
            context_data["framework"] = framework

        context_data["run_tests"] = run

        if not stream:
            with console.status("[cyan]Generating tests..."):
                result = agent.execute(f"Generate tests for {target}", context_data, stream=False)
        else:
            result = agent.execute(f"Generate tests for {target}", context_data, stream=True)

        result.display()

        if output and result.success:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(result.output)
            console.print(f"[green]✓ Tests saved to {output_path}[/green]")

    except Exception as e:
        handle_common_errors(e)


@main.command()
@click.argument("target", required=True)
@click.option("--focus", help="Focus area (security, performance, style, etc.)")
@click.option("--model", "-m", help="Override model for this task")
@click.option("--output", "-o", type=click.Path(), help="Save review to file")
@click.option("--stream/--no-stream", default=True, help="Stream output in real-time")
def review(
    target: str,
    focus: Optional[str],
    model: Optional[str],
    output: Optional[str],
    stream: bool,
) -> None:
    """Analyze and review code."""
    try:
        target_path = Path(target)

        if not target_path.exists():
            console.print(
                Panel(
                    f"[red]Target does not exist: {target}[/red]\n\n"
                    "Please provide a valid file or directory path.",
                    title="Error",
                    border_style="red",
                )
            )
            return

        target_type = "file" if target_path.is_file() else "directory"

        console.print(
            Panel(
                f"[bold magenta]Code Review Task[/bold magenta]\n\n"
                f"Target: {target} ({target_type})\n"
                f"Focus: {focus or 'general review'}\n"
                f"Model: {model or 'default'}\n"
                f"Streaming: {'enabled' if stream else 'disabled'}",
                title="Review Agent",
                border_style="magenta",
            )
        )

        agent = ReviewAgent(model=model)
        agent.display_info()

        context_data = {}

        if target_path.is_file():
            context_data["target_file"] = target
            context_data["code_content"] = target_path.read_text()
            console.print(f"[dim]Loaded code from file: {target}[/dim]")
        else:
            context_data["target_directory"] = target
            console.print(f"[dim]Reviewing directory: {target}[/dim]")

        if focus:
            context_data["focus_area"] = focus

        if not stream:
            with console.status("[cyan]Analyzing code..."):
                result = agent.execute(f"Review {target}", context_data, stream=False)
        else:
            result = agent.execute(f"Review {target}", context_data, stream=True)

        result.display()

        if output and result.success:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(result.output)
            console.print(f"[green]✓ Review saved to {output_path}[/green]")

    except Exception as e:
        handle_common_errors(e)


@main.command()
@click.argument("workflow_name", required=True)
@click.argument("task", required=True)
@click.option("--context", "-c", type=click.Path(exists=True), help="Context file or directory")
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(),
    help="Output directory for results (defaults to current directory)",
)
@click.option("--stream", is_flag=True, help="Stream output in real-time")
def workflow(
    workflow_name: str,
    task: str,
    context: Optional[str],
    output_dir: Optional[str],
    stream: bool,
) -> None:
    """Execute a multi-agent workflow."""
    try:
        wf = Workflow()

        context_data = {}
        if context:
            context_path = Path(context)
            if context_path.is_file():
                context_data["file_content"] = context_path.read_text()
            elif context_path.is_dir():
                context_data["directory"] = str(context_path)

        # Use PWD as default output directory if none specified
        if not output_dir:
            output_dir = str(Path.cwd())
        context_data["output_directory"] = output_dir
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        result = wf.execute_workflow(workflow_name, task, context_data, stream=stream)

        # Use the WorkflowResult's built-in display method
        result.display()

        # Save results to output directory (always available now)
        if result.success:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            # Save workflow summary
            summary_path = output_path / f"{workflow_name}_summary.md"
            summary_path.write_text(result.summary)
            console.print(f"[dim]Workflow summary saved to {summary_path}[/dim]")

            # Save individual step outputs
            for i, step_result in enumerate(result.results, 1):
                if step_result.success and step_result.output:
                    step_path = output_path / f"step_{i}_{step_result.agent_type}.txt"
                    step_path.write_text(step_result.output)

    except Exception as e:
        handle_common_errors(e)


@main.group()
def config():
    """Manage configuration."""
    pass


@config.command()
def show():
    """Show current configuration."""
    try:
        config_obj = config_manager.load_config()

        table = Table(title="Local Agents Configuration")
        table.add_column("Setting", style="cyan", no_wrap=True)
        table.add_column("Value", style="green")
        table.add_column("Description", style="dim")

        table.add_row(
            "Config File",
            str(config_manager.config_path),
            "Configuration file location",
        )
        table.add_row("Default Model", config_obj.default_model, "Default model for all agents")
        table.add_row("Ollama Host", config_obj.ollama_host, "Ollama service URL")
        table.add_row("Temperature", str(config_obj.temperature), "Model creativity (0.0-2.0)")
        table.add_row("Max Tokens", str(config_obj.max_tokens), "Maximum response length")
        table.add_row("Context Length", str(config_obj.context_length), "Maximum context size")
        table.add_row("", "", "")  # Separator
        table.add_row("[bold]Agent Models[/bold]", "", "")
        table.add_row("Planning Model", config_obj.agents.planning, "Model for planning tasks")
        table.add_row("Coding Model", config_obj.agents.coding, "Model for code generation")
        table.add_row("Testing Model", config_obj.agents.testing, "Model for test creation")
        table.add_row("Review Model", config_obj.agents.reviewing, "Model for code review")

        console.print(table)

    except Exception as e:
        handle_common_errors(e)


@config.command()
@click.argument("key")
@click.argument("value")
def set(key: str, value: str):
    """Set a configuration value."""
    try:
        # Handle nested keys like agents.coding
        if "." in key:
            main_key, sub_key = key.split(".", 1)
            config_manager.update_config(f"{main_key}.{sub_key}", value)
        else:
            config_manager.update_config(key, value)

        console.print(f"[green]✓ Set {key} = {value}[/green]")

        # Show updated value
        config_obj = config_manager.load_config()
        if "." in key:
            main_key, sub_key = key.split(".", 1)
            if hasattr(config_obj, main_key):
                section = getattr(config_obj, main_key)
                if hasattr(section, sub_key):
                    actual_value = getattr(section, sub_key)
                    console.print(f"[dim]Updated value: {actual_value}[/dim]")
        elif hasattr(config_obj, key):
            actual_value = getattr(config_obj, key)
            console.print(f"[dim]Updated value: {actual_value}[/dim]")

    except Exception as e:
        handle_common_errors(e)


@config.command()
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
def reset(force: bool):
    """Reset configuration to defaults."""
    try:
        if not force:
            if not click.confirm("This will reset all configuration to defaults. Continue?"):
                console.print("[dim]Configuration reset cancelled[/dim]")
                return

        config_manager._config = None
        config_manager.save_config()
        console.print("[green]✓ Configuration reset to defaults[/green]")

    except Exception as e:
        handle_common_errors(e)


@config.command()
def backup():
    """Create a backup of current configuration."""
    try:
        backup_path = config_manager.create_backup()
        console.print(f"[green]✓ Configuration backup created: {backup_path}[/green]")

    except Exception as e:
        handle_common_errors(e)


@config.command()
@click.argument("backup_file", type=click.Path(exists=True))
def restore(backup_file: str):
    """Restore configuration from backup."""
    try:
        if not click.confirm(
            f"This will replace current configuration with {backup_file}. Continue?"
        ):
            console.print("[dim]Configuration restore cancelled[/dim]")
            return

        config_manager.restore_from_backup(backup_file)
        console.print(f"[green]✓ Configuration restored from {backup_file}[/green]")

    except Exception as e:
        handle_common_errors(e)


@config.command()
def validate():
    """Validate current configuration."""
    try:
        config_manager.load_config()  # Just validate, don't store
        console.print("[green]✓ Configuration is valid[/green]")

        # Test Ollama connection
        try:
            from .ollama_client import OllamaClient

            client = OllamaClient()
            models = client.list_models()
            console.print(
                f"[green]✓ Ollama connection successful "
                f"({len(models)} models available)[/green]"
            )
        except Exception as ollama_error:
            console.print(f"[yellow]⚠ Ollama connection failed: {ollama_error}[/yellow]")

    except Exception as e:
        handle_common_errors(e)


@main.group()
def model():
    """Manage AI models."""
    pass


@model.command()
def list():
    """List available models."""
    try:
        from .ollama_client import OllamaClient

        client = OllamaClient()
        models = client.list_models()

        table = Table(title="Available Models")
        table.add_column("Model Name", style="cyan")
        table.add_column("Size", style="green")
        table.add_column("Modified", style="dim")

        for model_info in models:
            table.add_row(
                model_info.get("name", "Unknown"),
                model_info.get("size_human", "Unknown"),
                model_info.get("modified_human", "Unknown"),
            )

        console.print(table)

    except Exception as e:
        handle_common_errors(e)


@model.command()
@click.argument("model_name")
def pull(model_name: str):
    """Download a model from Ollama library."""
    try:
        from .ollama_client import OllamaClient

        client = OllamaClient()

        console.print(f"[cyan]Downloading model: {model_name}[/cyan]")

        with console.status(f"[cyan]Pulling {model_name}..."):
            client.pull_model(model_name)

        console.print(f"[green]✓ Model {model_name} downloaded successfully[/green]")

    except Exception as e:
        handle_common_errors(e)


@model.command()
@click.argument("model_name")
def remove(model_name: str):
    """Remove a model."""
    try:
        from .ollama_client import OllamaClient

        client = OllamaClient()

        if click.confirm(f"Are you sure you want to remove model '{model_name}'?"):
            client.remove_model(model_name)
            console.print(f"[green]✓ Model {model_name} removed successfully[/green]")
        else:
            console.print("[dim]Model removal cancelled[/dim]")

    except Exception as e:
        handle_common_errors(e)


@model.command()
def status():
    """Show Ollama service status."""
    try:
        from .ollama_client import OllamaClient

        client = OllamaClient()

        # Test connection
        models = client.list_models()

        config_obj = config_manager.load_config()

        console.print(
            Panel(
                f"[green]✓ Ollama service is running[/green]\n\n"
                f"Host: {config_obj.ollama_host}\n"
                f"Available models: {len(models)}\n"
                f"Default model: {config_obj.default_model}",
                title="Ollama Status",
                border_style="green",
            )
        )

    except Exception:
        console.print(
            Panel(
                "[red]✗ Ollama service is not accessible[/red]\n\n"
                "Please ensure Ollama is installed and running:\n"
                "• Install: https://ollama.ai\n"
                "• Start: [cyan]ollama serve[/cyan]",
                title="Ollama Status",
                border_style="red",
            )
        )


# Performance and hardware optimization commands
@main.group()
def performance():
    """Performance monitoring and optimization."""
    pass


@performance.command()
def monitor():
    """Start performance monitoring."""
    performance_monitor.start_monitoring()


@performance.command()
def stop():
    """Stop performance monitoring."""
    performance_monitor.stop_monitoring()


@performance.command()
def report():
    """Display performance report."""
    performance_monitor.display_performance_report()


@performance.command()
@click.option("--filepath", "-f", type=click.Path(), help="Export file path")
def export(filepath: Optional[str]):
    """Export performance metrics to file."""
    try:
        import time
        from pathlib import Path

        if not filepath:
            filepath = Path.cwd() / f"performance_metrics_{int(time.time())}.json"
        else:
            filepath = Path(filepath)

        performance_monitor.export_metrics(filepath)
    except Exception as e:
        handle_common_errors(e)


@performance.command()
def clear():
    """Clear performance metrics."""
    if click.confirm("Clear all performance metrics?"):
        performance_monitor.clear_metrics()
    else:
        console.print("[dim]Operation cancelled[/dim]")


@main.group()
def hardware():
    """Hardware optimization and detection."""
    pass


@hardware.command()
def detect():
    """Detect hardware configuration."""
    hardware_optimizer.display_hardware_info()


@hardware.command()
def optimize():
    """Apply hardware-specific optimizations."""
    try:
        profile = hardware_optimizer.detect_best_profile()

        console.print(f"[cyan]Detected Profile:[/cyan] {profile.name}")
        console.print("\n[bold]Optimization Changes:[/bold]")

        # Show what will be changed
        config = hardware_optimizer.get_optimization_config(profile)
        settings_table = Table(title="Performance Settings")
        settings_table.add_column("Setting", style="yellow")
        settings_table.add_column("Value", style="green")

        for key, value in config["performance_settings"].items():
            settings_table.add_row(key.replace("_", " ").title(), str(value))

        console.print(settings_table)

        if click.confirm("Apply these optimizations?"):
            success = hardware_optimizer.apply_optimization(config_manager, profile)
            if success:
                console.print("[green]✓ Hardware optimization applied successfully[/green]")
            else:
                console.print("[red]✗ Failed to apply optimization[/red]")
        else:
            console.print("[dim]Optimization cancelled[/dim]")

    except Exception as e:
        handle_common_errors(e)


@hardware.command()
def profiles():
    """Show all hardware profiles."""
    hardware_optimizer.display_all_profiles()


@main.group()
def benchmark():
    """Performance benchmarking."""
    pass


@benchmark.command()
@click.option(
    "--suite",
    "-s",
    default="quick",
    type=click.Choice(["quick", "comprehensive", "stress"]),
    help="Benchmark suite to run",
)
@click.option(
    "--concurrent",
    "-c",
    multiple=True,
    type=int,
    help="Concurrent levels to test (can specify multiple)",
)
@click.option("--repeat", "-r", default=1, help="Number of repetitions")
@click.option("--export", "-e", type=click.Path(), help="Export results to file")
def run(suite: str, concurrent: tuple, repeat: int, export: Optional[str]):
    """Run performance benchmark suite."""
    try:
        concurrent_levels = list(concurrent) if concurrent else [1, 2]

        console.print(f"[bold blue]Running {suite} benchmark suite[/bold blue]")
        console.print(f"Concurrent levels: {concurrent_levels}")
        console.print(f"Repetitions: {repeat}")

        results = benchmark_system.run_benchmark_suite(
            suite_type=suite, concurrent_levels=concurrent_levels, repeat_count=repeat
        )

        benchmark_system.display_benchmark_results(results)

        if export:
            from pathlib import Path

            benchmark_system.export_benchmark_results(results, Path(export))

    except Exception as e:
        handle_common_errors(e)


@benchmark.command()
def targets():
    """Show performance targets."""
    targets_table = Table(title="Performance Targets (Phase 2)")
    targets_table.add_column("Target", style="cyan")
    targets_table.add_column("Value", style="green")
    targets_table.add_column("Description", style="dim")

    targets = benchmark_system.performance_targets
    targets_table.add_row(
        "Memory Usage", f"< {targets['memory_usage']}MB", "Peak usage on 16GB systems"
    )
    targets_table.add_row(
        "Response Time", f"< {targets['response_time']}s", "Individual agent execution"
    )
    targets_table.add_row(
        "Workflow Time", f"< {targets['workflow_time']}s", "Complete workflow execution"
    )
    targets_table.add_row(
        "Startup Time", f"< {targets['startup_time']}s", "CLI command initialization"
    )

    console.print(targets_table)


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


if __name__ == "__main__":
    main()
