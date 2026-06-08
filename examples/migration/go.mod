module github.com/agent-fox-dev/af-spec/examples/migration

go 1.26.3

require github.com/af/speclib v0.0.0-00010101000000-000000000000

require (
	github.com/santhosh-tekuri/jsonschema/v6 v6.0.2 // indirect
	golang.org/x/text v0.14.0 // indirect
	gopkg.in/yaml.v3 v3.0.1 // indirect
)

replace github.com/af/speclib => github.com/agent-fox-dev/speclib-go v0.0.0-20260608111937-8c7a5240a8ed
