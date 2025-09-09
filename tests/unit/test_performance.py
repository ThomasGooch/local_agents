"""Unit tests for performance monitoring system."""

import time
from unittest.mock import Mock, patch, MagicMock
import pytest

from local_agents.performance import (
    PerformanceMonitor,
    PerformanceMetrics,
    PerformanceContext,
    performance_monitor
)


class TestPerformanceMetrics:
    """Test PerformanceMetrics dataclass."""
    
    def test_performance_metrics_creation(self):
        """Test PerformanceMetrics can be created with valid data."""
        metrics = PerformanceMetrics(
            execution_time=1.5,
            memory_usage_mb=256.0,
            cpu_percent=45.2,
            peak_memory_mb=300.0,
            model_name="llama3.1:8b",
            agent_type="plan",
            task_size=150,
            cache_hit=True
        )
        
        assert metrics.execution_time == 1.5
        assert metrics.memory_usage_mb == 256.0
        assert metrics.cpu_percent == 45.2
        assert metrics.peak_memory_mb == 300.0
        assert metrics.model_name == "llama3.1:8b"
        assert metrics.agent_type == "plan"
        assert metrics.task_size == 150
        assert metrics.cache_hit is True

    def test_performance_metrics_defaults(self):
        """Test PerformanceMetrics default values."""
        metrics = PerformanceMetrics(
            execution_time=1.0,
            memory_usage_mb=100.0,
            cpu_percent=20.0,
            peak_memory_mb=120.0,
            model_name="test:model",
            agent_type="test",
            task_size=50
        )
        
        assert metrics.cache_hit is False  # Default value


class TestPerformanceMonitor:
    """Test PerformanceMonitor class."""
    
    @pytest.fixture
    def monitor(self):
        """Create a fresh PerformanceMonitor for testing."""
        return PerformanceMonitor()

    def test_monitor_initialization(self, monitor):
        """Test PerformanceMonitor initializes correctly."""
        assert monitor.metrics == []
        assert monitor.monitoring_active is False
        assert isinstance(monitor.system_info, dict)
        
        # Test system info structure
        assert 'cpu_count' in monitor.system_info
        assert 'memory_gb' in monitor.system_info
        assert 'platform' in monitor.system_info

    def test_start_stop_monitoring(self, monitor):
        """Test monitoring can be started and stopped."""
        # Initially inactive
        assert monitor.monitoring_active is False
        
        # Start monitoring
        monitor.start_monitoring()
        assert monitor.monitoring_active is True
        
        # Stop monitoring
        monitor.stop_monitoring()
        assert monitor.monitoring_active is False

    def test_record_execution_when_active(self, monitor):
        """Test recording execution metrics when monitoring is active."""
        monitor.start_monitoring()
        
        metrics = PerformanceMetrics(
            execution_time=2.0,
            memory_usage_mb=512.0,
            cpu_percent=60.0,
            peak_memory_mb=600.0,
            model_name="test:model",
            agent_type="code",
            task_size=200
        )
        
        monitor.record_execution(metrics)
        assert len(monitor.metrics) == 1
        assert monitor.metrics[0] == metrics

    def test_record_execution_when_inactive(self, monitor):
        """Test recording execution metrics when monitoring is inactive."""
        # Monitoring is inactive by default
        assert monitor.monitoring_active is False
        
        metrics = PerformanceMetrics(
            execution_time=1.0,
            memory_usage_mb=100.0,
            cpu_percent=30.0,
            peak_memory_mb=120.0,
            model_name="test:model",
            agent_type="plan",
            task_size=100
        )
        
        monitor.record_execution(metrics)
        assert len(monitor.metrics) == 0  # Should not record when inactive

    def test_get_system_recommendations(self, monitor):
        """Test system recommendations based on hardware."""
        recommendations = monitor.get_system_recommendations()
        
        assert isinstance(recommendations, dict)
        assert 'tier' in recommendations
        assert 'recommended_models' in recommendations
        assert 'max_concurrent_agents' in recommendations
        assert 'optimization_notes' in recommendations
        
        # Test tier is one of expected values
        assert recommendations['tier'] in ['high_performance', 'medium_performance', 'basic_performance']
        
        # Test recommended models structure
        models = recommendations['recommended_models']
        assert isinstance(models, list)
        assert len(models) > 0

    @patch('local_agents.performance.platform.system', return_value='Darwin')
    def test_macbook_pro_optimization(self, mock_platform, monitor):
        """Test MacBook Pro specific optimizations."""
        # Mock system info to simulate MacBook Pro Intel i7 16GB
        monitor.system_info = {
            'cpu_count': 6,
            'cpu_count_logical': 12,
            'memory_gb': 16.0,
            'platform': 'Darwin'
        }
        
        optimization = monitor.get_macbook_pro_optimization()
        
        assert isinstance(optimization, dict)
        assert 'model_recommendations' in optimization
        assert 'performance_settings' in optimization
        assert 'workflow_optimizations' in optimization
        assert 'hardware_notes' in optimization
        
        # Test MacBook Pro specific settings
        perf_settings = optimization['performance_settings']
        assert perf_settings['max_concurrent_agents'] == 3
        assert perf_settings['context_length'] == 16384
        assert perf_settings['cache_size'] == 200

    def test_get_performance_report_empty(self, monitor):
        """Test performance report with no metrics."""
        report = monitor.get_performance_report()
        
        assert isinstance(report, dict)
        assert 'message' in report
        assert report['message'] == "No performance data available"

    def test_get_performance_report_with_data(self, monitor):
        """Test performance report with metrics data."""
        monitor.start_monitoring()
        
        # Add some test metrics
        metrics = [
            PerformanceMetrics(1.0, 100.0, 20.0, 120.0, "model1", "plan", 50, True),
            PerformanceMetrics(2.0, 200.0, 40.0, 250.0, "model2", "code", 100, False),
            PerformanceMetrics(1.5, 150.0, 30.0, 180.0, "model1", "plan", 75, True),
        ]
        
        for metric in metrics:
            monitor.record_execution(metric)
        
        report = monitor.get_performance_report()
        
        assert isinstance(report, dict)
        assert 'total_executions' in report
        assert 'average_execution_time' in report
        assert 'average_memory_usage' in report
        assert 'cache_hit_rate' in report
        assert 'agent_statistics' in report
        assert 'system_info' in report
        
        # Test calculated values
        assert report['total_executions'] == 3
        assert report['cache_hit_rate'] == 2/3 * 100  # 2 cache hits out of 3
        
        # Test agent statistics
        agent_stats = report['agent_statistics']
        assert 'plan' in agent_stats
        assert 'code' in agent_stats
        assert agent_stats['plan']['count'] == 2
        assert agent_stats['code']['count'] == 1

    def test_clear_metrics(self, monitor):
        """Test clearing metrics."""
        monitor.start_monitoring()
        
        # Add some metrics
        metrics = PerformanceMetrics(1.0, 100.0, 20.0, 120.0, "model", "plan", 50)
        monitor.record_execution(metrics)
        assert len(monitor.metrics) == 1
        
        # Clear metrics
        monitor.clear_metrics()
        assert len(monitor.metrics) == 0

    @patch('builtins.open', create=True)
    @patch('json.dump')
    def test_export_metrics(self, mock_json_dump, mock_open, monitor):
        """Test exporting metrics to JSON file."""
        from pathlib import Path
        
        monitor.start_monitoring()
        metrics = PerformanceMetrics(1.0, 100.0, 20.0, 120.0, "model", "plan", 50)
        monitor.record_execution(metrics)
        
        filepath = Path("/tmp/test_metrics.json")
        monitor.export_metrics(filepath)
        
        mock_open.assert_called_once_with(filepath, 'w')
        mock_json_dump.assert_called_once()


class TestPerformanceContext:
    """Test PerformanceContext context manager."""
    
    @patch('local_agents.performance.performance_monitor')
    @patch('psutil.Process')
    def test_performance_context_manager(self, mock_process_class, mock_monitor):
        """Test PerformanceContext as context manager."""
        # Setup mocks
        mock_process = Mock()
        mock_process_class.return_value = mock_process
        mock_process.memory_info.return_value.rss = 1024 * 1024 * 100  # 100MB in bytes
        mock_process.cpu_percent.return_value = 25.0
        
        mock_monitor.monitoring_active = True
        
        # Test context manager
        with PerformanceContext("test", "test:model", "test task"):
            time.sleep(0.01)  # Small delay to ensure measurable execution time
        
        # Verify record_execution was called
        mock_monitor.record_execution.assert_called_once()
        
        # Get the recorded metrics
        call_args = mock_monitor.record_execution.call_args[0]
        metrics = call_args[0]
        
        assert isinstance(metrics, PerformanceMetrics)
        assert metrics.agent_type == "test"
        assert metrics.model_name == "test:model"
        assert metrics.task_size == len("test task")
        assert metrics.execution_time > 0

    @patch('local_agents.performance.performance_monitor')
    def test_performance_context_when_monitoring_inactive(self, mock_monitor):
        """Test PerformanceContext when monitoring is inactive."""
        mock_monitor.monitoring_active = False
        
        with PerformanceContext("test", "test:model", "test task"):
            pass
        
        # Should not record when monitoring is inactive
        mock_monitor.record_execution.assert_not_called()


class TestGlobalPerformanceMonitor:
    """Test the global performance monitor instance."""
    
    def test_global_performance_monitor_exists(self):
        """Test that global performance monitor instance exists."""
        assert performance_monitor is not None
        assert isinstance(performance_monitor, PerformanceMonitor)

    def test_global_performance_monitor_system_info(self):
        """Test that global monitor has valid system info."""
        system_info = performance_monitor.system_info
        
        assert isinstance(system_info, dict)
        assert 'platform' in system_info
        assert 'memory_gb' in system_info
        assert 'cpu_count' in system_info
        
        # Test values are reasonable
        assert system_info['memory_gb'] > 0
        assert system_info['cpu_count'] > 0