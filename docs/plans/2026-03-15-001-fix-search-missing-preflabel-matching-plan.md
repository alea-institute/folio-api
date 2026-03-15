---
title: "fix: Search does not match skos:prefLabel (preferred_label)"
type: fix
status: active
date: 2026-03-15
---

# fix: Search does not match skos:prefLabel (preferred_label)

## Overview

Searching for a term that exists only in an entity's `skos:prefLabel` returns no results. For example, "Education - Real Estate Asset" has `skos:prefLabel = "School"`, but searching "school" does not find it. Searching "education" works because it matches the `rdfs:label`. The root cause is that `preferred_label` is parsed and stored but **never indexed or searched** in either `folio-python` (trie/index) or `folio-api` (substring search).

## Problem Statement / Motivation

FOLIO entities have multiple label types from the SKOS vocabulary:
- `rdfs:label` — the display label (always searched)
- `skos:altLabel` — alternative labels/synonyms (always searched)
- `skos:prefLabel` — the preferred/canonical label (**never searched**)
- `skos:hiddenLabel` — hidden labels for search (appended to `alternative_labels` during parsing, so effectively searched)

The `preferred_label` is displayed in the detail panel under "Labels & Synonyms" and is included in API responses, but it is invisible to all search paths. This means users cannot find entities by their canonical preferred name, which defeats the purpose of SKOS vocabulary labeling.

## Proposed Solution

Fix both layers:

1. **folio-python (upstream):** Add `preferred_label` to the `alt_label_to_index` during class parsing so it's included in the marisa-trie and prefix search
2. **folio-api (this repo):** Add `preferred_label` to all substring search checks across 4 endpoints
3. **UI highlighting:** Ensure matches via `preferred_label` are visible in tree nodes and typeahead suggestions

## Technical Considerations

### Architecture

The search pipeline has two phases:
1. **Prefix/trie search** (folio-python) — fast prefix matching via `marisa_trie` built from `label_to_index` + `alt_label_to_index`
2. **Substring search** (folio-api) — fallback loop over all entities checking `label` and `alternative_labels`

Both phases omit `preferred_label`. The fix must address both.

### Affected Search Paths

| Search path | File | Lines | What's checked now | Fix needed |
|---|---|---|---|---|
| `/search/prefix` (class substring) | `search.py` | 172-189 | `label`, `alternative_labels` | Add `preferred_label` |
| `/search/prefix` (property substring) | `search.py` | 199-218 | `label`, `alternative_labels` | Add `preferred_label` |
| `/taxonomy/tree/search` | `taxonomy.py` | 949-967 | `label`, `alternative_labels` | Add `preferred_label` |
| `/properties/tree/search` | `properties.py` | 396-416 | `label`, `alternative_labels`, `definition` | Add `preferred_label` |
| `search_by_prefix` (trie) | folio-python `graph.py` | 989-997 | `label_to_index`, `alt_label_to_index` | Add `preferred_label` to index |
| `search_by_label` (fuzzy) | folio-python `graph.py` | 1377-1381 | `label_to_index`, `alt_label_to_index` | Fixed implicitly by index fix |

### UI Highlighting

Currently, when a tree node matches, `highlightText()` (`unified_tree.js:869-871`) highlights the query within the `node-label` text. If "school" matches via `preferred_label` but the displayed label is "Education - Real Estate Asset", no text highlights — the node just gets a blue background with no indication of WHY it matched.

**Fix:** When a match is via `preferred_label` (query not found in label or alt labels), append a visible annotation like `(School)` highlighted in the tree node label, and show the preferred label in typeahead suggestion results.

### Performance

Adding one more string comparison per entity in O(n) loops is negligible overhead.

### Data Integrity

- `preferred_label` can be `None` — all checks must guard against this
- Deduplication uses IRI-based `seen_iris` sets — no risk of duplicate results even if `preferred_label` equals `label` or an alt label
- When adding to `alt_label_to_index` upstream, if `preferred_label` duplicates an existing alt label, the index list just gains a duplicate entry that's already deduped at the API layer

## System-Wide Impact

- **Interaction graph**: Search endpoints → folio-python `search_by_prefix()` → trie lookup + index lookup → API substring fallback → tree/typeahead rendering. Adding `preferred_label` touches the index build (parse time) and the search loops (query time).
- **Error propagation**: No new error paths — just additional `None`-guarded string comparisons in existing loops.
- **State lifecycle risks**: None — search is read-only against the parsed ontology.
- **API surface parity**: All 4 API search endpoints + the upstream trie/fuzzy search must be updated together. The LLM search (`/search/llm/*`) already includes `preferred_label` via `format_classes_for_llm` and is not affected.
- **Integration test scenarios**:
  1. Search "school" → should return "Education - Real Estate Asset" (prefLabel match)
  2. Search "education" → should still return "Education - Real Estate Asset" (rdfs:label match, no regression)
  3. Search a term that matches both `label` and `preferred_label` of different entities → both should appear, no duplicates
  4. Search a term matching `preferred_label` in the tree → node should be highlighted with visible indication of the prefLabel match
  5. Typeahead search for "school" → suggestion should appear with "School" visible as preferred label

## Acceptance Criteria

### folio-python (upstream)

- [x] **Index `preferred_label`** — In `graph.py` class parsing (~line 754-765), add `owl_class.preferred_label` to `alt_label_to_index` when not `None`
- [x] **Property index** — Similarly add `owl_property.preferred_label` to `property_label_to_index` if applicable
- [x] **Trie includes prefLabels** — The marisa-trie (built at line 989-997) automatically includes the new index entries
- [x] **Tests pass** — Existing folio-python tests continue to pass (38/38)
- [x] **New test** — Verified `search_by_prefix("School")` returns "Education - Real Estate Asset"

### folio-api (this repo) — Search Logic

- [x] **`search.py` class search** (~line 189) — Add `preferred_label` check after `alternative_labels` check
- [x] **`search.py` property search** (~line 216) — Add equivalent `preferred_label` check for properties
- [x] **`taxonomy.py` tree search** (~line 967) — Add `preferred_label` check after `alternative_labels` check
- [x] **`properties.py` tree search** (~line 409) — Add `preferred_label` check after `alternative_labels` check (before `definition` check)

### folio-api — Tree Highlighting

- [x] **Include `preferred_label` in tree node data** — In `taxonomy.py` (~line 1027-1032), add `"preferred_label": cls.preferred_label` to the filtered tree node dict
- [x] **Track match source** — Add `"match_field"` to the node data indicating whether the match was via `label`, `alternative_labels`, or `preferred_label`
- [x] **Update `unified_tree.js` rendering** — In `renderFilteredNode()`, when match is via `preferred_label`, append italic annotation with highlighting
- [x] **Update `highlightText()` call** — Highlight both main label text and preflabel annotation separately, preserving DOM structure

### folio-api — Typeahead Highlighting

- [x] **Show preferred label in suggestions** — Added "Preferred: ..." line in typeahead suggestions when `data.preferred_label` exists
- [x] **Highlight in suggestion** — Query text highlighted within the preferred label line

### Testing

- [x] **API test** — Search for "school" returns "Education - Real Estate Asset" via `/search/prefix` (36 results)
- [x] **Tree test** — Search "school" in `/taxonomy/tree/search` returns tree with match_field: "preferred_label"
- [x] **No regression** — Search for "education" still returns the same entities
- [x] **Visual verification** — Tree shows "Education - Real Estate Asset (School)" with highlighting; detail panel shows preferred label

## Success Metrics

- Searching for any `skos:prefLabel` value finds the corresponding entity across all search surfaces
- Matched tree nodes clearly indicate WHY they matched when the match is through `preferred_label`
- No regressions in existing label/altLabel search behavior

## Dependencies & Risks

| Dependency | Risk | Mitigation |
|---|---|---|
| folio-python upstream change | Upstream PR may take time to merge | Fix folio-api substring search first (works independently); upstream fix adds trie/prefix coverage |
| folio-python version bump | After upstream fix, need to bump `folio-python` in 4 projects | Coordinate bumps: folio-api, folio-enrich, folio-mapper, clio-skills |
| Tree node data shape change | Adding `preferred_label` and `match_field` to tree nodes changes the API response shape | Additive fields — no breaking change to existing consumers |
| Cross-project coordination | 5 repos need changes in sequence | folio-python first, then folio-api, then 3 downstream projects in parallel |
| folio-mapper scoring refactor | `_compute_relevance_score()` signature change affects callers | Add `preferred_label` as optional kwarg with `None` default for backwards compat |
| clio-skills client search perf | Adding `preferredLabel` to client-side index increases memory | Negligible — same O(n) entries, one more string field per entity |

## Implementation Order

1. **folio-python** — Add `preferred_label` to `alt_label_to_index` in `graph.py`
2. **folio-api search logic** — Add `preferred_label` checks to all 4 search endpoints (parallel with #1)
3. **folio-api tree data** — Include `preferred_label` and `match_field` in tree node responses
4. **folio-api UI highlighting** — Update `unified_tree.js` and `typeahead_search.js`
5. **folio-api testing** — Run tests and take screenshots
6. **Downstream: folio-enrich** — Fix 4 files: add `include_alt_labels=True` + scoring
7. **Downstream: folio-mapper** — Fix `_compute_relevance_score()` + all scoring sites + tests
8. **Downstream: clio-skills** — Add `preferredLabel` to client-side search index
9. **Version bumps** — Bump `folio-python` in all downstream `pyproject.toml` / requirements
10. **Cross-project verification** — Run test suites across all 5 affected projects

## Phase 6: Downstream Project Impact Assessment & Fixes

Five downstream projects depend on folio-python and/or folio-api. After fixing the core libraries, each must be assessed and patched as needed.

### Downstream Dependency Map

```
folio-python (upstream library)
├── folio-api         (direct dep — THIS REPO)
├── folio-enrich      (direct dep: folio-python>=0.1.5)
├── folio-mapper      (direct dep: folio-python>=0.2.0,<1.0.0)
├── clio-skills       (direct dep via Python subprocess bridge)
└── ontokit-api       (NO dep — uses RDFLib independently)
       └── ontokit-web (frontend → consumes ontokit-api only)
```

### Assessment Summary

| Project | Depends on | Affected? | Severity | Fix needed |
|---------|-----------|-----------|----------|------------|
| **folio-enrich** | folio-python | **YES** | High | 4 files: add `include_alt_labels=True` + score `preferred_label` |
| **folio-mapper** | folio-python | **YES** | High | 2 files: scoring function ignores `preferred_label`; all search calls affected |
| **clio-skills** | folio-python (subprocess) | **PARTIAL** | Medium | Client-side search index omits `preferredLabel`; server-side fixed by upstream |
| **ontokit-web** | ontokit-api | **NO** | None | Pure frontend; delegates all search to ontokit-api |
| **ontokit-api** | RDFLib (independent) | **NO** | None | Already searches ALL label properties including `skos:prefLabel` via `LABEL_PROPERTY_MAP` |

---

### 6a. folio-enrich — AFFECTED (High)

**Dependency:** `folio-python>=0.1.5` (direct)

**Root cause:** Multiple search calls use `folio.search_by_label()` without `include_alt_labels=True`, and scoring logic only evaluates `label` + `alternative_labels`, never `preferred_label`.

**Affected files:**

| File | Line(s) | Issue |
|------|---------|-------|
| `backend/app/services/folio/search.py` | 282, 292, 304 | `search_by_label` + `search_by_prefix` miss prefLabel candidates |
| `backend/app/services/folio/folio_service.py` | 196 | `search_by_label()` missing `include_alt_labels=True` |
| `backend/app/services/folio/resolver.py` | 243 | Fallback `search_by_label()` missing `include_alt_labels=True` |
| `backend/app/services/concept/branch_judge.py` | 30 | `search_by_label()` missing `include_alt_labels=True` |

**Safe files (already handle preferred_label):**
- `folio_service.py` — `get_all_labels()`, `get_all_labels_multi()`, `get_all_property_labels()` methods properly index `preferred_label` with priority
- `property_matcher.py` — uses the safe `get_all_property_labels()` index
- `entity_ruler_stage.py`, `individual_stage.py` — use `get_all_labels()` exact matching

**Acceptance criteria:**
- [ ] **`folio_service.py:196`** — Add `include_alt_labels=True` to `search_by_label()` call
- [ ] **`resolver.py:243`** — Add `include_alt_labels=True` to fallback `search_by_label()` call
- [ ] **`branch_judge.py:30`** — Add `include_alt_labels=True` to `search_by_label()` call
- [ ] **`search.py` scoring** (~line 336-338) — Add `preferred_label` to scoring alongside `label` and `alternative_labels`
- [ ] **Bump folio-python version** in `pyproject.toml` to version with the upstream fix
- [ ] **Tests pass** — Existing test suite continues to pass

---

### 6b. folio-mapper — AFFECTED (High)

**Dependency:** `folio-python>=0.2.0,<1.0.0` (direct)

**Root cause:** All search code uses only `owl_class.label` for scoring. The `_compute_relevance_score()` function has no `preferred_label` parameter. All `search_by_label()` and `search_by_prefix()` calls are affected by the upstream folio-python indexing gap.

**Affected files:**

| File | Line(s) | Issue |
|------|---------|-------|
| `backend/app/services/folio_service.py` | 460-481 | `_see_also_within_branch()` — uses `owl_class.label` only, ignores `preferred_label` |
| `backend/app/services/folio_service.py` | 619-681 | `_compute_relevance_score()` — function signature takes no `preferred_label` param |
| `backend/app/services/folio_service.py` | 1042-1089 | `search_candidates()` — only scores `.label` |
| `backend/app/services/pipeline/stage1_filter.py` | 60-79 | `_search_within_branch()` — scores with `label` + `alternative_labels`, no `preferred_label` |

**Test files needing updates:**
- `test_see_also_traversal.py` — Mock OWL classes don't set `preferred_label`
- `test_search_expansion.py` — `_compute_relevance_score()` tests don't cover `preferred_label`
- `test_pipeline.py` — Mock OWL classes don't set `preferred_label`

**Acceptance criteria:**
- [ ] **`_compute_relevance_score()`** — Add `preferred_label` parameter; score it between `label` (highest) and `alternative_labels`
- [ ] **`_see_also_within_branch()`** — Include `preferred_label` in candidate data alongside `label` and `alternative_labels`
- [ ] **`search_candidates()`** — Pass `preferred_label` to scoring function
- [ ] **`stage1_filter.py:60-79`** — Include `preferred_label` in result scoring
- [ ] **Update test mocks** — Add `preferred_label` field to mock OWL classes in all 3 test files
- [ ] **Bump folio-python version** in `pyproject.toml` to version with the upstream fix
- [ ] **Tests pass** — All existing + new tests pass

---

### 6c. clio-skills — PARTIALLY AFFECTED (Medium)

**Dependency:** `folio-python` (via Python subprocess bridge in `app/scripts/folio_bridge.py`)

**Root cause:** Client-side search index (`client-search.ts`) builds its index from `label` and `alternativeLabels` only — `preferredLabel` is stored in the data model but excluded from search. Server-side search delegates to folio-python, which will be fixed upstream.

**Affected files:**

| File | Line(s) | Issue |
|------|---------|-------|
| `app/src/lib/folio/client-search.ts` | 39-90 | `buildLabelIndex()` omits `preferredLabel` from search entries |
| `app/scripts/folio_bridge.py` | 145-171 | Delegates to folio-python `search_by_label()` — fixed by upstream |

**Not affected:**
- `app/src/lib/folio/types.ts` — Already defines `preferredLabel` field in interfaces
- `app/src/lib/folio/ontology-store.ts` — Already populates `preferredLabel` in node construction

**Acceptance criteria:**
- [ ] **`client-search.ts:buildLabelIndex()`** — Add `preferredLabel` to the `SearchEntry` type and include it in matching with appropriate scoring (prefix match = 85, substring = 75 — between label and altLabel scores)
- [ ] **`folio_bridge.py`** — No code change needed; upstream folio-python fix resolves server-side search
- [ ] **Bump folio-python version** in requirements to version with the upstream fix
- [ ] **Test** — Search for a term matching only `preferredLabel` returns the entity in both Tier 1 (client) and Tier 2 (server) results

---

### 6d. ontokit-web — NOT AFFECTED

**Dependency:** Consumes `ontokit-api` REST endpoints only (at `localhost:58002`)

**Assessment:** Pure frontend. All search is delegated to `ontokit-api` via `projectOntologyApi.searchEntities()`. The `getPreferredLabel()` utility in `lib/utils.ts` only selects display labels from already-resolved data — it doesn't perform search.

**Action:** None required. ontokit-web inherits correct behavior from ontokit-api.

---

### 6e. ontokit-api — NOT AFFECTED

**Dependency:** Uses RDFLib directly. **Does NOT depend on folio-python.**

**Assessment:** ontokit-api implements its own `search_entities()` method (`ontokit/services/ontology.py:441-545`) that iterates through ALL label properties via `LABEL_PROPERTY_MAP`, which already includes `skos:prefLabel`:
```python
LABEL_PROPERTY_MAP = {
    "rdfs:label": RDFS.label,
    "skos:prefLabel": SKOS.prefLabel,  # Already searched
    "skos:altLabel": SKOS.altLabel,
    "dcterms:title": ...,
    "dc:title": ...,
}
```
The matching at line 505 (`any(query_lower in lbl.lower() for lbl in all_labels)`) already searches across all collected labels including prefLabel.

**Action:** None required. ontokit-api is independently correct.

---

### Updated Implementation Order

1. **folio-python** — Add `preferred_label` to `alt_label_to_index` in `graph.py`
2. **folio-api** — Add `preferred_label` checks to 4 search endpoints + UI highlighting
3. **folio-enrich** — Add `include_alt_labels=True` to 3 search calls + add `preferred_label` to scoring
4. **folio-mapper** — Add `preferred_label` to `_compute_relevance_score()` + all scoring sites
5. **clio-skills** — Add `preferredLabel` to client-side search index in `client-search.ts`
6. **Version bumps** — Bump `folio-python` dependency in folio-api, folio-enrich, folio-mapper, clio-skills
7. **Testing & verification** — Run test suites across all affected projects

## Sources & References

### Internal References

- Search logic (class substring): `folio_api/routes/search.py:172-189`
- Search logic (property substring): `folio_api/routes/search.py:199-218`
- Tree search (classes): `folio_api/routes/taxonomy.py:949-967`
- Tree search (properties): `folio_api/routes/properties.py:396-416`
- Tree node rendering: `folio_api/static/js/unified_tree.js:748-774`
- Tree highlighting: `folio_api/static/js/unified_tree.js:717-722, 869-876`
- Typeahead suggestion template: `folio_api/static/js/typeahead_search.js:150-188`
- Client-side tokenization (already includes prefLabel): `folio_api/static/js/typeahead_search.js:87-88`
- Upstream model: `.venv/lib/python3.13/site-packages/folio/models.py:54-56, 115-117`
- Upstream parsing (prefLabel stored but not indexed): `.venv/lib/python3.13/site-packages/folio/graph.py:652-654`
- Upstream index building (omits prefLabel): `.venv/lib/python3.13/site-packages/folio/graph.py:754-765`
- Upstream trie building (omits prefLabel): `.venv/lib/python3.13/site-packages/folio/graph.py:989-997`

### Downstream Project References

- folio-enrich search: `~/Coding Projects/folio-enrich/backend/app/services/folio/search.py:282`
- folio-enrich service: `~/Coding Projects/folio-enrich/backend/app/services/folio/folio_service.py:196`
- folio-enrich resolver fallback: `~/Coding Projects/folio-enrich/backend/app/services/folio/resolver.py:243`
- folio-enrich branch judge: `~/Coding Projects/folio-enrich/backend/app/services/concept/branch_judge.py:30`
- folio-mapper scoring: `~/Coding Projects/folio-mapper/backend/app/services/folio_service.py:619-681`
- folio-mapper see-also: `~/Coding Projects/folio-mapper/backend/app/services/folio_service.py:460-481`
- folio-mapper stage1 filter: `~/Coding Projects/folio-mapper/backend/app/services/pipeline/stage1_filter.py:60-79`
- clio-skills client search: `~/Coding Projects/clio-skills/app/src/lib/folio/client-search.ts:39-90`
- ontokit-api search (NOT affected): `~/Coding Projects/ontokit-api/ontokit/services/ontology.py:441-545`
