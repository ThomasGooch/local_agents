"""Custom exceptions for Local Agents."""


class LocalAgentsError(Exception):
    """Base exception for all Local Agents errors."""
    pass


class ModelNotAvailableError(LocalAgentsError):
    """Raised when a requested model is not available in Ollama."""
    pass


class ConfigurationError(LocalAgentsError):
    """Raised when there's an issue with configuration."""
    pass


class FileOperationError(LocalAgentsError):
    """Raised when file operations fail."""
    pass


class WorkflowError(LocalAgentsError):
    """Raised when workflow execution fails."""
    pass


class AgentExecutionError(LocalAgentsError):
    """Raised when agent execution fails."""
    pass