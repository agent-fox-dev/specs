.PHONY: check test lint build

check: lint test

test:
	go test -count=1 ./...

lint:
	go vet ./...

build:
	mkdir -p bin
	go build -o bin/af ./cmd/af/
