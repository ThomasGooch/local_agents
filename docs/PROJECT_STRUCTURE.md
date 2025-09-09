# Local Agents - Project Structure

This document describes the organized project structure for Local Agents.

## Directory Organization

```
local-agents/
├── README.md                     # Main project documentation
├── CLAUDE.md                     # Claude-specific project instructions  
├── pyproject.toml               # Poetry configuration and dependencies
├── poetry.lock                  # Locked dependency versions
├── pytest.ini                  # pytest configuration
├── run_tests.py                 # Advanced test runner with multiple modes
├── install.sh                   # Global installation script
├──── 
├── src/                         # Source code
│   └── local_agents/
│       ├── __init__.py          # Package initialization
│       ├── __main__.py          # CLI entry point (python -m local_agents)
│       ├── base.py              # Base agent classes and decorators
│       ├── config.py            # Configuration management with Pydantic
│       ├── cli.py               # Click-based CLI interface  
│       ├── exceptions.py        # Custom exception types
│       ├── ollama_client.py     # Ollama API integration
│       ├── file_manager.py      # File creation and management utilities
│       ├── performance.py       # Performance monitoring and caching
│       ├── hardware.py          # Hardware optimization profiles
│       ├── benchmarks.py        # Performance benchmarking utilities
│       ├──
│       ├── agents/              # Individual agent implementations
│       │   ├── __init__.py      # Agent package exports
│       │   ├── planner.py       # Planning & architecture agent
│       │   ├── coder.py         # Code generation agent with file creation
│       │   ├── tester.py        # Testing agent with framework detection
│       │   └── reviewer.py      # Code review agent with static analysis
│       └──
│       └── workflows/           # Multi-agent workflow orchestration
│           ├── __init__.py      # Workflow package exports
│           └── orchestrator.py  # Workflow coordination and execution
│
├── tests/                       # Comprehensive test suite (1500+ tests)
│   ├── conftest.py             # Shared fixtures and test configuration
│   ├── unit/                   # Unit tests for individual components
│   │   ├── test_base.py        # Base agent and decorator tests
│   │   ├── test_config.py      # Configuration validation tests
│   │   ├── test_orchestrator.py # Workflow orchestrator tests (500+ lines)
│   │   ├── test_hardware.py    # Hardware optimization tests
│   │   ├── test_performance.py # Performance monitoring tests
│   │   └── test_agents/        # Individual agent test suites
│   │       ├── test_planner.py # Planning agent tests
│   │       ├── test_coder.py   # Coding agent tests (400+ lines)
│   │       ├── test_tester.py  # Testing agent tests (350+ lines)
│   │       └── test_reviewer.py # Review agent tests (450+ lines)
│   ├──
│   ├── integration/            # End-to-end integration tests
│   │   ├── test_cli_integration.py    # Complete CLI functionality tests
│   │   ├── test_workflows.py          # Workflow execution scenarios  
│   │   ├── test_agent_integration.py  # Agent chaining tests
│   │   └── test_performance_integration.py # Performance integration tests
│   └──
│   └── performance/            # Performance benchmarking suite
│       └── test_benchmarks.py  # Agent and workflow performance tests
│
└── docs/                       # Project documentation
    ├── PROJECT_STRUCTURE.md    # This file
    ├── CLI_IMPLEMENTATION_REPORT.md     # CLI development report
    ├── IMPLEMENTATION_SUMMARY.md       # System implementation overview
    ├── MACBOOK_PRO_OPTIMIZATION.md     # Hardware-specific optimization guide
    ├── TEST_RESULTS_SUMMARY.md         # Testing strategy and results
    ├── next_steps.md                   # Development roadmap
    └── plan_phase5.md                  # Phase 5 development plan
```

## Key Components

### Core Infrastructure
- **Base Agent System** (`base.py`): Common functionality, error handling, decorators
- **Configuration Management** (`config.py`): Pydantic-based validation and settings
- **CLI Interface** (`cli.py`): Rich terminal interface with Click framework
- **File Management** (`file_manager.py`): Smart file creation and project structure generation
- **Performance System** (`performance.py`): Monitoring, caching, and optimization

### Agent System
- **PlanningAgent**: Architecture and planning with specialized prompts
- **CodingAgent**: Code generation with file creation and project structure support
- **TestingAgent**: Test generation with framework detection and execution
- **ReviewAgent**: Code review with static analysis integration (flake8, pylint, mypy, bandit)

### Workflow Orchestration
- **Predefined Workflows**: feature-dev, bug-fix, code-review, refactor
- **Custom Workflows**: User-configurable YAML workflow definitions
- **Context Management**: State passing and dependency handling between agents
- **Rich Output**: Beautiful terminal displays with progress tracking

### Testing Infrastructure
- **1500+ Comprehensive Tests**: Unit, integration, and performance test suites
- **Multi-OS CI/CD**: Linux, macOS, Windows testing across Python 3.9-3.12
- **Performance Benchmarking**: Automated performance validation and regression detection
- **Realistic Mock Data**: Comprehensive AI model responses for testing scenarios

## File Creation System

The project includes a sophisticated file creation system that:
- Extracts files from agent responses using multiple patterns
- Supports .NET, Python, JavaScript, and other language project structures
- Creates proper directory hierarchies automatically
- Validates file paths and content safely
- Integrates seamlessly with all workflow types

## Development Standards

### Code Quality
- **PEP 8** formatting with Black
- **Type coverage** > 90% with mypy
- **Test coverage** > 80% with pytest-cov
- **Import organization** with isort
- **Security scanning** with bandit

### Performance Requirements
- **Individual agents**: < 60 seconds execution time
- **Complete workflows**: < 120 seconds total time  
- **Memory usage**: < 4GB peak during execution
- **MacBook Pro Intel i7 16GB**: Optimized configuration included

### Documentation Standards
- **Comprehensive README** with examples and setup instructions
- **Inline documentation** for all public APIs with docstrings
- **CLI help text** for all commands with usage examples
- **Configuration documentation** with validation explanations

## Installation and Usage

The project supports multiple installation methods:
- **Global installation**: `./install.sh` for system-wide access
- **Development setup**: `poetry install` for local development
- **CLI access**: `python -m local_agents` or `lagents` (after global install)

## Quality Assurance

The project maintains high quality through:
- **100% test pass rate** across all test suites
- **Multi-language support** with comprehensive project templates
- **Error recovery** with graceful degradation and user guidance
- **Privacy protection** with local-only AI model execution
- **Performance monitoring** with automatic optimization recommendations

This structure provides a clean, maintainable, and scalable foundation for the Local Agents project while ensuring excellent developer experience and production reliability.