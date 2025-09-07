# Graph Reconstruction from Random Walk Observations

## Problem Statement

### Graph Structure
- **Undirected port-labeled graph** with N nodes (rooms), where N is specified by user.
- Each node has exactly **6 ports/doors** (labeled 0-5)
- Each node has a **2-bit label** (value 0, 1, 2, or 3)
- Edges connect pairs of ports (can include self-loops and multi-edges)
- Graph is connected and traversable

### Observations
- Multiple random walks from a fixed starting room
- Walk format: `0(5)1(4)3` means:
  - From room with label 0, take door 5 → arrive at room with label 1
  - From room with label 1, take door 4 → arrive at room with label 3
- **Available information**: departure room label, chosen door, arrival room label
- **Missing information**: arrival port number (which door we entered through)

### Constraints
- Labels distributed roughly uniformly: max ⌈N/4⌉ rooms per label
- Possibly more rooms with label 1 than label 0
- Graph is undirected: if room A door X → room B, then some door of B → room A

### Goal
Reconstruct the complete graph (all rooms, labels, and door connections) consistent with all observed walks.

---

## Recommended Solution: Automata Learning via State Merging

### Core Insight
This is a **passive automata learning problem**, not a general CSP/SMT problem. We're learning a Moore machine (states=rooms, outputs=labels, transitions=doors) from execution traces.

### Algorithm Overview

#### Phase 1: Build Prefix Tree Automaton (PTA)
```python
class Node:
    label: Optional[int]          # 0-3, observed on arrival
    children: dict[int, Node]     # door -> child node

# Build prefix tree from all walks
for walk in walks:
    node = root
    for (door, arrival_label) in parse_walk(walk):
        if door not in node.children:
            node.children[door] = Node()
        node = node.children[door]
        node.label = arrival_label
```

#### Phase 2: Signature Refinement (Weisfeiler-Lehman Style)
```python
# Initial signature = room label
sig[node] = node.label

# Iterative refinement
while signatures_changing:
    for node in all_nodes:
        # Signature = (my_label, pattern_of_reachable_labels)
        outgoing_pattern = []
        for door in range(6):
            if door in node.children:
                child = node.children[door]
                outgoing_pattern.append((door, sig[child]))
            else:
                outgoing_pattern.append((door, "unobserved"))
        
        new_sig[node] = (sig[node], tuple(sorted(outgoing_pattern)))
```

#### Phase 3: State Merging
```python
# Group nodes by final signature
groups = group_by_signature(nodes)

# Merge compatible nodes within groups
for group in groups:
    for node1, node2 in group:
        if can_merge(node1, node2):  # Same label, consistent transitions
            union_find.merge(node1, node2)

# Each equivalence class becomes one room in final graph
rooms = union_find.get_equivalence_classes()
```

#### Phase 4: Graph Completion
```python
# Fill unobserved door connections
for room in rooms:
    for door in range(6):
        if door not in room.observed_doors:
            # Find compatible target (room, door) pair
            # Respect: undirectedness, label constraints, total room count
            target = find_best_match(room, door, remaining_stubs)
            connect(room, door, target.room, target.door)
```

#### Phase 5: Validation
```python
# Verify all walks match reconstructed graph
for walk in original_walks:
    simulated = simulate_walk(reconstructed_graph, walk.doors)
    assert simulated.labels == walk.labels
```

---

## Key Implementation Strategies

### 1. Conservative Merging
- Only merge nodes with identical signatures AND compatible observed transitions
- When uncertain, keep nodes separate (completion phase will handle connections)

### 2. Constraint Propagation During Completion
- Enforce undirectedness: every edge must have reverse edge
- Respect label distribution: max ⌈N/4⌉ per label
- Maintain exactly N total rooms

### 3. Optimization Techniques
- **Start small**: Process short walks first, then extend with longer ones
- **Prioritize frequent paths**: High-frequency observations are more reliable
- **Early pruning**: Use label count constraints to eliminate impossible merges

### 4. Active Learning (If Multiple Queries Allowed)
Generate distinguishing walks to resolve ambiguities:
```python
# Test if nodes X and Y are same room
path_to_X = find_path(start, X)
path_to_Y = find_path(start, Y)
test_doors = [0, 1, 2, 3, 4, 5]  # Try all doors

plan1 = path_to_X + test_doors
plan2 = path_to_Y + test_doors
# If label sequences differ → X ≠ Y
```

---

## Why This Approach Works

### Efficiency
- PTA size = O(total walk steps) - manageable
- Refinement = O(nodes × doors) per iteration - fast
- Merging = O(nodes²) with early pruning - tractable
- Completion only handles unobserved edges - not full N×6 space

### Convergence
- With sufficient diverse walks, converges to unique graph (up to isomorphism)
- Each refinement iteration distinguishes more behaviorally different nodes
- Active learning exponentially accelerates convergence

### Robustness
- Handles sparse observations gracefully
- Works with self-loops and multi-edges
- Respects all hard constraints while remaining flexible on unobserved portions

---

## Implementation Checklist

1. **Data Structures**
   - [ ] PTA with efficient prefix sharing
   - [ ] Union-Find for merging operations
   - [ ] Graph representation for final result

2. **Core Algorithm**
   - [ ] Walk parser (extract door/label sequences)
   - [ ] PTA construction
   - [ ] Signature refinement loop
   - [ ] State merging with consistency checks
   - [ ] Graph completion with constraint satisfaction
   - [ ] Walk validation/simulation

3. **Optimizations**
   - [ ] Incremental processing of walks
   - [ ] Label count tracking for early pruning
   - [ ] Distinguishing sequence generator for active learning

4. **Output Format**
   - [ ] `rooms`: array of labels (0-3) for each room
   - [ ] `connections`: list of door-to-door pairings
   - [ ] `startingRoom`: index of initial room

---

## Common Pitfalls to Avoid

1. **Over-merging**: Merging nodes too aggressively → inconsistent graph
2. **Under-observing**: Attempting reconstruction with < 50% coverage → high ambiguity
3. **Ignoring undirectedness**: Forgetting reverse edges must exist
4. **Label overflow**: Creating more than ⌈N/4⌉ rooms with same label
5. **CSP/SMT approach**: Modeling entire problem as constraints → exponential blowup

---

## Success Metrics

- **Coverage**: Aim for > 70% of (room, door) pairs observed before final reconstruction
- **Refinement convergence**: Signatures should stabilize within 5-10 iterations
- **Merge rate**: Expect 60-80% reduction from PTA nodes to final rooms
- **Validation**: 100% of original walks must replay correctly on reconstructed graph
