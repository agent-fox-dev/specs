# Rendering Examples

The `afspec` libraries can render each spec artifact — or all of them combined —
to a human-readable markdown document. Rendered output is useful for publishing
specs as documentation pages, code-review comments, or CI reports.

## Go

### Rendering Requirements to Markdown

`RenderRequirements` converts the structured `Requirements` artifact into a
markdown document. The output preserves EARS-pattern sentences, correctness
properties, execution paths, and the glossary.

```go
package main

import (
	"fmt"
	"log"

	"github.com/agent-fox/afspec"
)

func main() {
	spec, err := afspec.LoadSpec(".agent-fox/specs/01_my_feature")
	if err != nil {
		log.Fatalf("load: %v", err)
	}

	md, err := afspec.RenderRequirements(spec.Requirements)
	if err != nil {
		log.Fatalf("render requirements: %v", err)
	}
	fmt.Println(string(md))
}
```

### Rendering the Test Specification to Markdown

`RenderTestSpec` converts the `TestSpecDoc` artifact into a markdown document
containing all unit tests, property tests, edge-case tests, and smoke tests with
their descriptions, preconditions, inputs, and expected outputs.

```go
package main

import (
	"fmt"
	"log"

	"github.com/agent-fox/afspec"
)

func main() {
	spec, err := afspec.LoadSpec(".agent-fox/specs/01_my_feature")
	if err != nil {
		log.Fatalf("load: %v", err)
	}

	md, err := afspec.RenderTestSpec(spec.TestSpec)
	if err != nil {
		log.Fatalf("render test spec: %v", err)
	}
	fmt.Println(string(md))
}
```

### Rendering Tasks to Markdown

`RenderTasks` converts the `Tasks` artifact into a markdown checklist. Completed
subtasks are shown with `[x]`, pending ones with `[ ]`, and in-progress ones with
`[-]`.

```go
package main

import (
	"fmt"
	"log"

	"github.com/agent-fox/afspec"
)

func main() {
	spec, err := afspec.LoadSpec(".agent-fox/specs/01_my_feature")
	if err != nil {
		log.Fatalf("load: %v", err)
	}

	md, err := afspec.RenderTasks(spec.Tasks)
	if err != nil {
		log.Fatalf("render tasks: %v", err)
	}
	fmt.Println(string(md))
}
```

### Rendering a Combined Document

`RenderCombined` produces a single markdown document containing the PRD verbatim
followed by the rendered requirements, test spec, and tasks. This is useful for
exporting a complete spec to a wiki or review tool.

```go
package main

import (
	"log"
	"os"

	"github.com/agent-fox/afspec"
)

func main() {
	spec, err := afspec.LoadSpec(".agent-fox/specs/01_my_feature")
	if err != nil {
		log.Fatalf("load: %v", err)
	}

	md, err := afspec.RenderCombined(spec)
	if err != nil {
		log.Fatalf("render combined: %v", err)
	}

	// Write to a file for publishing.
	if err := os.WriteFile("spec_01_my_feature.md", md, 0o644); err != nil {
		log.Fatalf("write: %v", err)
	}
}
```

## Python

### Rendering Requirements to Markdown

`render_requirements` converts the `Requirements` object into a markdown string.
In Python the function returns a `str` rather than `([]byte, error)` as in Go;
exceptions are raised only on internal failures, not on empty or sparse inputs.

```python
import pathlib
import afspec

spec = afspec.load_spec(pathlib.Path(".agent-fox/specs/01_my_feature"))

md = afspec.render_requirements(spec.requirements)
print(md)
```

### Rendering the Test Specification to Markdown

`render_test_spec` converts the `TestSpec` object into a human-readable markdown
document that mirrors the structure defined in the spec format.

```python
import pathlib
import afspec

spec = afspec.load_spec(pathlib.Path(".agent-fox/specs/01_my_feature"))

md = afspec.render_test_spec(spec.test_spec)
print(md)
```

### Rendering Tasks to Markdown

`render_tasks` renders the `Tasks` object as a markdown checklist. The output
format is identical to what the Go library produces, enabling cross-tool
comparison.

```python
import pathlib
import afspec

spec = afspec.load_spec(pathlib.Path(".agent-fox/specs/01_my_feature"))

md = afspec.render_tasks(spec.tasks)
print(md)
```

### Rendering a Combined Document

`render_combined` produces a single markdown string containing the PRD verbatim
followed by all three rendered artifacts — equivalent to calling `render_requirements`,
`render_test_spec`, and `render_tasks` and concatenating the results with the PRD body.

```python
import pathlib
import afspec

spec = afspec.load_spec(pathlib.Path(".agent-fox/specs/01_my_feature"))

md = afspec.render_combined(spec)

# Save to disk for publishing.
pathlib.Path("spec_01_my_feature.md").write_text(md, encoding="utf-8")
```
