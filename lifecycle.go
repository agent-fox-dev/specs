package afspec

import (
	"fmt"
	"strings"

	"github.com/agent-fox/afspec/internal/lifecycle"
	prdpkg "github.com/agent-fox/afspec/internal/prd"
)

const deprecationBanner = "SUPERSEDED: This specification has been superseded. Refer to the superseding spec for the current version."

// Transition applies a lifecycle state transition to spec and returns a NEW
// Spec with the updated state. The original spec is never modified.
//
// Legal transitions:
//
//	draft → active    (computes and stores intent_hash)
//	draft → archived
//	active → sealed
//	sealed → superseded  (adds deprecation banner to all artifacts)
//	sealed → archived
//
// Returns a *LifecycleError if the transition is illegal.
func Transition(spec *Spec, target Status) (*Spec, error) {
	if spec == nil || spec.PRD == nil {
		return nil, fmt.Errorf("Transition: spec or PRD is nil")
	}

	current := spec.PRD.Frontmatter.Status

	// Validate the transition against the legal edge set.
	if err := lifecycle.ValidateTransition(
		lifecycle.Status(current),
		lifecycle.Status(target),
	); err != nil {
		return nil, &LifecycleError{
			Current: current,
			Target:  target,
			Reason:  fmt.Sprintf("transition from %q to %q is not permitted", current, target),
		}
	}

	// Deep-copy the spec so we never mutate the caller's value.
	newSpec := deepCopySpec(spec)

	// Apply the new status.
	newSpec.PRD.Frontmatter.Status = target

	switch {
	case current == StatusDraft && target == StatusActive:
		// Compute and store the intent_hash.
		intentBody, err := prdpkg.ExtractIntent(newSpec.PRD.Body)
		if err != nil {
			return nil, fmt.Errorf("Transition draft→active: %w", err)
		}
		hash := lifecycle.ComputeIntentHash(intentBody)
		newSpec.PRD.Frontmatter.IntentHash = &hash

	case current == StatusSealed && target == StatusSuperseded:
		// Add the deprecation banner to all four artifacts.
		applyDeprecationBanner(newSpec)
	}

	return newSpec, nil
}

// ComputeIntentHash computes the SHA-256 hash of the normalised Intent section
// body. If the body contains a `## Intent` section header, only that section's
// text is hashed (useful when passing a full PRD body). If no such section is
// present, the entire body is normalised and hashed directly (useful when
// passing the intent text alone).
//
// Returns a 64-character lowercase hex string.
func ComputeIntentHash(body string) string {
	intentBody, err := prdpkg.ExtractIntent(body)
	if err != nil {
		// No ## Intent section found — treat the full body as the intent text
		// so that callers can pass the intent body directly (e.g. property tests).
		return lifecycle.ComputeIntentHash(body)
	}
	return lifecycle.ComputeIntentHash(intentBody)
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

// deepCopySpec returns a deep copy of spec suitable for mutation.
// All nested pointers are duplicated so the caller's spec is unaffected.
func deepCopySpec(s *Spec) *Spec {
	if s == nil {
		return nil
	}

	newSpec := &Spec{
		Dir: s.Dir,
	}

	// Copy PRD
	if s.PRD != nil {
		prd := *s.PRD
		fm := s.PRD.Frontmatter
		// Copy pointer slices in Frontmatter
		fm.Supersedes = copyStringSlice(s.PRD.Frontmatter.Supersedes)
		fm.Tags = copyStringSlice(s.PRD.Frontmatter.Tags)
		if s.PRD.Frontmatter.IntentHash != nil {
			h := *s.PRD.Frontmatter.IntentHash
			fm.IntentHash = &h
		}
		prd.Frontmatter = fm
		newSpec.PRD = &prd
	}

	// Copy Requirements
	if s.Requirements != nil {
		req := *s.Requirements
		newSpec.Requirements = &req
	}

	// Copy TestSpec
	if s.TestSpec != nil {
		ts := *s.TestSpec
		newSpec.TestSpec = &ts
	}

	// Copy Tasks
	if s.Tasks != nil {
		tasks := *s.Tasks
		newSpec.Tasks = &tasks
	}

	return newSpec
}

// copyStringSlice returns a new slice with the same elements as src.
func copyStringSlice(src []string) []string {
	if src == nil {
		return nil
	}
	dst := make([]string, len(src))
	copy(dst, src)
	return dst
}

// applyDeprecationBanner adds the SUPERSEDED notice to all four artifacts.
func applyDeprecationBanner(spec *Spec) {
	// PRD body: prepend a markdown blockquote banner.
	if spec.PRD != nil {
		banner := "> **SUPERSEDED**: " + deprecationBanner + "\n\n"
		if !strings.Contains(spec.PRD.Body, "SUPERSEDED") {
			spec.PRD.Body = banner + spec.PRD.Body
		}
	}

	// JSON artifacts: set the $comment field.
	if spec.Requirements != nil && spec.Requirements.Comment == "" {
		spec.Requirements.Comment = deprecationBanner
	}
	if spec.TestSpec != nil && spec.TestSpec.Comment == "" {
		spec.TestSpec.Comment = deprecationBanner
	}
	if spec.Tasks != nil && spec.Tasks.Comment == "" {
		spec.Tasks.Comment = deprecationBanner
	}
}
