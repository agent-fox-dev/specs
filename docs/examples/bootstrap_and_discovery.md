# Bootstrap and Discovery Examples

The `afspec` libraries provide two higher-level workflows beyond load/save: the
**bootstrap** API for creating new specs file-by-file with incremental validation,
and the **discovery** API for scanning a spec root and building a dependency graph
of all specs.

## Go

### Creating a New Spec with Bootstrap

`NewBootstrap` creates a new spec folder and returns a `*Bootstrap` builder.
Each `Write*` call writes one artifact file and runs schema validation on that
file immediately. `Finalize` runs full validation across all four files and
returns the completed `*Spec`.

```go
package main

import (
	"fmt"
	"log"

	"github.com/agent-fox/afspec"
)

func main() {
	bs, err := afspec.NewBootstrap(".agent-fox/specs/05_my_feature", "05", "my_feature")
	if err != nil {
		log.Fatalf("new bootstrap: %v", err)
	}

	// Write each artifact in order; each call validates the file against its schema.
	if err := bs.WritePRD(prd); err != nil {
		log.Fatalf("write prd: %v", err)
	}
	if err := bs.WriteRequirements(req); err != nil {
		log.Fatalf("write requirements: %v", err)
	}
	if err := bs.WriteTestSpec(ts); err != nil {
		log.Fatalf("write test spec: %v", err)
	}
	if err := bs.WriteTasks(tasks); err != nil {
		log.Fatalf("write tasks: %v", err)
	}

	// Finalize runs cross-file validation and returns the complete Spec.
	spec, err := bs.Finalize()
	if err != nil {
		log.Fatalf("finalize: %v", err)
	}
	fmt.Printf("Created spec: %s\n", spec.PRD.Frontmatter.SpecName)
}
```

### Discovering All Specs in a Root

`DiscoverSpecs` scans a directory for spec folders matching the `{NN}_{name}`
naming convention, reads each spec's `prd.md` frontmatter, and builds a
dependency graph from cross-spec references. The `archive/` subdirectory is
excluded automatically.

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

	fmt.Printf("Found %d spec(s):\n", len(result.Entries))
	for _, entry := range result.Entries {
		fmt.Printf("  %s (%s) — complete: %v\n",
			entry.SpecID, entry.SpecName, entry.Complete)
	}
}
```

### Topological Order

`DependencyGraph.TopologicalOrder` returns spec IDs ordered so that each spec
appears after all its dependencies. It returns an error if the dependency graph
contains a cycle.

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

	order, err := result.Graph.TopologicalOrder()
	if err != nil {
		log.Fatalf("topological order (cycle detected?): %v", err)
	}

	fmt.Println("Build order:")
	for i, id := range order {
		fmt.Printf("  %d. %s\n", i+1, id)
	}
}
```

## Python

### Creating a New Spec with Bootstrap

Python uses a context manager (`BootstrapSpec`) rather than a builder object.
Each `write_*` call runs per-file schema validation. Full validation runs when the
`with` block exits normally. Unlike the Go builder where errors are returned,
Python raises `SpecValidationError` on validation failure.

```python
import pathlib
import afspec
from afspec import BootstrapSpec

with BootstrapSpec(pathlib.Path(".agent-fox/specs"), "05", "my_feature") as bs:
    bs.write_prd(prd)           # schema-validates prd.md immediately
    bs.write_requirements(req)  # schema-validates requirements.json
    bs.write_test_spec(ts)      # schema-validates test_spec.json
    bs.write_tasks(tasks)       # schema-validates tasks.json
# Full cross-file validation runs on context exit.

spec = bs.result
print(f"Created spec: {spec.prd.frontmatter.spec_name}")
```

### Discovering All Specs in a Root

`discover` scans a spec root directory (defaulting to the current directory if
`None` is passed), reads each spec's `prd.md` frontmatter, and returns a
`DiscoveryResult` containing entries and a dependency graph. Like the Go version,
`archive/` is excluded automatically.

```python
import pathlib
import afspec

result = afspec.discover(pathlib.Path(".agent-fox/specs"))

print(f"Found {len(result.entries)} spec(s):")
for entry in result.entries:
    print(f"  {entry.spec_id} ({entry.spec_name}) — complete: {entry.complete}")
```

### Topological Order

`DependencyGraph.topological_sort()` returns spec IDs in dependency order. It
raises `AfspecError` if a cycle is detected. Unlike Go's `TopologicalOrder` which
returns `([]string, error)`, Python raises on failure rather than returning an
error value.

```python
import pathlib
import afspec

result = afspec.discover(pathlib.Path(".agent-fox/specs"))

try:
    order = result.dependency_graph.topological_sort()
    print("Build order:")
    for i, spec_id in enumerate(order, 1):
        print(f"  {i}. {spec_id}")
except afspec.AfspecError as exc:
    print(f"Cycle detected: {exc}")
```

### Checking the Schema Version

`schema_version()` returns the integer schema version bundled with the library.
This function exists only in the Python library; in Go the schema version is
exposed as a package-level constant (`SchemaVersion`). This is one behavioral
difference between the two libraries: Go uses a constant, Python uses a function.

```python
import afspec

version = afspec.schema_version()
print(f"afspec schema version: {version}")
```
