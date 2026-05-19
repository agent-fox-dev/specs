# Loading and Saving Examples

The `afspec` libraries provide functions for loading spec packages from disk into
memory and saving them back. A spec package is a directory containing four files:
`prd.md`, `requirements.json`, `test_spec.json`, and `tasks.json`.

## Go

### Loading a Spec

The `LoadSpec` function reads all four spec files from a directory and returns a
fully populated `*Spec`. Files are parsed and validated for well-formedness; call
`Validate` for full cross-file integrity checking.

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
	fmt.Printf("Loaded spec %s (status: %s)\n",
		spec.PRD.Frontmatter.SpecName,
		spec.PRD.Frontmatter.Status,
	)
}
```

### Saving a Spec

`SaveSpec` writes all four spec files to the given directory. Before writing it
sets `updated_at` to the current UTC timestamp and recomputes `coverage` in
`test_spec.json`. Writes are atomic (write-to-temp-then-rename), so partial
outputs are not left on disk if an error occurs.

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

	// Mutate the spec in memory, then persist.
	spec.PRD.Frontmatter.Tags = append(spec.PRD.Frontmatter.Tags, "reviewed")

	if err := afspec.SaveSpec(".agent-fox/specs/01_my_feature", spec); err != nil {
		log.Fatalf("save: %v", err)
	}
}
```

### Round-Trip (Load → Modify → Save → Reload)

A load → save → load cycle is idempotent: after the first save (which updates
`updated_at` and recomputes `coverage`), subsequent save/load pairs produce
byte-identical JSON files.

```go
package main

import (
	"fmt"
	"log"

	"github.com/agent-fox/afspec"
)

func main() {
	dir := ".agent-fox/specs/01_my_feature"

	first, err := afspec.LoadSpec(dir)
	if err != nil {
		log.Fatalf("load: %v", err)
	}

	if err := afspec.SaveSpec(dir, first); err != nil {
		log.Fatalf("save: %v", err)
	}

	second, err := afspec.LoadSpec(dir)
	if err != nil {
		log.Fatalf("reload: %v", err)
	}

	fmt.Printf("SpecName after round-trip: %s\n", second.PRD.Frontmatter.SpecName)
}
```

## Python

### Loading a Spec

The `load_spec` function reads all four spec artifacts from a directory path and
returns a `Spec` dataclass. It raises `SpecValidationError` if any file is
missing or malformed. Unlike the Go library which returns an `(value, error)`
pair, the Python library raises an exception on failure.

```python
import pathlib
import afspec

spec = afspec.load_spec(pathlib.Path(".agent-fox/specs/01_my_feature"))
print(f"Loaded spec {spec.prd.frontmatter.spec_name} (status: {spec.prd.frontmatter.status})")
```

### Saving a Spec

`save_spec` writes all four spec artifacts to the given directory. Like the Go
version it sets `updated_at` automatically and recomputes `coverage`. On failure
it raises `AfspecError`. Note: unlike Go which returns an error value, Python
raises an exception — wrap in try/except for production code.

```python
import pathlib
import afspec

spec = afspec.load_spec(pathlib.Path(".agent-fox/specs/01_my_feature"))

# Mutate in memory, then persist.
spec.prd.frontmatter.tags.append("reviewed")

afspec.save_spec(spec, pathlib.Path(".agent-fox/specs/01_my_feature"))
```

### Round-Trip (Load → Modify → Save → Reload)

The Python library guarantees the same round-trip idempotency as the Go library.
After the first save, subsequent save/load pairs produce byte-identical JSON.

```python
import pathlib
import afspec

dir_path = pathlib.Path(".agent-fox/specs/01_my_feature")

first = afspec.load_spec(dir_path)
afspec.save_spec(first, dir_path)

second = afspec.load_spec(dir_path)
print(f"SpecName after round-trip: {second.prd.frontmatter.spec_name}")
```
