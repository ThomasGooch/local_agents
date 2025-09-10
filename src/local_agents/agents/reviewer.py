"""Review agent for analyzing and reviewing code quality."""

import json
import re
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..base import BaseAgent, TaskResult, handle_agent_execution
from ..file_manager import FileManager


class Severity(Enum):
    """Severity levels for static analysis findings."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class AnalysisFinding:
    """Represents a single static analysis finding."""

    tool: str
    file: str
    line: int
    column: int
    severity: Severity
    message: str
    rule: Optional[str] = None


class ReviewAgent(BaseAgent):
    """Agent specialized in code review and quality analysis."""

    def __init__(self, model: Optional[str] = None, ollama_client=None, **kwargs):
        super().__init__(
            agent_type="review",
            role="Senior Code Reviewer and Quality Analyst",
            goal=(
                "Analyze code quality, identify issues, and suggest improvements "
                "for maintainability, security, and performance"
            ),
            model=model,
            ollama_client=ollama_client,
            **kwargs,
        )
        self.file_manager = None

    @handle_agent_execution
    def execute(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        stream: bool = False,
    ) -> TaskResult:
        """Execute code review task."""
        # Initialize file manager if not already done
        if not self.file_manager:
            # Use output_directory from CLI first, fallback to directory
            working_dir = (
                context.get("output_directory") or context.get("directory", ".") if context else "."
            )
            # Resolve relative paths to current working directory like Planning Agent
            working_path = Path(working_dir).expanduser()
            if working_path.is_absolute():
                resolved_dir = working_path
            else:
                # Resolve relative to the current working directory where lagents was called
                resolved_dir = Path.cwd() / working_path

            self.file_manager = FileManager(str(resolved_dir))

        # Enhance context with automated analysis
        self._add_automated_analysis(context)

        prompt = self._build_review_prompt(task, context)
        response = self._call_ollama(prompt, stream=stream)

        # Create review document if enabled (default to True for feature-dev workflows)
        context_with_agent = context.copy() if context else {}
        context_with_agent["agent_type"] = "review"
        context_with_agent["task"] = task

        # Skip file creation during unit tests to improve performance
        if context.get("create_files", True) and not context.get("_test_mode", False):
            created_files = self.file_manager.extract_and_write_files_from_response(
                response, context_with_agent
            )
            if created_files:
                # Add file creation info to the output
                file_list = "\n".join(f"- {f}" for f in created_files)
                response += f"\n\n## Created Review Documents:\n{file_list}"

        return self._create_success_result(response, task, context)

    def _build_review_prompt(self, task: str, context: Dict[str, Any]) -> str:
        """Build a structured prompt for code review tasks."""
        prompt_parts = [
            "# Code Review Task",
            f"\n## Task Description\n{task}",
        ]

        if context.get("target_file"):
            prompt_parts.append(f"\n## Target File\n{context['target_file']}")

        if context.get("code_content"):
            prompt_parts.append(f"\n## Code to Review\n```\n{context['code_content']}\n```")

        if context.get("target_directory"):
            prompt_parts.append(f"\n## Target Directory\n{context['target_directory']}")

        if context.get("focus_area"):
            prompt_parts.append(f"\n## Review Focus\nFocus Area: {context['focus_area']}")

        if context.get("language"):
            prompt_parts.append(f"\n## Language\nLanguage: {context['language']}")

        if context.get("static_analysis"):
            prompt_parts.append(
                f"\n## Static Analysis Results\n```\n{context['static_analysis']}\n```"
            )

        if context.get("static_analysis_results"):
            analysis_text = "\n".join(
                [
                    f"**{tool}:**\n" + "\n".join(f"  - {issue}" for issue in issues)
                    for tool, issues in context["static_analysis_results"].items()
                ]
            )
            prompt_parts.append(f"\n## Static Analysis Results\n{analysis_text}")

        if context.get("previous_reviews"):
            reviews_text = "\n".join(f"- {review}" for review in context["previous_reviews"])
            prompt_parts.append(f"\n## Previous Reviews\n{reviews_text}")

        if context.get("changes_made"):
            prompt_parts.append(f"\n## Changes Made\n{context['changes_made']}")

        if context.get("complexity_metrics"):
            prompt_parts.append(f"\n## Complexity Metrics\n{context['complexity_metrics']}")

        if context.get("extract_metrics"):
            prompt_parts.append(
                "\n## Metrics Extraction\n"
                "Please extract and analyze code metrics including complexity, "
                "maintainability, and quality scores."
            )

        # Add review criteria section
        prompt_parts.append(
            "\n## Review Criteria\n"
            "Please focus on:\n"
            "• Security vulnerabilities\n"
            "• Code quality and best practices\n"
            "• Performance considerations\n"
            "• Maintainability and readability\n"
            "• Testing and error handling"
        )

        prompt_parts.extend(
            [
                "\n## Review Instructions",
                """
Please provide a comprehensive code review that covers:

1. **Code Quality & Style**
   - Adherence to coding standards and conventions
   - Code readability and maintainability
   - Naming conventions and clarity
   - Code organization and structure
   - DRY (Don't Repeat Yourself) principle compliance

2. **Functionality & Logic**
   - Correctness of implementation
   - Logic flow and algorithm efficiency
   - Edge case handling
   - Error handling and exception management
   - Input validation and sanitization

3. **Security Analysis**
   - Potential security vulnerabilities
   - Input validation and sanitization
   - Authentication and authorization issues
   - Data exposure risks
   - Injection attack vulnerabilities

4. **Performance Considerations**
   - Algorithm efficiency and complexity
   - Resource usage optimization
   - Memory leaks and resource cleanup
   - Database query efficiency
   - Caching opportunities

5. **Architecture & Design**
   - Design pattern usage appropriateness
   - Separation of concerns
   - Coupling and cohesion analysis
   - SOLID principles compliance
   - Scalability considerations

6. **Testing & Testability**
   - Code testability assessment
   - Missing test coverage areas
   - Test quality and completeness
   - Mock/stub usage appropriateness

7. **Documentation & Comments**
   - Code documentation completeness
   - Comment quality and necessity
   - API documentation adequacy
   - Inline explanation clarity

8. **Dependencies & Libraries**
   - Dependency appropriateness and necessity
   - Version compatibility issues
   - Security vulnerabilities in dependencies
   - License compatibility

## Review Format

Please structure your review as follows:

### Summary
Brief overall assessment of the code quality and main concerns.

### Issues Found
List specific issues with severity levels (Critical, High, Medium, Low):

#### Critical Issues
- [Description of critical issues requiring immediate attention]

#### High Priority Issues
- [Important issues that should be addressed soon]

#### Medium Priority Issues
- [Issues that should be addressed but are not urgent]

#### Low Priority Issues
- [Minor improvements and suggestions]

### Positive Aspects
- Highlight good practices and well-implemented features

### Recommendations
- Specific, actionable suggestions for improvement
- Best practice recommendations
- Refactoring suggestions where appropriate

### Security Considerations
- Specific security issues identified
- Security best practice recommendations

### Performance Notes
- Performance optimization opportunities
- Efficiency improvements

Be specific in your feedback, provide examples where helpful, and prioritize
issues by their potential impact.
""",
            ]
        )

        return "\n".join(prompt_parts)

    def review_for_security(
        self, code: str, context: Optional[Dict[str, Any]] = None
    ) -> TaskResult:
        """Review code specifically for security issues."""
        context = context or {}
        context["focus_area"] = "security"
        context["code_content"] = code
        task = "Review this code for security vulnerabilities and potential " "security issues"
        return self.execute(task, context)

    def review_for_performance(
        self, code: str, context: Optional[Dict[str, Any]] = None
    ) -> TaskResult:
        """Review code specifically for performance issues."""
        context = context or {}
        context["focus_area"] = "performance"
        context["code_content"] = code
        task = "Review this code for performance issues and optimization opportunities"
        return self.execute(task, context)

    def review_for_maintainability(
        self, code: str, context: Optional[Dict[str, Any]] = None
    ) -> TaskResult:
        """Review code specifically for maintainability issues."""
        context = context or {}
        context["focus_area"] = "maintainability"
        context["code_content"] = code
        task = "Review this code for maintainability and code quality issues"
        return self.execute(task, context)

    def comprehensive_review(
        self,
        code: str,
        target_file: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> TaskResult:
        """Perform a comprehensive code review."""
        context = context or {}
        context["code_content"] = code
        if target_file:
            context["target_file"] = target_file
        task = "Perform a comprehensive code review covering all aspects " "of code quality"
        return self.execute(task, context)

    def _add_automated_analysis(self, context: Dict[str, Any]) -> None:
        """Add automated analysis results to context."""
        target_file = context.get("target_file")
        target_directory = context.get("target_directory")

        if target_file and Path(target_file).exists():
            # Run static analysis on file
            context["static_analysis"] = self._run_static_analysis(target_file)
            context["complexity_metrics"] = self._analyze_complexity(target_file)
        elif target_directory and Path(target_directory).exists():
            # Run analysis on directory
            context["static_analysis"] = self._run_static_analysis(target_directory)
        elif context.get("enable_static_analysis") and context.get("code_content"):
            # Run static analysis when explicitly enabled even without file path
            # Create a temporary file for analysis
            import tempfile

            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
                tmp.write(context["code_content"])
                tmp_path = tmp.name
            context["static_analysis"] = self._run_static_analysis(tmp_path)
            # Clean up temp file
            Path(tmp_path).unlink(missing_ok=True)

    def _run_static_analysis(self, target: str, tool: Optional[str] = None) -> str:
        """Run static analysis tools on target with error handling."""
        # Handle test case where specific tool is requested
        if tool is not None:
            import os
            import subprocess

            if not os.path.exists(target):
                return "Tool not available"

            try:
                result = subprocess.run([tool, target], capture_output=True, text=True, timeout=30)
                return result.stdout if result.stdout else "Tool not available"
            except subprocess.TimeoutExpired:
                return "Analysis timeout - tool execution took too long"
            except (subprocess.CalledProcessError, FileNotFoundError):
                return "Tool not available"

        # Original implementation for automated analysis
        findings = []
        target_path = Path(target)

        try:
            # Python static analysis
            if target_path.suffix == ".py" or (
                target_path.is_dir() and self._contains_python_files(target_path)
            ):
                findings.extend(self._run_python_analysis_structured(target))

            # JavaScript/TypeScript analysis
            if target_path.suffix in [".js", ".ts", ".jsx", ".tsx"] or (
                target_path.is_dir() and self._contains_js_files(target_path)
            ):
                findings.extend(self._run_js_analysis_structured(target))

            if not findings:
                return "No static analysis tools available or no issues found"

            # Format findings by severity
            return self._format_analysis_findings(findings)

        except Exception as e:
            return f"Static analysis failed: {e}. Basic analysis will be performed " "instead."

    def _run_python_analysis_structured(self, target: str) -> List[AnalysisFinding]:
        """Run Python-specific static analysis with structured output."""
        findings = []

        # Try flake8 with structured output
        findings.extend(self._run_flake8(target))

        # Try pylint with structured output
        findings.extend(self._run_pylint(target))

        # Try mypy with structured output
        findings.extend(self._run_mypy(target))

        # Try bandit for security analysis
        findings.extend(self._run_bandit(target))

        return findings

    def _run_flake8(self, target: str) -> List[AnalysisFinding]:
        """Run flake8 with timeout and error handling."""
        findings = []
        try:
            result = subprocess.run(
                ["flake8", "--format=json", target],
                capture_output=True,
                text=True,
                timeout=30,  # Reduced timeout
            )
            if result.stdout:
                try:
                    data = json.loads(result.stdout)
                    for item in data:
                        findings.append(
                            AnalysisFinding(
                                tool="flake8",
                                file=item.get("filename", ""),
                                line=item.get("line_number", 0),
                                column=item.get("column_number", 0),
                                severity=self._map_flake8_severity(item.get("code", "")),
                                message=item.get("text", ""),
                                rule=item.get("code", ""),
                            )
                        )
                except json.JSONDecodeError:
                    # Fallback to text parsing
                    findings.extend(self._parse_flake8_text(result.stdout))
        except subprocess.TimeoutExpired:
            findings.append(
                AnalysisFinding(
                    tool="flake8",
                    file=target,
                    line=0,
                    column=0,
                    severity=Severity.HIGH,
                    message="Flake8 analysis timed out - code may be too complex",
                    rule="timeout",
                )
            )
        except FileNotFoundError:
            # Tool not available - silently continue
            pass
        except Exception as e:
            findings.append(
                AnalysisFinding(
                    tool="flake8",
                    file=target,
                    line=0,
                    column=0,
                    severity=Severity.MEDIUM,
                    message=f"Flake8 analysis failed: {e}",
                    rule="error",
                )
            )

        return findings

    def _run_pylint(self, target: str) -> List[AnalysisFinding]:
        """Run pylint with timeout and error handling."""
        findings = []
        try:
            result = subprocess.run(
                ["pylint", "--output-format=json", "--reports=n", target],
                capture_output=True,
                text=True,
                timeout=45,  # Slightly longer for pylint
            )
            if result.stdout:
                try:
                    data = json.loads(result.stdout)
                    for item in data:
                        findings.append(
                            AnalysisFinding(
                                tool="pylint",
                                file=item.get("path", ""),
                                line=item.get("line", 0),
                                column=item.get("column", 0),
                                severity=self._map_pylint_severity(item.get("type", "")),
                                message=item.get("message", ""),
                                rule=item.get("message-id", ""),
                            )
                        )
                except json.JSONDecodeError:
                    # Pylint sometimes outputs non-JSON, skip for now
                    pass
        except subprocess.TimeoutExpired:
            findings.append(
                AnalysisFinding(
                    tool="pylint",
                    file=target,
                    line=0,
                    column=0,
                    severity=Severity.HIGH,
                    message="Pylint analysis timed out - code may be too complex",
                    rule="timeout",
                )
            )
        except FileNotFoundError:
            pass
        except Exception as e:
            findings.append(
                AnalysisFinding(
                    tool="pylint",
                    file=target,
                    line=0,
                    column=0,
                    severity=Severity.MEDIUM,
                    message=f"Pylint analysis failed: {e}",
                    rule="error",
                )
            )

        return findings

    def _run_mypy(self, target: str) -> List[AnalysisFinding]:
        """Run mypy with timeout and error handling."""
        findings = []
        try:
            result = subprocess.run(
                ["mypy", "--no-error-summary", target],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.stdout:
                findings.extend(self._parse_mypy_output(result.stdout))
        except subprocess.TimeoutExpired:
            findings.append(
                AnalysisFinding(
                    tool="mypy",
                    file=target,
                    line=0,
                    column=0,
                    severity=Severity.HIGH,
                    message="MyPy analysis timed out - code may be too complex",
                    rule="timeout",
                )
            )
        except FileNotFoundError:
            pass
        except Exception as e:
            findings.append(
                AnalysisFinding(
                    tool="mypy",
                    file=target,
                    line=0,
                    column=0,
                    severity=Severity.MEDIUM,
                    message=f"MyPy analysis failed: {e}",
                    rule="error",
                )
            )

        return findings

    def _run_bandit(self, target: str) -> List[AnalysisFinding]:
        """Run bandit security analysis with timeout and error handling."""
        findings = []
        try:
            result = subprocess.run(
                ["bandit", "-f", "json", "-r", target],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.stdout:
                try:
                    data = json.loads(result.stdout)
                    for item in data.get("results", []):
                        findings.append(
                            AnalysisFinding(
                                tool="bandit",
                                file=item.get("filename", ""),
                                line=item.get("line_number", 0),
                                column=0,
                                severity=self._map_bandit_severity(item.get("issue_severity", "")),
                                message=item.get("issue_text", ""),
                                rule=item.get("test_id", ""),
                            )
                        )
                except json.JSONDecodeError:
                    pass
        except subprocess.TimeoutExpired:
            findings.append(
                AnalysisFinding(
                    tool="bandit",
                    file=target,
                    line=0,
                    column=0,
                    severity=Severity.HIGH,
                    message="Bandit security analysis timed out",
                    rule="timeout",
                )
            )
        except FileNotFoundError:
            pass
        except Exception:
            pass  # Silently continue for security tool

        return findings

    def _run_python_analysis(self, target: str) -> List[str]:
        """Legacy method - kept for backward compatibility."""
        findings = self._run_python_analysis_structured(target)
        if not findings:
            return ["No Python static analysis tools available"]

        return [self._format_analysis_findings(findings)]

    def _run_js_analysis_structured(self, target: str) -> List[AnalysisFinding]:
        """Run JavaScript/TypeScript static analysis with structured output."""
        findings = []

        # Try ESLint with structured output
        findings.extend(self._run_eslint(target))

        return findings

    def _run_eslint(self, target: str) -> List[AnalysisFinding]:
        """Run ESLint with timeout and error handling."""
        findings = []
        try:
            result = subprocess.run(
                ["eslint", "--format=json", target],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.stdout:
                try:
                    data = json.loads(result.stdout)
                    for file_result in data:
                        for message in file_result.get("messages", []):
                            findings.append(
                                AnalysisFinding(
                                    tool="eslint",
                                    file=file_result.get("filePath", ""),
                                    line=message.get("line", 0),
                                    column=message.get("column", 0),
                                    severity=self._map_eslint_severity(message.get("severity", 1)),
                                    message=message.get("message", ""),
                                    rule=message.get("ruleId", ""),
                                )
                            )
                except json.JSONDecodeError:
                    # Fallback to text parsing
                    pass
        except subprocess.TimeoutExpired:
            findings.append(
                AnalysisFinding(
                    tool="eslint",
                    file=target,
                    line=0,
                    column=0,
                    severity=Severity.HIGH,
                    message="ESLint analysis timed out - code may be too complex",
                    rule="timeout",
                )
            )
        except FileNotFoundError:
            pass
        except Exception as e:
            findings.append(
                AnalysisFinding(
                    tool="eslint",
                    file=target,
                    line=0,
                    column=0,
                    severity=Severity.MEDIUM,
                    message=f"ESLint analysis failed: {e}",
                    rule="error",
                )
            )

        return findings

    def _run_js_analysis(self, target: str) -> List[str]:
        """Legacy method - kept for backward compatibility."""
        findings = self._run_js_analysis_structured(target)
        if not findings:
            return ["No JavaScript/TypeScript static analysis tools available"]

        return [self._format_analysis_findings(findings)]

    def _analyze_complexity(self, target: str) -> str:
        """Analyze code complexity metrics."""
        target_path = Path(target)

        if target_path.suffix == ".py":
            return self._analyze_python_complexity(target)

        return "Complexity analysis not available for this file type"

    def _analyze_python_complexity(self, target: str) -> str:
        """Analyze Python code complexity."""
        try:
            # Try radon for complexity metrics
            result = subprocess.run(
                ["radon", "cc", target, "-s"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.stdout:
                return f"Cyclomatic Complexity:\n{result.stdout}"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Fallback: simple complexity analysis
        try:
            with open(target, "r") as f:
                content = f.read()
                lines = len(content.split("\n"))
                functions = len(re.findall(r"^def ", content, re.MULTILINE))
                classes = len(re.findall(r"^class ", content, re.MULTILINE))

                return (
                    f"Basic Metrics:\n- Lines: {lines}\n- Functions: {functions}\n"
                    f"- Classes: {classes}"
                )
        except Exception:
            return "Could not analyze complexity"

    def _contains_python_files(self, directory: Path) -> bool:
        """Check if directory contains Python files."""
        return any(file.suffix == ".py" for file in directory.rglob("*.py"))

    def _contains_js_files(self, directory: Path) -> bool:
        """Check if directory contains JavaScript/TypeScript files."""
        extensions = [".js", ".ts", ".jsx", ".tsx"]
        return any(
            file.suffix in extensions for file in directory.rglob("*") if file.suffix in extensions
        )

    def review_security(self, target: str, context: Optional[Dict[str, Any]] = None) -> TaskResult:
        """Focus review on security aspects."""
        context = context or {}
        context["focus_area"] = "security"

        if Path(target).exists():
            if Path(target).is_file():
                context["target_file"] = target
                context["code_content"] = Path(target).read_text()
            else:
                context["target_directory"] = target

        task = f"Security-focused code review of {target}"
        return self.execute(task, context)

    def review_performance(
        self, target: str, context: Optional[Dict[str, Any]] = None
    ) -> TaskResult:
        """Focus review on performance aspects."""
        context = context or {}
        context["focus_area"] = "performance"

        if Path(target).exists():
            if Path(target).is_file():
                context["target_file"] = target
                context["code_content"] = Path(target).read_text()
            else:
                context["target_directory"] = target

        task = f"Performance-focused code review of {target}"
        return self.execute(task, context)

    def review_architecture(
        self, target: str, context: Optional[Dict[str, Any]] = None
    ) -> TaskResult:
        """Focus review on architecture and design."""
        context = context or {}
        context["focus_area"] = "architecture"

        if Path(target).exists():
            context["target_directory"] = target

        task = f"Architecture review of {target}"
        return self.execute(task, context)

    def review_pull_request(
        self, diff_content: str, context: Optional[Dict[str, Any]] = None
    ) -> TaskResult:
        """Review a pull request diff."""
        context = context or {}
        context["diff_content"] = diff_content
        context["review_type"] = "pull_request"

        task = "Review pull request changes"
        return self.execute(task, context)

    # Severity mapping methods
    def _map_flake8_severity(self, code: str) -> Severity:
        """Map flake8 codes to severity levels."""
        if code.startswith("E9") or code.startswith("F"):  # Syntax errors, undefined names
            return Severity.CRITICAL
        elif code.startswith("E") and code[1] in [
            "1",
            "2",
            "3",
        ]:  # Indentation, whitespace, blank line
            return Severity.LOW
        elif code.startswith("E"):  # Other style errors
            return Severity.MEDIUM
        elif code.startswith("W"):  # Warnings
            return Severity.LOW
        else:
            return Severity.MEDIUM

    def _map_pylint_severity(self, type_: str) -> Severity:
        """Map pylint message types to severity levels."""
        mapping = {
            "error": Severity.CRITICAL,
            "fatal": Severity.CRITICAL,
            "warning": Severity.MEDIUM,
            "refactor": Severity.LOW,
            "convention": Severity.LOW,
            "info": Severity.INFO,
        }
        return mapping.get(type_.lower(), Severity.MEDIUM)

    def _map_bandit_severity(self, severity: str) -> Severity:
        """Map bandit severity levels to our severity levels."""
        mapping = {
            "high": Severity.CRITICAL,
            "medium": Severity.HIGH,
            "low": Severity.MEDIUM,
        }
        return mapping.get(severity.lower(), Severity.MEDIUM)

    def _map_eslint_severity(self, severity: int) -> Severity:
        """Map ESLint severity levels to our severity levels."""
        if severity >= 2:
            return Severity.HIGH
        elif severity == 1:
            return Severity.MEDIUM
        else:
            return Severity.LOW

    # Parsing methods
    def _parse_flake8_text(self, output: str) -> List[AnalysisFinding]:
        """Parse flake8 text output as fallback."""
        findings = []
        for line in output.strip().split("\n"):
            if ":" in line:
                parts = line.split(":", 3)
                if len(parts) >= 4:
                    file_path, line_num, col, message = parts
                    # Extract error code from message
                    code_match = re.search(r"([EWF]\d+)", message)
                    code = code_match.group(1) if code_match else ""

                    findings.append(
                        AnalysisFinding(
                            tool="flake8",
                            file=file_path,
                            line=int(line_num) if line_num.isdigit() else 0,
                            column=int(col) if col.isdigit() else 0,
                            severity=self._map_flake8_severity(code),
                            message=message.strip(),
                            rule=code,
                        )
                    )
        return findings

    def _parse_mypy_output(self, output: str) -> List[AnalysisFinding]:
        """Parse MyPy output."""
        findings = []
        for line in output.strip().split("\n"):
            if ":" in line and " error:" in line:
                # Format: file.py:line: error: message
                parts = line.split(":", 2)
                if len(parts) >= 3:
                    file_path = parts[0]
                    line_part = parts[1]
                    message_part = parts[2]

                    line_num = int(line_part) if line_part.isdigit() else 0

                    findings.append(
                        AnalysisFinding(
                            tool="mypy",
                            file=file_path,
                            line=line_num,
                            column=0,
                            severity=Severity.HIGH if "error" in message_part else Severity.MEDIUM,
                            message=message_part.strip(),
                            rule="type-check",
                        )
                    )
        return findings

    def _format_analysis_findings(self, findings: List[AnalysisFinding]) -> str:
        """Format analysis findings by severity."""
        if not findings:
            return "No issues found"

        # Group by severity
        by_severity = {
            Severity.CRITICAL: [],
            Severity.HIGH: [],
            Severity.MEDIUM: [],
            Severity.LOW: [],
            Severity.INFO: [],
        }

        for finding in findings:
            by_severity[finding.severity].append(finding)

        output_parts = []

        for severity in [
            Severity.CRITICAL,
            Severity.HIGH,
            Severity.MEDIUM,
            Severity.LOW,
            Severity.INFO,
        ]:
            severity_findings = by_severity[severity]
            if severity_findings:
                output_parts.append(
                    f"\n{severity.value.upper()} Issues ({len(severity_findings)}):"
                )
                for finding in severity_findings:
                    location = f"{finding.file}:{finding.line}"
                    if finding.column:
                        location += f":{finding.column}"
                    rule_info = f" [{finding.rule}]" if finding.rule else ""
                    output_parts.append(
                        f"  {finding.tool}: {location} - {finding.message}{rule_info}"
                    )

        return "\n".join(output_parts)
