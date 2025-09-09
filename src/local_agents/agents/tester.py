"""Testing agent for generating and running tests."""

import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..base import BaseAgent, TaskResult, handle_agent_execution


class TestingAgent(BaseAgent):
    """Agent specialized in creating and running tests."""

    def __init__(self, model: Optional[str] = None, **kwargs):
        super().__init__(
            agent_type="test",
            role="Senior QA Engineer and Test Developer",
            goal=(
                "Generate comprehensive test suites and run tests to ensure "
                "code quality and correctness"
            ),
            model=model,
            **kwargs,
        )

    @handle_agent_execution
    def execute(
        self, task: str, context: Optional[Dict[str, Any]] = None, stream: bool = False
    ) -> TaskResult:
        """Execute testing task."""
        prompt = self._build_testing_prompt(task, context)
        response = self._call_ollama(prompt, stream=stream)

        # If requested to run tests, do so
        if context.get("run_tests", False):
            test_output = self._run_tests(context)
            if test_output:
                response += f"\n\n## Test Execution Results\n\n{test_output}"

        return self._create_success_result(response, task, context)

    def _build_testing_prompt(self, task: str, context: Dict[str, Any]) -> str:
        """Build a structured prompt for testing tasks."""
        prompt_parts = [
            "# Test Generation Task",
            f"\n## Task Description\n{task}",
        ]

        if context.get("target_file"):
            prompt_parts.append(f"\n## Target File\n{context['target_file']}")

        if context.get("code_content"):
            prompt_parts.append(
                f"\n## Code to Test\n```\n{context['code_content']}\n```"
            )

        if context.get("target_directory"):
            prompt_parts.append(f"\n## Target Directory\n{context['target_directory']}")
            self._add_testing_context(prompt_parts, Path(context["target_directory"]))

        if context.get("framework"):
            prompt_parts.append(
                f"\n## Preferred Testing Framework\n{context['framework']}"
            )

        if context.get("target_description"):
            prompt_parts.append(
                f"\n## Target Description\n{context['target_description']}"
            )

        prompt_parts.extend(
            [
                "\n## Testing Instructions",
                """
Please generate comprehensive tests that:

1. **Test Coverage**
   - Cover all public methods and functions
   - Test both happy path and edge cases
   - Include error handling and boundary conditions
   - Test different input types and values

2. **Test Quality**
   - Use clear, descriptive test names
   - Follow testing best practices and conventions
   - Include appropriate setup and teardown
   - Use meaningful assertions with good error messages

3. **Test Organization**
   - Group related tests logically
   - Use appropriate test fixtures and helpers
   - Follow the testing framework's conventions
   - Include integration tests where appropriate

4. **Framework Selection**
   - Auto-detect the appropriate testing framework from project context
   - Use pytest for Python, Jest for JavaScript, etc.
   - Include necessary imports and setup code
   - Follow framework-specific patterns and conventions

5. **Mock and Stub Usage**
   - Mock external dependencies appropriately
   - Create test doubles for complex dependencies
   - Isolate units under test effectively
   - Use appropriate mocking frameworks

6. **Output Format**
   - Provide complete, runnable test code
   - Include file structure recommendations
   - Add explanations for complex test scenarios
   - Suggest test execution commands

Generate tests that are maintainable, reliable, and provide good coverage of
the code under test.
""",
            ]
        )

        return "\n".join(prompt_parts)

    def _add_testing_context(self, prompt_parts: List[str], directory: Path) -> None:
        """Add testing context information to the prompt."""
        if not directory.exists():
            return

        # Detect testing framework
        framework_files = {
            "pytest.ini": "pytest",
            "tox.ini": "pytest",
            "jest.config.js": "jest",
            "package.json": "npm test framework",
            "Cargo.toml": "Rust testing",
            "go.mod": "Go testing",
        }

        detected_frameworks = []
        for file_name, framework in framework_files.items():
            if (directory / file_name).exists():
                detected_frameworks.append(framework)

        if detected_frameworks:
            prompt_parts.append(
                f"\n## Detected Testing Frameworks\n{', '.join(detected_frameworks)}"
            )

        # Look for existing test directories
        test_dirs = []
        for test_dir in ["tests", "test", "__tests__", "spec"]:
            if (directory / test_dir).exists():
                test_dirs.append(test_dir)

        if test_dirs:
            prompt_parts.append(
                f"\n## Existing Test Directories\n{', '.join(test_dirs)}"
            )

    def _run_tests(self, context: Dict[str, Any]) -> Optional[str]:
        """Run tests and return output."""
        try:
            # Determine the appropriate test command
            test_commands = self._get_test_commands(context)

            for command in test_commands:
                try:
                    result = subprocess.run(
                        command,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=300,  # 5 minute timeout
                        cwd=context.get("target_directory", "."),
                    )

                    output = f"Command: {command}\n"
                    output += f"Exit Code: {result.returncode}\n\n"

                    if result.stdout:
                        output += f"STDOUT:\n{result.stdout}\n\n"

                    if result.stderr:
                        output += f"STDERR:\n{result.stderr}\n\n"

                    return output

                except subprocess.TimeoutExpired:
                    return f"Test command '{command}' timed out after 5 minutes"
                except Exception:
                    continue  # Try next command

            return "No suitable test command found or all commands failed"

        except Exception as e:
            return f"Error running tests: {e}"

    def _get_test_commands(self, context: Dict[str, Any]) -> List[str]:
        """Get possible test commands based on context."""
        commands = []

        target_dir = Path(context.get("target_directory", "."))

        # Python test commands
        if (target_dir / "pytest.ini").exists() or (
            target_dir / "pyproject.toml"
        ).exists():
            commands.append("python -m pytest -v")

        # Node.js test commands
        if (target_dir / "package.json").exists():
            commands.append("npm test")
            commands.append("yarn test")

        # Go test commands
        if (target_dir / "go.mod").exists():
            commands.append("go test ./...")

        # Rust test commands
        if (target_dir / "Cargo.toml").exists():
            commands.append("cargo test")

        # Generic Python commands
        commands.extend(
            [
                "python -m pytest",
                "python -m unittest discover",
                "python -m unittest",
            ]
        )

        return commands

    def generate_unit_tests(
        self,
        target_file: str,
        test_file: Optional[str] = None,
        framework: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> TaskResult:
        """Generate unit tests for a specific file."""
        context = context or {}
        context["target_file"] = target_file
        context["test_type"] = "unit"

        if Path(target_file).exists():
            context["code_content"] = Path(target_file).read_text()

        if test_file:
            context["output_file"] = test_file

        if framework:
            context["framework"] = framework

        task = f"Generate unit tests for {target_file}"
        return self.execute(task, context)

    def generate_integration_tests(
        self,
        description: str,
        components: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> TaskResult:
        """Generate integration tests."""
        context = context or {}
        context["test_type"] = "integration"
        context["components"] = components or []

        task = f"Generate integration tests for: {description}"
        return self.execute(task, context)

    def run_test_suite(
        self,
        test_path: Optional[str] = None,
        framework: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> TaskResult:
        """Run existing test suite."""
        context = context or {}
        context["run_tests"] = True
        context["test_path"] = test_path

        if framework:
            context["framework"] = framework

        task = f"Run test suite{f' at {test_path}' if test_path else ''}"
        return self.execute(task, context)

    def analyze_test_coverage(
        self, target_path: str, context: Optional[Dict[str, Any]] = None
    ) -> TaskResult:
        """Analyze test coverage for a given path."""
        context = context or {}
        context["target_path"] = target_path
        context["analysis_type"] = "coverage"

        # Try to run coverage analysis
        coverage_output = self._run_coverage_analysis(target_path)
        if coverage_output:
            context["coverage_report"] = coverage_output

        task = f"Analyze test coverage for {target_path}"
        return self.execute(task, context)

    def _run_coverage_analysis(self, target_path: str) -> Optional[str]:
        """Run coverage analysis and return results."""
        coverage_commands = [
            "python -m coverage run -m pytest && python -m coverage report",
            "python -m pytest --cov",
            "npm test -- --coverage",
            "yarn test --coverage",
        ]

        for command in coverage_commands:
            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=300,
                    cwd=target_path
                    if Path(target_path).is_dir()
                    else Path(target_path).parent,
                )

                if result.returncode == 0 and result.stdout:
                    return result.stdout

            except Exception:
                continue

        return None
