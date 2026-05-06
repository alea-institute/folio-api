/**
 * entity_graph.js — Entity Graph renderer for /explore/tree.
 *
 * Phase 1 (milestone v1.1) module skeleton. Implements:
 *   - window.EntityGraph public API (most methods are stubs; later plans fill them in)
 *   - Lazy loader for /static/js/vendor/elk.bundled.js (loadELK)
 *   - 'entity:selected' custom-event listener (refreshes graph when tab is active)
 *   - Internal state container for pan/zoom + expanded children
 *
 * Donor: folio-enrich/frontend/index.html lines 8750-9232 (per CONTEXT.md D-01).
 * UI-SPEC: .planning/phases/01-entity-graph/01-UI-SPEC.md.
 *
 * Wiring (downstream plans):
 *   Plan 04: backend endpoint /explore/api/entity-graph/{iri:path} (consumed by refreshFor + expand).
 *   Plan 05: tab UI in tree.html + tab-switch handler emits 'entity:selected' from unified_tree.js.
 *   Plan 07: ELK layout + buildELKGraph (consumes window.ELK from loadELK).
 *   Plan 08: SVG renderer + buildEdgePath.
 *   Plan 09: visual styling (Heroicons, selected/root/hover).
 *   Plan 10: pan/zoom transform tracking.
 *   Plan 11: +N Children expansion logic.
 *   Plan 12: graph-node click → selectNodeByIri + tab activation hookup.
 *   Plan 13: full-screen modal toggle.
 */
(function () {
  'use strict';

  // ---------------- Internal state ----------------
  // Mutated by later plans; declared here so all plans see one source of truth.
  const state = {
    activeTab: 'details',          // 'details' | 'graph'  (D-05)
    currentIri: null,              // last entity rendered as 'selected'
    currentType: null,             // 'class' | 'property'
    graphData: null,               // last fetched ancestors payload
    transform: { x: 0, y: 0, scale: 1 },  // pan/zoom (D-13)
    expandedIris: new Set(),       // IRIs whose children are merged in
    isFullscreen: false,           // modal open? (D-07)
  };

  // ---------------- Lazy ELK loader ----------------
  // Loads /static/js/vendor/elk.bundled.js exactly once on first call.
  // Per RESEARCH.md Pattern 3 + Pitfall 1 (cdnjs URL was wrong → vendor path).
  let _elkLoadPromise = null;
  function loadELK() {
    if (typeof window.ELK !== 'undefined') {
      return Promise.resolve(window.ELK);
    }
    if (_elkLoadPromise) {
      return _elkLoadPromise;
    }
    _elkLoadPromise = new Promise(function (resolve, reject) {
      const s = document.createElement('script');
      s.src = '/static/js/vendor/elk.bundled.js';
      s.async = true;
      s.onload = function () {
        if (typeof window.ELK === 'undefined') {
          reject(new Error('elk.bundled.js loaded but window.ELK is undefined'));
          return;
        }
        resolve(window.ELK);
      };
      s.onerror = function () {
        _elkLoadPromise = null;  // allow retry on next call
        reject(new Error('Failed to load /static/js/vendor/elk.bundled.js'));
      };
      document.head.appendChild(s);
    });
    return _elkLoadPromise;
  }

  // ---------------- Public API stubs ----------------
  // Each method is a stub that throws until the relevant plan implements it.
  // The throws make accidental early-call regressions loud during plan execution.

  function init() {
    // Real implementation: register the entity:selected listener.
    // Subsequent plans add tab DOM wiring, modal DOM wiring, etc.
    document.addEventListener('entity:selected', _onEntitySelected);
  }

  function _onEntitySelected(ev) {
    // Plan 12 implements the real handler. The skeleton dedupes per
    // RESEARCH.md Pitfall 7 (re-fetch loop on graph-node click) and otherwise
    // does nothing if the Graph tab is not active (D-10 lazy fetch).
    const detail = (ev && ev.detail) || {};
    if (state.activeTab !== 'graph') return;
    if (detail.iri === state.currentIri && detail.type === state.currentType) return;
    // Plan 12 will replace this body with a real refreshFor() call.
    // For now, leave a console hint so a misconfigured handler is visible.
    if (typeof window.console !== 'undefined' && window.console.debug) {
      window.console.debug('[EntityGraph] entity:selected pending Plan 12 wire-up:', detail);
    }
  }

  function refreshFor(iri, type) {
    // Plan 07/08 implementation.
    return Promise.reject(new Error('EntityGraph.refreshFor not yet implemented (Plan 07)'));
  }

  function expand(iri) {
    // Plan 11 implementation.
    return Promise.reject(new Error('EntityGraph.expand not yet implemented (Plan 11)'));
  }

  function close() {
    // Plan 13 (or wherever close becomes meaningful). No-op in skeleton.
  }

  function toggleFullscreen() {
    // Plan 13 implementation.
    throw new Error('EntityGraph.toggleFullscreen not yet implemented (Plan 13)');
  }

  // ---------------- Export ----------------
  window.EntityGraph = {
    init: init,
    loadELK: loadELK,                 // exposed so tests + later plans can preflight
    refreshFor: refreshFor,
    expand: expand,
    close: close,
    toggleFullscreen: toggleFullscreen,
    // Read-only state reference. Later plans mutate via internal closure;
    // external readers see the current values.
    get state() { return state; },
  };

  // ---------------- Boot ----------------
  // Run init() on DOMContentLoaded so the listener is registered before any
  // tree click can dispatch 'entity:selected'. If the document is already
  // interactive/complete, run immediately.
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
