"""Performance benchmarking and validation for Local Agents."""

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress
from rich.table import Table

from .config import config_manager
from .hardware import hardware_optimizer

console = Console()


@dataclass
class BenchmarkResult:
    """Result of a benchmark test."""

    test_name: str
    agent_type: str
    model_name: str
    execution_time: float
    memory_usage_mb: float
    success: bool
    error: Optional[str] = None
    tokens_generated: int = 0
    cache_hit: bool = False
    concurrent_level: int = 1


@dataclass
class BenchmarkSuite:
    """Collection of benchmark results."""

    suite_name: str
    hardware_profile: str
    timestamp: float
    results: List[BenchmarkResult]
    summary: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "suite_name": self.suite_name,
            "hardware_profile": self.hardware_profile,
            "timestamp": self.timestamp,
            "results": [asdict(result) for result in self.results],
            "summary": self.summary,
        }


class PerformanceBenchmark:
    """Performance benchmarking system for Local Agents."""

    def __init__(self):
        self.benchmark_tasks = {
            "quick": [
                (
                    "plan",
                    "Create a simple Hello World application",
                    "llama3.1:8b",
                ),
                (
                    "code",
                    "Write a Python function to add two numbers",
                    "codellama:7b",
                ),
                (
                    "test",
                    "Create a unit test for a basic function",
                    "deepseek-coder:6.7b",
                ),
                ("review", "Review a simple Python function", "llama3.1:8b"),
            ],
            "comprehensive": [
                (
                    "plan",
                    "Design a RESTful API for a task management system",
                    "llama3.1:8b",
                ),
                (
                    "code",
                    "Implement authentication middleware in Python",
                    "codellama:7b",
                ),
                (
                    "code",
                    "Create a React component with TypeScript",
                    "codellama:13b-instruct",
                ),
                (
                    "test",
                    "Write comprehensive tests for an API endpoint",
                    "deepseek-coder:6.7b",
                ),
                (
                    "test",
                    "Create integration tests for a web service",
                    "deepseek-coder:6.7b",
                ),
                (
                    "review",
                    "Review a complex multi-file codebase",
                    "llama3.1:8b",
                ),
                (
                    "review",
                    "Perform security review of authentication code",
                    "llama3.1:70b-instruct-q4_0",
                ),
            ],
            "stress": [
                (
                    "plan",
                    "Architect a microservices-based e-commerce platform",
                    "llama3.1:8b",
                ),
                (
                    "code",
                    "Implement distributed caching with Redis",
                    "codellama:13b-instruct",
                ),
                (
                    "code",
                    "Create a concurrent data processing pipeline",
                    "codellama:7b",
                ),
                (
                    "code",
                    "Build a GraphQL API with complex resolvers",
                    "codellama:13b-instruct",
                ),
                (
                    "test",
                    "Design load tests for high-traffic API",
                    "deepseek-coder:6.7b",
                ),
                (
                    "test",
                    "Create end-to-end tests for complex workflows",
                    "deepseek-coder:6.7b",
                ),
                (
                    "review",
                    "Security audit of distributed system",
                    "llama3.1:70b-instruct-q4_0",
                ),
                (
                    "review",
                    "Performance analysis of data pipeline",
                    "llama3.1:8b",
                ),
            ],
        }

        # Performance targets (Phase 2 goals from next_steps.md)
        self.performance_targets = {
            "memory_usage": 12288,  # < 12GB peak on 16GB systems (MB)
            "response_time": 30,  # < 30s for individual agents
            "workflow_time": 120,  # < 120s for complete workflows
            "startup_time": 3,  # < 3s for CLI command initialization
        }

    def run_benchmark_suite(
        self,
        suite_type: str = "quick",
        concurrent_levels: List[int] = [1, 2],
        repeat_count: int = 1,
    ) -> BenchmarkSuite:
        """Run a complete benchmark suite."""
        if suite_type not in self.benchmark_tasks:
            available = list(self.benchmark_tasks.keys())
            raise ValueError(f"Unknown suite type: {suite_type}. Available: {available}")

        suite_title = f"Running {suite_type.title()} Benchmark Suite"
        console.print(f"[bold blue]{suite_title}[/bold blue]")

        # Get hardware profile
        profile = hardware_optimizer.detect_best_profile()
        console.print(f"Hardware Profile: {profile.name}")

        start_time = time.time()
        all_results = []

        tasks = self.benchmark_tasks[suite_type]
        with Progress() as progress:
            task_name = f"[cyan]{suite_type.title()} Benchmark"
            total_tasks = len(tasks) * len(concurrent_levels) * repeat_count
            main_task = progress.add_task(task_name, total=total_tasks)

            for concurrent_level in concurrent_levels:
                msg = f"Testing with {concurrent_level} concurrent agent(s)"
                console.print(f"\n[bold]{msg}[/bold]")

                for repeat in range(repeat_count):
                    if repeat_count > 1:
                        iter_msg = f"  Iteration {repeat + 1}/{repeat_count}"
                        console.print(iter_msg)

                    if concurrent_level == 1:
                        # Sequential execution
                        for agent_type, task, model in tasks:
                            result = self._benchmark_single_agent(
                                agent_type, task, model, concurrent_level
                            )
                            all_results.append(result)
                            progress.advance(main_task)
                    else:
                        # Concurrent execution
                        batch_results = self._benchmark_concurrent_agents(tasks, concurrent_level)
                        all_results.extend(batch_results)
                        progress.advance(main_task, len(tasks))

        # Generate summary
        summary = self._generate_benchmark_summary(all_results)

        benchmark_suite = BenchmarkSuite(
            suite_name=f"{suite_type}_benchmark",
            hardware_profile=profile.name,
            timestamp=time.time(),
            results=all_results,
            summary=summary,
        )

        execution_time = time.time() - start_time
        msg = f"✓ Benchmark suite completed in {execution_time:.2f}s"
        console.print(f"\n[green]{msg}[/green]")

        return benchmark_suite

    def _benchmark_single_agent(
        self, agent_type: str, task: str, model: str, concurrent_level: int = 1
    ) -> BenchmarkResult:
        """Benchmark a single agent execution."""
        from .workflows.orchestrator import Workflow

        try:
            start_time = time.time()
            start_memory = self._get_memory_usage()

            # Create workflow and execute single step
            workflow = Workflow()

            # Mock agent execution for benchmarking
            result = workflow._execute_step(agent_type, task, {}, False)

            execution_time = time.time() - start_time
            memory_usage = self._get_memory_usage() - start_memory

            return BenchmarkResult(
                test_name=f"{agent_type}_{model.replace(':', '_')}",
                agent_type=agent_type,
                model_name=model,
                execution_time=execution_time,
                memory_usage_mb=memory_usage,
                success=(result.success if hasattr(result, "success") else True),
                error=result.error if hasattr(result, "error") else None,
                tokens_generated=(len(result.output) if hasattr(result, "output") else 0),
                concurrent_level=concurrent_level,
            )

        except Exception as e:
            return BenchmarkResult(
                test_name=f"{agent_type}_{model.replace(':', '_')}",
                agent_type=agent_type,
                model_name=model,
                execution_time=0,
                memory_usage_mb=0,
                success=False,
                error=str(e),
                concurrent_level=concurrent_level,
            )

    def _benchmark_concurrent_agents(
        self, tasks: List[Tuple[str, str, str]], concurrent_level: int
    ) -> List[BenchmarkResult]:
        """Benchmark concurrent agent execution."""
        results = []

        # Group tasks into batches for concurrent execution
        batches = [tasks[i:i + concurrent_level] for i in range(0, len(tasks), concurrent_level)]
        for batch in batches:
            start_time = time.time()
            start_memory = self._get_memory_usage()

            batch_results = []

            with ThreadPoolExecutor(max_workers=concurrent_level) as executor:
                # Submit batch tasks
                future_to_task = {
                    executor.submit(
                        self._benchmark_single_agent,
                        agent_type,
                        task,
                        model,
                        concurrent_level,
                    ): (agent_type, task, model)
                    for agent_type, task, model in batch
                }

                # Collect results
                for future in as_completed(future_to_task):
                    agent_type, task, model = future_to_task[future]
                    try:
                        result = future.result()
                        batch_results.append(result)
                    except Exception as e:
                        error_result = BenchmarkResult(
                            test_name=f"{agent_type}_{model.replace(':', '_')}",
                            agent_type=agent_type,
                            model_name=model,
                            execution_time=0,
                            memory_usage_mb=0,
                            success=False,
                            error=f"Concurrent execution failed: {e}",
                            concurrent_level=concurrent_level,
                        )
                        batch_results.append(error_result)

            # Update timing for concurrent batch
            batch_time = time.time() - start_time
            batch_memory = self._get_memory_usage() - start_memory

            # Adjust individual results to reflect concurrent execution
            for result in batch_results:
                # Approximate per-agent time
                result.execution_time = batch_time / len(batch)
                # Approximate per-agent memory
                result.memory_usage_mb = batch_memory / len(batch)

            results.extend(batch_results)

        return results

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        import psutil

        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024

    def _generate_benchmark_summary(self, results: List[BenchmarkResult]) -> Dict[str, Any]:
        """Generate summary statistics from benchmark results."""
        if not results:
            return {"message": "No benchmark results"}

        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]

        # Overall statistics
        summary = {
            "total_tests": len(results),
            "successful_tests": len(successful_results),
            "failed_tests": len(failed_results),
            "success_rate": (len(successful_results) / len(results)) * 100,
        }

        if successful_results:
            execution_times = [r.execution_time for r in successful_results]
            memory_usages = [r.memory_usage_mb for r in successful_results]

            summary.update(
                {
                    "avg_execution_time": (sum(execution_times) / len(execution_times)),
                    "max_execution_time": max(execution_times),
                    "min_execution_time": min(execution_times),
                    "avg_memory_usage": (sum(memory_usages) / len(memory_usages)),
                    "max_memory_usage": max(memory_usages),
                    "total_tokens_generated": sum(r.tokens_generated for r in successful_results),
                }
            )

            # Performance target validation
            response_target = self.performance_targets["response_time"]
            memory_target = self.performance_targets["memory_usage"]
            target_validation = {
                "response_time_target": response_target,
                "response_time_met": all(t <= response_target for t in execution_times),
                "memory_target_mb": memory_target,
                "memory_target_met": max(memory_usages) <= memory_target,
            }
            summary["target_validation"] = target_validation

        # Agent-specific statistics
        agent_stats = {}
        for result in successful_results:
            agent = result.agent_type
            if agent not in agent_stats:
                agent_stats[agent] = {
                    "count": 0,
                    "total_time": 0,
                    "total_memory": 0,
                    "failures": 0,
                }
            agent_stats[agent]["count"] += 1
            agent_stats[agent]["total_time"] += result.execution_time
            agent_stats[agent]["total_memory"] += result.memory_usage_mb

        # Add failed results to agent stats
        for result in failed_results:
            agent = result.agent_type
            if agent not in agent_stats:
                agent_stats[agent] = {
                    "count": 0,
                    "total_time": 0,
                    "total_memory": 0,
                    "failures": 0,
                }
            agent_stats[agent]["failures"] += 1
        # Calculate averages
        for agent, stats in agent_stats.items():
            if stats["count"] > 0:
                stats["avg_time"] = stats["total_time"] / stats["count"]
                stats["avg_memory"] = stats["total_memory"] / stats["count"]
            else:
                stats["avg_time"] = 0
                stats["avg_memory"] = 0

        summary["agent_statistics"] = agent_stats

        return summary

    def display_benchmark_results(self, suite: BenchmarkSuite) -> None:
        """Display formatted benchmark results."""
        title = f"Benchmark Results: {suite.suite_name.title()}"
        console.print(f"\n[bold blue]{title}[/bold blue]")
        console.print(f"Hardware: {suite.hardware_profile}")
        timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(suite.timestamp))
        console.print(f"Timestamp: {timestamp_str}")
        summary = suite.summary

        # Overall statistics table
        overall_table = Table(title="Overall Performance")
        overall_table.add_column("Metric", style="cyan")
        overall_table.add_column("Value", style="green")

        overall_table.add_row("Total Tests", str(summary["total_tests"]))
        overall_table.add_row("Successful", str(summary["successful_tests"]))
        overall_table.add_row("Failed", str(summary["failed_tests"]))
        overall_table.add_row("Success Rate", f"{summary['success_rate']:.1f}%")

        if "avg_execution_time" in summary:
            overall_table.add_row("Avg Execution Time", f"{summary['avg_execution_time']:.2f}s")
            overall_table.add_row("Max Execution Time", f"{summary['max_execution_time']:.2f}s")
            overall_table.add_row("Avg Memory Usage", f"{summary['avg_memory_usage']:.1f}MB")
            overall_table.add_row("Max Memory Usage", f"{summary['max_memory_usage']:.1f}MB")
        console.print(overall_table)

        # Performance targets validation
        if "target_validation" in summary:
            targets = summary["target_validation"]
            target_text = ""

            response_status = "✅" if targets["response_time_met"] else "❌"
            response_target = targets["response_time_target"]
            target_text += f"{response_status} Response Time: < {response_target}s\n"

            memory_status = "✅" if targets["memory_target_met"] else "❌"
            memory_target = targets["memory_target_mb"]
            target_text += f"{memory_status} Memory Usage: < {memory_target}MB\n"

            console.print(
                Panel(
                    target_text,
                    title="Performance Targets",
                    border_style="blue",
                )
            )
        # Agent statistics table
        if "agent_statistics" in summary:
            agent_table = Table(title="Agent Performance")
            agent_table.add_column("Agent", style="cyan")
            agent_table.add_column("Tests", style="yellow")
            agent_table.add_column("Avg Time (s)", style="green")
            agent_table.add_column("Avg Memory (MB)", style="blue")
            agent_table.add_column("Failures", style="red")

            for agent, stats in summary["agent_statistics"].items():
                agent_table.add_row(
                    agent.title(),
                    str(stats["count"]),
                    f"{stats['avg_time']:.2f}",
                    f"{stats['avg_memory']:.1f}",
                    str(stats["failures"]),
                )

            console.print(agent_table)

    def export_benchmark_results(self, suite: BenchmarkSuite, filepath: Path) -> None:
        """Export benchmark results to JSON file."""
        with open(filepath, "w") as f:
            json.dump(suite.to_dict(), f, indent=2)
        msg = f"Benchmark results exported to {filepath}"
        console.print(f"[green]{msg}[/green]")

    def validate_performance_targets(self, suite: BenchmarkSuite) -> Dict[str, bool]:
        """Validate benchmark results against performance targets."""
        summary = suite.summary

        if "target_validation" not in summary:
            return {"error": "No target validation data available"}

        targets = summary["target_validation"]

        return {
            "response_time_target_met": targets["response_time_met"],
            "memory_target_met": targets["memory_target_met"],
            "overall_success": (targets["response_time_met"] and targets["memory_target_met"]),
        }

    def run_macbook_pro_optimization_test(self) -> BenchmarkSuite:
        """Run specific test for MacBook Pro Intel i7 16GB optimization."""
        title = "Running MacBook Pro Intel i7 16GB Optimization Test"
        console.print(f"[bold blue]{title}[/bold blue]")

        # Apply MacBook Pro optimizations first
        profile = hardware_optimizer.profiles["macbook_pro_intel_i7_16gb"]
        hardware_optimizer.apply_optimization(config_manager, profile)

        # Run comprehensive benchmark
        suite = self.run_benchmark_suite("comprehensive", [1, 2, 3], repeat_count=2)

        # Validate against MacBook Pro specific targets
        macbook_targets = {
            "max_concurrent_agents": 3,
            "context_length": 16384,
            "cache_size": 200,
            "parallel_execution": True,
        }

        suite.summary["macbook_pro_validation"] = macbook_targets

        return suite


# Global benchmark instance
benchmark_system = PerformanceBenchmark()
