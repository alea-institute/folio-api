---
title: Canon Tree Toggle - Plan
type: feat
date: 2026-11-06
topic: canon-tree-toggle
artifact_contract: ce-unified-plan/v1
product_contract_source: ce-brainstorm
execution: code
---

# Canon Tree Toggle - Plan

## Goal Capsule

- **Objective:** Anyone visiting FOLIO's tree explorer can switch to the Catholic Semantic Canon and browse its classes and properties the same way they browse FOLIO, with FOLIO still the default.
- **Means:** A plain FOLIO/Canon toggle on the existing tree page at `folio.openlegalstandard.org/explore/tree` (reached from `/taxonomy/tree`), hosted there temporarily.
- **Product authority:** Damien Riehl. Framing decided 2026-11-06 (Cockpit ask `folio-api-2026-11-06-1326-canon-tree-framing`, qid `canon-framing`).
- **Open blockers:** None.

---

## Product Contract

### Summary

The FOLIO tree page gains a plain "FOLIO / Canon" toggle. Switching to Canon reloads the same explorer (class tree, property tree, detail panel, search) from the Catholic Semantic Canon's own ontology. The choice lives in the URL, so shared links open the right view.

### Problem Frame

CatholicOS maintains the Catholic Semantic Canon, a fork of FOLIO with about 15,000 classes under 10 top-level branches (Actor, Authority, Document / Artifact, Event, Normative Concepts, Operational Concepts, Place, and licensing and deprecated branches). Its source of truth sits in a login-gated WebProtégé project, and its public form is a set of OWL, TTL, and other exports in `CatholicOS/ontology-semantic-canon`. No one can browse it without ontology tooling.

FOLIO's tree explorer already serves a near-identical ontology well. The Canon needs a public home for browsing now, before it has its own site.

### Key Decisions

- **A plain toggle with no explanatory note or Canon branding.** (session-settled: user-directed — chosen over a "Preview" label crediting CatholicOS and over full Canon branding: Damien picked the plain toggle.) Governs R1, R2.
- **Show "Canon" as the page heading while the Canon view is active.** The Canon's own ontology title still reads "FOLIO", so the toggle and heading are the only cues that the visitor has left FOLIO. (session-settled: user-approved — proposed alongside the plain toggle, with the risk that visitors may not notice the switch; Damien approved the scope.) Governs R3.
- **Only the tree page changes.** FOLIO's standalone pages, API, and entity graph stay FOLIO-only, so removing the Canon later means removing the toggle and nothing else. Governs R9, R10.
- **The Canon comes from CatholicOS's GitHub repository.** The repository's README designates WebProtégé exports to it as the published form. Governs R7.

### Requirements

**Toggle and identity**

- R1. The tree page shows a plain two-way toggle labeled "FOLIO" and "Canon". FOLIO is selected by default.
- R2. The page adds no explanatory note, credit line, or Canon-specific colors or logo in either view.
- R3. While the Canon view is active, the page heading reads "Canon" in place of the FOLIO heading.
- R4. The selected view is part of the page URL. Opening a link with the Canon selected opens the Canon view, including any selected node.

**Canon explorer behavior**

- R5. In the Canon view, the class tree, property tree, detail panel, and search all show Canon data only, with Canon's own top-level branches as roots.
- R6. Every in-panel navigation in the Canon view (parents, children, related classes and properties) stays inside the Canon tree. No link in the Canon view opens a FOLIO page or a broken link.
- R7. Canon data comes from the CatholicOS `ontology-semantic-canon` GitHub repository and refreshes on the same schedule and mechanism as FOLIO's data.
- R8. Canon classes and properties keep their own identifiers (`https://ontology.catholicos.catholic/...`). None are rewritten to FOLIO identifiers.

**Boundaries with FOLIO features**

- R9. The detail panel's Entity Graph tab is hidden in the Canon view.
- R10. The FOLIO view, FOLIO's API, and FOLIO's standalone pages behave exactly as before.

### Key Flows

- F1. Switch to the Canon and share a link
  - **Trigger:** A visitor on the FOLIO tree selects "Canon".
  - **Steps:** The heading changes to "Canon"; the trees reload with Canon's top-level branches; the visitor searches, opens a class, and follows its parents and children in the detail panel; they copy the URL and send it.
  - **Outcome:** The recipient opens the same Canon view and node.
  - **Covered by:** R1, R3, R4, R5, R6

### Acceptance Examples

- AE1. **Covers R1, R4.** Given a visitor opens `/taxonomy/tree` with no view in the URL, the FOLIO view loads with "FOLIO" selected.
- AE2. **Covers R4, R5.** Given a link with the Canon view and a Canon class selected, opening it shows that class in the Canon tree, not a FOLIO class or an empty panel.
- AE3. **Covers R6, R8.** Given a Canon class detail panel, every parent, child, and related link resolves to a Canon node with an `ontology.catholicos.catholic` identifier.
- AE4. **Covers R9, R10.** Given a visitor switches back to FOLIO, the Entity Graph tab reappears and the FOLIO view matches today's behavior.
- AE5. **Covers R5.** Given a search for "Sacrament" in the Canon view, results come from the Canon, not from FOLIO.

### Scope Boundaries

- **Deferred for later:** Canon versions of FOLIO's standalone class pages, the REST API, the MCP server, the entity graph, and LLM-backed search.
- **Deferred for later:** A language selector for labels. The tree has none today, and the Canon carries the same multilingual labels FOLIO does.
- **Outside this work:** Editing the Canon. WebProtégé stays its source of truth.
- **Outside this work:** A permanent Canon site. This toggle lives on FOLIO's site only until the Canon has its own home.

### Dependencies / Assumptions

- CatholicOS maintainers export Canon edits from WebProtégé to the GitHub repository. Changes made only in WebProtégé never reach the site.
- "Temporary" carries no end date. Removal means deleting the toggle and its data source, with no data migration.
- The PROD host has memory headroom for a second ontology of about 15,000 classes. Planning verifies this.

### Outstanding Questions

**Deferred to Planning**

- The ontology library assumes FOLIO's identifier prefix and fetches only a file named `FOLIO.owl` from GitHub. How does the app load the Canon so R7 and R8 both hold?
- The app hardcodes FOLIO's identifier prefix and root classes in several routes. How do they become per-ontology without changing FOLIO behavior (R10)?
- Should the Canon track the repository's default branch or a pinned revision, given that FOLIO pins a release branch?

### Sources / Research

- `folio_api/routes/taxonomy.py`: `/taxonomy/tree` returns a 301 to `/explore/tree` and passes through only `node`; FOLIO's class roots come from the hardcoded `ROOT_CLASS_IRI_IDS`.
- `folio_api/routes/properties.py`: property roots are computed, and only hidden roots are hardcoded as FOLIO identifiers.
- `folio_api/routes/explore.py`: the unified tree page; `_FOLIO_IRI_PREFIX` hardcodes FOLIO's identifier prefix, which also appears in other routes.
- `folio_api/api.py`: the app loads one ontology into `app.state.folio`, which the MCP server shares.
- `folio_api/templates/jinja2/components/class_details.html` and `property_details.html`: these detail panels link out to standalone `<iri>/html` pages (relevant to R6).
- folio-python 0.3.6, `folio/graph.py`: the constructor accepts an `http` source URL. Its GitHub loader always fetches `FOLIO.owl`, and `normalize_iri` assumes FOLIO's prefix.
- `CatholicOS/ontology-semantic-canon`, `sources/`: the Canon exports (`.owl`, `.ttl`, `.owx`, `.omn`, `.ofn`).
