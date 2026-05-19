package discovery

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

// tasksMinimal is the minimal tasks.json structure needed to read dependencies.
type tasksMinimal struct {
	Dependencies []taskDepMinimal `json:"dependencies"`
}

type taskDepMinimal struct {
	DependsOnSpec string `json:"depends_on_spec"`
}

// BuildGraph constructs an adjacency-list dependency graph from tasks.json
// files found in each spec directory.
//
// The returned map has the invariant: edges[A] = [B, ...] means spec A depends
// on spec B (B must be processed before A). Every discovered spec ID appears as
// a key, even if it has no dependencies.
//
// Returns an error if a cycle is detected.
func BuildGraph(entries []*SpecMetadata) (map[string][]string, error) {
	edges := make(map[string][]string)

	// Ensure every spec has an entry, even with no deps.
	for _, e := range entries {
		edges[e.SpecID] = nil
	}

	for _, e := range entries {
		tasksPath := filepath.Join(e.Dir, "tasks.json")
		data, err := os.ReadFile(tasksPath)
		if err != nil {
			if os.IsNotExist(err) {
				continue // tasks.json optional for incomplete specs
			}
			return nil, fmt.Errorf("read tasks.json for spec %q: %w", e.SpecID, err)
		}

		var t tasksMinimal
		if err := json.Unmarshal(data, &t); err != nil {
			return nil, fmt.Errorf("parse tasks.json for spec %q: %w", e.SpecID, err)
		}

		for _, dep := range t.Dependencies {
			if dep.DependsOnSpec == "" {
				continue
			}
			edges[e.SpecID] = append(edges[e.SpecID], dep.DependsOnSpec)
		}
	}

	// Detect cycles before returning.
	if _, err := TopologicalOrder(edges); err != nil {
		return nil, err
	}

	return edges, nil
}

// TopologicalOrder performs Kahn's algorithm on edges and returns spec_ids in
// dependency order (dependencies before dependents). Returns an error if a
// cycle is detected.
//
// edges[A] = [B] means A depends on B; B must appear before A in the output.
func TopologicalOrder(edges map[string][]string) ([]string, error) {
	// Collect all nodes (sources and dependency targets).
	allNodes := make(map[string]bool)
	for src, deps := range edges {
		allNodes[src] = true
		for _, dep := range deps {
			allNodes[dep] = true
		}
	}

	// depCount[node] = number of its dependencies not yet processed.
	// revEdges[dep] = list of nodes that depend on dep (so we can decrement
	//                 their counters once dep is processed).
	depCount := make(map[string]int)
	revEdges := make(map[string][]string)

	for n := range allNodes {
		depCount[n] = 0
	}
	for src, deps := range edges {
		depCount[src] += len(deps)
		for _, dep := range deps {
			revEdges[dep] = append(revEdges[dep], src)
		}
	}

	// Seed the queue with nodes that have no outstanding dependencies.
	var queue []string
	for n := range allNodes {
		if depCount[n] == 0 {
			queue = append(queue, n)
		}
	}
	sort.Strings(queue) // deterministic ordering within a level

	var order []string
	for len(queue) > 0 {
		node := queue[0]
		queue = queue[1:]
		order = append(order, node)

		// Unlock dependents whose last dependency was just processed.
		var ready []string
		for _, dependent := range revEdges[node] {
			depCount[dependent]--
			if depCount[dependent] == 0 {
				ready = append(ready, dependent)
			}
		}
		sort.Strings(ready)
		queue = append(queue, ready...)
	}

	if len(order) < len(allNodes) {
		// Remaining nodes with depCount > 0 are part of a cycle.
		var cycleNodes []string
		for n := range allNodes {
			if depCount[n] > 0 {
				cycleNodes = append(cycleNodes, n)
			}
		}
		sort.Strings(cycleNodes)
		return nil, fmt.Errorf("dependency cycle detected among specs: %s",
			strings.Join(cycleNodes, ", "))
	}

	return order, nil
}
