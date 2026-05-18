package version

// Version is the current af release version.
const Version = "0.0.0-dev"

// String returns the version string for CLI output.
func String() string {
	return Version
}
