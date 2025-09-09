"""Coding agent for generating and modifying code."""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..base import BaseAgent, TaskResult, handle_agent_execution
from ..file_manager import FileManager


class CodingAgent(BaseAgent):
    """Agent specialized in generating and modifying code."""

    def __init__(self, model: Optional[str] = None, **kwargs):
        super().__init__(
            agent_type="code",
            role="Senior Software Engineer and Code Generator",
            goal=(
                "Generate high-quality, maintainable code that follows best "
                "practices and integrates well with existing codebases"
            ),
            model=model,
            **kwargs,
        )
        self.file_manager = None

    @handle_agent_execution
    def execute(
        self, task: str, context: Optional[Dict[str, Any]] = None, stream: bool = False
    ) -> TaskResult:
        """Execute coding task."""
        # Initialize file manager if not already done
        if not self.file_manager:
            # Use output_directory from CLI first, then fallback to directory or current dir
            working_dir = (
                context.get("output_directory") or 
                context.get("directory", ".") if context else "."
            )
            self.file_manager = FileManager(working_dir)

        prompt = self._build_coding_prompt(task, context)
        response = self._call_ollama(prompt, stream=stream)

        # Post-process response to extract code if needed
        processed_output = self._post_process_code_response(response, context)

        # Create files if enabled (default to True for feature-dev workflows)
        context_with_agent = context.copy() if context else {}
        context_with_agent["agent_type"] = "code"
        context_with_agent["task"] = task

        # Skip file creation during unit tests to improve performance
        if context.get("create_files", True) and not context.get("_test_mode", False):
            created_files = self.file_manager.extract_and_write_files_from_response(
                processed_output, context_with_agent
            )
            if created_files:
                # Add file creation info to the output
                file_list = "\n".join(f"- {f}" for f in created_files)
                processed_output += f"\n\n## Created Files:\n{file_list}"

        return self._create_success_result(processed_output, task, context)

    def _build_coding_prompt(self, task: str, context: Dict[str, Any]) -> str:
        """Build a structured prompt for coding tasks."""
        prompt_parts = [
            "# Code Generation Task",
            f"\n## Task Description\n{task}",
        ]

        # Add language specification if provided
        if context.get("language"):
            prompt_parts.append(f"\n## Language\nLanguage: {context['language']}")

        if context.get("target_file"):
            prompt_parts.append(f"\n## Target File\n{context['target_file']}")

        if context.get("existing_code"):
            prompt_parts.append(f"\n## Existing Code\n```\n{context['existing_code']}\n```")

        if context.get("specification"):
            prompt_parts.append(f"\n## Detailed Specification\n{context['specification']}")

        if context.get("implementation_plan"):
            prompt_parts.append(f"\n## Implementation Plan\n{context['implementation_plan']}")

        if context.get("requirements"):
            prompt_parts.append(f"\n## Requirements\n{context['requirements']}")

        if context.get("style_guide"):
            prompt_parts.append(f"\n## Style Guide\n{context['style_guide']}")

        if context.get("docstring_style"):
            prompt_parts.append(f"\n## Docstring Style\n{context['docstring_style']}")

        if context.get("review_feedback"):
            prompt_parts.append(f"\n## Review Feedback\n{context['review_feedback']}")

        if context.get("framework"):
            prompt_parts.append(f"\n## Framework\n{context['framework']}")

        if context.get("database"):
            prompt_parts.append(f"\n## Database\n{context['database']}")

        if context.get("buggy_code"):
            prompt_parts.append(f"\n## Buggy Code\n```\n{context['buggy_code']}\n```")

        if context.get("error_message"):
            prompt_parts.append(f"\n## Error Message\n{context['error_message']}")

        if context.get("code_to_refactor"):
            prompt_parts.append(f"\n## Code to Refactor\n```\n{context['code_to_refactor']}\n```")

        if context.get("target_structure"):
            prompt_parts.append(f"\n## Target Structure\n{context['target_structure']}")

        if context.get("file_content"):
            prompt_parts.append(f"\n## Context File Content\n```\n{context['file_content']}\n```")

        # Use output_directory or directory for context
        work_dir = context.get("output_directory") or context.get("directory")
        if work_dir:
            prompt_parts.append(f"\n## Working Directory\n{work_dir}")
            # Try to infer project structure and language
            self._add_project_context(prompt_parts, Path(work_dir))

        prompt_parts.extend(
            [
                "\n## Coding Instructions",
                """
Please generate high-quality code that:

1. **Follows Best Practices**
   - Uses appropriate design patterns
   - Has clear, descriptive naming conventions
   - Includes proper error handling
   - Is well-structured and maintainable

2. **Code Quality**
   - Write clean, readable code
   - Include appropriate comments for complex logic
   - Follow language-specific conventions and idioms
   - Use consistent formatting and style

3. **Integration**
   - Consider existing codebase patterns and conventions
   - Ensure compatibility with existing code
   - Use appropriate imports and dependencies
   - Follow project structure and organization

4. **Functionality**
   - Implement the requested functionality completely
   - Handle edge cases and error conditions
   - Consider security implications
   - Optimize for readability and maintainability

5. **Output Format**
   - Provide complete, working code in properly formatted code blocks
   - Include any necessary imports and dependencies
   - Add brief explanations for complex logic
   - Use clear file path indicators like "File: Controllers/WeatherController.cs"

6. **File Organization**
   - Create a complete project structure when building applications
   - Organize code into appropriate directories (Controllers, Models, Services, etc.)
   - Include configuration files (appsettings.json, .csproj files, etc.)
   - Ensure files follow naming conventions for the target language/framework

Please provide the complete code implementation with proper file paths and 
structure. Format each file clearly with "File: [filepath]" followed by the code block.
""",
            ]
        )

        return "\n".join(prompt_parts)

    def _add_project_context(self, prompt_parts: List[str], directory: Path) -> None:
        """Add project context information to the prompt."""
        if not directory.exists():
            return

        # Look for common project files to infer language and framework
        project_files = []
        for file_pattern in [
            "package.json",
            "requirements.txt",
            "Cargo.toml",
            "go.mod",
            "pom.xml",
            "build.gradle",
        ]:
            if (directory / file_pattern).exists():
                project_files.append(file_pattern)

        if project_files:
            prompt_parts.append(f"\n## Detected Project Files\n{', '.join(project_files)}")

        # Look for common directory structures
        common_dirs = ["src", "lib", "app", "components", "utils", "tests", "test"]
        found_dirs = [d for d in common_dirs if (directory / d).exists()]

        if found_dirs:
            prompt_parts.append(
                f"\n## Project Structure\nDetected directories: {', '.join(found_dirs)}"
            )

    def _post_process_code_response(self, response: str, context: Dict[str, Any]) -> str:
        """Post-process the code response to extract and format code blocks."""
        # If the response contains code blocks, extract the main one
        code_blocks = re.findall(r"```(\w*)\n(.*?)\n```", response, re.DOTALL)

        if code_blocks and len(code_blocks) == 1:
            # If there's exactly one code block, return just the code
            _, code = code_blocks[0]
            return code.strip()
        elif len(code_blocks) > 1:
            # Multiple code blocks - return the full response
            return response
        else:
            # No code blocks found - return full response
            return response

    def generate_function(
        self,
        function_spec: str,
        language: str = "python",
        context: Optional[Dict[str, Any]] = None,
    ) -> TaskResult:
        """Generate a specific function."""
        context = context or {}
        context["language"] = language

        task = f"Generate function: {function_spec}"
        return self.execute(task, context)

    def modify_code(
        self,
        file_path: str,
        modification_description: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> TaskResult:
        """Modify existing code in a file."""
        context = context or {}
        context["target_file"] = file_path

        if Path(file_path).exists():
            context["existing_code"] = Path(file_path).read_text()

        task = f"Modify the code in {file_path}: {modification_description}"
        return self.execute(task, context)

    def generate_class(
        self,
        class_spec: str,
        language: str = "python",
        context: Optional[Dict[str, Any]] = None,
    ) -> TaskResult:
        """Generate a specific class."""
        context = context or {}
        context["language"] = language

        task = f"Generate class: {class_spec}"
        return self.execute(task, context)

    def create_class(
        self,
        class_name: str,
        description: str,
        methods: Optional[List[str]] = None,
        base_classes: Optional[List[str]] = None,
        language: str = "python",
        context: Optional[Dict[str, Any]] = None,
    ) -> TaskResult:
        """Create a new class."""
        context = context or {}
        context["class_name"] = class_name
        context["methods"] = methods or []
        context["base_classes"] = base_classes or []
        context["language"] = language

        task = f"Create a {language} class named '{class_name}' that {description}"
        return self.execute(task, context)

    def implement_feature(
        self,
        feature_description: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> TaskResult:
        """Implement a feature."""
        task = f"Implement feature: {feature_description}"
        return self.execute(task, context)

    def fix_bug(
        self,
        bug_description: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> TaskResult:
        """Fix a bug."""
        task = f"Fix bug: {bug_description}"
        return self.execute(task, context)

    def refactor_code(
        self,
        refactor_description: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> TaskResult:
        """Refactor code."""
        task = f"Refactor code: {refactor_description}"
        return self.execute(task, context)

    def implement_interface(
        self,
        interface_name: str,
        implementation_description: str,
        language: str = "python",
        context: Optional[Dict[str, Any]] = None,
    ) -> TaskResult:
        """Implement an interface or abstract class."""
        context = context or {}
        context["interface_name"] = interface_name
        context["language"] = language

        task = f"Implement the {interface_name} interface: {implementation_description}"
        return self.execute(task, context)
