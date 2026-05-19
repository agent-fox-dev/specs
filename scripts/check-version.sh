#!/usr/bin/env bash
# check-version.sh — validate that a git tag version matches the version in library code.
#
# Usage: scripts/check-version.sh <language> <tag>
#   language: "go" or "python"
#   tag:      full git tag string (e.g., "pkg/afspec/v1.2.3" or "afspec-v1.2.3")
#
# Exit codes:
#   0 — version match
#   1 — version mismatch, invalid tag format, or invalid input

set -euo pipefail

# Semver regex: MAJOR.MINOR.PATCH with no leading zeros
SEMVER_RE='^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$'
GO_TAG_RE='^pkg/afspec/v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$'
PY_TAG_RE='^afspec-v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$'

usage() {
    echo "Usage: $0 <language> <tag>" >&2
    echo "  language: 'go' or 'python'" >&2
    echo "  tag:      e.g., 'pkg/afspec/v1.2.3' or 'afspec-v1.2.3'" >&2
    exit 1
}

if [ $# -ne 2 ]; then
    echo "Error: expected 2 arguments, got $#" >&2
    usage
fi

LANG_ARG="$1"
TAG="$2"

case "$LANG_ARG" in
    go)
        # Validate Go tag format
        if ! echo "$TAG" | grep -qE "$GO_TAG_RE"; then
            echo "Error: tag '$TAG' does not match Go tag format 'pkg/afspec/vMAJOR.MINOR.PATCH'" >&2
            echo "Expected format: pkg/afspec/v{MAJOR}.{MINOR}.{PATCH} (semver, no leading zeros)" >&2
            exit 1
        fi

        # Extract version from tag (strip "pkg/afspec/v" prefix)
        TAG_VERSION="${TAG#pkg/afspec/v}"

        # Validate extracted version is semver (belt-and-suspenders)
        if ! echo "$TAG_VERSION" | grep -qE "$SEMVER_RE"; then
            echo "Error: extracted version '$TAG_VERSION' is not valid semver" >&2
            exit 1
        fi

        # Read version from internal/version/version.go
        VERSION_FILE="internal/version/version.go"
        if [ ! -f "$VERSION_FILE" ]; then
            echo "Error: $VERSION_FILE not found (run from repo root)" >&2
            exit 1
        fi

        # Extract the version string from: const Version = "x.y.z"
        CODE_VERSION=$(grep 'const Version' "$VERSION_FILE" | sed 's/.*"\([^"]*\)".*/\1/')

        if [ -z "$CODE_VERSION" ]; then
            echo "Error: could not extract Version constant from $VERSION_FILE" >&2
            exit 1
        fi

        if [ "$TAG_VERSION" != "$CODE_VERSION" ]; then
            echo "Error: version mismatch — tag has '$TAG_VERSION', code has '$CODE_VERSION'" >&2
            exit 1
        fi

        echo "Version match: $TAG_VERSION"
        exit 0
        ;;

    python)
        # Validate Python tag format
        if ! echo "$TAG" | grep -qE "$PY_TAG_RE"; then
            echo "Error: tag '$TAG' does not match Python tag format 'afspec-vMAJOR.MINOR.PATCH'" >&2
            echo "Expected format: afspec-v{MAJOR}.{MINOR}.{PATCH} (semver, no leading zeros)" >&2
            exit 1
        fi

        # Extract version from tag (strip "afspec-v" prefix)
        TAG_VERSION="${TAG#afspec-v}"

        # Validate extracted version is semver (belt-and-suspenders)
        if ! echo "$TAG_VERSION" | grep -qE "$SEMVER_RE"; then
            echo "Error: extracted version '$TAG_VERSION' is not valid semver" >&2
            exit 1
        fi

        # Read version from pyproject.toml
        PYPROJECT_FILE="pyproject.toml"
        if [ ! -f "$PYPROJECT_FILE" ]; then
            echo "Error: $PYPROJECT_FILE not found (run from repo root)" >&2
            exit 1
        fi

        # Extract version from [project] section: version = "x.y.z"
        CODE_VERSION=$(grep -E '^[[:space:]]*version[[:space:]]*=' "$PYPROJECT_FILE" | \
            head -1 | sed 's/.*"\([^"]*\)".*/\1/')

        if [ -z "$CODE_VERSION" ]; then
            echo "Error: could not extract version from $PYPROJECT_FILE" >&2
            exit 1
        fi

        if [ "$TAG_VERSION" != "$CODE_VERSION" ]; then
            echo "Error: version mismatch — tag has '$TAG_VERSION', code has '$CODE_VERSION'" >&2
            exit 1
        fi

        echo "Version match: $TAG_VERSION"
        exit 0
        ;;

    *)
        echo "Error: unknown language '$LANG_ARG'; must be 'go' or 'python'" >&2
        usage
        ;;
esac
