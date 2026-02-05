// BAML Function Definitions for Brief
// Run `baml-cli generate` from the brief directory to generate the client

// ============================================================
// Response Types
// ============================================================

class FunctionDescription {
    purpose string @description("One sentence: what this function does and WHEN to call it")
    behavior string @description("Key algorithm/steps - what makes this function unique")
    inputs string @description("Parameters: name, type, constraints")
    outputs string @description("Return value: type and meaning")
    side_effects string? @description("File I/O, state changes, exceptions thrown, or null")
}

class ClassDescription {
    purpose string @description("One sentence: what this class represents and WHEN to use it")
    responsibility string @description("Single responsibility: what domain concern it owns")
    key_methods string @description("Most important methods and when to call each")
    state string? @description("Instance data this class manages, or null")
    relationships string? @description("Parent classes, key collaborators, or null")
}

class FileDescription {
    purpose string @description("One sentence: what capability this file provides to the codebase")
    contents string @description("Key exports: classes, functions, constants")
    role string @description("System context: how other code uses this file")
    dependencies string @description("Critical imports and why they're needed")
    exports string @description("What to import: primary public API")
}

class ModuleDescription {
    purpose string @description("One sentence: what this module/package provides")
    components string @description("Key files and their responsibilities")
    architecture string @description("How components collaborate")
    public_api string @description("Recommended imports for external use")
}

// ============================================================
// Functions
// ============================================================

function DescribeFunction(
    function_name: string,
    function_code: string,
    file_context: string,
    docstring: string?
) -> FunctionDescription {
    client Default

    prompt #"
        Analyze this Python function for an AI coding agent.

        Context: {{ file_context }}
        Function: {{ function_name }}

        ```python
        {{ function_code }}
        ```

        {% if docstring %}
        Docstring: {{ docstring }}
        {% endif %}

        Write descriptions optimized for AI agents working on this codebase:

        PURPOSE: Start with WHEN to use this function, then what it does.
          Good: "Call this to validate user input before saving. Checks format and sanitizes data."
          Bad: "This function validates input."

        BEHAVIOR: Focus on the unique logic, not obvious code flow.
          - What algorithm or approach?
          - What edge cases are handled?
          - What makes this different from similar functions?

        INPUTS: Be specific about types and constraints.
          - What values are valid?
          - What happens with invalid input?

        OUTPUTS: What does the caller receive?
          - Return type and meaning
          - None vs exceptions

        SIDE_EFFECTS: List any effects beyond the return value, or null.
          - File/DB operations
          - State mutations
          - Exceptions thrown

        Be concise. Each field should be 1-2 sentences max.

        {{ ctx.output_format }}
    "#
}

function DescribeClass(
    class_name: string,
    class_code: string,
    file_context: string,
    docstring: string?,
    method_names: string[]
) -> ClassDescription {
    client Default

    prompt #"
        Analyze this Python class for an AI coding agent.

        Context: {{ file_context }}
        Class: {{ class_name }}
        Methods: {{ method_names }}

        ```python
        {{ class_code }}
        ```

        {% if docstring %}
        Docstring: {{ docstring }}
        {% endif %}

        Write descriptions optimized for AI agents working on this codebase:

        PURPOSE: Start with WHEN to use this class.
          Good: "Use when you need to parse markdown files. Handles headings, links, and code blocks."
          Bad: "A class for parsing markdown."

        RESPONSIBILITY: What single concern does this class own?
          - Be specific about boundaries
          - What does it NOT handle?

        KEY_METHODS: For each important method:
          - When to call it
          - What it does (briefly)
          Skip obvious getters/setters.

        STATE: What instance data does it manage? Or null if stateless.

        RELATIONSHIPS: Parent classes or key collaborators? Or null if standalone.

        Be concise. Each field should be 1-3 sentences max.

        {{ ctx.output_format }}
    "#
}

function DescribeFile(
    file_path: string,
    file_content: string,
    class_names: string[],
    function_names: string[],
    imports: string[]
) -> FileDescription {
    client Default

    prompt #"
        Analyze this Python file for an AI coding agent.

        File: {{ file_path }}
        Classes: {{ class_names }}
        Functions: {{ function_names }}
        Imports: {{ imports }}

        ```python
        {{ file_content }}
        ```

        Determine file type from path:
        - "commands/" or "cli" = CLI command module
        - "models" or "types" = Data models
        - "test_" prefix = Test file
        - "utils" or "helpers" = Utility functions
        - Other = Core implementation

        Write descriptions optimized for AI agents working on this codebase:

        PURPOSE: Start with WHEN an agent should look at this file.
          Good: "Look here when implementing new CLI commands. Contains Typer app setup and command patterns."
          Bad: "This file contains CLI commands."

        CONTENTS: List the key exports an agent might import.
          - Main classes and their roles
          - Important functions
          - Constants or config values

        ROLE: How does this file fit in the system architecture?
          - What layer is it? (CLI, business logic, data, etc.)
          - What depends on it?

        DEPENDENCIES: What critical imports does it need and why?
          - External packages
          - Internal modules

        EXPORTS: What should agents import from here?
          - Primary public API
          - Entry points

        Be concise. Each field should be 1-3 sentences max.

        {{ ctx.output_format }}
    "#
}

function DescribeModule(
    module_name: string,
    file_summaries: string[],
    class_count: int,
    function_count: int
) -> ModuleDescription {
    client Default

    prompt #"
        Analyze this Python module (package/directory) for an AI coding agent.

        Module: {{ module_name }}
        Classes: {{ class_count }}
        Functions: {{ function_count }}

        Files:
        {% for summary in file_summaries %}
        - {{ summary }}
        {% endfor %}

        Write descriptions optimized for AI agents working on this codebase:

        PURPOSE: Start with WHEN an agent should explore this module.
          Good: "Look here when working with task management. Contains task creation, tracking, and queries."
          Bad: "This module handles tasks."

        COMPONENTS: Map key files to their responsibilities.
          - Which file does what?
          - How to find specific functionality?

        ARCHITECTURE: How do the components work together?
          - Data flow between files
          - Main entry points

        PUBLIC_API: What should agents import?
          - Recommended import statements
          - Key classes/functions to use

        Be concise. Each field should be 2-4 sentences max.

        {{ ctx.output_format }}
    "#
}
