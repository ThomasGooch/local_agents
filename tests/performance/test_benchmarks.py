"""Performance benchmarking tests for Local Agents.

This module contains performance tests to ensure the system meets
the benchmarks defined in the testing plan:

- Planning tasks: < 30 seconds
- Code generation: < 45 seconds  
- Test creation: < 30 seconds
- Code review: < 60 seconds (including static analysis)
- Workflow execution: < 120 seconds
- Memory usage: < 4GB peak during workflow
"""

import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch

import psutil
import pytest

from local_agents.agents.coder import CodingAgent
from local_agents.agents.planner import PlanningAgent
from local_agents.agents.reviewer import ReviewAgent
from local_agents.agents.tester import TestingAgent
from local_agents.ollama_client import OllamaClient
from local_agents.workflows.orchestrator import Workflow


class PerformanceMonitor:
    """Monitor system resources during test execution."""

    def __init__(self):
        self.process = psutil.Process()
        self.start_time = None
        self.end_time = None
        self.peak_memory = 0
        self.monitoring = False
        self.monitor_thread = None

    def start_monitoring(self):
        """Start performance monitoring."""
        self.start_time = time.time()
        self.peak_memory = 0
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_resources)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def stop_monitoring(self):
        """Stop performance monitoring and return metrics."""
        self.end_time = time.time()
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)

        return {
            "execution_time": self.end_time - self.start_time,
            "peak_memory_mb": self.peak_memory / (1024 * 1024),
            "peak_memory_gb": self.peak_memory / (1024 * 1024 * 1024),
        }

    def _monitor_resources(self):
        """Monitor resources in background thread."""
        while self.monitoring:
            try:
                memory_info = self.process.memory_info()
                current_memory = memory_info.rss
                if current_memory > self.peak_memory:
                    self.peak_memory = current_memory
                time.sleep(0.1)  # Sample every 100ms
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break


@pytest.fixture
def mock_ollama_client():
    """Create a mock Ollama client with realistic response times."""
    client = Mock(spec=OllamaClient)
    client.is_model_available.return_value = True

    def mock_generate(*args, **kwargs):
        # Simulate realistic response times
        time.sleep(0.5)  # 500ms simulated processing
        return "Mock response content"

    client.generate.side_effect = mock_generate
    return client


@pytest.fixture
def performance_monitor():
    """Create a performance monitor for tests."""
    return PerformanceMonitor()


class TestAgentPerformanceBenchmarks:
    """Test individual agent performance benchmarks."""

    def test_planning_agent_performance_benchmark(self, mock_ollama_client, performance_monitor):
        """Test planning agent meets < 30 second benchmark."""
        agent = PlanningAgent(model="test:model", ollama_client=mock_ollama_client)

        performance_monitor.start_monitoring()

        # Execute typical planning task
        result = agent.execute(
            "Create a comprehensive implementation plan for a user authentication system with JWT tokens, password hashing, role-based access control, and secure session management",
            {
                "requirements": ["Security", "Scalability", "Maintainability"],
                "technologies": ["Python", "FastAPI", "PostgreSQL", "Redis"],
                "constraints": ["GDPR compliance", "High availability"],
            },
        )

        metrics = performance_monitor.stop_monitoring()

        # Verify benchmark
        assert (
            metrics["execution_time"] < 30.0
        ), f"Planning took {metrics['execution_time']:.2f}s, exceeds 30s benchmark"
        assert result.success is True

        # Log performance metrics
        print(
            f"Planning Performance: {metrics['execution_time']:.2f}s, Peak Memory: {metrics['peak_memory_mb']:.1f}MB"
        )

    def test_coding_agent_performance_benchmark(self, mock_ollama_client, performance_monitor):
        """Test coding agent meets < 45 second benchmark."""
        agent = CodingAgent(model="test:model", ollama_client=mock_ollama_client)

        performance_monitor.start_monitoring()

        # Execute complex coding task
        result = agent.execute(
            "Implement a complete REST API for user management with authentication, CRUD operations, input validation, error handling, and comprehensive logging",
            {
                "language": "python",
                "framework": "fastapi",
                "database": "postgresql",
                "requirements": [
                    "JWT authentication",
                    "Input validation with Pydantic",
                    "Async/await patterns",
                    "Comprehensive error handling",
                    "API documentation",
                    "Database migrations",
                ],
            },
        )

        metrics = performance_monitor.stop_monitoring()

        # Verify benchmark
        assert (
            metrics["execution_time"] < 45.0
        ), f"Coding took {metrics['execution_time']:.2f}s, exceeds 45s benchmark"
        assert result.success is True

        print(
            f"Coding Performance: {metrics['execution_time']:.2f}s, Peak Memory: {metrics['peak_memory_mb']:.1f}MB"
        )

    def test_testing_agent_performance_benchmark(self, mock_ollama_client, performance_monitor):
        """Test testing agent meets < 30 second benchmark."""
        agent = TestingAgent(model="test:model", ollama_client=mock_ollama_client)

        performance_monitor.start_monitoring()

        # Execute comprehensive testing task
        result = agent.execute(
            "Generate comprehensive test suite for user authentication API including unit tests, integration tests, security tests, and performance tests",
            {
                "framework": "pytest",
                "code_to_test": """
class UserAuthenticator:
    def authenticate(self, username, password):
        # Complex authentication logic
        pass
    
    def authorize(self, user, resource, action):
        # Authorization logic
        pass
    
    def create_jwt_token(self, user):
        # JWT token creation
        pass
""",
                "test_types": [
                    "unit_tests",
                    "integration_tests",
                    "security_tests",
                    "performance_tests",
                ],
            },
        )

        metrics = performance_monitor.stop_monitoring()

        # Verify benchmark
        assert (
            metrics["execution_time"] < 30.0
        ), f"Testing took {metrics['execution_time']:.2f}s, exceeds 30s benchmark"
        assert result.success is True

        print(
            f"Testing Performance: {metrics['execution_time']:.2f}s, Peak Memory: {metrics['peak_memory_mb']:.1f}MB"
        )

    @patch("subprocess.run")
    def test_review_agent_performance_benchmark(
        self, mock_subprocess, mock_ollama_client, performance_monitor
    ):
        """Test review agent meets < 60 second benchmark (including static analysis)."""
        # Mock static analysis tools
        mock_subprocess.return_value = Mock(
            returncode=0, stdout="test.py:1:1: E302 expected 2 blank lines", stderr=""
        )

        agent = ReviewAgent(model="test:model", ollama_client=mock_ollama_client)

        performance_monitor.start_monitoring()

        # Execute comprehensive review task
        result = agent.execute(
            "Perform comprehensive code review including security analysis, performance assessment, maintainability evaluation, and static analysis",
            {
                "code_content": """
import hashlib
import jwt
from datetime import datetime, timedelta

class UserAuthenticator:
    def __init__(self, secret_key):
        self.secret_key = secret_key
        self.users = {}  # In production, use proper database
    
    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    def create_user(self, username, password, email):
        if username in self.users:
            raise ValueError("User already exists")
        
        self.users[username] = {
            'password_hash': self.hash_password(password),
            'email': email,
            'created_at': datetime.utcnow(),
            'is_active': True
        }
    
    def authenticate(self, username, password):
        if username not in self.users:
            return None
        
        user = self.users[username]
        if not user['is_active']:
            return None
            
        password_hash = self.hash_password(password)
        if password_hash == user['password_hash']:
            return self.create_jwt_token(username)
        
        return None
    
    def create_jwt_token(self, username):
        payload = {
            'username': username,
            'exp': datetime.utcnow() + timedelta(hours=24),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
""",
                "focus_area": "all",
                "enable_static_analysis": True,
                "analysis_tools": ["flake8", "pylint", "bandit", "mypy"],
            },
        )

        metrics = performance_monitor.stop_monitoring()

        # Verify benchmark (including static analysis overhead)
        assert (
            metrics["execution_time"] < 60.0
        ), f"Review took {metrics['execution_time']:.2f}s, exceeds 60s benchmark"
        assert result.success is True

        print(
            f"Review Performance: {metrics['execution_time']:.2f}s, Peak Memory: {metrics['peak_memory_mb']:.1f}MB"
        )


class TestWorkflowPerformanceBenchmarks:
    """Test workflow performance benchmarks."""

    @pytest.fixture
    def mock_agents_for_workflow(self, mock_ollama_client):
        """Create mock agents optimized for workflow testing."""
        agents = {}

        # Create agents with realistic timing
        def create_mock_agent(agent_type, base_delay=0.5):
            mock_agent = Mock()
            mock_agent.agent_type = agent_type

            def mock_execute(*args, **kwargs):
                time.sleep(base_delay)  # Simulate processing time
                return Mock(
                    success=True,
                    output=f"Mock {agent_type} output",
                    agent_type=agent_type,
                    task=args[0] if args else "test task",
                    context=args[1] if len(args) > 1 else {},
                    error=None,
                )

            mock_agent.execute.side_effect = mock_execute
            return mock_agent

        agents["planner"] = create_mock_agent("plan", 0.8)
        agents["coder"] = create_mock_agent("code", 1.0)
        agents["tester"] = create_mock_agent("test", 0.7)
        agents["reviewer"] = create_mock_agent("review", 1.2)

        return agents

    def test_feature_development_workflow_benchmark(
        self, mock_agents_for_workflow, performance_monitor
    ):
        """Test feature development workflow meets < 120 second benchmark."""
        workflow = Workflow()

        performance_monitor.start_monitoring()

        with patch.object(
            PlanningAgent, "__new__", return_value=mock_agents_for_workflow["planner"]
        ):
            with patch.object(
                CodingAgent, "__new__", return_value=mock_agents_for_workflow["coder"]
            ):
                with patch.object(
                    TestingAgent,
                    "__new__",
                    return_value=mock_agents_for_workflow["tester"],
                ):
                    with patch.object(
                        ReviewAgent,
                        "__new__",
                        return_value=mock_agents_for_workflow["reviewer"],
                    ):
                        result = workflow.execute_workflow(
                            "feature-dev",
                            "Develop complete user authentication system with comprehensive security features",
                            {
                                "language": "python",
                                "framework": "fastapi",
                                "database": "postgresql",
                                "requirements": [
                                    "JWT authentication",
                                    "Password hashing with salt",
                                    "Role-based access control",
                                    "Session management",
                                    "Rate limiting",
                                    "Audit logging",
                                ],
                            },
                        )

        metrics = performance_monitor.stop_monitoring()

        # Verify benchmark
        assert (
            metrics["execution_time"] < 120.0
        ), f"Workflow took {metrics['execution_time']:.2f}s, exceeds 120s benchmark"
        assert result.success is True
        assert len(result.steps) == 4  # plan, code, test, review

        print(
            f"Feature Development Workflow: {metrics['execution_time']:.2f}s, Peak Memory: {metrics['peak_memory_mb']:.1f}MB"
        )

    def test_bug_fix_workflow_benchmark(self, mock_agents_for_workflow, performance_monitor):
        """Test bug fix workflow performance."""
        workflow = Workflow()

        performance_monitor.start_monitoring()

        with patch.object(
            PlanningAgent, "__new__", return_value=mock_agents_for_workflow["planner"]
        ):
            with patch.object(
                CodingAgent, "__new__", return_value=mock_agents_for_workflow["coder"]
            ):
                with patch.object(
                    TestingAgent,
                    "__new__",
                    return_value=mock_agents_for_workflow["tester"],
                ):
                    result = workflow.execute_workflow(
                        "bug-fix",
                        "Fix critical security vulnerability in JWT token validation",
                        {
                            "bug_report": "JWT tokens can be forged due to missing signature validation",
                            "priority": "critical",
                            "affected_components": ["authentication", "authorization"],
                        },
                    )

        metrics = performance_monitor.stop_monitoring()

        # Bug fix should be faster than full feature development
        assert (
            metrics["execution_time"] < 90.0
        ), f"Bug fix workflow took {metrics['execution_time']:.2f}s, exceeds expected 90s"
        assert result.success is True

        print(
            f"Bug Fix Workflow: {metrics['execution_time']:.2f}s, Peak Memory: {metrics['peak_memory_mb']:.1f}MB"
        )

    def test_code_review_workflow_benchmark(self, mock_agents_for_workflow, performance_monitor):
        """Test code review workflow performance."""
        workflow = Workflow()

        performance_monitor.start_monitoring()

        with patch.object(
            ReviewAgent, "__new__", return_value=mock_agents_for_workflow["reviewer"]
        ):
            result = workflow.execute_workflow(
                "code-review",
                "Review complete authentication module for security and performance",
                {
                    "code_files": ["auth.py", "models.py", "utils.py"],
                    "focus_areas": ["security", "performance", "maintainability"],
                },
            )

        metrics = performance_monitor.stop_monitoring()

        # Code review should be fast (single step)
        assert (
            metrics["execution_time"] < 60.0
        ), f"Code review workflow took {metrics['execution_time']:.2f}s, exceeds 60s benchmark"
        assert result.success is True

        print(
            f"Code Review Workflow: {metrics['execution_time']:.2f}s, Peak Memory: {metrics['peak_memory_mb']:.1f}MB"
        )


class TestMemoryUsageBenchmarks:
    """Test memory usage benchmarks."""

    def test_workflow_memory_usage_benchmark(self, mock_agents_for_workflow, performance_monitor):
        """Test that workflow execution stays under 4GB memory benchmark."""
        workflow = Workflow()

        performance_monitor.start_monitoring()

        # Execute multiple workflows to stress test memory usage
        workflows_to_test = [
            ("feature-dev", "Create user management system"),
            ("bug-fix", "Fix authentication bug"),
            ("code-review", "Review security implementation"),
            ("refactor", "Refactor authentication module"),
        ]

        with patch.object(
            PlanningAgent, "__new__", return_value=mock_agents_for_workflow["planner"]
        ):
            with patch.object(
                CodingAgent, "__new__", return_value=mock_agents_for_workflow["coder"]
            ):
                with patch.object(
                    TestingAgent,
                    "__new__",
                    return_value=mock_agents_for_workflow["tester"],
                ):
                    with patch.object(
                        ReviewAgent,
                        "__new__",
                        return_value=mock_agents_for_workflow["reviewer"],
                    ):
                        results = []
                        for workflow_name, task in workflows_to_test:
                            result = workflow.execute_workflow(workflow_name, task)
                            results.append(result)

                            # Force garbage collection between workflows
                            import gc

                            gc.collect()

        metrics = performance_monitor.stop_monitoring()

        # Verify memory benchmark (4GB = 4096 MB)
        assert (
            metrics["peak_memory_mb"] < 4096
        ), f"Peak memory usage {metrics['peak_memory_mb']:.1f}MB exceeds 4GB benchmark"

        # Verify all workflows succeeded
        for result in results:
            assert result.success is True

        print(
            f"Memory Usage Test: Peak {metrics['peak_memory_mb']:.1f}MB, Total time: {metrics['execution_time']:.2f}s"
        )

    def test_concurrent_agent_memory_usage(self, mock_ollama_client, performance_monitor):
        """Test memory usage with concurrent agent operations."""
        import concurrent.futures

        performance_monitor.start_monitoring()

        def run_agent_task(agent_class, task, context):
            agent = agent_class(model="test:model", ollama_client=mock_ollama_client)
            return agent.execute(task, context)

        # Create multiple concurrent tasks
        tasks = [
            (PlanningAgent, "Plan feature A", {"type": "feature"}),
            (CodingAgent, "Code feature A", {"language": "python"}),
            (TestingAgent, "Test feature A", {"framework": "pytest"}),
            (ReviewAgent, "Review feature A", {"focus": "security"}),
            (PlanningAgent, "Plan feature B", {"type": "enhancement"}),
            (CodingAgent, "Code feature B", {"language": "javascript"}),
        ]

        # Execute tasks concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(run_agent_task, *task) for task in tasks]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        metrics = performance_monitor.stop_monitoring()

        # Verify memory stays reasonable under concurrent load
        assert (
            metrics["peak_memory_mb"] < 2048
        ), f"Concurrent operation peak memory {metrics['peak_memory_mb']:.1f}MB exceeds 2GB"

        # Verify all tasks succeeded
        for result in results:
            assert result.success is True

        print(
            f"Concurrent Memory Test: Peak {metrics['peak_memory_mb']:.1f}MB, {len(tasks)} concurrent tasks"
        )


class TestScalabilityBenchmarks:
    """Test system scalability under various loads."""

    def test_large_context_processing_performance(self, mock_ollama_client, performance_monitor):
        """Test performance with large context inputs."""
        agent = PlanningAgent(model="test:model", ollama_client=mock_ollama_client)

        # Create large context (simulating large codebase analysis)
        large_context = {
            "existing_codebase": "large code content" * 1000,  # ~20KB of text
            "requirements": ["requirement " + str(i) for i in range(100)],
            "constraints": ["constraint " + str(i) for i in range(50)],
            "architecture_docs": "architecture documentation" * 500,
        }

        performance_monitor.start_monitoring()

        result = agent.execute(
            "Analyze existing large codebase and create comprehensive modernization plan",
            large_context,
        )

        metrics = performance_monitor.stop_monitoring()

        # Should still meet planning benchmark even with large context
        assert (
            metrics["execution_time"] < 45.0
        ), f"Large context processing took {metrics['execution_time']:.2f}s"
        assert result.success is True

        print(
            f"Large Context Processing: {metrics['execution_time']:.2f}s, Peak Memory: {metrics['peak_memory_mb']:.1f}MB"
        )

    def test_multiple_workflow_execution_performance(
        self, mock_agents_for_workflow, performance_monitor
    ):
        """Test performance of multiple sequential workflow executions."""
        workflow = Workflow()

        performance_monitor.start_monitoring()

        # Execute 5 workflows sequentially
        workflows = [
            ("code-review", "Review module A"),
            ("bug-fix", "Fix bug in module A"),
            ("code-review", "Review module B"),
            ("feature-dev", "Add feature to module B"),
            ("refactor", "Refactor modules A and B"),
        ]

        results = []
        with patch.object(
            PlanningAgent, "__new__", return_value=mock_agents_for_workflow["planner"]
        ):
            with patch.object(
                CodingAgent, "__new__", return_value=mock_agents_for_workflow["coder"]
            ):
                with patch.object(
                    TestingAgent,
                    "__new__",
                    return_value=mock_agents_for_workflow["tester"],
                ):
                    with patch.object(
                        ReviewAgent,
                        "__new__",
                        return_value=mock_agents_for_workflow["reviewer"],
                    ):
                        for workflow_name, task in workflows:
                            result = workflow.execute_workflow(workflow_name, task)
                            results.append(result)

        metrics = performance_monitor.stop_monitoring()

        # Total time should be reasonable for 5 workflows
        assert (
            metrics["execution_time"] < 300.0
        ), f"5 workflows took {metrics['execution_time']:.2f}s, exceeds 5min"

        # All workflows should succeed
        for result in results:
            assert result.success is True

        print(f"Multiple Workflows: {len(workflows)} workflows in {metrics['execution_time']:.2f}s")


@pytest.mark.performance
class TestPerformanceRegression:
    """Test for performance regressions."""

    def test_baseline_performance_metrics(self, mock_ollama_client, performance_monitor):
        """Establish baseline performance metrics for regression testing."""
        baseline_metrics = {}

        # Test each agent type
        agents = [
            (PlanningAgent, "Create implementation plan"),
            (CodingAgent, "Generate Python function"),
            (TestingAgent, "Create unit tests"),
            (ReviewAgent, "Review code quality"),
        ]

        for agent_class, task in agents:
            agent = agent_class(model="test:model", ollama_client=mock_ollama_client)

            performance_monitor.start_monitoring()
            result = agent.execute(task)
            metrics = performance_monitor.stop_monitoring()

            agent_name = agent_class.__name__.lower()
            baseline_metrics[agent_name] = {
                "execution_time": metrics["execution_time"],
                "memory_mb": metrics["peak_memory_mb"],
            }

            assert result.success is True

        # Log baseline metrics for future regression testing
        print("Baseline Performance Metrics:")
        for agent, metrics in baseline_metrics.items():
            print(f"  {agent}: {metrics['execution_time']:.2f}s, {metrics['memory_mb']:.1f}MB")

        # Store baseline for comparison (in real implementation, save to file)
        return baseline_metrics
