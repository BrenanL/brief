// BAML Function Definitions for Brief
// Run `baml-cli generate` from the brief directory to generate the client

// ============================================================
// Response Types
// ============================================================

class FunctionDescription {
    purpose string @description("One sentence describing what the function does")
    behavior string @description("How the function accomplishes its purpose")
    inputs string @description("Description of parameters and their purpose")
    outputs string @description("What the function returns or yields")
    side_effects string? @description("Any side effects, or null if none")
}

class ClassDescription {
    purpose string @description("One sentence describing what the class does")
    responsibility string @description("What domain/concern this class owns")
    key_methods string @description("Brief description of important methods")
    state string? @description("What state/data this class manages")
    relationships string? @description("How it relates to other classes")
}

class FileDescription {
    purpose string @description("One sentence describing what this file provides")
    contents string @description("Summary of classes and functions defined")
    role string @description("How this file fits into the larger system")
    dependencies string @description("What it depends on and why")
    exports string @description("What other code should import from here")
}

class ModuleDescription {
    purpose string @description("One sentence describing what this module provides")
    components string @description("Summary of key components")
    architecture string @description("How components work together")
    public_api string @description("What should be imported from this module")
}

// ============================================================
// Functions
// ============================================================

// Function to describe what a Python function does
function DescribeFunction(
    function_name: string,
    function_code: string,
    file_context: string,
    docstring: string?
) -> FunctionDescription {
    client Default

    prompt #"
        You are a code documentation expert. Analyze this Python function and provide a concise description.

        File context: {{ file_context }}

        Function name: {{ function_name }}

        Code:
        ```python
        {{ function_code }}
        ```

        {% if docstring %}
        Existing docstring: {{ docstring }}
        {% endif %}

        Provide a description following this structure:
        1. PURPOSE: One sentence describing what this function does (the "why")
        2. BEHAVIOR: How it accomplishes its purpose (key steps, not line-by-line)
        3. INPUTS: What it expects (parameters and their purpose)
        4. OUTPUTS: What it returns or yields
        5. SIDE_EFFECTS: Any side effects (file I/O, state changes, etc.) or null if none

        Be concise but complete. Focus on understanding, not just restating the code.

        {{ ctx.output_format }}
    "#
}

// Function to describe what a class does
function DescribeClass(
    class_name: string,
    class_code: string,
    file_context: string,
    docstring: string?,
    method_names: string[]
) -> ClassDescription {
    client Default

    prompt #"
        You are a code documentation expert. Analyze this Python class and provide a concise description.

        File context: {{ file_context }}

        Class name: {{ class_name }}

        Methods: {{ method_names }}

        Code:
        ```python
        {{ class_code }}
        ```

        {% if docstring %}
        Existing docstring: {{ docstring }}
        {% endif %}

        Provide a description following this structure:
        1. PURPOSE: One sentence describing what this class represents/does
        2. RESPONSIBILITY: What domain/concern this class owns
        3. KEY_METHODS: Brief description of the most important methods
        4. STATE: What state/data this class manages (if any), or null
        5. RELATIONSHIPS: How it relates to other classes (inheritance, composition), or null

        Be concise but complete.

        {{ ctx.output_format }}
    "#
}

// Function to describe what a file/module does
function DescribeFile(
    file_path: string,
    file_content: string,
    class_names: string[],
    function_names: string[],
    imports: string[]
) -> FileDescription {
    client Default

    prompt #"
        You are a code documentation expert. Analyze this Python file and provide a concise description.

        File: {{ file_path }}

        Classes defined: {{ class_names }}
        Functions defined: {{ function_names }}
        Key imports: {{ imports }}

        Full code:
        ```python
        {{ file_content }}
        ```

        Provide a description following this structure:
        1. PURPOSE: One sentence describing what this file/module provides
        2. CONTENTS: Summary of what's defined here
        3. ROLE: How this file fits into the larger system
        4. DEPENDENCIES: What it depends on and why
        5. EXPORTS: What other code should import from here

        Be concise but complete.

        {{ ctx.output_format }}
    "#
}

// Function to describe a module (directory)
function DescribeModule(
    module_name: string,
    file_summaries: string[],
    class_count: int,
    function_count: int
) -> ModuleDescription {
    client Default

    prompt #"
        You are a code documentation expert. Analyze this Python module (directory) and provide a description.

        Module: {{ module_name }}

        Files in this module:
        {% for summary in file_summaries %}
        - {{ summary }}
        {% endfor %}

        Total classes: {{ class_count }}
        Total functions: {{ function_count }}

        Provide a description following this structure:
        1. PURPOSE: One sentence describing what this module provides
        2. COMPONENTS: Summary of key components and their roles
        3. ARCHITECTURE: How the components work together
        4. PUBLIC_API: What should be imported from this module

        Be concise but complete.

        {{ ctx.output_format }}
    "#
}
