"""Pytest configuration and shared fixtures."""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from local_agents.agents.planner import PlanningAgent
from local_agents.base import TaskResult
from local_agents.config import Config
from local_agents.ollama_client import OllamaClient


@pytest.fixture
def mock_ollama_client():
    """Create a mock Ollama client for testing."""
    client = Mock(spec=OllamaClient)
    client.is_model_available.return_value = True
    client.pull_model.return_value = True
    client.generate.return_value = "Mock response"
    client.chat.return_value = "Mock chat response"
    client.list_models.return_value = ["llama3.1:8b", "codellama:7b"]
    return client


@pytest.fixture
def test_config():
    """Create a test configuration."""
    return Config(
        default_model="test:model",
        ollama_host="http://localhost:11434",
        temperature=0.7,
        max_tokens=2048,
    )


@pytest.fixture
def temp_directory():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_python_file(temp_directory):
    """Create a sample Python file for testing."""
    file_path = temp_directory / "sample.py"
    content = '''"""Sample Python module for testing."""

def calculate_sum(a, b):
    """Calculate the sum of two numbers."""
    return a + b


class Calculator:
    """A simple calculator class."""

    def __init__(self):
        self.history = []

    def add(self, a, b):
        """Add two numbers and store in history."""
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result

    def get_history(self):
        """Get calculation history."""
        return self.history
'''
    file_path.write_text(content)
    return file_path


@pytest.fixture
def sample_javascript_file(temp_directory):
    """Create a sample JavaScript file for testing."""
    file_path = temp_directory / "sample.js"
    content = """// Sample JavaScript module for testing

function calculateSum(a, b) {
    return a + b;
}

class Calculator {
    constructor() {
        this.history = [];
    }

    add(a, b) {
        const result = a + b;
        this.history.push(`${a} + ${b} = ${result}`);
        return result;
    }

    getHistory() {
        return this.history;
    }
}

module.exports = { calculateSum, Calculator };
"""
    file_path.write_text(content)
    return file_path


@pytest.fixture
def sample_project_directory(temp_directory):
    """Create a sample project directory structure."""
    project_dir = temp_directory / "sample_project"
    project_dir.mkdir()

    # Create package.json
    (project_dir / "package.json").write_text(
        """{
    "name": "sample-project",
    "version": "1.0.0",
    "scripts": {
        "test": "jest",
        "lint": "eslint ."
    },
    "devDependencies": {
        "jest": "^28.0.0",
        "eslint": "^8.0.0"
    }
}"""
    )

    # Create source directory
    src_dir = project_dir / "src"
    src_dir.mkdir()

    (src_dir / "index.js").write_text(
        """const { Calculator } = require('./calculator');

const calc = new Calculator();
console.log(calc.add(2, 3));
"""
    )

    (src_dir / "calculator.js").write_text(
        """class Calculator {
    constructor() {
        this.history = [];
    }

    add(a, b) {
        const result = a + b;
        this.history.push(`${a} + ${b} = ${result}`);
        return result;
    }
}

module.exports = { Calculator };
"""
    )

    # Create tests directory
    tests_dir = project_dir / "__tests__"
    tests_dir.mkdir()

    (tests_dir / "calculator.test.js").write_text(
        """const { Calculator } = require('../src/calculator');

describe('Calculator', () => {
    test('should add two numbers', () => {
        const calc = new Calculator();
        expect(calc.add(2, 3)).toBe(5);
    });
});
"""
    )

    return project_dir


@pytest.fixture
def sample_python_project(temp_directory):
    """Create a sample Python project directory structure."""
    project_dir = temp_directory / "python_project"
    project_dir.mkdir()

    # Create pyproject.toml
    (project_dir / "pyproject.toml").write_text(
        """[build-system]
requires = ["setuptools", "wheel"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.black]
line-length = 88
"""
    )

    # Create source directory
    src_dir = project_dir / "src" / "mypackage"
    src_dir.mkdir(parents=True)

    (src_dir / "__init__.py").write_text("")

    (src_dir / "calculator.py").write_text(
        '''"""Calculator module."""

class Calculator:
    """A simple calculator."""

    def __init__(self):
        self.history = []

    def add(self, a: int, b: int) -> int:
        """Add two numbers."""
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result

    def get_history(self):
        """Get calculation history."""
        return self.history
'''
    )

    # Create tests directory
    tests_dir = project_dir / "tests"
    tests_dir.mkdir()

    (tests_dir / "__init__.py").write_text("")

    (tests_dir / "test_calculator.py").write_text(
        '''"""Tests for calculator module."""

import pytest
from src.mypackage.calculator import Calculator


def test_calculator_add():
    """Test calculator addition."""
    calc = Calculator()
    result = calc.add(2, 3)
    assert result == 5
    assert len(calc.get_history()) == 1
'''
    )

    return project_dir


@pytest.fixture
def mock_ollama_responses():
    """Provide realistic AI model responses for different agent types."""
    return {
        "plan": """# Implementation Plan

## Requirements Analysis
- Analyze user requirements and constraints
- Identify key functional and non-functional requirements
- Define success criteria and acceptance tests

## Architecture Design
- Design system architecture and component structure
- Define data models and interfaces
- Plan security and performance considerations

## Implementation Strategy
1. **Phase 1: Core Infrastructure**
   - Set up project structure and dependencies
   - Implement base classes and utilities
   - Create configuration management

2. **Phase 2: Business Logic**
   - Implement main functionality
   - Add input validation and error handling
   - Create data persistence layer

3. **Phase 3: Integration & Testing**
   - Integrate all components
   - Comprehensive testing (unit, integration, e2e)
   - Performance optimization

## Risk Assessment
- Technical risks and mitigation strategies
- Timeline and resource considerations
- Dependencies and external factors""",
        "code": '''```python
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class User:
    """User data model."""
    id: int
    username: str
    email: str
    created_at: datetime
    is_active: bool = True

class UserManager:
    """Manages user operations with proper error handling."""

    def __init__(self):
        self.users: Dict[int, User] = {}
        self._next_id = 1
        logger.info("UserManager initialized")

    def create_user(self, username: str, email: str) -> User:
        """Create a new user with validation."""
        if not username or len(username) < 3:
            raise ValueError("Username must be at least 3 characters")

        if not email or '@' not in email:
            raise ValueError("Invalid email format")

        user = User(
            id=self._next_id,
            username=username,
            email=email,
            created_at=datetime.now()
        )

        self.users[self._next_id] = user
        self._next_id += 1

        logger.info(f"Created user: {username} (ID: {user.id})")
        return user
```''',
        "test": '''```python
import pytest
from datetime import datetime
from unittest.mock import patch

from mymodule import User, UserManager

class TestUserManager:
    """Test UserManager class."""

    @pytest.fixture
    def user_manager(self):
        """Create a UserManager instance for testing."""
        return UserManager()

    def test_create_user_success(self, user_manager):
        """Test successful user creation."""
        user = user_manager.create_user("alice", "alice@example.com")

        assert user.id == 1
        assert user.username == "alice"
        assert user.email == "alice@example.com"
        assert user.is_active is True
        assert isinstance(user.created_at, datetime)

        # Verify user is stored
        assert len(user_manager.users) == 1
        assert user_manager.users[1] == user
```''',
        "review": """# Code Review Report

## Summary
This code demonstrates good practices but has areas for improvement.

## Positive Aspects
✅ **Type Hints**: Comprehensive use of type hints
✅ **Error Handling**: Good use of specific exceptions
✅ **Documentation**: Well-documented functions

## Issues Found

### High Priority 🔴
1. **Thread Safety**
   - **Issue**: Not thread-safe for concurrent access
   - **Recommendation**: Add threading locks

### Medium Priority 🟡
1. **Email Validation**
   - **Issue**: Basic validation (only checks '@')
   - **Recommendation**: Use proper email validation

## Overall Rating: B+ (Good)""",
    }


@pytest.fixture
def comprehensive_mock_agents():
    """Create comprehensive mock agents for testing workflows."""
    agents = {}

    # Create mock planning agent
    mock_planner = Mock(spec=PlanningAgent)
    mock_planner.agent_type = "plan"
    mock_planner.execute.return_value = TaskResult(
        success=True,
        output=(
            "# Implementation Plan\n\n## Phase 1: Core Setup\n"
            "- Set up project structure"
        ),
        agent_type="plan",
        task="Create implementation plan",
        context={},
    )
    agents["planner"] = mock_planner

    return agents
