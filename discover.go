package afspec

import "errors"

// DiscoveryResult holds the list of discovered specs and their dependency graph.
type DiscoveryResult struct {
	Entries []SpecEntry
	Graph   *DependencyGraph
}

// SpecEntry holds metadata for a single discovered spec folder.
type SpecEntry struct {
	Dir      string // absolute path to spec folder
	SpecID   string
	SpecName string
	Status   Status
	Complete bool // true if all 4 files present
}

// DependencyGraph is an adjacency-list graph of spec dependencies.
type DependencyGraph struct {
	// Edges: spec_id → list of spec_ids it depends on.
	Edges map[string][]string
}

// TopologicalOrder returns spec_ids in dependency order (dependencies first).
// Returns an error if a cycle is detected.
func (g *DependencyGraph) TopologicalOrder() ([]string, error) {
	return nil, errors.New("not implemented")
}

// DiscoverSpecs scans root for spec folders and builds a dependency graph.
// If root is empty, uses the current working directory.
func DiscoverSpecs(root string) (*DiscoveryResult, error) {
	return nil, errors.New("not implemented")
}
