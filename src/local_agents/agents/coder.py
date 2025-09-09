"""Coding agent for generating and modifying code."""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..base import BaseAgent, TaskResult, handle_agent_execution


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

    @handle_agent_execution
    def execute(
        self, task: str, context: Optional[Dict[str, Any]] = None, stream: bool = False
    ) -> TaskResult:
        """Execute coding task."""
        prompt = self._build_coding_prompt(task, context)
        response = self._call_ollama(prompt, stream=stream)

        # Post-process response to extract code if needed
        processed_output = self._post_process_code_response(response, context)

        return self._create_success_result(processed_output, task, context)

    def _build_coding_prompt(self, task: str, context: Dict[str, Any]) -> str:
        """Build a structured prompt for coding tasks."""
        prompt_parts = [
            "# Code Generation Task",
            f"\n## Task Description\n{task}",
        ]

        if context.get("target_file"):
            prompt_parts.append(f"\n## Target File\n{context['target_file']}")

        if context.get("existing_code"):
            prompt_parts.append(
                f"\n## Existing Code\n```\n{context['existing_code']}\n```"
            )

        if context.get("specification"):
            prompt_parts.append(
                f"\n## Detailed Specification\n{context['specification']}"
            )

        if context.get("file_content"):
            prompt_parts.append(
                f"\n## Context File Content\n```\n{context['file_content']}\n```"
            )

        if context.get("directory"):
            prompt_parts.append(f"\n## Working Directory\n{context['directory']}")
            # Try to infer project structure and language
            self._add_project_context(prompt_parts, Path(context["directory"]))

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
   - Provide complete, working code
   - Include any necessary imports or dependencies
   - Add brief explanations for complex logic
   - Specify the file path where code should be placed

Please provide the complete code implementation with clear explanations of any
important design decisions.
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
            prompt_parts.append(
                f"\n## Detected Project Files\n{', '.join(project_files)}"
            )

        # Look for common directory structures
        common_dirs = ["src", "lib", "app", "components", "utils", "tests", "test"]
        found_dirs = [d for d in common_dirs if (directory / d).exists()]

        if found_dirs:
            prompt_parts.append(
                f"\n## Project Structure\nDetected directories: {', '.join(found_dirs)}"
            )

    def _post_process_code_response(
        self, response: str, context: Dict[str, Any]
    ) -> str:
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
        function_name: str,
        description: str,
        parameters: Optional[List[str]] = None,
        return_type: Optional[str] = None,
        language: str = "python",
        context: Optional[Dict[str, Any]] = None,
    ) -> TaskResult:
        """Generate a specific function."""
        context = context or {}
        context["function_name"] = function_name
        context["parameters"] = parameters or []
        context["return_type"] = return_type
        context["language"] = language

        task = (
            f"Generate a {language} function named '{function_name}' that {description}"
        )
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
