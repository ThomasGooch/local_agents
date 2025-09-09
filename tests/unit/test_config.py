"""Tests for configuration management."""

import tempfile
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest
import yaml
from pydantic import ValidationError

from local_agents.config import AgentSettings, Config, ConfigManager, WorkflowConfig


class TestConfig:
    """Test Config model."""

    def test_config_defaults(self):
        """Test default configuration values."""
        config = Config()
        assert config.default_model == "llama3.1:8b"
        assert config.ollama_host == "http://localhost:11434"
        assert config.temperature == 0.7
        assert config.max_tokens == 4096
        assert isinstance(config.agents, AgentSettings)
        assert isinstance(config.workflows, WorkflowConfig)

    def test_config_custom_values(self):
        """Test configuration with custom values."""
        config = Config(default_model="custom:model", temperature=0.5, max_tokens=2048)
        assert config.default_model == "custom:model"
        assert config.temperature == 0.5
        assert config.max_tokens == 2048

    def test_temperature_validation_valid_range(self):
        """Test temperature validation accepts valid range."""
        # Test boundary values and mid-range
        valid_temps = [0.0, 0.5, 1.0, 1.5, 2.0]
        for temp in valid_temps:
            config = Config(temperature=temp)
            assert config.temperature == temp

    def test_temperature_validation_invalid_range(self):
        """Test temperature validation rejects invalid range."""
        with pytest.raises(ValueError, match="Temperature must be between 0.0 and 2.0"):
            Config(temperature=-0.1)

        with pytest.raises(ValueError, match="Temperature must be between 0.0 and 2.0"):
            Config(temperature=2.1)

    def test_max_tokens_validation(self):
        """Test max_tokens validation."""
        # Valid values
        valid_tokens = [1, 1000, 4096, 8192, 32768]
        for tokens in valid_tokens:
            config = Config(max_tokens=tokens)
            assert config.max_tokens == tokens

        # Invalid values
        with pytest.raises(ValueError, match="max_tokens must be greater than 0"):
            Config(max_tokens=0)

        with pytest.raises(ValueError, match="max_tokens must be greater than 0"):
            Config(max_tokens=-100)

    def test_context_length_validation(self):
        """Test context_length validation."""
        # Valid values
        valid_lengths = [1024, 2048, 4096, 8192, 32768]
        for length in valid_lengths:
            config = Config(context_length=length)
            assert config.context_length == length

        # Invalid values
        with pytest.raises(ValueError, match="context_length must be greater than 0"):
            Config(context_length=0)

        with pytest.raises(ValueError, match="context_length must be greater than 0"):
            Config(context_length=-1000)

    def test_ollama_host_validation(self):
        """Test Ollama host URL validation."""
        # Valid URLs
        valid_hosts = [
            "http://localhost:11434",
            "https://localhost:11434",
            "http://192.168.1.100:8080",
            "https://ollama.example.com:443",
            "http://ollama-server:11434",
        ]

        for host in valid_hosts:
            config = Config(ollama_host=host)
            assert config.ollama_host == host

        # Invalid URLs
        invalid_hosts = [
            "localhost:11434",  # Missing protocol
            "ftp://localhost:11434",  # Wrong protocol
            "http://",  # Incomplete URL
            "not-a-url",  # Not a URL at all
            "",  # Empty string
        ]

        for host in invalid_hosts:
            with pytest.raises(
                ValueError, match="ollama_host must be a valid HTTP/HTTPS URL"
            ):
                Config(ollama_host=host)

    def test_model_name_validation(self):
        """Test model name format validation."""
        # Valid model names
        valid_models = [
            "llama3.1:8b",
            "codellama:7b",
            "deepseek-coder:6.7b",
            "mistral:7b-instruct",
            "phi3:3.8b-mini-instruct-4k",
        ]

        for model in valid_models:
            config = Config(default_model=model)
            assert config.default_model == model

        # Invalid model names
        invalid_models = [
            "invalid_model",  # No colon separator
            "model:",  # Empty tag
            ":tag",  # Empty name
            "",  # Empty string
            "model:tag:extra",  # Too many parts
        ]

        for model in invalid_models:
            with pytest.raises(
                ValueError, match="Model name must follow format 'name:tag'"
            ):
                Config(default_model=model)


class TestAgentSettings:
    """Test AgentSettings model."""

    def test_agent_settings_defaults(self):
        """Test default agent settings."""
        settings = AgentSettings()
        assert settings.planning == "llama3.1:8b"
        assert settings.coding == "codellama:7b"
        assert settings.testing == "deepseek-coder:6.7b"
        assert settings.reviewing == "llama3.1:8b"

    def test_agent_settings_custom(self):
        """Test custom agent settings."""
        settings = AgentSettings(planning="custom:planner", coding="custom:coder")
        assert settings.planning == "custom:planner"
        assert settings.coding == "custom:coder"
        assert settings.testing == "deepseek-coder:6.7b"  # Default unchanged


class TestWorkflowConfig:
    """Test WorkflowConfig model."""

    def test_workflow_config_defaults(self):
        """Test default workflow configurations."""
        config = WorkflowConfig()
        assert config.feature_development == ["plan", "code", "test", "review"]
        assert config.bug_fix == ["plan", "code", "test"]
        assert config.code_review == ["review"]
        assert config.refactoring == ["plan", "code", "test", "review"]


class TestConfigManager:
    """Test ConfigManager class."""

    def test_init_default_path(self):
        """Test ConfigManager initialization with default path."""
        manager = ConfigManager()
        assert manager.config_path.name == ".local_agents_config.yml"
        assert str(manager.config_path).startswith(str(Path.home()))

    def test_init_custom_path(self):
        """Test ConfigManager initialization with custom path."""
        custom_path = "/tmp/test_config.yml"
        manager = ConfigManager(custom_path)
        assert str(manager.config_path) == custom_path

    def test_load_config_creates_default_when_missing(self):
        """Test that missing config file creates default configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "missing_config.yml"
            manager = ConfigManager(str(config_path))

            # Ensure file doesn't exist
            assert not config_path.exists()

            config = manager.load_config()

            # Should create default config
            assert isinstance(config, Config)
            assert config.default_model == "llama3.1:8b"
            assert config.temperature == 0.7

            # File should now exist with default content
            assert config_path.exists()
            with open(config_path) as f:
                saved_data = yaml.safe_load(f)
            assert saved_data["default_model"] == "llama3.1:8b"

    def test_load_config_handles_permission_errors(self):
        """Test loading config handles permission errors gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "no_permission.yml"
            config_path.write_text("default_model: test:model")
            config_path.chmod(0o000)  # No permissions

            try:
                manager = ConfigManager(str(config_path))
                config = manager.load_config()

                # Should fallback to default config
                assert config.default_model == "llama3.1:8b"
            finally:
                config_path.chmod(0o644)  # Restore permissions for cleanup

    def test_save_config_validation_prevents_invalid_config(self):
        """Test that save_config validates before saving."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "validation_test.yml"
            manager = ConfigManager(str(config_path))

            # Create invalid config
            invalid_config = Config()
            invalid_config.temperature = 5.0  # Invalid temperature

            # Should raise validation error and not save
            with pytest.raises(ValueError):
                manager.save_config(invalid_config)

            # File should not exist or contain invalid data
            if config_path.exists():
                with open(config_path) as f:
                    data = yaml.safe_load(f)
                assert data.get("temperature", 0.7) != 5.0

    def test_update_config_nested_values(self):
        """Test updating nested configuration values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "nested_test.yml"
            manager = ConfigManager(str(config_path))

            # Load initial config
            config = manager.load_config()

            # Update nested agent settings
            manager.update_config("agents.planning", "custom:planner")
            manager.update_config("agents.coding", "custom:coder")

            # Verify updates
            updated_config = manager.load_config()
            assert updated_config.agents.planning == "custom:planner"
            assert updated_config.agents.coding == "custom:coder"
            # Other values should remain unchanged
            assert updated_config.agents.testing == "deepseek-coder:6.7b"

    def test_backup_and_restore_config(self):
        """Test config backup and restore functionality."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "backup_test.yml"
            manager = ConfigManager(str(config_path))

            # Create and save initial config
            config = manager.load_config()
            config.temperature = 0.8
            manager.save_config(config)

            # Create backup
            backup_path = manager.create_backup()
            assert backup_path.exists()

            # Modify config
            config.temperature = 1.5
            manager.save_config(config)

            # Restore from backup
            manager.restore_from_backup(backup_path)
            restored_config = manager.load_config()
            assert restored_config.temperature == 0.8

    def test_load_config_nonexistent_file(self):
        """Test loading configuration when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "nonexistent.yml"
            manager = ConfigManager(str(config_path))

            config = manager.load_config()

            assert isinstance(config, Config)
            assert config.default_model == "llama3.1:8b"
            # Config file should be created
            assert config_path.exists()

    def test_load_config_existing_file(self):
        """Test loading configuration from existing file."""
        config_data = {
            "default_model": "test:model",
            "temperature": 0.5,
            "agents": {"planning": "test:planner"},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            manager = ConfigManager(config_path)
            config = manager.load_config()

            assert config.default_model == "test:model"
            assert config.temperature == 0.5
            assert config.agents.planning == "test:planner"
        finally:
            Path(config_path).unlink()

    def test_load_config_invalid_yaml(self):
        """Test loading configuration with invalid YAML."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            config_path = f.name

        try:
            manager = ConfigManager(config_path)
            config = manager.load_config()

            # Should fallback to default configuration
            assert config.default_model == "llama3.1:8b"
        finally:
            Path(config_path).unlink()

    def test_save_config(self):
        """Test saving configuration to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_config.yml"
            manager = ConfigManager(str(config_path))

            # Load and modify config
            config = manager.load_config()
            config.default_model = "test:model"
            manager._config = config

            # Save config
            manager.save_config()

            # Verify file was created and contains expected data
            assert config_path.exists()
            with open(config_path) as f:
                saved_data = yaml.safe_load(f)

            assert saved_data["default_model"] == "test:model"

    def test_get_model_for_agent(self):
        """Test getting model for specific agent type."""
        manager = ConfigManager()
        manager._config = Config()

        assert manager.get_model_for_agent("plan") == "llama3.1:8b"
        assert manager.get_model_for_agent("code") == "codellama:7b"
        assert manager.get_model_for_agent("test") == "deepseek-coder:6.7b"
        assert manager.get_model_for_agent("review") == "llama3.1:8b"
        assert manager.get_model_for_agent("unknown") == "llama3.1:8b"  # Default

    def test_get_workflow_steps(self):
        """Test getting workflow steps."""
        manager = ConfigManager()
        manager._config = Config()

        assert manager.get_workflow_steps("feature-dev") == [
            "plan",
            "code",
            "test",
            "review",
        ]
        assert manager.get_workflow_steps("bug-fix") == ["plan", "code", "test"]
        assert manager.get_workflow_steps("code-review") == ["review"]
        assert manager.get_workflow_steps("refactor") == [
            "plan",
            "code",
            "test",
            "review",
        ]
        assert manager.get_workflow_steps("unknown") == []

    @patch("builtins.open", new_callable=mock_open)
    @patch("yaml.dump")
    def test_save_config_creates_directory(self, mock_yaml_dump, mock_file):
        """Test that save_config creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "subdir" / "config.yml"
            manager = ConfigManager(str(config_path))

            manager.save_config()

            # Verify directory was created
            assert config_path.parent.exists()
            mock_file.assert_called_once()
            mock_yaml_dump.assert_called_once()

    def test_config_validation_comprehensive(self):
        """Test comprehensive configuration validation scenarios."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "validation_comprehensive.yml"

            # Test various invalid configurations
            invalid_configs = [
                {"default_model": "invalid_model_name"},  # Invalid model format
                {"temperature": -1.0},  # Invalid temperature
                {"max_tokens": 0},  # Invalid max_tokens
                {"ollama_host": "invalid-url"},  # Invalid URL
                {"context_length": -100},  # Invalid context_length
            ]

            manager = ConfigManager(str(config_path))

            for invalid_config in invalid_configs:
                # Write invalid config to file
                with open(config_path, "w") as f:
                    yaml.dump(invalid_config, f)

                # Loading should handle validation gracefully
                config = manager.load_config()

                # Should fallback to valid defaults
                assert config.default_model == "llama3.1:8b"
                assert 0.0 <= config.temperature <= 2.0
                assert config.max_tokens > 0
                assert config.context_length > 0
                assert config.ollama_host.startswith("http")

    def test_configuration_rollback_on_failure(self):
        """Test configuration rollback when update fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "rollback_test.yml"
            manager = ConfigManager(str(config_path))

            # Create valid initial config
            initial_config = manager.load_config()
            initial_config.temperature = 0.5
            manager.save_config(initial_config)

            # Attempt invalid update
            try:
                manager.update_config("temperature", 5.0)  # Invalid value
            except ValueError:
                pass  # Expected to fail

            # Configuration should remain unchanged
            current_config = manager.load_config()
            assert current_config.temperature == 0.5
