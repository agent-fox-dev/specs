package afspec

import (
	"path/filepath"

	"github.com/agent-fox/afspec/internal/discovery"
)

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
	return discovery.TopologicalOrder(g.Edges)
}

// DiscoverSpecs scans root for spec folders and builds a dependency graph.
// If root is empty, uses the current working directory.
func DiscoverSpecs(root string) (*DiscoveryResult, error) {
	dirs, err := discovery.ScanRoot(root)
	if err != nil {
		return nil, err
	}

	// Load metadata for each discovered directory.
	var metas []*discovery.SpecMetadata
	for _, dir := range dirs {
		meta, err := discovery.LoadMetadata(dir)
		if err != nil {
			// If we can't load metadata (e.g., corrupted prd.md), skip gracefully
			// but still include the entry as incomplete using directory name parsing.
			name := filepath.Base(dir)
			absDir, _ := filepath.Abs(dir)
			specID, specName, _ := discovery.ParseSpecDir(name)
			metas = append(metas, &discovery.SpecMetadata{
				Dir:      absDir,
				SpecID:   specID,
				SpecName: specName,
				Status:   "",
				Complete: false,
			})
			_ = err
			continue
		}
		metas = append(metas, meta)
	}

	// Build dependency graph.
	edges, err := discovery.BuildGraph(metas)
	if err != nil {
		return nil, err
	}

	// Convert internal metadata to public SpecEntry values.
	entries := make([]SpecEntry, 0, len(metas))
	for _, m := range metas {
		entries = append(entries, SpecEntry{
			Dir:      m.Dir,
			SpecID:   m.SpecID,
			SpecName: m.SpecName,
			Status:   Status(m.Status),
			Complete: m.Complete,
		})
	}

	return &DiscoveryResult{
		Entries: entries,
		Graph: &DependencyGraph{
			Edges: edges,
		},
	}, nil
}
