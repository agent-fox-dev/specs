ROOT_DIR := $(shell git rev-parse --show-toplevel)
BIN_DIR  := $(ROOT_DIR)/bin

GO_BIN   := $(BIN_DIR)/migration-go
GO_OUT   := $(ROOT_DIR)/examples/migration/01_audit_hub_go
PY_OUT   := $(CURDIR)/01_audit_hub_python

EXPECTED_FILES := prd.md requirements.json tasks.json test_spec.json

.PHONY: all clean setup setup-go setup-python build run-go run-python test compare

all: check

# ── Setup ───────────────────────────────────────────────────────────

setup: setup-go setup-python

setup-go:
	$(eval SPECLIB_VER := $(shell GOPROXY=direct go list -m -f '{{.Version}}' github.com/agent-fox-dev/speclib-go@latest))
	go mod edit -replace github.com/af/speclib=github.com/agent-fox-dev/speclib-go@$(SPECLIB_VER)
	go mod tidy

setup-python:
	uv lock --upgrade-package afspec
	uv sync

# ── Build ───────────────────────────────────────────────────────────

build: setup-go
	go build -o $(GO_BIN) ./main.go

# ── Run ─────────────────────────────────────────────────────────────

run-go: build
	cd $(ROOT_DIR) && $(GO_BIN)

run-python: setup-python
	uv run python main.py

# ── Test ────────────────────────────────────────────────────────────

check: clean setup build
	@rm -rf $(GO_OUT) $(PY_OUT)
	@cd $(ROOT_DIR) && $(GO_BIN) 2>/dev/null
	@for f in $(EXPECTED_FILES); do \
		if [ ! -f "$(GO_OUT)/$$f" ]; then \
			echo "FAIL [go]: missing $$f"; exit 1; \
		fi; \
	done
	@echo "ok   [go] — $(GO_OUT)"
	@uv run python main.py >/dev/null
	@for f in $(EXPECTED_FILES); do \
		if [ ! -f "$(PY_OUT)/$$f" ]; then \
			echo "FAIL [python]: missing $$f"; exit 1; \
		fi; \
	done
	@echo "ok   [python] — $(PY_OUT)"
	@uv run python compare.py
	@rm -rf $(GO_OUT) $(PY_OUT)
	@echo "all examples passed"

# ── Clean ───────────────────────────────────────────────────────────

clean:
	rm -rf $(GO_OUT) $(PY_OUT) $(GO_BIN)
