# Lifecycle Management Examples

Specs move through a defined lifecycle: **draft → active → sealed**, with
side-exits to **archived** or **superseded**. The `Transition`/`transition`
function enforces the state machine and computes the `intent_hash` on the
`draft → active` transition.

> **Note:** In Go, `Transition` returns `(*Spec, error)` — the updated spec or an
> error if the transition is illegal. In Python, `transition` raises `LifecycleError`
> on an illegal transition and returns the updated `Spec` on success.

## Go

### Transitioning a Spec from Draft to Active

When a spec moves from `draft` to `active`, the library computes and stores an
`intent_hash` — a SHA-256 of the normalized `## Intent` section in `prd.md`. This
hash is later used to detect unauthorized mutation of a sealed spec's intent.

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

	// Transition from draft → active.
	active, err := afspec.Transition(spec, afspec.StatusActive)
	if err != nil {
		log.Fatalf("transition: %v", err)
	}

	fmt.Printf("Status: %s\n", active.PRD.Frontmatter.Status)
	fmt.Printf("Intent hash set: %v\n", active.PRD.Frontmatter.IntentHash != nil)

	if err := afspec.SaveSpec(".agent-fox/specs/01_my_feature", active); err != nil {
		log.Fatalf("save: %v", err)
	}
}
```

### Transitioning to Sealed

Sealing a spec freezes it. After sealing, `SaveSpec` will return an error if
the caller attempts to modify the `## Intent` section. Only `active` specs can
be sealed.

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

	// Must be active before sealing.
	active, err := afspec.Transition(spec, afspec.StatusActive)
	if err != nil {
		log.Fatalf("draft→active: %v", err)
	}

	sealed, err := afspec.Transition(active, afspec.StatusSealed)
	if err != nil {
		log.Fatalf("active→sealed: %v", err)
	}

	fmt.Printf("Status: %s\n", sealed.PRD.Frontmatter.Status)
}
```

### Handling Illegal Transitions

`Transition` returns a `LifecycleError` when the requested transition is not
permitted by the state machine. Inspect the error to understand which transitions
are legal from the current state.

```go
package main

import (
	"errors"
	"fmt"
	"log"

	"github.com/agent-fox/afspec"
)

func main() {
	spec, err := afspec.LoadSpec(".agent-fox/specs/01_my_feature")
	if err != nil {
		log.Fatalf("load: %v", err)
	}

	// draft → sealed is illegal; must go through active first.
	_, err = afspec.Transition(spec, afspec.StatusSealed)
	if err != nil {
		var le *afspec.LifecycleError
		if errors.As(err, &le) {
			fmt.Printf("Lifecycle error: cannot transition %s → %s\n",
				le.From, le.To)
		} else {
			log.Fatalf("unexpected error: %v", err)
		}
	}
}
```

### Archiving a Spec

A spec can be archived from `draft` or `sealed` (not from `active`). Archived
specs are immutable and excluded from discovery by default.

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

	archived, err := afspec.Transition(spec, afspec.StatusArchived)
	if err != nil {
		log.Fatalf("transition to archived: %v", err)
	}

	fmt.Printf("Status: %s\n", archived.PRD.Frontmatter.Status)
	if err := afspec.SaveSpec(".agent-fox/specs/01_my_feature", archived); err != nil {
		log.Fatalf("save: %v", err)
	}
}
```

## Python

### Transitioning a Spec from Draft to Active

Python's `transition` function accepts the target status as a string and raises
`LifecycleError` on an illegal transition — unlike Go which returns an error
value. On the `draft → active` transition it sets the `intent_hash` field on the
frontmatter, exactly as the Go library does.

```python
import pathlib
import afspec

spec = afspec.load_spec(pathlib.Path(".agent-fox/specs/01_my_feature"))

# Transition from draft → active.
active = afspec.transition(spec, "active")

print(f"Status: {active.prd.frontmatter.status}")
print(f"Intent hash set: {active.prd.frontmatter.intent_hash is not None}")

afspec.save_spec(active, pathlib.Path(".agent-fox/specs/01_my_feature"))
```

### Transitioning to Sealed

Only an `active` spec can be sealed. After sealing the intent is frozen; the
library will reject any subsequent save that alters the `## Intent` section.

```python
import pathlib
import afspec

spec = afspec.load_spec(pathlib.Path(".agent-fox/specs/01_my_feature"))

active = afspec.transition(spec, "active")
sealed = afspec.transition(active, "sealed")

print(f"Status: {sealed.prd.frontmatter.status}")
```

### Handling Illegal Transitions

Unlike Go, Python raises `LifecycleError` (a subclass of `AfspecError`) rather
than returning an error value. Wrap the call in `try/except` to handle illegal
transitions gracefully.

```python
import pathlib
import afspec
from afspec import LifecycleError

spec = afspec.load_spec(pathlib.Path(".agent-fox/specs/01_my_feature"))

try:
    # draft → sealed is not a legal transition.
    sealed = afspec.transition(spec, "sealed")
except LifecycleError as exc:
    print(f"Lifecycle error: {exc}")
```

### Archiving a Spec

Archiving works from `draft` or `sealed`. The Python `transition` call mirrors the
Go `Transition` call; the only difference is that failure surfaces as an exception
rather than a second return value.

```python
import pathlib
import afspec

spec = afspec.load_spec(pathlib.Path(".agent-fox/specs/01_my_feature"))

archived = afspec.transition(spec, "archived")
print(f"Status: {archived.prd.frontmatter.status}")

afspec.save_spec(archived, pathlib.Path(".agent-fox/specs/01_my_feature"))
```
