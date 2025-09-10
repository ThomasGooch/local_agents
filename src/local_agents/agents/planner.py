"""Planning agent for creating implementation plans."""

import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from rich.console import Console

from ..base import BaseAgent, TaskResult, handle_agent_execution

console = Console()


class PlanningAgent(BaseAgent):
    """Agent specialized in creating detailed implementation plans."""

    def __init__(self, model: Optional[str] = None, **kwargs):
        super().__init__(
            agent_type="plan",
            role="Senior Software Architect and Project Planner",
            goal=(
                "Create comprehensive, actionable implementation plans that "
                "break down complex tasks into manageable steps"
            ),
            model=model,
            **kwargs,
        )

    @handle_agent_execution
    def execute(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        stream: bool = False,
    ) -> TaskResult:
        """Execute planning task."""
        prompt = self._build_planning_prompt(task, context)
        response = self._call_ollama(prompt, stream=stream)

        # Save plan to file if configured
        plan_file_path = self._save_plan_to_file(task, response, context)

        # Add plan file path to context for downstream agents
        updated_context = context.copy() if context else {}
        if plan_file_path:
            updated_context["plan_file"] = str(plan_file_path)
            updated_context["plan_content"] = response
        return self._create_success_result(response, task, updated_context)

    def _build_planning_prompt(self, task: str, context: Dict[str, Any]) -> str:
        """Build a structured prompt for planning tasks."""
        prompt_parts = [
            "# Implementation Planning Task",
            f"\n## Task Description\n{task}",
        ]

        if context.get("file_content"):
            prompt_parts.append(f"\n## Context File Content\n```\n{context['file_content']}\n```")

        # Use output_directory or directory for context
        work_dir = context.get("output_directory") or context.get("directory")
        if work_dir:
            prompt_parts.append(f"\n## Working Directory\n{work_dir}")

        if context.get("specification"):
            prompt_parts.append(f"\n## Additional Specifications\n{context['specification']}")

        prompt_parts.extend(
            [
                "\n## Planning Instructions",
                """
Please create a comprehensive implementation plan that includes:

1. **Analysis & Requirements**
   - Break down the task into clear requirements
   - Identify dependencies and constraints
   - Note any assumptions being made

2. **Architecture & Design**
   - Outline the overall approach and architecture
   - Identify key components and their relationships
   - Consider design patterns and best practices

3. **Implementation Steps**
   - Break down into specific, actionable steps
   - Order steps logically with dependencies
   - Estimate complexity and potential risks for each step

4. **File Structure & Changes**
   - List files that need to be created or modified
   - Describe the purpose of each file
   - Note any configuration or setup requirements

5. **Testing Strategy**
   - Identify what needs to be tested
   - Suggest testing approaches and tools
   - Consider edge cases and error scenarios

6. **Potential Risks & Mitigation**
   - Identify potential issues or blockers
   - Suggest mitigation strategies
   - Note areas that may need extra attention

7. **Success Criteria**
   - Define what "done" looks like
   - List measurable outcomes
   - Include validation steps

Please format your response in clear markdown with appropriate headers and
bullet points.
Make the plan detailed enough to be actionable but concise enough to be easily
followed.
""",
            ]
        )

        return "\n".join(prompt_parts)

    def _save_plan_to_file(
        self, task: str, plan_content: str, context: Optional[Dict[str, Any]] = None
    ) -> Optional[Path]:
        """Save the generated plan to a markdown file."""
        from ..config import get_config

        config = get_config()
        plan_config = config.plan_output

        # Skip if file output is disabled
        if not plan_config.enable_file_output:
            return None

        try:
            # Create output directory
            output_dir = Path(plan_config.output_directory).expanduser().resolve()
            output_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename
            filename = self._generate_plan_filename(task, plan_config, context)
            file_path = output_dir / filename

            # Create enhanced markdown content
            markdown_content = self._create_markdown_content(task, plan_content, context)

            # Write to file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            console.print(f"[green]✓[/green] Plan saved to: [cyan]{file_path}[/cyan]")
            return file_path

        except Exception as e:
            console.print(f"[yellow]Warning: Failed to save plan to file: {e}[/yellow]")
            return None

    def _generate_plan_filename(
        self, task: str, plan_config: Any, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate a filename for the plan based on configuration."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        task_hash = hashlib.md5(task.encode("utf-8")).hexdigest()[:8]

        # Start with the configured format
        filename = plan_config.filename_format.format(timestamp=timestamp, task_hash=task_hash)

        # Add context info if requested
        if plan_config.include_context_in_filename and context:
            if context.get("plan_type"):
                filename = filename.replace(".md", f"_{context['plan_type']}.md")

        # Ensure filename isn't too long
        if len(filename) > plan_config.max_filename_length:
            # Keep the extension and truncate the middle
            name, ext = os.path.splitext(filename)
            max_name_length = plan_config.max_filename_length - len(ext)
            if max_name_length > 20:  # Ensure we have reasonable minimum
                truncated_name = name[: max_name_length - 3] + "..."
                filename = truncated_name + ext
            else:
                filename = f"plan_{timestamp}.md"

        return filename

    def _create_markdown_content(
        self, task: str, plan_content: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create enhanced markdown content with metadata."""
        metadata_lines = [
            "---",
            "# Planning Session Metadata",
            f"- **Generated**: {datetime.now().isoformat()}",
            f"- **Task**: {task}",
            "- **Agent**: Planning Agent",
            f"- **Model**: {self.model}",
        ]

        if context:
            if context.get("plan_type"):
                metadata_lines.append(f"- **Plan Type**: {context['plan_type']}")
            if context.get("directory"):
                metadata_lines.append(f"- **Working Directory**: {context['directory']}")
            if context.get("file_content"):
                file_len = len(context["file_content"])
                metadata_lines.append(f"- **Context File**: {file_len} characters")

        metadata_lines.extend(["---", "", "# Implementation Plan", "", plan_content])

        return "\n".join(metadata_lines)

    def plan_feature(
        self,
        feature_description: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> TaskResult:
        """Create a plan specifically for a new feature."""
        context = context or {}
        context["plan_type"] = "feature"
        return self.execute(
            f"Plan implementation of new feature: {feature_description}",
            context,
        )

    def plan_bugfix(
        self, bug_description: str, context: Optional[Dict[str, Any]] = None
    ) -> TaskResult:
        """Create a plan specifically for a bug fix."""
        context = context or {}
        context["plan_type"] = "bugfix"
        return self.execute(f"Plan bug fix for: {bug_description}", context)

    def plan_refactor(
        self,
        refactor_description: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> TaskResult:
        """Create a plan specifically for refactoring."""
        context = context or {}
        context["plan_type"] = "refactor"
        return self.execute(f"Plan refactoring: {refactor_description}", context)
