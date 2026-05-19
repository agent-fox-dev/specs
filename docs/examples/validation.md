# Validation Examples

The `afspec` libraries provide three levels of validation: full validation
(`Validate`/`validate`), schema-only validation (`ValidateSchema`), and
cross-file integrity checks (`ValidateCrossFile`). All validation functions return
a list of `ValidationError` values rather than stopping at the first error.

> **Note:** In Go, validation functions return `([]ValidationError, error)` — the
> first return value is the list of spec-level validation errors, and the second
> is a hard error (e.g., I/O failure) that prevented validation from completing.
> In Python, a hard failure raises `AfspecError`, while spec-level errors are
> returned as a list without raising an exception.

## Go

### Full Validation

`Validate` runs all three checks — schema, ID format, and cross-file integrity —
and returns every error found. Use this as your primary validation call before
saving or transitioning a spec.

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
		log.Fatalf("validation failed unexpectedly: %v", err)
	}
	if len(errs) > 0 {
		for _, e := range errs {
			fmt.Printf("[%s] %s#%s: %s\n", e.Severity, e.File, e.Path, e.Message)
		}
	} else {
		fmt.Println("Spec is valid.")
	}
}
```

### Schema-Only Validation

`ValidateSchema` checks each spec file against its JSON schema without running
cross-file integrity rules. Useful during incremental authoring when not all
cross-references are established yet.

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

	errs, err := afspec.ValidateSchema(spec)
	if err != nil {
		log.Fatalf("schema validation failed: %v", err)
	}
	fmt.Printf("Schema check: %d error(s)\n", len(errs))
}
```

### Cross-File Integrity Validation

`ValidateCrossFile` checks the seven cross-file integrity rules (e.g., every
requirement ID referenced in `test_spec.json` must exist in `requirements.json`).
Run this after schema validation passes to catch relational inconsistencies.

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

	errs, err := afspec.ValidateCrossFile(spec)
	if err != nil {
		log.Fatalf("cross-file validation failed: %v", err)
	}
	if len(errs) == 0 {
		fmt.Println("Cross-file integrity: OK")
	}
	for _, e := range errs {
		fmt.Printf("  [%s] %s#%s: %s\n", e.Severity, e.File, e.Path, e.Message)
	}
}
```

## Python

### Full Validation

`validate` runs schema + ID format + cross-file integrity checks and returns all
errors as a list. The function never raises on spec-level errors — only on hard
failures such as I/O errors or internal bugs. Unlike Go, no second return value
signals hard failures; those surface as exceptions instead.

```python
import pathlib
import afspec

spec = afspec.load_spec(pathlib.Path(".agent-fox/specs/01_my_feature"))

errors = afspec.validate(spec)
if errors:
    for e in errors:
        print(f"[{e.severity}] {e.file}#{e.path}: {e.message}")
else:
    print("Spec is valid.")
```

### Handling Validation Errors

`ValidationError` objects carry `severity` ("error" or "warning"), `file`,
`path` (JSON pointer), and `message`. Filter by severity to treat warnings
separately from blocking errors.

```python
import pathlib
import afspec

spec = afspec.load_spec(pathlib.Path(".agent-fox/specs/01_my_feature"))
errors = afspec.validate(spec)

blocking = [e for e in errors if e.severity == "error"]
warnings = [e for e in errors if e.severity == "warning"]

print(f"Blocking errors: {len(blocking)}, Warnings: {len(warnings)}")

if blocking:
    raise SystemExit(1)
```

### Schema-Only vs. Full Validation

Python does not expose `ValidateSchema` or `ValidateCrossFile` as standalone
public functions. The single `validate` function internally runs all three
checks. For incremental use, create a `BootstrapSpec` context manager — it runs
per-file schema validation on each `write_*` call and full validation on exit.

```python
import pathlib
import afspec

# Full validation in one call.
spec = afspec.load_spec(pathlib.Path(".agent-fox/specs/01_my_feature"))
all_errors = afspec.validate(spec)

# Contrast with Go which exposes ValidateSchema / ValidateCrossFile separately.
# In Python, use BootstrapSpec for incremental per-file schema validation.
print(f"Total errors: {len(all_errors)}")
```
