"""Tests for the testing agent."""

import pytest
from unittest.mock import Mock, patch

from local_agents.agents.tester import TestingAgent
from local_agents.base import TaskResult
from local_agents.ollama_client import OllamaClient


class TestTestingAgent:
    """Test TestingAgent class."""
    
    @pytest.fixture
    def mock_ollama_client(self):
        """Create a mock Ollama client."""
        client = Mock(spec=OllamaClient)
        client.is_model_available.return_value = True
        client.generate.return_value = """```python
import pytest

def test_calculator_add():
    assert calculator('+', 2, 3) == 5

def test_calculator_divide_by_zero():
    with pytest.raises(ValueError):
        calculator('/', 10, 0)
```"""
        return client
    
    @pytest.fixture
    def tester_agent(self, mock_ollama_client):
        """Create a TestingAgent instance for testing."""
        return TestingAgent(model="test:model", ollama_client=mock_ollama_client)
    
    def test_agent_initialization(self, tester_agent):
        """Test testing agent initialization."""
        assert tester_agent.agent_type == "test"
        assert tester_agent.role == "Senior Test Engineer and Quality Assurance Specialist"
        assert "comprehensive tests" in tester_agent.goal
        assert tester_agent.model == "test:model"
    
    def test_execute_success(self, tester_agent):
        """Test successful execution of testing task."""
        task = "Generate tests for calculator function"
        context = {
            "code_to_test": "def calculator(op, a, b): return a + b if op == '+' else a / b",
            "framework": "pytest"
        }
        
        result = tester_agent.execute(task, context)
        
        assert isinstance(result, TaskResult)
        assert result.success is True
        assert "test_calculator" in result.output
        assert "pytest" in result.output
        assert result.agent_type == "test"
        assert result.task == task
        assert result.context == context
        assert result.error is None
    
    def test_execute_failure(self, tester_agent):
        """Test execution failure handling."""
        tester_agent.ollama_client.generate.side_effect = Exception("Test generation error")
        
        task = "Generate tests"
        result = tester_agent.execute(task)
        
        assert isinstance(result, TaskResult)
        assert result.success is False
        assert result.output == ""
        assert result.error == "Test generation error"
    
    def test_build_testing_prompt_basic(self, tester_agent):
        """Test building basic testing prompt."""
        task = "Create unit tests for user class"
        context = {"framework": "pytest", "language": "python"}
        
        prompt = tester_agent._build_testing_prompt(task, context)
        
        assert "# Test Generation Task" in prompt
        assert task in prompt
        assert "## Testing Instructions" in prompt
        assert "Framework: pytest" in prompt
        assert "Language: python" in prompt
        assert "## Test Coverage Requirements" in prompt
        assert "Happy path scenarios" in prompt
        assert "Edge cases" in prompt
        assert "Error conditions" in prompt
    
    def test_build_testing_prompt_with_code_to_test(self, tester_agent):
        """Test building testing prompt with code to test."""
        task = "Generate comprehensive tests"
        context = {
            "framework": "pytest",
            "code_to_test": "def factorial(n):\n    if n <= 1: return 1\n    return n * factorial(n-1)",
            "target_file": "math_utils.py"
        }
        
        prompt = tester_agent._build_testing_prompt(task, context)
        
        assert "## Code to Test" in prompt
        assert "def factorial(n)" in prompt
        assert "## Target File" in prompt
        assert "math_utils.py" in prompt
        assert "Framework: pytest" in prompt
    
    def test_build_testing_prompt_with_specifications(self, tester_agent):
        """Test building testing prompt with test specifications."""
        task = "Create API endpoint tests"
        context = {
            "framework": "pytest",
            "test_specifications": [
                "Test successful login with valid credentials",
                "Test login failure with invalid credentials",
                "Test rate limiting"
            ],
            "test_data": {"valid_user": "test@example.com"}
        }
        
        prompt = tester_agent._build_testing_prompt(task, context)
        
        assert "## Test Specifications" in prompt
        assert "successful login" in prompt
        assert "rate limiting" in prompt
        assert "## Test Data" in prompt
        assert "test@example.com" in prompt
    
    def test_generate_unit_tests(self, tester_agent):
        """Test generating unit tests."""
        code_to_test = "def add(a, b): return a + b"
        framework = "pytest"
        
        result = tester_agent.generate_unit_tests(code_to_test, framework)
        
        assert result.success is True
        assert "Generate unit tests for provided code" in result.task
        
        # Verify context contains code and framework
        call_args = tester_agent.ollama_client.generate.call_args
        prompt = call_args[0][1]
        assert "def add(a, b)" in prompt
        assert "Framework: pytest" in prompt
    
    def test_generate_integration_tests(self, tester_agent):
        """Test generating integration tests."""
        system_description = "User authentication system with database"
        framework = "pytest"
        
        result = tester_agent.generate_integration_tests(system_description, framework)
        
        assert result.success is True
        assert "Generate integration tests for: User authentication system" in result.task
    
    def test_generate_api_tests(self, tester_agent):
        """Test generating API tests."""
        api_spec = {
            "endpoint": "/api/users",
            "method": "GET",
            "parameters": {"page": "int", "limit": "int"},
            "response_format": "json"
        }
        framework = "pytest"
        
        result = tester_agent.generate_api_tests(api_spec, framework)
        
        assert result.success is True
        assert "Generate API tests for endpoint: /api/users" in result.task
    
    def test_create_test_data(self, tester_agent):
        """Test creating test data."""
        data_spec = "User registration data with various validation scenarios"
        format_type = "json"
        
        result = tester_agent.create_test_data(data_spec, format_type)
        
        assert result.success is True
        assert f"Create test data: {data_spec}" in result.task
        
        # Verify format is included in context
        call_args = tester_agent.ollama_client.generate.call_args
        prompt = call_args[0][1]
        assert "json" in prompt.lower()
    
    def test_framework_detection_and_adaptation(self, tester_agent):
        """Test framework detection and adaptation."""
        frameworks = [
            {"framework": "pytest", "language": "python"},
            {"framework": "jest", "language": "javascript"},
            {"framework": "junit", "language": "java"},
            {"framework": "rspec", "language": "ruby"},
            {"framework": "go test", "language": "go"}
        ]
        
        for context in frameworks:
            task = f"Generate tests using {context['framework']}"
            result = tester_agent.execute(task, context)
            
            assert result.success is True
            call_args = tester_agent.ollama_client.generate.call_args
            prompt = call_args[0][1]
            assert context['framework'] in prompt
            assert context['language'] in prompt
    
    def test_test_coverage_scenarios(self, tester_agent):
        """Test that various coverage scenarios are addressed."""
        task = "Create comprehensive test suite"
        context = {
            "framework": "pytest",
            "coverage_requirements": [
                "happy_path",
                "edge_cases", 
                "error_conditions",
                "security_tests",
                "performance_tests"
            ]
        }
        
        result = tester_agent.execute(task, context)
        
        assert result.success is True
        call_args = tester_agent.ollama_client.generate.call_args
        prompt = call_args[0][1]
        
        # Verify coverage requirements are mentioned
        for requirement in context['coverage_requirements']:
            assert requirement.replace('_', ' ') in prompt.lower()
    
    def test_mock_and_fixture_handling(self, tester_agent):
        """Test handling of mocks and fixtures."""
        task = "Generate tests with mocking for external dependencies"
        context = {
            "framework": "pytest",
            "external_dependencies": ["database", "api_client", "file_system"],
            "mock_strategy": "pytest-mock"
        }
        
        result = tester_agent.execute(task, context)
        
        assert result.success is True
        call_args = tester_agent.ollama_client.generate.call_args
        prompt = call_args[0][1]
        assert "database" in prompt
        assert "pytest-mock" in prompt
        assert "external dependencies" in prompt.lower()
    
    def test_test_execution_integration(self, tester_agent):
        """Test integration with test execution."""
        task = "Generate and validate test execution"
        context = {
            "framework": "pytest",
            "test_command": "pytest -v",
            "expected_results": "all tests should pass"
        }
        
        result = tester_agent.execute(task, context)
        
        assert result.success is True
        call_args = tester_agent.ollama_client.generate.call_args
        prompt = call_args[0][1]
        assert "pytest -v" in prompt
    
    def test_performance_test_generation(self, tester_agent):
        """Test performance test generation."""
        task = "Create performance tests for API endpoints"
        context = {
            "framework": "pytest",
            "performance_requirements": {
                "response_time": "< 200ms",
                "throughput": "100 requests/second",
                "concurrent_users": 50
            }
        }
        
        result = tester_agent.execute(task, context)
        
        assert result.success is True
        call_args = tester_agent.ollama_client.generate.call_args
        prompt = call_args[0][1]
        assert "performance" in prompt.lower()
        assert "200ms" in prompt
    
    def test_execute_with_stream(self, tester_agent):
        """Test execution with streaming."""
        task = "Generate streaming tests"
        
        result = tester_agent.execute(task, stream=True)
        
        assert result.success is True
        tester_agent.ollama_client.generate.assert_called_once()
        call_args = tester_agent.ollama_client.generate.call_args
        assert call_args.kwargs['stream'] is True
    
    @patch('local_agents.config.get_model_for_agent')
    def test_default_model_selection(self, mock_get_model, mock_ollama_client):
        """Test default model selection for testing agent."""
        mock_get_model.return_value = "deepseek-coder:6.7b"
        
        agent = TestingAgent(ollama_client=mock_ollama_client)
        
        mock_get_model.assert_called_with("test")
        assert agent.model == "deepseek-coder:6.7b"
    
    def test_security_test_generation(self, tester_agent):
        """Test security test generation."""
        task = "Generate security tests for authentication system"
        context = {
            "framework": "pytest",
            "security_concerns": [
                "SQL injection",
                "XSS attacks",
                "CSRF protection",
                "Authentication bypass"
            ]
        }
        
        result = tester_agent.execute(task, context)
        
        assert result.success is True
        call_args = tester_agent.ollama_client.generate.call_args
        prompt = call_args[0][1]
        assert "security" in prompt.lower()
        assert "SQL injection" in prompt
    
    def test_test_result_parsing_and_formatting(self, tester_agent):
        """Test that agent can parse and format test results."""
        task = "Analyze test execution results"
        context = {
            "framework": "pytest",
            "test_results": "5 passed, 2 failed, 1 skipped",
            "failure_details": "AssertionError in test_divide_by_zero"
        }
        
        result = tester_agent.execute(task, context)
        
        assert result.success is True
        call_args = tester_agent.ollama_client.generate.call_args
        prompt = call_args[0][1]
        assert "5 passed" in prompt
        assert "AssertionError" in prompt