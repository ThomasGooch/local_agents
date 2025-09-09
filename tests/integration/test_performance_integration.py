"""Integration tests for Phase 2 performance features."""

from local_agents.performance import performance_monitor
from local_agents.hardware import hardware_optimizer
from local_agents.benchmarks import benchmark_system
from local_agents.ollama_client import OllamaClient
from local_agents.config import config_manager
from local_agents.agents import PlanningAgent, CodingAgent, TestingAgent, ReviewAgent


class TestPerformanceIntegration:
    """Test Phase 2 performance feature integration."""

    def test_performance_module_imports(self):
        """Test that all Phase 2 performance modules can be imported and accessed."""
        # Test that objects are accessible
        assert performance_monitor is not None
        assert hardware_optimizer is not None
        assert benchmark_system is not None
        assert OllamaClient is not None
        assert config_manager is not None

    def test_configuration_with_performance_settings(self):
        """Test configuration system includes performance settings."""
        config = config_manager.load_config()

        # Test performance configuration exists
        assert hasattr(config, 'performance')
        assert hasattr(config.performance, 'max_concurrent_agents')
        assert hasattr(config.performance, 'enable_response_cache')
        assert hasattr(config.performance, 'cache_size')
        assert hasattr(config.performance, 'cache_ttl_seconds')
        assert hasattr(config.performance, 'enable_parallel_workflows')
        assert hasattr(config.performance, 'performance_monitoring')

        # Test default values are reasonable
        assert 1 <= config.performance.max_concurrent_agents <= 8
        assert isinstance(config.performance.enable_response_cache, bool)
        assert config.performance.cache_size >= 0
        assert config.performance.cache_ttl_seconds >= 0

    def test_hardware_detection_system(self):
        """Test hardware detection and profiling functionality."""
        hw_info = hardware_optimizer.detected_hardware
        profile = hardware_optimizer.detect_best_profile()

        # Test hardware info structure
        assert 'platform' in hw_info
        assert 'memory_gb' in hw_info
        assert 'cpu_count' in hw_info
        assert 'architecture' in hw_info

        # Test hardware values are reasonable
        assert hw_info['memory_gb'] > 0
        assert hw_info['cpu_count'] > 0
        assert hw_info['platform'] in ['Darwin', 'Linux', 'Windows']

        # Test profile is valid
        assert profile.name is not None
        assert profile.cpu_cores > 0
        assert profile.memory_gb > 0
        assert isinstance(profile.recommended_models, dict)
        assert isinstance(profile.performance_settings, dict)
        assert isinstance(profile.optimization_notes, list)

    def test_performance_monitoring_lifecycle(self):
        """Test performance monitoring system lifecycle."""
        # Test monitoring can be started and stopped
        performance_monitor.start_monitoring()
        assert performance_monitor.monitoring_active is True

        performance_monitor.stop_monitoring()
        assert performance_monitor.monitoring_active is False

        # Test report generation
        report = performance_monitor.get_performance_report()
        assert isinstance(report, dict)
        assert 'message' in report or 'total_executions' in report

    def test_caching_system_functionality(self):
        """Test OllamaClient caching system."""
        # Test client creation with caching
        client = OllamaClient(enable_cache=True)
        assert client.enable_cache is True

        # Test cache statistics
        cache_stats = OllamaClient.get_cache_stats()
        assert isinstance(cache_stats, dict)
        assert 'total_entries' in cache_stats
        assert 'cache_size_limit' in cache_stats
        assert 'ttl_seconds' in cache_stats

        # Test cache clearing
        OllamaClient.clear_cache()
        stats_after_clear = OllamaClient.get_cache_stats()
        assert stats_after_clear['total_entries'] == 0

    def test_benchmark_system_configuration(self):
        """Test benchmark system is properly configured."""
        targets = benchmark_system.performance_targets

        # Test performance targets are defined
        assert isinstance(targets, dict)
        assert 'memory_usage' in targets
        assert 'response_time' in targets
        assert 'workflow_time' in targets
        assert 'startup_time' in targets

        # Test target values are reasonable
        assert targets['memory_usage'] > 1000  # At least 1GB in MB
        assert targets['response_time'] > 0
        assert targets['workflow_time'] > 0
        assert targets['startup_time'] > 0

    def test_agent_creation_with_performance_features(self):
        """Test that agents can be created with performance enhancements active."""
        # Test agent creation doesn't break with performance features
        planner = PlanningAgent()
        coder = CodingAgent()
        tester = TestingAgent()
        reviewer = ReviewAgent()

        # Test basic agent properties
        assert planner.agent_type == 'plan'
        assert coder.agent_type == 'code'
        assert tester.agent_type == 'test'
        assert reviewer.agent_type == 'review'

        # Test agents have OllamaClient with performance features
        assert hasattr(planner, 'ollama_client')
        assert hasattr(coder, 'ollama_client')
        assert hasattr(tester, 'ollama_client')
        assert hasattr(reviewer, 'ollama_client')

    def test_hardware_optimization_integration(self):
        """Test hardware optimization can be applied to configuration."""
        # Get current config
        original_config = config_manager.load_config()

        # Test optimization config generation
        profile = hardware_optimizer.detect_best_profile()
        optimization_config = hardware_optimizer.get_optimization_config(profile)

        assert isinstance(optimization_config, dict)
        assert 'profile_name' in optimization_config
        assert 'recommended_models' in optimization_config
        assert 'performance_settings' in optimization_config
        assert 'detected_hardware' in optimization_config

    def test_performance_features_backward_compatibility(self):
        """Test that performance features don't break existing functionality."""
        # Test that config manager still works normally
        config = config_manager.load_config()
        assert hasattr(config, 'default_model')
        assert hasattr(config, 'agents')
        assert hasattr(config, 'workflows')

        # Test that model retrieval still works
        plan_model = config_manager.get_model_for_agent('plan')
        code_model = config_manager.get_model_for_agent('code')
        assert isinstance(plan_model, str)
        assert isinstance(code_model, str)

        # Test that workflow steps still work
        workflow_steps = config_manager.get_workflow_steps('feature-dev')
        assert isinstance(workflow_steps, list)

    def test_connection_pooling_functionality(self):
        """Test that OllamaClient connection pooling works."""
        host1 = "http://localhost:11434"
        host2 = "http://localhost:11435"  # Different host for testing

        # Create clients for different hosts
        client1 = OllamaClient(host1)
        client2 = OllamaClient(host1)  # Same host
        client3 = OllamaClient(host2)  # Different host

        # Test that same host shares connection pool
        assert client1.client is client2.client
        assert client1.client is not client3.client

        # Test memory usage tracking
        memory_stats = client1.get_memory_usage()
        assert isinstance(memory_stats, dict)
        assert 'connection_pools' in memory_stats
        assert memory_stats['connection_pools'] >= 1


class TestPerformanceBenchmarkIntegration:
    """Test benchmark system integration."""

    def test_benchmark_suite_structure(self):
        """Test that benchmark suites are properly structured."""
        # Test benchmark task definitions exist
        assert hasattr(benchmark_system, 'benchmark_tasks')
        assert isinstance(benchmark_system.benchmark_tasks, dict)

        # Test suite types
        for suite_type in ['quick', 'comprehensive', 'stress']:
            assert suite_type in benchmark_system.benchmark_tasks
            tasks = benchmark_system.benchmark_tasks[suite_type]
            assert isinstance(tasks, list)
            assert len(tasks) > 0

            # Test task structure
            for task in tasks:
                assert isinstance(task, tuple)
                assert len(task) == 3  # (agent_type, task, model)
                agent_type, task_desc, model = task
                assert agent_type in ['plan', 'code', 'test', 'review']
                assert isinstance(task_desc, str)
                assert isinstance(model, str)

    def test_performance_target_validation(self):
        """Test performance target validation functionality."""
        # Test validation function exists
        assert hasattr(benchmark_system, 'validate_performance_targets')

        # Test with mock benchmark result
        from local_agents.benchmarks import BenchmarkSuite, BenchmarkResult

        # Create mock results
        mock_results = [
            BenchmarkResult(
                test_name="test1",
                agent_type="plan",
                model_name="llama3.1:8b",
                execution_time=25.0,  # Under 30s target
                memory_usage_mb=8000,  # Under 12GB target
                success=True
            )
        ]

        mock_suite = BenchmarkSuite(
            suite_name="test_suite",
            hardware_profile="test_profile",
            timestamp=1234567890,
            results=mock_results,
            summary={
                "target_validation": {
                    "response_time_met": True,
                    "memory_target_met": True
                }
            }
        )

        validation = benchmark_system.validate_performance_targets(mock_suite)
        assert isinstance(validation, dict)