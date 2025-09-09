"""Performance monitoring and optimization utilities."""

import platform
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import psutil
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@dataclass
class PerformanceMetrics:
    """Performance metrics for agent/workflow execution."""

    execution_time: float
    memory_usage_mb: float
    cpu_percent: float
    peak_memory_mb: float
    model_name: str
    agent_type: str
    task_size: int  # characters in task
    cache_hit: bool = False


class PerformanceMonitor:
    """Monitor and track performance metrics for Local Agents."""

    def __init__(self):
        self.metrics: List[PerformanceMetrics] = []
        self.monitoring_active = False
        self._lock = threading.Lock()

        # Hardware detection
        self.system_info = self._detect_system_info()

    def _detect_system_info(self) -> Dict[str, Any]:
        """Detect system hardware configuration."""
        return {
            "cpu_count": psutil.cpu_count(logical=False),
            "cpu_count_logical": psutil.cpu_count(logical=True),
            "memory_gb": round(psutil.virtual_memory().total / (1024**3), 1),
            "cpu_freq_mhz": psutil.cpu_freq().current
            if psutil.cpu_freq()
            else 0,
            "platform": platform.system(),
        }

    def start_monitoring(self) -> None:
        """Start performance monitoring."""
        self.monitoring_active = True
        console.print("[blue]Performance monitoring started[/blue]")

    def stop_monitoring(self) -> None:
        """Stop performance monitoring."""
        self.monitoring_active = False
        console.print("[blue]Performance monitoring stopped[/blue]")

    def record_execution(self, metrics: PerformanceMetrics) -> None:
        """Record execution metrics."""
        if not self.monitoring_active:
            return

        with self._lock:
            self.metrics.append(metrics)

    def get_system_recommendations(self) -> Dict[str, Any]:
        """Get performance recommendations based on system hardware."""
        memory_gb = self.system_info["memory_gb"]
        cpu_cores = self.system_info["cpu_count"]

        if memory_gb >= 16 and cpu_cores >= 6:
            return {
                "tier": "high_performance",
                "recommended_models": [
                    "llama3.1:8b",
                    "codellama:13b-instruct",
                    "deepseek-coder:6.7b",
                    "llama3.1:70b-instruct-q4_0",  # Quantized for memory efficiency
                ],
                "max_concurrent_agents": min(cpu_cores // 2, 4),
                "context_length": 16384,
                "temperature": 0.7,
                "cache_enabled": True,
                "optimization_notes": [
                    (
                        f"Excellent hardware for Local Agents "
                        f"({memory_gb}GB RAM, {cpu_cores} cores)"
                    ),
                    "Can run large models and concurrent workflows",
                    "Enable response caching for best performance",
                ],
            }
        elif memory_gb >= 8 and cpu_cores >= 4:
            return {
                "tier": "medium_performance",
                "recommended_models": [
                    "llama3.1:8b",
                    "codellama:7b",
                    "deepseek-coder:6.7b",
                ],
                "max_concurrent_agents": 2,
                "context_length": 8192,
                "temperature": 0.7,
                "cache_enabled": True,
                "optimization_notes": [
                    (
                        f"Good hardware for Local Agents "
                        f"({memory_gb}GB RAM, {cpu_cores} cores)"
                    ),
                    "Recommended to use medium-sized models",
                    "Limited concurrent execution for stability",
                ],
            }
        else:
            return {
                "tier": "basic_performance",
                "recommended_models": ["llama3.1:8b", "phi:3.5", "gemma:7b"],
                "max_concurrent_agents": 1,
                "context_length": 4096,
                "temperature": 0.8,  # Slightly higher for creativity in smaller models
                "cache_enabled": True,
                "optimization_notes": [
                    f"Limited hardware ({memory_gb}GB RAM, {cpu_cores} cores)",
                    "Use smaller models and sequential execution",
                    "Consider upgrading hardware for better performance",
                ],
            }

    def get_macbook_pro_optimization(self) -> Dict[str, Any]:
        """Get specific optimizations for MacBook Pro Intel i7 16GB."""
        return {
            "model_recommendations": {
                "speed_optimized": {
                    "planning": "llama3.1:8b",
                    "coding": "codellama:7b",
                    "testing": "deepseek-coder:6.7b",
                    "reviewing": "llama3.1:8b",
                },
                "quality_optimized": {
                    "planning": "llama3.1:8b",
                    "coding": "codellama:13b-instruct",
                    "testing": "deepseek-coder:6.7b",
                    "reviewing": "llama3.1:70b-instruct-q4_0",
                },
            },
            "performance_settings": {
                "max_concurrent_agents": 3,  # Optimal for 6-core i7
                "context_length": 16384,  # Maximize 16GB RAM
                "temperature": 0.7,  # Balanced creativity/consistency
                "cache_size": 200,  # Larger cache for 16GB RAM
                "cache_ttl": 600,  # 10 minute cache TTL
                "ollama_host": "http://localhost:11434",
                "timeout": 300,  # 5 minute timeout for large models
            },
            "workflow_optimizations": {
                "enable_parallel_execution": True,
                "parallel_independent_steps": True,
                "memory_cleanup_interval": 300,  # 5 minutes
                "preload_common_models": ["llama3.1:8b", "codellama:7b"],
            },
            "hardware_notes": [
                "MacBook Pro Intel i7 optimizations active",
                "Utilizing 6-core CPU for parallel agent execution",
                "16GB RAM allows for larger context windows",
                "SSD storage enables fast model loading",
                "Consider GPU acceleration for compatible models",
            ],
        }

    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        if not self.metrics:
            return {"message": "No performance data available"}

        # Calculate statistics
        execution_times = [m.execution_time for m in self.metrics]
        memory_usage = [m.memory_usage_mb for m in self.metrics]
        cache_hits = sum(1 for m in self.metrics if m.cache_hit)

        agent_stats = {}
        for metrics in self.metrics:
            agent = metrics.agent_type
            if agent not in agent_stats:
                agent_stats[agent] = {
                    "count": 0,
                    "total_time": 0,
                    "total_memory": 0,
                    "cache_hits": 0,
                }
            agent_stats[agent]["count"] += 1
            agent_stats[agent]["total_time"] += metrics.execution_time
            agent_stats[agent]["total_memory"] += metrics.memory_usage_mb
            if metrics.cache_hit:
                agent_stats[agent]["cache_hits"] += 1

        # Calculate averages
        for agent, stats in agent_stats.items():
            stats["avg_time"] = stats["total_time"] / stats["count"]
            stats["avg_memory"] = stats["total_memory"] / stats["count"]
            stats["cache_hit_rate"] = (
                stats["cache_hits"] / stats["count"]
            ) * 100

        return {
            "total_executions": len(self.metrics),
            "average_execution_time": sum(execution_times)
            / len(execution_times),
            "average_memory_usage": sum(memory_usage) / len(memory_usage),
            "cache_hit_rate": (cache_hits / len(self.metrics)) * 100,
            "agent_statistics": agent_stats,
            "system_info": self.system_info,
            "recommendations": self.get_system_recommendations(),
        }

    def display_performance_report(self) -> None:
        """Display formatted performance report."""
        report = self.get_performance_report()

        if "message" in report:
            console.print(Panel(report["message"], title="Performance Report"))
            return

        # System info table
        system_table = Table(title="System Information")
        system_table.add_column("Metric", style="cyan")
        system_table.add_column("Value", style="green")

        system_info = report["system_info"]
        system_table.add_row("CPU Cores", str(system_info["cpu_count"]))
        system_table.add_row("Memory (GB)", str(system_info["memory_gb"]))
        system_table.add_row("Platform", system_info["platform"])

        # Performance metrics table
        perf_table = Table(title="Performance Metrics")
        perf_table.add_column("Metric", style="cyan")
        perf_table.add_column("Value", style="green")

        perf_table.add_row("Total Executions", str(report["total_executions"]))
        perf_table.add_row(
            "Avg Execution Time", f"{report['average_execution_time']:.2f}s"
        )
        perf_table.add_row(
            "Avg Memory Usage", f"{report['average_memory_usage']:.1f}MB"
        )
        perf_table.add_row(
            "Cache Hit Rate", f"{report['cache_hit_rate']:.1f}%"
        )

        # Agent statistics table
        agent_table = Table(title="Agent Performance")
        agent_table.add_column("Agent", style="cyan")
        agent_table.add_column("Executions", style="yellow")
        agent_table.add_column("Avg Time (s)", style="green")
        agent_table.add_column("Avg Memory (MB)", style="blue")
        agent_table.add_column("Cache Hit %", style="magenta")

        for agent, stats in report["agent_statistics"].items():
            agent_table.add_row(
                agent.title(),
                str(stats["count"]),
                f"{stats['avg_time']:.2f}",
                f"{stats['avg_memory']:.1f}",
                f"{stats['cache_hit_rate']:.1f}%",
            )

        console.print(system_table)
        console.print(perf_table)
        console.print(agent_table)

        # Recommendations
        recommendations = report["recommendations"]
        tier_name = recommendations["tier"].replace("_", " ").title()
        rec_text = f"**Performance Tier**: {tier_name}\n\n"
        models_str = ", ".join(recommendations["recommended_models"])
        rec_text += f"**Recommended Models**: {models_str}\n\n"
        rec_text += "**Optimization Notes**:\n"
        for note in recommendations["optimization_notes"]:
            rec_text += f"• {note}\n"

        console.print(
            Panel(rec_text, title="Recommendations", border_style="blue")
        )

    def clear_metrics(self) -> None:
        """Clear all recorded performance metrics."""
        with self._lock:
            self.metrics.clear()
        console.print("[blue]Performance metrics cleared[/blue]")

    def export_metrics(self, filepath: Path) -> None:
        """Export metrics to JSON file."""
        import json

        with self._lock:
            data = {
                "system_info": self.system_info,
                "metrics": [
                    {
                        "execution_time": m.execution_time,
                        "memory_usage_mb": m.memory_usage_mb,
                        "cpu_percent": m.cpu_percent,
                        "peak_memory_mb": m.peak_memory_mb,
                        "model_name": m.model_name,
                        "agent_type": m.agent_type,
                        "task_size": m.task_size,
                        "cache_hit": m.cache_hit,
                    }
                    for m in self.metrics
                ],
                "report": self.get_performance_report(),
            }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        console.print(f"[green]Metrics exported to {filepath}[/green]")


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


class PerformanceContext:
    """Context manager for monitoring agent execution performance."""

    def __init__(self, agent_type: str, model_name: str, task: str):
        self.agent_type = agent_type
        self.model_name = model_name
        self.task = task
        self.start_time = 0
        self.start_memory = 0
        self.process = psutil.Process()

    def __enter__(self) -> "PerformanceContext":
        if performance_monitor.monitoring_active:
            self.start_time = time.time()
            self.start_memory = (
                self.process.memory_info().rss / 1024 / 1024
            )  # MB
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if performance_monitor.monitoring_active:
            execution_time = time.time() - self.start_time
            current_memory = self.process.memory_info().rss / 1024 / 1024  # MB

            metrics = PerformanceMetrics(
                execution_time=execution_time,
                memory_usage_mb=current_memory - self.start_memory,
                cpu_percent=self.process.cpu_percent(),
                peak_memory_mb=current_memory,
                model_name=self.model_name,
                agent_type=self.agent_type,
                task_size=len(self.task),
                cache_hit=False,  # Will be updated by OllamaClient if cached
            )

            performance_monitor.record_execution(metrics)
