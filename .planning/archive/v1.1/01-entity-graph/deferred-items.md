# Phase 1 — Deferred Items

Out-of-scope discoveries surfaced during plan execution. Recorded for
consideration in a future milestone; **not** blockers for v1.1.

---

## A11y candidates (logged by Plan 01-15)

### 1. Edge stroke contrast tightening

- **Surface:** SVG cubic-bezier edges between graph nodes.
- **Current:** `stroke: #9CA3AF` (Tailwind `gray-400`) — see `styles.css:302`.
- **Contrast against white:** 2.84:1.
- **WCAG AA non-text UI threshold:** 3:1.
- **Status:** Borderline below threshold by 0.16. Edges are decorative
  connectors; semantic information lives in the node labels (which clear
  10:1+).
- **Suggested change (future milestone):** `stroke: #6B7280` (Tailwind
  `gray-500`) — 4.83:1, well above the threshold. Requires a UI-SPEC color
  table update.
- **Why deferred:** The donor folio-enrich uses `gray-400` and the v1.1
  aesthetic intentionally favors thin, light edges. Tightening contrast
  here is a stylistic decision, not a functional defect.

### 2. Graph nodes individually tab-focusable

- **Status:** Documented in UI-SPEC §Interaction Contract line 238 as an
  intentional v1.1 limitation. Future milestone may add arrow-key node
  navigation (e.g., focused node + ←↑→↓ to move between connected nodes).
- **Why deferred:** Designing a coherent keyboard nav model for ELK-laid
  layered graphs (with potential 50+ nodes) is a multi-week design problem
  that did not fit the v1.1 scope. The keyboard-accessible left tree is the
  canonical selection surface in v1.1.

### 3. Manual UAT walkthrough (Plan 01-15 sections A-E)

- **Status:** Deferred to the orchestrator's `/gsd-verify-work` step. The
  parallel worktree executor cannot run a live server + browser + screen
  reader + axe DevTools extension.
- **Items pending live verification:**
  - **A.** Live keyboard navigation (Tab into tree, Tab to tabs, arrow-key
    cycle, Tab to +N button, Tab to Full screen, Tab inside modal, ESC).
  - **B.** Live screen reader (VoiceOver/NVDA) announcement of tab
    activation, graph SVG summary, loading state, error state, empty state.
  - **C.** Live `prefers-reduced-motion` toggle (OS or DevTools Rendering
    panel emulation) — confirm skeleton has no pulse, hover badge appears
    instantly, modal opens instantly, graph re-renders without animation.
  - **D.** Live axe-core or Lighthouse a11y audit on `/explore/tree` with
    the Graph tab active — expected: 0 critical/serious violations.
  - **E.** Spot-check contrast in DevTools (the static calculations in
    `01-15-SUMMARY.md` § E should match).

---

*Last updated: 2026-05-06 (Plan 01-15)*
