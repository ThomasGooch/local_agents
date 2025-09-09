"""Planning agent for creating implementation plans."""

from typing import Any, Dict, Optional

from ..base import BaseAgent, TaskResult, handle_agent_execution


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
        self, task: str, context: Optional[Dict[str, Any]] = None, stream: bool = False
    ) -> TaskResult:
        """Execute planning task."""
        prompt = self._build_planning_prompt(task, context)
        response = self._call_ollama(prompt, stream=stream)
        return self._create_success_result(response, task, context)

    def _build_planning_prompt(self, task: str, context: Dict[str, Any]) -> str:
        """Build a structured prompt for planning tasks."""
        prompt_parts = [
            "# Implementation Planning Task",
            f"\n## Task Description\n{task}",
        ]

        if context.get("file_content"):
            prompt_parts.append(f"\n## Context File Content\n```\n{context['file_content']}\n```")

        if context.get("directory"):
            prompt_parts.append(f"\n## Working Directory\n{context['directory']}")

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

    def plan_feature(
        self, feature_description: str, context: Optional[Dict[str, Any]] = None
    ) -> TaskResult:
        """Create a plan specifically for a new feature."""
        context = context or {}
        context["plan_type"] = "feature"
        return self.execute(f"Plan implementation of new feature: {feature_description}", context)

    def plan_bugfix(
        self, bug_description: str, context: Optional[Dict[str, Any]] = None
    ) -> TaskResult:
        """Create a plan specifically for a bug fix."""
        context = context or {}
        context["plan_type"] = "bugfix"
        return self.execute(f"Plan bug fix for: {bug_description}", context)

    def plan_refactor(
        self, refactor_description: str, context: Optional[Dict[str, Any]] = None
    ) -> TaskResult:
        """Create a plan specifically for refactoring."""
        context = context or {}
        context["plan_type"] = "refactor"
        return self.execute(f"Plan refactoring: {refactor_description}", context)
