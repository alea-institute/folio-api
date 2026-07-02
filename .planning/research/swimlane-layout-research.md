# Swimlane Layout: How folio-enrich and folio-mapper handle it

## TL;DR

Neither folio-enrich nor folio-mapper implements swimlane layout. Both use a single flat ELK `layered` graph over all nodes, relying on ELK's own crossing-minimization to arrange horizontal positions. The only structural hint they give to ELK is a `layerConstraint: FIRST` on ultimate-root nodes (folio-enrich) so they land in the top layer — they do not partition by ancestor branch, do not assign column ranges, and do not post-process x-coordinates. The result is the same horizontal mixing folio-api experiences. Swimlanes would require folio-api (or its backend) to add new logic that neither reference implementation has.

---

## folio-enrich

- **Layout engine:** ELK `layered`, elkjs@0.11.1 (loaded from unpkg CDN)
- **Where it lives:** `frontend/index.html` lines 8809–8845 (`buildELKGraph`), lines 8842–8846 (`runELKLayout`)
- **Swimlane behavior:** None. All nodes are passed as a single flat `children` array. There is no partitioning, grouping, or column assignment by branch.
- **Config (verbatim):**
  ```js
  layoutOptions: {
    'elk.algorithm': 'layered',
    'elk.direction': dir,           // 'DOWN' or 'RIGHT'
    'elk.spacing.nodeNode': '30',
    'elk.layered.spacing.nodeNodeBetweenLayers': '70',
    'elk.layered.spacing.edgeNodeBetweenLayers': '30',
    'elk.layered.spacing.edgeEdgeBetweenLayers': '15',
    'elk.layered.crossingMinimization.strategy': 'LAYER_SWEEP',
    'elk.layered.nodePlacement.strategy': 'NETWORK_SIMPLEX',
    'elk.edgeRouting': 'POLYLINE',
    'elk.padding': '[top=30,left=30,bottom=30,right=30]',
  }
  ```
- **Per-node constraint (line 8815–8816):**
  ```js
  if (n.is_branch_root && !targetIds.has(n.id)) {
    node.layoutOptions = { 'elk.layered.layering.layerConstraint': 'FIRST' };
  }
  ```
  This forces ultimate-root nodes to the topmost ELK layer (y-row 0), but does not constrain their x-position at all. Multiple roots will share layer 0 and ELK places them side-by-side in whatever order its algorithm chooses.
- **Multi-parent nodes:** No special handling. A node with two ancestor paths gets one copy in the graph; ELK places it wherever its combined edge set pulls it. No duplication, no forced-column placement.
- **Pre/post-processing:** None. Nodes array is mapped 1-to-1 from API response to ELK children. No reorder, no partition, no x-offset adjustment after layout.

---

## folio-mapper

- **Layout engine:** ELK `layered`, elkjs@0.11.0 (dynamic import, code-split)
- **Where it lives:** `packages/ui/src/components/mapping/graph/useELKLayout.ts` lines 47–60 (layout call), lines 35–59 (full ELK graph construction)
- **Swimlane behavior:** None. Same flat-children approach as folio-enrich. No partitioning.
- **Config (verbatim, lines 49–57):**
  ```ts
  layoutOptions: {
    'elk.algorithm': 'layered',
    'elk.direction': direction === 'TB' ? 'DOWN' : 'RIGHT',
    'elk.spacing.nodeNode': '40',
    'elk.layered.spacing.nodeNodeBetweenLayers': '70',
    'elk.layered.crossingMinimization.strategy': 'LAYER_SWEEP',
    'elk.edgeRouting': 'SPLINES',
    'elk.layered.nodePlacement.strategy': 'BRANDES_KOEPF',
  }
  ```
  Note: folio-mapper uses `BRANDES_KOEPF` for node placement (vs. `NETWORK_SIMPLEX` in enrich/api), and `SPLINES` edge routing (vs. `POLYLINE`). Otherwise structurally identical.
- **Per-node constraints:** None at all. No `layerConstraint` is set on any node — not even on branch roots.
- **Multi-parent nodes:** No special handling. A node with two ultimate ancestors receives one position from ELK, wherever its combined incoming edges land it horizontally.
- **Pre/post-processing:** None. `data.nodes` maps 1-to-1 to ELK children. Positions from `elkGraph.children` are used as-is (lines 64–83).

---

## folio-api (current state, for context)

`folio_api/static/js/entity_graph.js` lines 313–316 mirrors folio-enrich's `layerConstraint: FIRST` trick:
```js
if (n.branch_root_type === 'ultimate' && !targetIds.has(n.iri)) {
  node.layoutOptions = { 'elk.layered.layering.layerConstraint': 'FIRST' };
}
```
It also uses `NETWORK_SIMPLEX` + `POLYLINE`, matching folio-enrich exactly. No swimlane logic here either.

---

## Recommendation for folio-api

- **Likely cheapest path to swimlane (if desired):** Use ELK's built-in compound/hierarchical grouping. The cleanest approach:
  1. **Backend:** add a `swimlane_root` field per node identifying which ultimate ancestor it belongs to (use the `branch` field that already exists, or a new IRI pointer).
  2. **Frontend pre-processing:** partition nodes into per-root subtrees. For each partition, call `elk.layout()` independently with the same `layered` options. Then stack the resulting sub-graphs side by side manually: offset each sub-graph's x-coordinates by the cumulative width of all previous sub-graphs + a gap (e.g., 80 px).
  3. **Multi-parent nodes** (the hard part): a node that belongs to two subtrees must either (a) be duplicated in both columns with a dashed "same-concept" edge between copies, or (b) be placed in a third floating column and have long cross-column edges drawn to both parents. Option (b) preserves identity but produces the "long curving edges crossing columns" artifact.

  Rough effort: the partition + independent layout step is ~1–2 hours of JS. The multi-parent policy is a product decision (duplicate vs. float) that adds 2–4 hours more depending on which way you go.

- **Alternative — ELK compound nodes (same call):** Wrap each branch's subtree in an ELK compound node (`children` of a group node). This keeps one `elk.layout()` call and lets ELK minimize crossings within each group, but ELK's `layered` algorithm does not respect group boundaries for horizontal ordering of groups themselves — you still need to set `org.eclipse.elk.partitioning.activate: true` and `org.eclipse.elk.partitioning.partition` integer values on each node to assign them to disjoint horizontal partitions. This ELK option exists but is documented as experimental; folio-enrich's attempt to use it has not been tried and its behavior with multi-parent cross-partition edges is unknown.

- **Pitfalls:**
  - `layerConstraint: FIRST` puts roots in layer 0 but does not stop ELK from interleaving their subtree columns. It is a y-constraint, not an x-constraint.
  - `NETWORK_SIMPLEX` is better at crossing minimization than `BRANDES_KOEPF` for dense multi-root graphs; switching to `BRANDES_KOEPF` (as folio-mapper does) tends to spread nodes out more but does not enforce column grouping.
  - Multi-parent nodes will always produce cross-column edges in a strict swimlane; the rendering layer needs to visually distinguish these (e.g., dashed, colored differently, or drawn as curved arcs behind other edges).
  - ELK `partitioning` is marked `@LayoutOptionData(legacy = true)` in the ELK source — test carefully before shipping.

- **Open questions for the user:**
  - Multi-parent policy: duplicate the node in both columns, float it between columns, or hide the secondary ancestry edge entirely?
  - Should the swimlane grouping be by ultimate ancestor (6–8 top-level branches) or by the first-level child of the ultimate ancestor (20–30 groupings)? The former is coarser but less visually overwhelming.
  - Is this a "nice to have" cosmetic improvement or a hard navigability requirement? If the latter, the per-partition independent layout approach is safest; if the former, `BRANDES_KOEPF` + wider `nodeNode` spacing may be sufficient to reduce (not eliminate) mixing.
