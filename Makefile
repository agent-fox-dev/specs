.PHONY: check test lint build test-go test-python lint-go lint-python

check: lint test

test: test-go test-python

lint: lint-go lint-python

test-go:
	@if [ -f go.mod ]; then \
		go test -count=1 ./...; \
	else \
		echo "Skipping Go tests (no go.mod found)"; \
	fi

lint-go:
	@if [ -f go.mod ]; then \
		go vet ./... && golangci-lint run; \
	else \
		echo "Skipping Go linting (no go.mod found)"; \
	fi

test-python:
	@if [ -f pyproject.toml ] && [ -f uv.lock ]; then \
		uv run --all-extras pytest -q; \
	else \
		echo "Skipping Python tests (no pyproject.toml or uv.lock found)"; \
	fi

lint-python:
	@if [ -f pyproject.toml ] && [ -f uv.lock ]; then \
		uv run --all-extras ruff check && uv run --all-extras mypy afspec/; \
	else \
		echo "Skipping Python linting (no pyproject.toml or uv.lock found)"; \
	fi

build:
	mkdir -p bin
	go build -o bin/af ./cmd/af/
