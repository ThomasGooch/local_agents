"""Configuration management for Local Agents."""

import re
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, ValidationError, field_validator


class ModelConfig(BaseModel):
    """Configuration for individual models."""

    name: str
    temperature: float = 0.7
    max_tokens: int = 4096
    context_length: int = 8192

    @field_validator("name")
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        """Validate model name format."""
        if not v or not v.strip():
            raise ValueError("Model name cannot be empty")

        # Basic validation for Ollama model name format
        if not re.match(r"^[\w\-\.]+:[\w\-\.]+$", v):
            raise ValueError("Model name must follow format 'name:tag'")
        return v.strip()

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        """Validate temperature is in valid range."""
        if not 0.0 <= v <= 2.0:
            raise ValueError(f"Temperature must be between 0.0 and 2.0, got {v}")
        return v

    @field_validator("max_tokens")
    @classmethod
    def validate_max_tokens(cls, v: int) -> int:
        """Validate max_tokens is positive."""
        if v <= 0:
            raise ValueError("max_tokens must be greater than 0")
        if v > 100000:  # Reasonable upper limit
            raise ValueError(f"max_tokens too large (max 100,000), got {v}")
        return v

    @field_validator("context_length")
    @classmethod
    def validate_context_length(cls, v: int) -> int:
        """Validate context_length is positive."""
        if v <= 0:
            raise ValueError("context_length must be greater than 0")
        if v > 1000000:  # Reasonable upper limit
            raise ValueError(f"context_length too large (max 1,000,000), got {v}")
        return v


class AgentSettings(BaseModel):
    """Settings for agent behavior."""

    planning: str = "llama3.1:8b"
    coding: str = "codellama:7b"
    testing: str = "deepseek-coder:6.7b"
    reviewing: str = "llama3.1:8b"

    @field_validator("planning", "coding", "testing", "reviewing")
    @classmethod
    def validate_model_names(cls, v: str) -> str:
        """Validate agent model names."""
        if not v or not v.strip():
            raise ValueError("Agent model name cannot be empty")

        # Use same validation as ModelConfig
        if not re.match(r"^[\w\-\.]+:[\w\-\.]+$", v):
            raise ValueError("Model name must follow format 'name:tag'")
        return v.strip()


class WorkflowConfig(BaseModel):
    """Configuration for predefined workflows."""

    feature_development: list[str] = ["plan", "code", "test", "review"]
    bug_fix: list[str] = ["plan", "code", "test"]
    code_review: list[str] = ["review"]
    refactoring: list[str] = ["plan", "code", "test", "review"]

    @field_validator("feature_development", "bug_fix", "code_review", "refactoring")
    @classmethod
    def validate_workflow_steps(cls, v: list[str]) -> list[str]:
        """Validate workflow steps."""
        if not v:
            raise ValueError("Workflow cannot be empty")

        valid_agents = {"plan", "code", "test", "review"}
        for step in v:
            if step not in valid_agents:
                raise ValueError(
                    f"Invalid workflow step: {step}. "
                    f"Valid steps are: {', '.join(sorted(valid_agents))}"
                )

        # Check for duplicates
        if len(v) != len(set(v)):
            raise ValueError("Workflow steps cannot contain duplicates")

        return v


class PerformanceConfig(BaseModel):
    """Performance and optimization settings."""

    max_concurrent_agents: int = 2
    enable_response_cache: bool = True
    cache_size: int = 100
    cache_ttl_seconds: int = 300
    enable_parallel_workflows: bool = True
    memory_cleanup_interval: int = 300
    performance_monitoring: bool = False

    @field_validator("max_concurrent_agents")
    @classmethod
    def validate_max_concurrent_agents(cls, v: int) -> int:
        """Validate max_concurrent_agents is reasonable."""
        if v < 1:
            raise ValueError("max_concurrent_agents must be at least 1")
        if v > 8:  # Reasonable upper limit
            raise ValueError("max_concurrent_agents too high (max 8)")
        return v

    @field_validator("cache_size")
    @classmethod
    def validate_cache_size(cls, v: int) -> int:
        """Validate cache_size is reasonable."""
        if v < 0:
            raise ValueError("cache_size must be non-negative")
        if v > 1000:  # Reasonable upper limit
            raise ValueError("cache_size too large (max 1000)")
        return v

    @field_validator("cache_ttl_seconds")
    @classmethod
    def validate_cache_ttl(cls, v: int) -> int:
        """Validate cache TTL is reasonable."""
        if v < 0:
            raise ValueError("cache_ttl_seconds must be non-negative")
        if v > 3600:  # 1 hour max
            raise ValueError("cache_ttl_seconds too large (max 3600)")
        return v


class Config(BaseModel):
    """Main configuration class."""

    default_model: str = "llama3.1:8b"
    ollama_host: str = "http://localhost:11434"
    temperature: float = 0.7
    max_tokens: int = 4096
    context_length: int = 8192
    agents: AgentSettings = AgentSettings()
    workflows: WorkflowConfig = WorkflowConfig()
    performance: PerformanceConfig = PerformanceConfig()

    @field_validator("default_model")
    @classmethod
    def validate_default_model(cls, v: str) -> str:
        """Validate default model name."""
        if not v or not v.strip():
            raise ValueError("Model name must follow format 'name:tag'")

        if not re.match(r"^[\w\-\.]+:[\w\-\.]+$", v):
            raise ValueError("Model name must follow format 'name:tag'")
        return v.strip()

    @field_validator("ollama_host")
    @classmethod
    def validate_ollama_host(cls, v: str) -> str:
        """Validate Ollama host URL format."""
        if not v or not v.strip():
            raise ValueError("ollama_host must be a valid HTTP/HTTPS URL")

        v = v.strip()

        # Must start with http:// or https://
        if not v.startswith(("http://", "https://")):
            raise ValueError("ollama_host must be a valid HTTP/HTTPS URL")

        # Basic URL validation
        url_pattern = (
            r"^https?://[a-zA-Z0-9]([a-zA-Z0-9\-\.]*[a-zA-Z0-9])?(\:[0-9]+)?(/.*)?$"
        )
        if not re.match(url_pattern, v):
            raise ValueError("ollama_host must be a valid HTTP/HTTPS URL")

        # Check for localhost or valid IP patterns
        host_part = v.replace("http://", "").replace("https://", "").split("/")[0]
        if ":" in host_part:
            host, port = host_part.split(":")
            try:
                port_num = int(port)
                if not 1 <= port_num <= 65535:
                    raise ValueError(
                        f"Port must be between 1 and 65535, got: {port_num}"
                    )
            except ValueError as e:
                if "Port must be" in str(e):
                    raise
                raise ValueError(f"Invalid port number: {port}")

        return v

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        """Validate temperature is in valid range."""
        if not 0.0 <= v <= 2.0:
            raise ValueError(f"Temperature must be between 0.0 and 2.0, got {v}")
        return v

    @field_validator("max_tokens")
    @classmethod
    def validate_max_tokens(cls, v: int) -> int:
        """Validate max_tokens is positive."""
        if v <= 0:
            raise ValueError("max_tokens must be greater than 0")
        if v > 100000:
            raise ValueError(f"max_tokens too large (max 100,000), got {v}")
        return v

    @field_validator("context_length")
    @classmethod
    def validate_context_length(cls, v: int) -> int:
        """Validate context_length is positive."""
        if v <= 0:
            raise ValueError("context_length must be greater than 0")
        if v > 1000000:
            raise ValueError(f"context_length too large (max 1,000,000), got {v}")
        return v


class ConfigManager:
    """Manages configuration loading and saving."""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = Path(
            config_path or "~/.local_agents_config.yml"
        ).expanduser()
        self._config: Optional[Config] = None

    def load_config(self) -> Config:
        """Load configuration from file or create default."""
        if self._config is not None:
            return self._config

        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    config_data = yaml.safe_load(f) or {}
                self._config = Config(**config_data)
            except ValidationError as e:
                print(f"Configuration validation failed: {self.config_path}")
                for error in e.errors():
                    field_path = " -> ".join(str(loc) for loc in error["loc"])
                    print(f"  {field_path}: {error['msg']}")
                print("Using default configuration.")
                self._config = Config()
            except yaml.YAMLError as e:
                print(f"Warning: Invalid YAML in config file {self.config_path}: {e}")
                print("Using default configuration.")
                self._config = Config()
            except Exception as e:
                print(f"Warning: Failed to load config from {self.config_path}: {e}")
                print("Using default configuration.")
                self._config = Config()
        else:
            self._config = Config()
            self.save_config()

        return self._config

    def save_config(self, config: Optional[Config] = None) -> None:
        """Save current configuration to file."""
        if config is not None:
            # Validate before saving by checking individual field constraints
            if hasattr(config, "temperature") and not (
                0.0 <= config.temperature <= 2.0
            ):
                raise ValueError(
                    f"Invalid configuration: temperature must be between 0.0 and "
                    f"2.0, got {config.temperature}"
                )
            if hasattr(config, "max_tokens") and config.max_tokens <= 0:
                raise ValueError(
                    "Invalid configuration: max_tokens must be greater than 0"
                )
            if hasattr(config, "context_length") and config.context_length <= 0:
                raise ValueError(
                    "Invalid configuration: context_length must be greater than 0"
                )
            self._config = config
        elif self._config is None:
            self._config = Config()

        # Ensure directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_path, "w") as f:
            yaml.dump(self._config.model_dump(), f, default_flow_style=False)

    def get_model_for_agent(self, agent_type: str) -> str:
        """Get the configured model for a specific agent type."""
        config = self.load_config()
        agent_models = {
            "plan": config.agents.planning,
            "code": config.agents.coding,
            "test": config.agents.testing,
            "review": config.agents.reviewing,
        }
        return agent_models.get(agent_type, config.default_model)

    def get_workflow_steps(self, workflow_name: str) -> list[str]:
        """Get the steps for a predefined workflow."""
        config = self.load_config()
        workflows = {
            "feature-dev": config.workflows.feature_development,
            "bug-fix": config.workflows.bug_fix,
            "code-review": config.workflows.code_review,
            "refactor": config.workflows.refactoring,
        }
        return workflows.get(workflow_name, [])

    def update_config(self, key: str, value: Any) -> None:
        """Update a configuration value."""
        config = self.load_config()
        config_dict = config.model_dump()

        if "." in key:
            # Handle nested keys like 'agents.planning'
            keys = key.split(".")
            target = config_dict
            for k in keys[:-1]:
                if k not in target:
                    target[k] = {}
                target = target[k]
            target[keys[-1]] = value
        else:
            config_dict[key] = value

        # Validate and update
        try:
            updated_config = Config(**config_dict)
            self._config = updated_config
            self.save_config()
        except ValidationError as e:
            raise ValueError(f"Configuration update failed: {e}")

    def create_backup(self) -> Path:
        """Create a backup of the current configuration file."""
        if not self.config_path.exists():
            # Create current config first
            self.save_config()

        backup_path = self.config_path.with_suffix(f"{self.config_path.suffix}.backup")
        shutil.copy2(self.config_path, backup_path)
        return backup_path

    def restore_from_backup(self, backup_path: Path) -> None:
        """Restore configuration from a backup file."""
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        # Validate backup before restoring
        try:
            with open(backup_path, "r") as f:
                backup_data = yaml.safe_load(f) or {}
            Config(**backup_data)  # Validate

            # Copy backup to config path
            shutil.copy2(backup_path, self.config_path)
            self._config = None  # Force reload
        except (yaml.YAMLError, ValidationError) as e:
            raise ValueError(f"Invalid backup file: {e}")

    def validate_config_dict(
        self, config_data: Dict[str, Any]
    ) -> tuple[bool, list[str]]:
        """Validate configuration dictionary without creating Config instance.

        Returns:
            Tuple of (is_valid, list_of_error_messages)
        """
        try:
            Config(**config_data)
            return True, []
        except ValidationError as e:
            error_messages = []
            for error in e.errors():
                field_path = " -> ".join(str(loc) for loc in error["loc"])
                error_messages.append(f"{field_path}: {error['msg']}")
            return False, error_messages
        except Exception as e:
            return False, [f"Configuration error: {e}"]

    def update_config_dict(self, updates: Dict[str, Any]) -> tuple[bool, list[str]]:
        """Update configuration with validation.

        Args:
            updates: Dictionary of configuration updates

        Returns:
            Tuple of (success, error_messages)
        """
        current_config = self.load_config()
        current_dict = current_config.model_dump()

        # Apply updates
        updated_dict = current_dict.copy()
        for key, value in updates.items():
            if "." in key:
                # Handle nested keys like 'agents.planning'
                keys = key.split(".")
                target = updated_dict
                for k in keys[:-1]:
                    target = target[k]
                target[keys[-1]] = value
            else:
                updated_dict[key] = value

        # Validate updated configuration
        is_valid, errors = self.validate_config_dict(updated_dict)
        if is_valid:
            self._config = Config(**updated_dict)
            self.save_config()
            return True, []
        else:
            return False, errors


# Global config manager instance
config_manager = ConfigManager()


def get_config() -> Config:
    """Get the global configuration."""
    return config_manager.load_config()


def get_model_for_agent(agent_type: str) -> str:
    """Get the configured model for a specific agent type."""
    return config_manager.get_model_for_agent(agent_type)
