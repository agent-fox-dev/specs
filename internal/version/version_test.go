package version

import "testing"

func TestString(t *testing.T) {
	if got := String(); got != Version {
		t.Fatalf("String() = %q, want %q", got, Version)
	}
}
