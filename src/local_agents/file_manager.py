"""File management utilities for local agents."""

import re
from pathlib import Path
from typing import Dict, List, Optional

from rich.console import Console

console = Console()


class FileManager:
    """Handles file creation and management for agents."""

    def __init__(self, working_directory: str = "."):
        self.working_directory = Path(working_directory)
        self.working_directory.mkdir(parents=True, exist_ok=True)

    def extract_and_write_files_from_response(
        self, response: str, context: Dict[str, any] = None
    ) -> List[str]:
        """Extract file content from agent response and write files."""
        context = context or {}
        created_files = []

        # Pattern 1: Explicit file path indicators
        file_patterns = [
            # "File: path/to/file.ext" followed by code block
            r"(?i)File:\s*([^\n]+\.[\w]+).*?```(?:\w+)?\s*\n(.*?)\n```",
            # "Create file: path/to/file.ext" followed by code block
            r"(?i)Create\s+file:\s*([^\n]+\.[\w]+).*?```(?:\w+)?\s*\n(.*?)\n```",
            # "Save as: path/to/file.ext" followed by code block
            r"(?i)Save\s+as:\s*([^\n]+\.[\w]+).*?```(?:\w+)?\s*\n(.*?)\n```",
        ]

        for pattern in file_patterns:
            matches = re.findall(pattern, response, re.DOTALL | re.MULTILINE)
            for file_path, content in matches:
                file_path = file_path.strip()
                if self._is_valid_file_path(file_path):
                    created_file = self._write_file(file_path, content.strip(), context)
                    if created_file:
                        created_files.append(created_file)

        # Pattern 2: Infer from code blocks with language hints
        if not created_files:
            created_files.extend(self._extract_from_language_blocks(response, context))

        # Pattern 3: Create default files based on agent type and content
        if not created_files:
            created_files.extend(self._create_default_files(response, context))

        return created_files

    def _extract_from_language_blocks(self, response: str, context: Dict[str, any]) -> List[str]:
        """Extract files from language-specific code blocks."""
        created_files = []

        # Language to file extension mapping
        lang_extensions = {
            "csharp": ".cs",
            "c#": ".cs",
            "cs": ".cs",
            "python": ".py",
            "py": ".py",
            "javascript": ".js",
            "js": ".js",
            "typescript": ".ts",
            "ts": ".ts",
            "java": ".java",
            "go": ".go",
            "rust": ".rs",
            "cpp": ".cpp",
            "c++": ".cpp",
            "c": ".c",
            "html": ".html",
            "css": ".css",
            "sql": ".sql",
            "xml": ".xml",
            "json": ".json",
            "yaml": ".yml",
            "yml": ".yml",
        }

        # Find code blocks with language specifiers
        code_blocks = re.findall(r"```(\w+)\s*\n(.*?)\n```", response, re.DOTALL)

        for language, content in code_blocks:
            language = language.lower()
            if language in lang_extensions:
                extension = lang_extensions[language]
                # Generate file name based on content analysis
                file_name = self._generate_filename(content, extension, context)
                created_file = self._write_file(file_name, content.strip(), context)
                if created_file:
                    created_files.append(created_file)

        return created_files

    def _create_default_files(self, response: str, context: Dict[str, any]) -> List[str]:
        """Create default files based on agent type and task context."""
        created_files = []
        agent_type = context.get("agent_type", "unknown")

        if agent_type == "code":
            created_files.extend(self._create_code_files(response, context))
        elif agent_type == "test":
            created_files.extend(self._create_test_files(response, context))
        elif agent_type == "review":
            created_files.extend(self._create_review_files(response, context))

        return created_files

    def _create_code_files(self, response: str, context: Dict[str, any]) -> List[str]:
        """Create code files from coding agent response."""
        created_files = []
        task = context.get("task", "")

        # Detect language from task or context
        language = self._detect_language(task, response, context)
        extension = self._get_extension_for_language(language)

        # For .NET projects, create basic project structure first
        if language.lower() in ["c#", "csharp"] and "api" in task.lower():
            project_name = self._extract_project_name(task, response)
            created_files.extend(self.create_project_structure(language, project_name))

        # Extract all code blocks
        code_blocks = re.findall(r"```(?:\w+)?\s*\n(.*?)\n```", response, re.DOTALL)

        if code_blocks:
            for i, code in enumerate(code_blocks):
                if code.strip():
                    # Generate meaningful filename
                    filename = self._generate_code_filename(code, extension, context, i)
                    created_file = self._write_file(filename, code.strip(), context)
                    if created_file:
                        created_files.append(created_file)
        else:
            # No code blocks found, create a single file with the response
            filename = self._generate_default_filename("code", extension, context)
            created_file = self._write_file(filename, response, context)
            if created_file:
                created_files.append(created_file)

        return created_files

    def _create_test_files(self, response: str, context: Dict[str, any]) -> List[str]:
        """Create test files from testing agent response."""
        created_files = []

        # Extract code blocks that look like tests
        code_blocks = re.findall(r"```(?:\w+)?\s*\n(.*?)\n```", response, re.DOTALL)

        if code_blocks:
            for i, code in enumerate(code_blocks):
                if code.strip() and ("test" in code.lower() or "Test" in code):
                    # Generate test filename
                    filename = self._generate_test_filename(code, context, i)
                    created_file = self._write_file(filename, code.strip(), context)
                    if created_file:
                        created_files.append(created_file)

        # Always create a test report/summary
        test_report_file = self._write_file("test_report.md", response, context)
        if test_report_file:
            created_files.append(test_report_file)

        return created_files

    def _create_review_files(self, response: str, context: Dict[str, any]) -> List[str]:
        """Create review documentation from review agent response."""
        created_files = []

        # Create code review document
        review_file = self._write_file("code_review.md", response, context)
        if review_file:
            created_files.append(review_file)

        return created_files

    def _detect_language(self, task: str, response: str, context: Dict[str, any]) -> str:
        """Detect programming language from task and context."""
        task_lower = task.lower()

        # Check explicit language specification
        if context.get("language"):
            return context["language"]

        # Language keywords in task
        language_keywords = {
            "c#": [".net", "csharp", "c#", ".net9", "dotnet"],
            "python": ["python", "py", "django", "flask", "fastapi"],
            "javascript": [
                "javascript",
                "js",
                "node",
                "react",
                "vue",
                "angular",
            ],
            "typescript": ["typescript", "ts"],
            "java": ["java", "spring", "maven", "gradle"],
            "go": ["go", "golang"],
            "rust": ["rust", "cargo"],
            "cpp": ["c++", "cpp"],
        }

        for language, keywords in language_keywords.items():
            if any(keyword in task_lower for keyword in keywords):
                return language

        # Check for language indicators in response
        code_block_lang = re.search(r"```(\w+)", response)
        if code_block_lang:
            return code_block_lang.group(1).lower()

        return "unknown"

    def _get_extension_for_language(self, language: str) -> str:
        """Get file extension for programming language."""
        extensions = {
            "c#": ".cs",
            "csharp": ".cs",
            "python": ".py",
            "javascript": ".js",
            "typescript": ".ts",
            "java": ".java",
            "go": ".go",
            "rust": ".rs",
            "cpp": ".cpp",
            "c++": ".cpp",
            "c": ".c",
            "html": ".html",
            "css": ".css",
        }
        return extensions.get(language, ".txt")

    def _generate_filename(self, content: str, extension: str, context: Dict[str, any]) -> str:
        """Generate meaningful filename from content."""
        # Look for class names, function names, etc.
        class_match = re.search(r"class\s+(\w+)", content)
        if class_match:
            return f"{class_match.group(1)}{extension}"

        function_match = re.search(r"(?:def|function|func)\s+(\w+)", content)
        if function_match:
            return f"{function_match.group(1)}{extension}"

        # Use task-based naming
        task = context.get("task", "")
        if "weather" in task.lower():
            return f"WeatherApi{extension}"
        elif "api" in task.lower():
            return f"Api{extension}"

        return f"generated_code{extension}"

    def _generate_code_filename(
        self, code: str, extension: str, context: Dict[str, any], index: int
    ) -> str:
        """Generate filename for code files."""
        task = context.get("task", "")

        # .NET specific patterns
        if extension == ".cs":
            # Look for class names
            class_match = re.search(r"public\s+class\s+(\w+)", code)
            if class_match:
                return f"{class_match.group(1)}{extension}"

            # Look for controller patterns
            controller_match = re.search(r"(\w+)Controller", code)
            if controller_match:
                return f"{controller_match.group(1)}Controller{extension}"

        # Generic patterns
        if "weather" in task.lower():
            if index == 0:
                return f"WeatherController{extension}"
            elif "model" in code.lower() or "class" in code.lower():
                return f"WeatherForecast{extension}"
            elif "service" in code.lower():
                return f"WeatherService{extension}"

        return f"code_{index + 1}{extension}"

    def _generate_test_filename(self, code: str, context: Dict[str, any], index: int) -> str:
        """Generate filename for test files."""
        language = self._detect_language(context.get("task", ""), code, context)

        if language == "c#":
            # Look for test class names
            test_class_match = re.search(r"public\s+class\s+(\w+Tests?)", code)
            if test_class_match:
                return f"{test_class_match.group(1)}.cs"
            return "WeatherApiTests.cs"
        elif language == "python":
            return f"test_{index + 1}.py"
        elif language in ["javascript", "typescript"]:
            extension = "js" if language == "javascript" else "ts"
            return f"test_{index + 1}.{extension}"

        return f"test_{index + 1}.txt"

    def _generate_default_filename(
        self, file_type: str, extension: str, context: Dict[str, any]
    ) -> str:
        """Generate default filename."""
        task = context.get("task", "")

        if "weather" in task.lower():
            return f"Weather{file_type.title()}{extension}"

        return f"{file_type}{extension}"

    def _extract_project_name(self, task: str, response: str) -> str:
        """Extract project name from task or response."""
        task_lower = task.lower()

        # Look for specific project names in task
        if "weather" in task_lower:
            return "WeatherApi"
        elif "user" in task_lower and "auth" in task_lower:
            return "UserAuthApi"
        elif "blog" in task_lower:
            return "BlogApi"
        elif "todo" in task_lower:
            return "TodoApi"

        # Look for namespace or class names in response
        namespace_match = re.search(r"namespace\s+(\w+)", response)
        if namespace_match:
            return namespace_match.group(1)

        # Default to generic API name
        return "WebApi"

    def _is_valid_file_path(self, path: str) -> bool:
        """Check if the path is valid for file creation."""
        # Basic validation
        if not path or path.strip() == "":
            return False

        # Check for dangerous paths
        dangerous_patterns = ["../", "..\\", "/etc/", "c:\\windows"]
        if any(pattern in path.lower() for pattern in dangerous_patterns):
            return False

        return True

    def _write_file(self, file_path: str, content: str, context: Dict[str, any]) -> Optional[str]:
        """Write content to file safely."""
        try:
            # Ensure we're writing within the working directory
            full_path = self.working_directory / file_path

            # Create parent directories if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Write the file
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

            console.print(f"[green]✓ Created file: {full_path}[/green]")
            return str(full_path)

        except Exception as e:
            console.print(f"[red]✗ Failed to create file {file_path}: {e}[/red]")
            return None

    def create_project_structure(self, language: str, project_name: str) -> List[str]:
        """Create basic project structure for different languages."""
        created_files = []

        if language.lower() in ["c#", "csharp"]:
            # .NET project structure
            project_files = [
                (
                    f"{project_name}.csproj",
                    self._get_csproj_template(project_name),
                ),
                ("Program.cs", self._get_program_cs_template()),
                ("appsettings.json", self._get_appsettings_template()),
                ("Controllers/.gitkeep", ""),
                ("Models/.gitkeep", ""),
                ("Services/.gitkeep", ""),
            ]

            for file_path, content in project_files:
                created_file = self._write_file(file_path, content, {"agent_type": "structure"})
                if created_file:
                    created_files.append(created_file)

        return created_files

    def _get_csproj_template(self, project_name: str) -> str:
        """Get .csproj template."""
        return """<Project Sdk="Microsoft.NET.Sdk.Web">

  <PropertyGroup>
    <TargetFramework>net9.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
  </PropertyGroup>

  <ItemGroup>
    <PackageReference Include="Microsoft.AspNetCore.OpenApi" Version="9.0.0" />
    <PackageReference Include="Swashbuckle.AspNetCore" Version="6.6.2" />
  </ItemGroup>

</Project>
"""

    def _get_program_cs_template(self) -> str:
        """Get Program.cs template."""
        return """using Microsoft.OpenApi.Models;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.
builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(c =>
{
    c.SwaggerDoc("v1", new OpenApiInfo
    {
        Title = "Weather API",
        Version = "v1",
        Description = "A simple Weather API built with .NET 9"
    });
});

var app = builder.Build();

// Configure the HTTP request pipeline.
if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseHttpsRedirection();
app.UseAuthorization();
app.MapControllers();

app.Run();
"""

    def _get_appsettings_template(self) -> str:
        """Get appsettings.json template."""
        return """{
  "Logging": {
    "LogLevel": {
      "Default": "Information",
      "Microsoft.AspNetCore": "Warning"
    }
  },
  "AllowedHosts": "*"
}
"""
