# Go vs. Python: Side-by-Side Comparison

This document shows equivalent operations in the Go and Python `afspec` libraries
side by side. Each section notes any behavioral differences between the two
implementations.

## Loading a Spec

Both libraries read all four spec files from a directory and return a populated
spec object. The main behavioral difference is error surfacing: Go returns
`(*Spec, error)` while Python raises `SpecValidationError` on failure.

**Go:**

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
	fmt.Println(spec.PRD.Frontmatter.SpecName)
}
```

**Python:**

Unlike Go, Python raises an exception instead of returning an error value. Use
`try/except` to handle load failures in production code.

```python
import pathlib
import afspec

spec = afspec.load_spec(pathlib.Path(".agent-fox/specs/01_my_feature"))
print(spec.prd.frontmatter.spec_name)
```

## Saving a Spec

Both libraries write all four spec files atomically and auto-update `updated_at`
and the `coverage` field. The function name differs (`SaveSpec` vs. `save_spec`)
but the behavior is identical.

**Go:**

```go
package main

import (
	"log"

	"github.com/agent-fox/afspec"
)

func main() {
	spec, err := afspec.LoadSpec(".agent-fox/specs/01_my_feature")
	if err != nil {
		log.Fatalf("load: %v", err)
	}
	if err := afspec.SaveSpec(".agent-fox/specs/01_my_feature", spec); err != nil {
		log.Fatalf("save: %v", err)
	}
}
```

**Python:**

Python's `save_spec` raises `AfspecError` on failure rather than returning an
error value.

```python
import pathlib
import afspec

spec = afspec.load_spec(pathlib.Path(".agent-fox/specs/01_my_feature"))
afspec.save_spec(spec, pathlib.Path(".agent-fox/specs/01_my_feature"))
```

## Validating a Spec

Both libraries return a list of `ValidationError` objects covering schema errors,
ID-format errors, and cross-file integrity errors. In Go, full validation is split
into three public functions (`Validate`, `ValidateSchema`, `ValidateCrossFile`).
In Python there is only one public function (`validate`) that runs all checks;
there is no direct Python equivalent to `ValidateSchema` or `ValidateCrossFile`
as standalone functions.

**Go:**

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
	errs, err := afspec.Validate(spec)
	if err != nil {
		log.Fatalf("validation error: %v", err)
	}
	fmt.Printf("%d validation issue(s)\n", len(errs))

	// Go also exposes ValidateSchema and ValidateCrossFile as separate functions.
	// Python has no direct equivalent; use validate() for all checks.
	schemaErrs, _ := afspec.ValidateSchema(spec)
	crossErrs, _ := afspec.ValidateCrossFile(spec)
	fmt.Printf("Schema: %d, Cross-file: %d\n", len(schemaErrs), len(crossErrs))
}
```

**Python:**

Python exposes only `validate()`, which combines schema and cross-file checks.
The closest alternative to Go's standalone `ValidateSchema` is using `BootstrapSpec`,
which performs per-file schema validation on each `write_*` call.

```python
import pathlib
import afspec

spec = afspec.load_spec(pathlib.Path(".agent-fox/specs/01_my_feature"))
errors = afspec.validate(spec)
print(f"{len(errors)} validation issue(s)")

# Note: Python has no direct equivalent to Go's ValidateSchema or ValidateCrossFile
# as standalone functions. validate() always runs all checks.
```

## Rendering to Markdown

Both libraries render spec artifacts to markdown with the same function names
(Go uses PascalCase, Python uses snake_case). In Go the functions return
`([]byte, error)`; in Python they return `str` and raise on failure.

**Go:**

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
	md, err := afspec.RenderCombined(spec)
	if err != nil {
		log.Fatalf("render: %v", err)
	}
	fmt.Println(string(md))
}
```

**Python:**

Python's render functions return `str` instead of `[]byte`. There is no need to
convert the result for string operations; call `.encode()` if you need bytes.

```python
import pathlib
import afspec

spec = afspec.load_spec(pathlib.Path(".agent-fox/specs/01_my_feature"))
md = afspec.render_combined(spec)
print(md)
```

## Lifecycle Transitions

Both libraries enforce the same state machine: `draft → active → sealed`, with
side-exits to `archived` or `superseded`. The draft → active transition computes
the `intent_hash` in both implementations. The key behavioral difference is error
signaling: Go returns `(*Spec, error)`, Python raises `LifecycleError`.

**Go:**

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
	active, err := afspec.Transition(spec, afspec.StatusActive)
	if err != nil {
		log.Fatalf("transition: %v", err)
	}
	fmt.Printf("Status: %s, intent_hash set: %v\n",
		active.PRD.Frontmatter.Status,
		active.PRD.Frontmatter.IntentHash != nil,
	)
}
```

**Python:**

Python accepts the target status as a plain string (e.g., `"active"`) rather than
a typed constant. On an illegal transition it raises `LifecycleError` instead of
returning an error value.

```python
import pathlib
import afspec

spec = afspec.load_spec(pathlib.Path(".agent-fox/specs/01_my_feature"))

active = afspec.transition(spec, "active")
print(f"Status: {active.prd.frontmatter.status}, "
      f"intent_hash set: {active.prd.frontmatter.intent_hash is not None}")
```

## Bootstrap (Incremental Spec Creation)

Both libraries allow building a new spec file-by-file with per-file schema
validation. Go uses a builder pattern (`*Bootstrap`); Python uses a context
manager (`BootstrapSpec`). In Go, `Finalize()` must be called explicitly to run
full validation. In Python, full validation runs automatically when the `with`
block exits normally.

**Go:**

```go
package main

import (
	"fmt"
	"log"

	"github.com/agent-fox/afspec"
)

func main() {
	bs, err := afspec.NewBootstrap(".agent-fox/specs/05_new_spec", "05", "new_spec")
	if err != nil {
		log.Fatalf("new bootstrap: %v", err)
	}
	// Write artifacts individually; each call validates against its schema.
	bs.WritePRD(prd)
	bs.WriteRequirements(req)
	bs.WriteTestSpec(ts)
	bs.WriteTasks(tasks)

	// Must call Finalize() to complete cross-file validation.
	spec, err := bs.Finalize()
	if err != nil {
		log.Fatalf("finalize: %v", err)
	}
	fmt.Printf("Created: %s\n", spec.PRD.Frontmatter.SpecName)
}
```

**Python:**

The context manager automatically calls full validation on `__exit__`. If any
`write_*` call fails schema validation, `SpecValidationError` is raised and the
`with` block exits immediately. Access the completed spec via `bs.result` after
the `with` block.

```python
import pathlib
import afspec
from afspec import BootstrapSpec

with BootstrapSpec(pathlib.Path(".agent-fox/specs"), "05", "new_spec") as bs:
    bs.write_prd(prd)
    bs.write_requirements(req)
    bs.write_test_spec(ts)
    bs.write_tasks(tasks)
# Full validation runs automatically on context exit.

spec = bs.result
print(f"Created: {spec.prd.frontmatter.spec_name}")
```

## Spec Discovery

Both libraries scan a spec root directory for spec folders matching the
`{NN}_{name}` naming convention, read their `prd.md` frontmatter, and return a
dependency graph. The Go function is `DiscoverSpecs`; the Python function is
`discover`. In Go the dependency graph exposes `TopologicalOrder() ([]string, error)`;
in Python the equivalent method is `topological_sort()` which raises `AfspecError`
on cycles instead of returning an error.

**Go:**

```go
package main

import (
	"fmt"
	"log"

	"github.com/agent-fox/afspec"
)

func main() {
	result, err := afspec.DiscoverSpecs(".agent-fox/specs")
	if err != nil {
		log.Fatalf("discover: %v", err)
	}
	for _, entry := range result.Entries {
		fmt.Printf("  %s %s (complete: %v)\n", entry.SpecID, entry.SpecName, entry.Complete)
	}
	order, err := result.Graph.TopologicalOrder()
	if err != nil {
		log.Fatalf("topological order: %v", err)
	}
	fmt.Println("Build order:", order)
}
```

**Python:**

`discover` accepts `None` to use the current directory, while Go's `DiscoverSpecs`
always requires an explicit path. The `dependency_graph.topological_sort()` method
raises `AfspecError` on cycles rather than returning `(order, error)`.

```python
import pathlib
import afspec

result = afspec.discover(pathlib.Path(".agent-fox/specs"))
for entry in result.entries:
    print(f"  {entry.spec_id} {entry.spec_name} (complete: {entry.complete})")

order = result.dependency_graph.topological_sort()
print("Build order:", order)
```
