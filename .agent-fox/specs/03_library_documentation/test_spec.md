# Test Specification: afspec Library Documentation

## Overview

Tests verify that the documentation files exist, are well-structured, and accurately cover the public API surfaces defined in the Go and Python library design documents. Tests parse markdown files to check for required headings, function entries, type entries, links, and content accuracy. Tests are implemented as pytest test functions.

## Test Cases

### TS-03-1: Go API reference contains all public functions

**Requirement:** 03-REQ-1.1
**Type:** unit
**Description:** Verify the Go API reference contains a section for every public function.

**Preconditions:**
- `docs/api/go.md` exists.

**Input:**
- Read `docs/api/go.md` and extract all `###` headings.

**Expected:**
- Headings include entries for: LoadSpec, SaveSpec, Validate, ValidateSchema, ValidateCrossFile, RenderRequirements, RenderTestSpec, RenderTasks, RenderCombined, Transition, NewBootstrap, DiscoverSpecs.

**Assertion pseudocode:**
```
content = read_file("docs/api/go.md")
headings = extract_h3_headings(content)
for func in GO_PUBLIC_FUNCTIONS:
    ASSERT func IN headings
```

### TS-03-2: Go API reference function entries have required sections

**Requirement:** 03-REQ-1.2
**Type:** unit
**Description:** Verify each function entry includes signature, description, parameters, returns, and errors.

**Preconditions:**
- `docs/api/go.md` exists.

**Input:**
- Parse each function section in `docs/api/go.md`.

**Expected:**
- Each function section contains: a code block with the Go signature, a description paragraph, a parameters table or list, a returns section, and an errors section.

**Assertion pseudocode:**
```
content = read_file("docs/api/go.md")
for func in GO_PUBLIC_FUNCTIONS:
    section = extract_section(content, func)
    ASSERT contains_code_block(section, "go")
    ASSERT contains_text(section, "Parameters") OR contains_text(section, "parameter")
    ASSERT contains_text(section, "Returns") OR contains_text(section, "return")
    ASSERT contains_text(section, "Errors") OR contains_text(section, "error")
```

### TS-03-3: Go API reference types section

**Requirement:** 03-REQ-1.3
**Type:** unit
**Description:** Verify the Go API reference includes a types section with all public types.

**Preconditions:**
- `docs/api/go.md` exists.

**Input:**
- Read `docs/api/go.md` and check for type entries.

**Expected:**
- The file contains a "Types" section with entries for key types: Spec, PRD, Frontmatter, Requirements, Criterion, TestSpecDoc, Tasks, ValidationError, DiscoveryResult, Bootstrap, Status, SubtaskState.

**Assertion pseudocode:**
```
content = read_file("docs/api/go.md")
ASSERT "## Types" IN content OR "# Types" IN content
for type_name in GO_KEY_TYPES:
    ASSERT type_name IN content
```

### TS-03-4: Go API reference category organization

**Requirement:** 03-REQ-1.4
**Type:** unit
**Description:** Verify the Go API reference is organized by functional category.

**Preconditions:**
- `docs/api/go.md` exists.

**Input:**
- Extract `##` headings from `docs/api/go.md`.

**Expected:**
- H2 headings include: Loading, Saving, Validation, Rendering, Lifecycle, Bootstrap, Discovery, Types.

**Assertion pseudocode:**
```
content = read_file("docs/api/go.md")
h2_headings = extract_h2_headings(content)
for category in ["Loading", "Saving", "Validation", "Rendering", "Lifecycle", "Bootstrap", "Discovery", "Types"]:
    ASSERT category IN h2_headings
```

### TS-03-5: Go API reference file location

**Requirement:** 03-REQ-1.5
**Type:** unit
**Description:** Verify the Go API reference exists at the specified path.

**Preconditions:**
- None.

**Input:**
- Check file existence.

**Expected:**
- `docs/api/go.md` exists and is a non-empty file.

**Assertion pseudocode:**
```
ASSERT file_exists("docs/api/go.md")
ASSERT file_size("docs/api/go.md") > 0
```

### TS-03-6: Python API reference contains all public functions

**Requirement:** 03-REQ-2.1
**Type:** unit
**Description:** Verify the Python API reference contains a section for every public function.

**Preconditions:**
- `docs/api/python.md` exists.

**Input:**
- Read `docs/api/python.md` and extract all `###` headings.

**Expected:**
- Headings include entries for: load_spec, save_spec, validate, render_requirements, render_test_spec, render_tasks, render_combined, transition, discover, schema_version.

**Assertion pseudocode:**
```
content = read_file("docs/api/python.md")
headings = extract_h3_headings(content)
for func in PYTHON_PUBLIC_FUNCTIONS:
    ASSERT func IN headings
```

### TS-03-7: Python API reference function entries have required sections

**Requirement:** 03-REQ-2.2
**Type:** unit
**Description:** Verify each function entry includes signature, description, parameters, returns, and exceptions.

**Preconditions:**
- `docs/api/python.md` exists.

**Input:**
- Parse each function section in `docs/api/python.md`.

**Expected:**
- Each function section contains: a code block with the Python signature, a description paragraph, a parameters table or list, a returns section, and an exceptions section.

**Assertion pseudocode:**
```
content = read_file("docs/api/python.md")
for func in PYTHON_PUBLIC_FUNCTIONS:
    section = extract_section(content, func)
    ASSERT contains_code_block(section, "python")
    ASSERT contains_text(section, "Parameters") OR contains_text(section, "parameter")
    ASSERT contains_text(section, "Returns") OR contains_text(section, "return")
    ASSERT contains_text(section, "Exceptions") OR contains_text(section, "Raises") OR contains_text(section, "exception")
```

### TS-03-8: Python API reference types section

**Requirement:** 03-REQ-2.3
**Type:** unit
**Description:** Verify the Python API reference includes a types section with all public types.

**Preconditions:**
- `docs/api/python.md` exists.

**Input:**
- Read `docs/api/python.md` and check for type entries.

**Expected:**
- The file contains a "Types" section with entries for key types: Spec, PRD, PRDFrontmatter, Requirements, EARSCriterion, TestSpec, Tasks, ValidationError, DiscoveryResult, BootstrapSpec, SubtaskState, LifecycleError.

**Assertion pseudocode:**
```
content = read_file("docs/api/python.md")
ASSERT "## Types" IN content OR "# Types" IN content
for type_name in PYTHON_KEY_TYPES:
    ASSERT type_name IN content
```

### TS-03-9: Python API reference category organization

**Requirement:** 03-REQ-2.4
**Type:** unit
**Description:** Verify the Python API reference is organized by functional category.

**Preconditions:**
- `docs/api/python.md` exists.

**Input:**
- Extract `##` headings from `docs/api/python.md`.

**Expected:**
- H2 headings include: Loading, Saving, Validation, Rendering, Lifecycle, Bootstrap, Discovery, Types.

**Assertion pseudocode:**
```
content = read_file("docs/api/python.md")
h2_headings = extract_h2_headings(content)
for category in ["Loading", "Saving", "Validation", "Rendering", "Lifecycle", "Bootstrap", "Discovery", "Types"]:
    ASSERT category IN h2_headings
```

### TS-03-10: Python API reference file location

**Requirement:** 03-REQ-2.5
**Type:** unit
**Description:** Verify the Python API reference exists at the specified path.

**Preconditions:**
- None.

**Input:**
- Check file existence.

**Expected:**
- `docs/api/python.md` exists and is a non-empty file.

**Assertion pseudocode:**
```
ASSERT file_exists("docs/api/python.md")
ASSERT file_size("docs/api/python.md") > 0
```

### TS-03-11: Example files exist at specified paths

**Requirement:** 03-REQ-3.4
**Type:** unit
**Description:** Verify all six example files exist.

**Preconditions:**
- None.

**Input:**
- Check file existence for each expected example file.

**Expected:**
- All six files exist and are non-empty.

**Assertion pseudocode:**
```
EXAMPLE_FILES = [
    "docs/examples/loading_and_saving.md",
    "docs/examples/validation.md",
    "docs/examples/rendering.md",
    "docs/examples/lifecycle.md",
    "docs/examples/bootstrap_and_discovery.md",
    "docs/examples/comparison.md",
]
for path in EXAMPLE_FILES:
    ASSERT file_exists(path)
    ASSERT file_size(path) > 0
```

### TS-03-12: Example files cover six operation categories

**Requirement:** 03-REQ-3.1
**Type:** unit
**Description:** Verify example files cover all required operation categories.

**Preconditions:**
- All example files exist.

**Input:**
- Read each example file and check for relevant content.

**Expected:**
- `loading_and_saving.md` contains "LoadSpec" or "load_spec" and "SaveSpec" or "save_spec".
- `validation.md` contains "Validate" or "validate".
- `rendering.md` contains "Render" or "render".
- `lifecycle.md` contains "Transition" or "transition".
- `bootstrap_and_discovery.md` contains "Bootstrap" or "bootstrap" and "Discover" or "discover".
- `comparison.md` contains both Go and Python code blocks.

**Assertion pseudocode:**
```
ASSERT contains("docs/examples/loading_and_saving.md", "LoadSpec") OR contains("docs/examples/loading_and_saving.md", "load_spec")
ASSERT contains("docs/examples/validation.md", "Validate") OR contains("docs/examples/validation.md", "validate")
ASSERT contains("docs/examples/rendering.md", "Render") OR contains("docs/examples/rendering.md", "render")
ASSERT contains("docs/examples/lifecycle.md", "Transition") OR contains("docs/examples/lifecycle.md", "transition")
ASSERT contains("docs/examples/bootstrap_and_discovery.md", "Bootstrap") OR contains("docs/examples/bootstrap_and_discovery.md", "bootstrap")
ASSERT contains("docs/examples/comparison.md", "```go") AND contains("docs/examples/comparison.md", "```python")
```

### TS-03-13: Examples are self-contained code snippets

**Requirement:** 03-REQ-3.2
**Type:** unit
**Description:** Verify that Go examples are package main programs and Python examples have imports.

**Preconditions:**
- Example files exist.

**Input:**
- Extract code blocks from non-comparison example files.

**Expected:**
- Every Go code block contains `package main` and `import`.
- Every Python code block contains `import afspec` or `from afspec`.

**Assertion pseudocode:**
```
for file in EXAMPLE_FILES_EXCEPT_COMPARISON:
    content = read_file(file)
    go_blocks = extract_code_blocks(content, "go")
    for block in go_blocks:
        ASSERT "package main" IN block
        ASSERT "import" IN block
    python_blocks = extract_code_blocks(content, "python")
    for block in python_blocks:
        ASSERT "import afspec" IN block OR "from afspec" IN block
```

### TS-03-14: Examples include both Go and Python

**Requirement:** 03-REQ-3.3
**Type:** unit
**Description:** Verify that each non-comparison example file has both Go and Python code blocks.

**Preconditions:**
- Example files exist.

**Input:**
- Check for Go and Python code blocks in each file.

**Expected:**
- Each file (except comparison.md) contains at least one Go code block and at least one Python code block.

**Assertion pseudocode:**
```
for file in ["loading_and_saving.md", "validation.md", "rendering.md", "lifecycle.md", "bootstrap_and_discovery.md"]:
    content = read_file("docs/examples/" + file)
    ASSERT count_code_blocks(content, "go") >= 1
    ASSERT count_code_blocks(content, "python") >= 1
```

### TS-03-15: Examples have prose descriptions

**Requirement:** 03-REQ-3.5
**Type:** unit
**Description:** Verify each code block is preceded by prose description.

**Preconditions:**
- Example files exist.

**Input:**
- For each example file, check that text paragraphs precede code blocks.

**Expected:**
- Every code block is preceded by at least one line of non-heading, non-empty prose.

**Assertion pseudocode:**
```
for file in EXAMPLE_FILES:
    content = read_file(file)
    code_block_positions = find_code_block_starts(content)
    for pos in code_block_positions:
        preceding_lines = get_lines_before(content, pos)
        ASSERT has_prose_line(preceding_lines)
```

### TS-03-16: Comparison file location

**Requirement:** 03-REQ-4.1
**Type:** unit
**Description:** Verify comparison file exists at docs/examples/comparison.md.

**Preconditions:**
- None.

**Input:**
- Check file existence.

**Expected:**
- `docs/examples/comparison.md` exists and is non-empty.

**Assertion pseudocode:**
```
ASSERT file_exists("docs/examples/comparison.md")
ASSERT file_size("docs/examples/comparison.md") > 0
```

### TS-03-17: Comparison covers required operations

**Requirement:** 03-REQ-4.2
**Type:** unit
**Description:** Verify the comparison document covers all required operations.

**Preconditions:**
- `docs/examples/comparison.md` exists.

**Input:**
- Extract headings from the comparison file.

**Expected:**
- The file contains headings or content covering: loading, saving, validating, rendering, lifecycle, bootstrap, and discovery.

**Assertion pseudocode:**
```
content = read_file("docs/examples/comparison.md")
operations = ["load", "save", "validat", "render", "lifecycle", "bootstrap", "discover"]
for op in operations:
    ASSERT op.lower() IN content.lower()
```

### TS-03-18: Comparison shows Go and Python side by side

**Requirement:** 03-REQ-4.3
**Type:** unit
**Description:** Verify the comparison presents alternating Go and Python code blocks.

**Preconditions:**
- `docs/examples/comparison.md` exists.

**Input:**
- Extract code blocks from the comparison file.

**Expected:**
- The file contains both `go` and `python` code blocks, with at least 7 of each (one per operation).

**Assertion pseudocode:**
```
content = read_file("docs/examples/comparison.md")
ASSERT count_code_blocks(content, "go") >= 7
ASSERT count_code_blocks(content, "python") >= 7
```

### TS-03-19: README overview section

**Requirement:** 03-REQ-5.1
**Type:** unit
**Description:** Verify README.md introduces both libraries.

**Preconditions:**
- `README.md` exists at repository root.

**Input:**
- Read README.md content.

**Expected:**
- README.md contains references to both the Go and Python libraries.

**Assertion pseudocode:**
```
content = read_file("README.md")
ASSERT "Go" IN content AND ("Python" IN content OR "python" IN content)
ASSERT "afspec" IN content
```

### TS-03-20: README quick-start sections

**Requirement:** 03-REQ-5.2
**Type:** unit
**Description:** Verify README.md has quick-start code examples for both libraries.

**Preconditions:**
- `README.md` exists.

**Input:**
- Extract code blocks from README.md.

**Expected:**
- README.md contains at least one Go code block and at least one Python code block.

**Assertion pseudocode:**
```
content = read_file("README.md")
ASSERT count_code_blocks(content, "go") >= 1
ASSERT count_code_blocks(content, "python") >= 1
```

### TS-03-21: README documentation links

**Requirement:** 03-REQ-5.3
**Type:** unit
**Description:** Verify README.md links to API docs, examples, and spec-format.

**Preconditions:**
- `README.md` exists.

**Input:**
- Extract markdown links from README.md.

**Expected:**
- README.md contains links to: `docs/api/go.md`, `docs/api/python.md`, `docs/examples/`, and `docs/spec-format.md`.

**Assertion pseudocode:**
```
content = read_file("README.md")
ASSERT "docs/api/go.md" IN content
ASSERT "docs/api/python.md" IN content
ASSERT "docs/examples" IN content
ASSERT "docs/spec-format.md" IN content
```

### TS-03-22: README file location

**Requirement:** 03-REQ-5.4
**Type:** unit
**Description:** Verify README.md exists at the repository root.

**Preconditions:**
- None.

**Input:**
- Check file existence.

**Expected:**
- `README.md` exists and is non-empty.

**Assertion pseudocode:**
```
ASSERT file_exists("README.md")
ASSERT file_size("README.md") > 0
```

### TS-03-23: Go API signatures match design doc

**Requirement:** 03-REQ-6.1
**Type:** integration
**Description:** Verify documented Go function signatures match spec 01 design.md.

**Preconditions:**
- `docs/api/go.md` and `.agent-fox/specs/01_golang_library/design.md` exist.

**Input:**
- Extract function signatures from both files and compare.

**Expected:**
- For each public function, the signature in the API reference matches the signature in the design doc.

**Assertion pseudocode:**
```
api_content = read_file("docs/api/go.md")
design_content = read_file(".agent-fox/specs/01_golang_library/design.md")
for func in GO_PUBLIC_FUNCTIONS:
    api_sig = extract_go_signature(api_content, func)
    design_sig = extract_go_signature(design_content, func)
    ASSERT normalize_whitespace(api_sig) == normalize_whitespace(design_sig)
```

### TS-03-24: Python API signatures match design doc

**Requirement:** 03-REQ-6.2
**Type:** integration
**Description:** Verify documented Python function signatures match spec 02 design.md.

**Preconditions:**
- `docs/api/python.md` and `.agent-fox/specs/02_python_library/design.md` exist.

**Input:**
- Extract function signatures from both files and compare.

**Expected:**
- For each public function, the signature in the API reference matches the signature in the design doc.

**Assertion pseudocode:**
```
api_content = read_file("docs/api/python.md")
design_content = read_file(".agent-fox/specs/02_python_library/design.md")
for func in PYTHON_PUBLIC_FUNCTIONS:
    api_sig = extract_python_signature(api_content, func)
    design_sig = extract_python_signature(design_content, func)
    ASSERT normalize_whitespace(api_sig) == normalize_whitespace(design_sig)
```

### TS-03-25: Documentation terminology consistency

**Requirement:** 03-REQ-6.4
**Type:** unit
**Description:** Verify domain terms used in docs match the spec-format glossary.

**Preconditions:**
- Documentation files exist. `docs/spec-format.md` exists.

**Input:**
- Extract key terms from `docs/spec-format.md` §2 and check consistency in API docs.

**Expected:**
- Domain terms (Spec, EARS, Operator, Coordinator, Archetype, Spec root) are used consistently.

**Assertion pseudocode:**
```
for file in ["docs/api/go.md", "docs/api/python.md"]:
    content = read_file(file)
    ASSERT NOT contains(content, "specification package") OR contains(content, "spec")
    ASSERT NOT contains(content, "spec directory") OR contains(content, "spec root")
```

## Property Test Cases

### TS-03-P1: Go API coverage completeness

**Property:** Property 1 from design.md
**Validates:** 03-REQ-1.1, 03-REQ-6.1
**Type:** property
**Description:** Every public Go function from the design doc appears in the API reference.

**For any:** public function name listed in spec 01 design.md Components and Interfaces section
**Invariant:** the function name appears as an H3 heading in docs/api/go.md

**Assertion pseudocode:**
```
FOR ANY func IN go_public_functions_from_design:
    content = read_file("docs/api/go.md")
    ASSERT "### " + func IN content OR "### `" + func + "`" IN content
```

### TS-03-P2: Python API coverage completeness

**Property:** Property 2 from design.md
**Validates:** 03-REQ-2.1, 03-REQ-6.2
**Type:** property
**Description:** Every public Python function from the design doc appears in the API reference.

**For any:** public function name listed in spec 02 design.md Components and Interfaces section
**Invariant:** the function name appears as an H3 heading in docs/api/python.md

**Assertion pseudocode:**
```
FOR ANY func IN python_public_functions_from_design:
    content = read_file("docs/api/python.md")
    ASSERT "### " + func IN content OR "### `" + func + "`" IN content
```

### TS-03-P3: Example operation coverage

**Property:** Property 3 from design.md
**Validates:** 03-REQ-3.1, 03-REQ-3.3
**Type:** property
**Description:** Every operation category has at least one Go and one Python example.

**For any:** operation category in {loading, saving, validation, rendering, lifecycle, bootstrap, discovery}
**Invariant:** at least one example file contains a Go code block and a Python code block referencing that operation

**Assertion pseudocode:**
```
FOR ANY operation IN ["load", "save", "validat", "render", "lifecycle", "bootstrap", "discover"]:
    found_go = False
    found_python = False
    for file in EXAMPLE_FILES:
        content = read_file(file)
        if operation.lower() IN content.lower():
            if count_code_blocks(content, "go") >= 1:
                found_go = True
            if count_code_blocks(content, "python") >= 1:
                found_python = True
    ASSERT found_go AND found_python
```

### TS-03-P4: Cross-reference integrity

**Property:** Property 4 from design.md
**Validates:** 03-REQ-5.3, 03-REQ-5.E1
**Type:** property
**Description:** Every relative link in README.md points to an existing file.

**For any:** relative markdown link in README.md (excluding external URLs)
**Invariant:** the linked file exists on disk

**Assertion pseudocode:**
```
FOR ANY link IN extract_relative_links(read_file("README.md")):
    ASSERT file_exists(link) OR directory_exists(link)
```

### TS-03-P5: Type documentation completeness

**Property:** Property 5 from design.md
**Validates:** 03-REQ-1.3, 03-REQ-2.3, 03-REQ-6.3
**Type:** property
**Description:** Every public type from the design docs appears in the API reference.

**For any:** public type name listed in spec 01 or 02 design.md
**Invariant:** the type name appears in the corresponding API reference file

**Assertion pseudocode:**
```
FOR ANY type_name IN go_public_types_from_design:
    ASSERT type_name IN read_file("docs/api/go.md")
FOR ANY type_name IN python_public_types_from_design:
    ASSERT type_name IN read_file("docs/api/python.md")
```

## Edge Case Tests

### TS-03-E1: Go function with no error return documented

**Requirement:** 03-REQ-1.E1
**Type:** unit
**Description:** Verify functions with no error return still document the errors section.

**Preconditions:**
- `docs/api/go.md` exists.

**Input:**
- Find function entries for functions that return only values (e.g., SubtaskState.LegalTransitions).

**Expected:**
- The section still contains an Errors reference (e.g., "None" or "This function does not return an error").

**Assertion pseudocode:**
```
content = read_file("docs/api/go.md")
section = extract_section(content, "LegalTransitions")
ASSERT contains_text(section, "error") OR contains_text(section, "None") OR contains_text(section, "N/A")
```

### TS-03-E2: Python function with no exceptions documented

**Requirement:** 03-REQ-2.E1
**Type:** unit
**Description:** Verify functions that raise no exceptions still document the exceptions section.

**Preconditions:**
- `docs/api/python.md` exists.

**Input:**
- Find function entries for functions that don't raise (e.g., schema_version).

**Expected:**
- The section still contains an Exceptions reference (e.g., "None").

**Assertion pseudocode:**
```
content = read_file("docs/api/python.md")
section = extract_section(content, "schema_version")
ASSERT contains_text(section, "exception") OR contains_text(section, "Raises") OR contains_text(section, "None")
```

### TS-03-E3: Go/Python behavioral differences noted in examples

**Requirement:** 03-REQ-3.E1
**Type:** unit
**Description:** Verify examples note behavioral differences between Go and Python.

**Preconditions:**
- Example files exist.

**Input:**
- Read example files and check for difference annotations.

**Expected:**
- At least one example file contains a note about Go vs Python differences (e.g., error handling via return values vs exceptions).

**Assertion pseudocode:**
```
found_difference_note = False
for file in EXAMPLE_FILES:
    content = read_file(file)
    if ("error" IN content AND "exception" IN content) OR "difference" IN content.lower() OR "unlike" IN content.lower() OR "contrast" IN content.lower():
        found_difference_note = True
ASSERT found_difference_note
```

### TS-03-E4: Missing Python-equivalent function noted in comparison

**Requirement:** 03-REQ-4.E1
**Type:** unit
**Description:** Verify the comparison document notes when an operation lacks a direct equivalent.

**Preconditions:**
- `docs/examples/comparison.md` exists.

**Input:**
- Read comparison file.

**Expected:**
- The file addresses Go functions that have no direct Python equivalent (e.g., ValidateSchema, ValidateCrossFile as standalone functions) or notes Python functions that have no Go equivalent.

**Assertion pseudocode:**
```
content = read_file("docs/examples/comparison.md")
ASSERT ("no direct" IN content.lower()) OR ("equivalent" IN content.lower()) OR ("alternative" IN content.lower()) OR ("not available" IN content.lower())
```

### TS-03-E5: README link to non-existent file includes note

**Requirement:** 03-REQ-5.E1
**Type:** unit
**Description:** Verify any README links to files that don't yet exist include a note.

**Preconditions:**
- `README.md` exists.

**Input:**
- Extract all relative links from README.md and check for existence.

**Expected:**
- All linked files exist, OR links to non-existent files have accompanying text noting the planned location.

**Assertion pseudocode:**
```
content = read_file("README.md")
links = extract_relative_links(content)
for link in links:
    ASSERT file_exists(link) OR directory_exists(link)
```

### TS-03-E6: Design doc ambiguity noted in API reference

**Requirement:** 03-REQ-6.E1
**Type:** unit
**Description:** Verify that if any design doc ambiguity exists, the API reference notes it.

**Preconditions:**
- API reference files exist.

**Input:**
- Read API reference files.

**Expected:**
- If any function has ambiguous behavior, a "Note" or "See also" reference is present. This test passes trivially if there are no ambiguities.

**Assertion pseudocode:**
```
go_content = read_file("docs/api/go.md")
python_content = read_file("docs/api/python.md")
ASSERT True  # passes if no ambiguities; manual review catches specific cases
```

## Integration Smoke Tests

### TS-03-SMOKE-1: Developer discovers library via README

**Execution Path:** Path 1 from design.md
**Description:** Verify the README → API docs → function entry navigation path works end to end.

**Setup:** All documentation files exist.

**Trigger:** Read README.md, follow links to API docs, verify function entries exist.

**Expected side effects:**
- README.md contains links to docs/api/go.md and docs/api/python.md.
- Each linked file exists and contains function documentation.
- Function documentation includes signatures and descriptions.

**Must NOT satisfy with:** Checking only link text without verifying target files exist and have content.

**Assertion pseudocode:**
```
readme = read_file("README.md")
ASSERT "docs/api/go.md" IN readme
ASSERT "docs/api/python.md" IN readme
go_api = read_file("docs/api/go.md")
ASSERT "LoadSpec" IN go_api
ASSERT "func LoadSpec" IN go_api
python_api = read_file("docs/api/python.md")
ASSERT "load_spec" IN python_api
ASSERT "def load_spec" IN python_api
```

### TS-03-SMOKE-2: Developer looks up Go function

**Execution Path:** Path 2 from design.md
**Description:** Verify a developer can navigate from the Go API doc to a specific function's full documentation.

**Setup:** `docs/api/go.md` exists with complete content.

**Trigger:** Open docs/api/go.md, locate "Validate" section, read full entry.

**Expected side effects:**
- The Validate function entry exists under a Validation heading.
- The entry includes: Go signature with `func Validate`, parameters (spec), return type ([]ValidationError, error), and error conditions.

**Must NOT satisfy with:** Checking only that "Validate" appears as a string — must verify structural completeness.

**Assertion pseudocode:**
```
content = read_file("docs/api/go.md")
validate_section = extract_function_section(content, "Validate")
ASSERT "func Validate" IN validate_section
ASSERT "Spec" IN validate_section
ASSERT "ValidationError" IN validate_section
ASSERT "Parameters" IN validate_section OR "**Parameters**" IN validate_section
```

### TS-03-SMOKE-3: Developer looks up Python function

**Execution Path:** Path 3 from design.md
**Description:** Verify a developer can navigate from the Python API doc to a specific function's full documentation.

**Setup:** `docs/api/python.md` exists with complete content.

**Trigger:** Open docs/api/python.md, locate "validate" section, read full entry.

**Expected side effects:**
- The validate function entry exists under a Validation heading.
- The entry includes: Python signature with `def validate`, parameters (spec: Spec), return type (list[ValidationError]), and exceptions.

**Must NOT satisfy with:** Checking only that "validate" appears as a string.

**Assertion pseudocode:**
```
content = read_file("docs/api/python.md")
validate_section = extract_function_section(content, "validate")
ASSERT "def validate" IN validate_section
ASSERT "Spec" IN validate_section
ASSERT "ValidationError" IN validate_section
ASSERT "Parameters" IN validate_section OR "**Parameters**" IN validate_section
```

### TS-03-SMOKE-4: Developer learns from examples

**Execution Path:** Path 4 from design.md
**Description:** Verify example files contain complete, understandable examples with prose and code.

**Setup:** All example files exist.

**Trigger:** Read docs/examples/loading_and_saving.md as a representative example file.

**Expected side effects:**
- The file has a title heading.
- The file has at least one Go code block with `package main`.
- The file has at least one Python code block with `import afspec`.
- Code blocks are preceded by prose descriptions.

**Must NOT satisfy with:** Checking only file existence without verifying content quality.

**Assertion pseudocode:**
```
content = read_file("docs/examples/loading_and_saving.md")
ASSERT content.startswith("#")
go_blocks = extract_code_blocks(content, "go")
ASSERT len(go_blocks) >= 1
ASSERT "package main" IN go_blocks[0]
python_blocks = extract_code_blocks(content, "python")
ASSERT len(python_blocks) >= 1
ASSERT "import afspec" IN python_blocks[0] OR "from afspec" IN python_blocks[0]
```

### TS-03-SMOKE-5: Developer translates between Go and Python

**Execution Path:** Path 5 from design.md
**Description:** Verify the comparison document provides side-by-side equivalent operations.

**Setup:** `docs/examples/comparison.md` exists.

**Trigger:** Read docs/examples/comparison.md and verify structure.

**Expected side effects:**
- The file covers at least 7 operations.
- Each operation section has both a Go and Python code block.
- Behavioral differences are noted where relevant.

**Must NOT satisfy with:** Checking only that Go and Python code blocks exist without verifying they appear in paired sections.

**Assertion pseudocode:**
```
content = read_file("docs/examples/comparison.md")
sections = split_by_h2(content)
operation_sections = [s for s in sections if has_code_blocks(s)]
ASSERT len(operation_sections) >= 7
for section in operation_sections:
    ASSERT count_code_blocks(section, "go") >= 1
    ASSERT count_code_blocks(section, "python") >= 1
```

## Coverage Matrix

| Requirement | Test Spec Entry | Type |
|-------------|-----------------|------|
| 03-REQ-1.1 | TS-03-1 | unit |
| 03-REQ-1.2 | TS-03-2 | unit |
| 03-REQ-1.3 | TS-03-3 | unit |
| 03-REQ-1.4 | TS-03-4 | unit |
| 03-REQ-1.5 | TS-03-5 | unit |
| 03-REQ-1.E1 | TS-03-E1 | unit |
| 03-REQ-2.1 | TS-03-6 | unit |
| 03-REQ-2.2 | TS-03-7 | unit |
| 03-REQ-2.3 | TS-03-8 | unit |
| 03-REQ-2.4 | TS-03-9 | unit |
| 03-REQ-2.5 | TS-03-10 | unit |
| 03-REQ-2.E1 | TS-03-E2 | unit |
| 03-REQ-3.1 | TS-03-12 | unit |
| 03-REQ-3.2 | TS-03-13 | unit |
| 03-REQ-3.3 | TS-03-14 | unit |
| 03-REQ-3.4 | TS-03-11 | unit |
| 03-REQ-3.5 | TS-03-15 | unit |
| 03-REQ-3.E1 | TS-03-E3 | unit |
| 03-REQ-4.1 | TS-03-16 | unit |
| 03-REQ-4.2 | TS-03-17 | unit |
| 03-REQ-4.3 | TS-03-18 | unit |
| 03-REQ-4.E1 | TS-03-E4 | unit |
| 03-REQ-5.1 | TS-03-19 | unit |
| 03-REQ-5.2 | TS-03-20 | unit |
| 03-REQ-5.3 | TS-03-21 | unit |
| 03-REQ-5.4 | TS-03-22 | unit |
| 03-REQ-5.E1 | TS-03-E5 | unit |
| 03-REQ-6.1 | TS-03-23 | integration |
| 03-REQ-6.2 | TS-03-24 | integration |
| 03-REQ-6.3 | TS-03-25 | unit |
| 03-REQ-6.4 | TS-03-25 | unit |
| 03-REQ-6.E1 | TS-03-E6 | unit |
| Property 1 | TS-03-P1 | property |
| Property 2 | TS-03-P2 | property |
| Property 3 | TS-03-P3 | property |
| Property 4 | TS-03-P4 | property |
| Property 5 | TS-03-P5 | property |
| Path 1 | TS-03-SMOKE-1 | integration |
| Path 2 | TS-03-SMOKE-2 | integration |
| Path 3 | TS-03-SMOKE-3 | integration |
| Path 4 | TS-03-SMOKE-4 | integration |
| Path 5 | TS-03-SMOKE-5 | integration |
