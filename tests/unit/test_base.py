"""Tests for base agent functionality."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from local_agents.base import BaseAgent, TaskResult, handle_agent_execution
from local_agents.exceptions import ConfigurationError, ModelNotAvailableError
from local_agents.ollama_client import OllamaClient


class TestBaseAgent:
    """Test BaseAgent abstract base class."""

    @pytest.fixture
    def mock_ollama_client(self):
        """Create a mock Ollama client."""
        client = Mock(spec=OllamaClient)
        client.is_model_available.return_value = True
        client.generate.return_value = "Test response"
        client.chat.return_value = "Test chat response"
        return client

    @pytest.fixture
    def test_agent(self, mock_ollama_client):
        """Create a test agent implementation."""

        class TestAgent(BaseAgent):
            def execute(self, task, context=None):
                return TaskResult(
                    success=True,
                    output="Test output",
                    agent_type=self.agent_type,
                    task=task,
                    context=context,
                )

        return TestAgent(
            agent_type="test",
            role="Test Agent",
            goal="Test goal",
            model="test:model",
            ollama_client=mock_ollama_client,
        )

    def test_agent_initialization(self, mock_ollama_client):
        """Test agent initialization."""

        class TestAgent(BaseAgent):
            def execute(self, task, context=None):
                pass

        agent = TestAgent(
            agent_type="test",
            role="Test Agent",
            goal="Test goal",
            model="test:model",
            ollama_client=mock_ollama_client,
        )

        assert agent.agent_type == "test"
        assert agent.role == "Test Agent"
        assert agent.goal == "Test goal"
        assert agent.model == "test:model"
        assert agent.ollama_client == mock_ollama_client

    @patch("local_agents.config.get_config")
    def test_agent_initialization_with_config(
        self, mock_get_config, mock_ollama_client
    ):
        """Test agent initialization using configuration."""
        mock_config = Mock()
        mock_config.temperature = 0.8
        mock_config.max_tokens = 2048
        mock_get_config.return_value = mock_config

        class TestAgent(BaseAgent):
            def execute(self, task, context=None):
                pass

        with patch(
            "local_agents.config.get_model_for_agent", return_value="config:model"
        ):
            agent = TestAgent(
                agent_type="test",
                role="Test Agent",
                goal="Test goal",
                ollama_client=mock_ollama_client,
            )

        assert agent.model == "config:model"
        assert agent.temperature == 0.8
        assert agent.max_tokens == 2048

    def test_agent_model_not_available(self, mock_ollama_client):
        """Test agent initialization when model is not available."""
        mock_ollama_client.is_model_available.return_value = False
        mock_ollama_client.pull_model.return_value = False

        class TestAgent(BaseAgent):
            def execute(self, task, context=None):
                pass

        with pytest.raises(RuntimeError, match="Failed to pull model"):
            TestAgent(
                agent_type="test",
                role="Test Agent",
                goal="Test goal",
                model="missing:model",
                ollama_client=mock_ollama_client,
            )

    def test_agent_model_pull_success(self, mock_ollama_client):
        """Test agent initialization with successful model pull."""
        mock_ollama_client.is_model_available.return_value = False
        mock_ollama_client.pull_model.return_value = True

        class TestAgent(BaseAgent):
            def execute(self, task, context=None):
                pass

        agent = TestAgent(
            agent_type="test",
            role="Test Agent",
            goal="Test goal",
            model="new:model",
            ollama_client=mock_ollama_client,
        )

        mock_ollama_client.pull_model.assert_called_once_with("new:model")
        assert agent.model == "new:model"

    def test_build_system_prompt(self, test_agent):
        """Test system prompt building."""
        system_prompt = test_agent._build_system_prompt()

        assert "Test Agent" in system_prompt
        assert "Test goal" in system_prompt
        assert "clear, actionable, and well-structured responses" in system_prompt

    def test_call_ollama(self, test_agent):
        """Test calling Ollama with prompt."""
        response = test_agent._call_ollama("Test prompt")

        assert response == "Test response"
        test_agent.ollama_client.generate.assert_called_once_with(
            model="test:model",
            prompt="Test prompt",
            temperature=test_agent.temperature,
            max_tokens=test_agent.max_tokens,
            system=test_agent._build_system_prompt(),
            stream=False,
        )

    def test_call_ollama_with_custom_system(self, test_agent):
        """Test calling Ollama with custom system prompt."""
        custom_system = "Custom system prompt"
        response = test_agent._call_ollama("Test prompt", system=custom_system)

        assert response == "Test response"
        test_agent.ollama_client.generate.assert_called_once_with(
            model="test:model",
            prompt="Test prompt",
            temperature=test_agent.temperature,
            max_tokens=test_agent.max_tokens,
            system=custom_system,
            stream=False,
        )

    def test_call_ollama_stream(self, test_agent):
        """Test calling Ollama with streaming."""
        response = test_agent._call_ollama("Test prompt", stream=True)

        assert response == "Test response"
        test_agent.ollama_client.generate.assert_called_once_with(
            model="test:model",
            prompt="Test prompt",
            temperature=test_agent.temperature,
            max_tokens=test_agent.max_tokens,
            system=test_agent._build_system_prompt(),
            stream=True,
        )

    def test_call_ollama_chat(self, test_agent):
        """Test calling Ollama chat."""
        messages = [{"role": "user", "content": "Hello"}]
        response = test_agent._call_ollama_chat(messages)

        assert response == "Test chat response"
        test_agent.ollama_client.chat.assert_called_once_with(
            model="test:model",
            messages=messages,
            temperature=test_agent.temperature,
            max_tokens=test_agent.max_tokens,
            stream=False,
        )

    def test_call_ollama_error(self, test_agent):
        """Test calling Ollama with error."""
        test_agent.ollama_client.generate.side_effect = Exception("Test error")

        with pytest.raises(Exception, match="Test error"):
            test_agent._call_ollama("Test prompt")

    @patch("local_agents.base.console.print")
    def test_display_info(self, mock_print, test_agent):
        """Test displaying agent info."""
        test_agent.display_info()
        mock_print.assert_called_once()


class TestTaskResult:
    """Test TaskResult class."""

    def test_task_result_success(self):
        """Test successful task result."""
        result = TaskResult(
            success=True,
            output="Test output",
            agent_type="test",
            task="Test task",
            context={"key": "value"},
        )

        assert result.success is True
        assert result.output == "Test output"
        assert result.agent_type == "test"
        assert result.task == "Test task"
        assert result.context == {"key": "value"}
        assert result.error is None

    def test_task_result_failure(self):
        """Test failed task result."""
        result = TaskResult(
            success=False,
            output="Partial output",
            agent_type="test",
            task="Test task",
            error="Test error",
        )

        assert result.success is False
        assert result.output == "Partial output"
        assert result.error == "Test error"
        assert result.context == {}

    def test_to_dict(self):
        """Test converting result to dictionary."""
        result = TaskResult(
            success=True,
            output="Test output",
            agent_type="test",
            task="Test task",
            context={"key": "value"},
            error="Test error",
        )

        result_dict = result.to_dict()

        expected = {
            "success": True,
            "output": "Test output",
            "agent_type": "test",
            "task": "Test task",
            "context": {"key": "value"},
            "error": "Test error",
        }

        assert result_dict == expected

    @patch("local_agents.base.console.print")
    def test_display_success(self, mock_print):
        """Test displaying successful result."""
        result = TaskResult(
            success=True, output="Test output", agent_type="test", task="Test task"
        )

        result.display()
        mock_print.assert_called_once()

    @patch("local_agents.base.console.print")
    def test_display_failure(self, mock_print):
        """Test displaying failed result."""
        result = TaskResult(
            success=False,
            output="Partial output",
            agent_type="test",
            task="Test task",
            error="Test error",
        )

        result.display()
        mock_print.assert_called_once()


class TestHandleAgentExecutionDecorator:
    """Test @handle_agent_execution decorator functionality."""

    @pytest.fixture
    def mock_ollama_client(self):
        """Create a mock Ollama client."""
        client = Mock(spec=OllamaClient)
        client.is_model_available.return_value = True
        client.generate.return_value = "Test response"
        return client

    def test_decorator_success_case(self, mock_ollama_client):
        """Test decorator with successful execution."""

        class TestAgent(BaseAgent):
            @handle_agent_execution
            def execute(self, task, context=None, stream=False):
                return self._create_success_result("success output", task, context)

        agent = TestAgent(
            agent_type="test",
            role="Test Agent",
            goal="Test goal",
            model="test:model",
            ollama_client=mock_ollama_client,
        )

        result = agent.execute("test task")

        assert result.success is True
        assert result.output == "success output"
        assert result.task == "test task"
        assert result.context == {}  # Should normalize None to empty dict

    def test_decorator_exception_handling(self, mock_ollama_client):
        """Test decorator handles exceptions properly."""

        class TestAgent(BaseAgent):
            @handle_agent_execution
            def execute(self, task, context=None, stream=False):
                raise ValueError("Test exception")

        agent = TestAgent(
            agent_type="test",
            role="Test Agent",
            goal="Test goal",
            model="test:model",
            ollama_client=mock_ollama_client,
        )

        result = agent.execute("test task")

        assert result.success is False
        assert result.output == ""
        assert "Test exception" in result.error
        assert result.agent_type == "test"

    def test_decorator_context_normalization(self, mock_ollama_client):
        """Test decorator normalizes None context to empty dict."""

        class TestAgent(BaseAgent):
            @handle_agent_execution
            def execute(self, task, context=None, stream=False):
                # Verify context is normalized
                assert context == {}
                return self._create_success_result("success", task, context)

        agent = TestAgent(
            agent_type="test",
            role="Test Agent",
            goal="Test goal",
            model="test:model",
            ollama_client=mock_ollama_client,
        )

        # Pass None context - should be normalized to {}
        result = agent.execute("test task", context=None)
        assert result.success is True

    def test_decorator_preserves_context(self, mock_ollama_client):
        """Test decorator preserves existing context."""

        class TestAgent(BaseAgent):
            @handle_agent_execution
            def execute(self, task, context=None, stream=False):
                assert context["key"] == "value"
                return self._create_success_result("success", task, context)

        agent = TestAgent(
            agent_type="test",
            role="Test Agent",
            goal="Test goal",
            model="test:model",
            ollama_client=mock_ollama_client,
        )

        original_context = {"key": "value"}
        result = agent.execute("test task", context=original_context)

        assert result.success is True
        assert result.context == original_context

    def test_decorator_handles_ollama_errors(self, mock_ollama_client):
        """Test decorator handles OllamaClient-specific errors."""

        class TestAgent(BaseAgent):
            @handle_agent_execution
            def execute(self, task, context=None, stream=False):
                response = self._call_ollama("test prompt")
                return self._create_success_result(response, task, context)

        # Mock Ollama client to raise connection error
        mock_ollama_client.generate.side_effect = ConnectionError(
            "Cannot connect to Ollama"
        )

        agent = TestAgent(
            agent_type="test",
            role="Test Agent",
            goal="Test goal",
            model="test:model",
            ollama_client=mock_ollama_client,
        )

        result = agent.execute("test task")

        assert result.success is False
        assert "Cannot connect to Ollama" in result.error

    def test_decorator_timeout_handling(self, mock_ollama_client):
        """Test decorator handles timeout errors."""

        class TestAgent(BaseAgent):
            @handle_agent_execution
            def execute(self, task, context=None, stream=False):
                raise TimeoutError("Request timed out after 30 seconds")

        agent = TestAgent(
            agent_type="test",
            role="Test Agent",
            goal="Test goal",
            model="test:model",
            ollama_client=mock_ollama_client,
        )

        result = agent.execute("test task")

        assert result.success is False
        assert "timed out" in result.error.lower()


class TestBaseAgentAdvanced:
    """Test advanced BaseAgent functionality."""

    @pytest.fixture
    def mock_ollama_client(self):
        """Create a mock Ollama client."""
        client = Mock(spec=OllamaClient)
        client.is_model_available.return_value = True
        client.generate.return_value = "Test response"
        client.chat.return_value = "Test chat response"
        return client

    def test_create_success_result_helper(self, mock_ollama_client):
        """Test _create_success_result helper method."""

        class TestAgent(BaseAgent):
            def execute(self, task, context=None):
                return self._create_success_result("test output", task, context)

        agent = TestAgent(
            agent_type="test",
            role="Test Agent",
            goal="Test goal",
            model="test:model",
            ollama_client=mock_ollama_client,
        )

        result = agent._create_success_result(
            "success output", "test task", {"key": "value"}
        )

        assert isinstance(result, TaskResult)
        assert result.success is True
        assert result.output == "success output"
        assert result.task == "test task"
        assert result.context == {"key": "value"}
        assert result.agent_type == "test"
        assert result.error is None

    def test_create_success_result_with_none_context(self, mock_ollama_client):
        """Test _create_success_result with None context."""

        class TestAgent(BaseAgent):
            def execute(self, task, context=None):
                pass

        agent = TestAgent(
            agent_type="test",
            role="Test Agent",
            goal="Test goal",
            model="test:model",
            ollama_client=mock_ollama_client,
        )

        result = agent._create_success_result("output", "task", None)

        assert result.context == {}

    def test_model_validation_on_initialization(self):
        """Test model validation during agent initialization."""
        mock_client = Mock(spec=OllamaClient)
        mock_client.is_model_available.return_value = False
        mock_client.pull_model.return_value = False

        class TestAgent(BaseAgent):
            def execute(self, task, context=None):
                pass

        with pytest.raises(RuntimeError, match="Failed to pull model"):
            TestAgent(
                agent_type="test",
                role="Test Agent",
                goal="Test goal",
                model="nonexistent:model",
                ollama_client=mock_client,
            )

    def test_model_auto_pull_on_initialization(self, mock_ollama_client):
        """Test automatic model pulling during initialization."""
        # First call returns False (model not available), second returns True (after pull)
        mock_ollama_client.is_model_available.side_effect = [False, True]
        mock_ollama_client.pull_model.return_value = True

        class TestAgent(BaseAgent):
            def execute(self, task, context=None):
                pass

        agent = TestAgent(
            agent_type="test",
            role="Test Agent",
            goal="Test goal",
            model="new:model",
            ollama_client=mock_ollama_client,
        )

        # Verify model was pulled
        mock_ollama_client.pull_model.assert_called_once_with("new:model")
        assert agent.model == "new:model"

    def test_agent_configuration_integration(self, mock_ollama_client):
        """Test agent integrates with configuration system."""
        with patch("local_agents.config.get_config") as mock_get_config:
            with patch("local_agents.config.get_model_for_agent") as mock_get_model:
                mock_config = Mock()
                mock_config.temperature = 0.9
                mock_config.max_tokens = 1024
                mock_config.context_length = 4096
                mock_get_config.return_value = mock_config
                mock_get_model.return_value = "config:model"

                class TestAgent(BaseAgent):
                    def execute(self, task, context=None):
                        pass

                agent = TestAgent(
                    agent_type="test",
                    role="Test Agent",
                    goal="Test goal",
                    ollama_client=mock_ollama_client,
                )

                # Verify configuration was applied
                assert agent.model == "config:model"
                assert agent.temperature == 0.9
                assert agent.max_tokens == 1024
                assert agent.context_length == 4096

    def test_error_handling_chain(self, mock_ollama_client):
        """Test complete error handling chain."""

        class TestAgent(BaseAgent):
            @handle_agent_execution
            def execute(self, task, context=None, stream=False):
                # Simulate different types of errors
                if "connection" in task:
                    raise ConnectionError("Connection failed")
                elif "timeout" in task:
                    raise TimeoutError("Request timeout")
                elif "model" in task:
                    raise ModelNotAvailableError("Model not found")
                elif "config" in task:
                    raise ConfigurationError("Invalid configuration")
                else:
                    raise ValueError("Generic error")

        agent = TestAgent(
            agent_type="test",
            role="Test Agent",
            goal="Test goal",
            model="test:model",
            ollama_client=mock_ollama_client,
        )

        # Test different error types
        error_cases = [
            ("connection error", "Connection failed"),
            ("timeout error", "Request timeout"),
            ("model error", "Model not found"),
            ("config error", "Invalid configuration"),
            ("generic error", "Generic error"),
        ]

        for task, expected_error in error_cases:
            result = agent.execute(task)
            assert result.success is False
            assert expected_error in result.error
