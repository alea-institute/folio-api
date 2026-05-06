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

  // ---------------- Heroicons v2 outline (inline SVG markup) ----------------
  // Verbatim path strings from tailwindlabs/heroicons master/optimized/24/outline.
  // RESEARCH.md verified 2026-05-05.
  // Inlined per D-19 / UI-SPEC §Iconography (no asset fetch, no CSP img-src).
  function _svg(sizeClass, pathsHtml) {
    return '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"' +
           ' stroke-width="1.5" stroke="currentColor"' +
           ' class="' + sizeClass + '" aria-hidden="true">' + pathsHtml + '</svg>';
  }
  function _path(d) {
    return '<path stroke-linecap="round" stroke-linejoin="round" d="' + d + '"></path>';
  }

  var ICONS = {
    tag: _svg('w-4 h-4',
      _path('M9.568 3H5.25A2.25 2.25 0 0 0 3 5.25v4.318c0 .597.237 1.17.659 1.591l9.581 9.581c.699.699 1.78.872 2.607.33a18.095 18.095 0 0 0 5.223-5.223c.542-.827.369-1.908-.33-2.607L11.16 3.66A2.25 2.25 0 0 0 9.568 3Z') +
      _path('M6 6h.008v.008H6V6Z')
    ),
    link: _svg('w-4 h-4',
      _path('M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m13.35-.622 1.757-1.757a4.5 4.5 0 0 0-6.364-6.364l-4.5 4.5a4.5 4.5 0 0 0 1.242 7.244')
    ),
    arrowsPointingOut: _svg('w-5 h-5',
      _path('M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15')
    ),
    xMark: _svg('w-5 h-5',
      _path('M6 18 L18 6M6 6l12 12')
    ),
    arrowPath: _svg('w-4 h-4',
      _path('M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99')
    ),
    share: _svg('w-16 h-16',
      _path('M7.217 10.907a2.25 2.25 0 1 0 0 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186 9.566-5.314m-9.566 7.5 9.566 5.314m0 0a2.25 2.25 0 1 0 3.935 2.186 2.25 2.25 0 0 0-3.935-2.186Zm0-12.814a2.25 2.25 0 1 0 3.933-2.185 2.25 2.25 0 0 0-3.933 2.185Z')
    )
  };

  // ---------------- UI state renderers (empty / skeleton / error) ----------------
  function _pane() {
    return document.getElementById('entity-graph-pane');
  }

  function clearStates() {
    var pane = _pane();
    if (!pane) return;
    pane.innerHTML = '';
    pane.removeAttribute('aria-busy');
  }

  function showEmpty() {
    // GRAPH-18 + UI-SPEC §State Inventory (Empty row).
    var pane = _pane();
    if (!pane) return;
    pane.removeAttribute('aria-busy');
    pane.innerHTML =
      '<div class="flex flex-col items-center justify-center w-full h-full p-6 gap-6 text-center">' +
        '<div class="text-gray-300">' + ICONS.share + '</div>' +
        '<div class="flex flex-col gap-1">' +
          '<h3 class="text-base font-semibold text-gray-700">No entity selected</h3>' +
          '<p class="text-sm font-normal text-gray-500">Select an entity in the tree to see its graph.</p>' +
        '</div>' +
      '</div>';
  }

  function showSkeleton() {
    // GRAPH-19 + UI-SPEC §State Inventory (Loading row).
    // 4 stacked rectangles; aria-busy=true; respects prefers-reduced-motion via CSS.
    var pane = _pane();
    if (!pane) return;
    pane.setAttribute('aria-busy', 'true');
    pane.innerHTML =
      '<div class="flex flex-col items-center justify-center w-full h-full gap-4 entity-graph-skeleton" role="status" aria-live="polite">' +
        '<div class="bg-gray-100 rounded h-8 w-48 animate-pulse"></div>' +
        '<div class="bg-gray-100 rounded h-8 w-56 animate-pulse"></div>' +
        '<div class="bg-gray-100 rounded h-8 w-48 animate-pulse"></div>' +
        '<div class="bg-gray-100 rounded h-8 w-44 animate-pulse"></div>' +
        '<span class="sr-only">Loading entity graph…</span>' +
      '</div>';
  }

  function showError(entityLabel, onRetry) {
    // GRAPH-20 + UI-SPEC §State Inventory (Error row) + Copywriting Contract.
    var pane = _pane();
    if (!pane) return;
    pane.removeAttribute('aria-busy');
    var safeLabel = (entityLabel == null) ? '' : String(entityLabel);
    pane.innerHTML =
      '<div class="flex items-center justify-center w-full h-full p-6">' +
        '<div role="alert" class="bg-red-50 border border-red-200 rounded-lg p-4 max-w-md flex flex-col gap-2">' +
          '<h3 class="text-sm font-semibold text-red-700">Couldn’t load graph</h3>' +
          '<p class="text-sm text-red-700"></p>' +
          '<div>' +
            '<button type="button" class="entity-graph-retry inline-flex items-center gap-1 bg-blue-50 text-blue-700 border border-blue-200 rounded px-3 py-1 text-sm font-semibold hover:bg-blue-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2">' +
              ICONS.arrowPath + '<span>Retry</span>' +
            '</button>' +
          '</div>' +
        '</div>' +
      '</div>';
    // textContent for label per RESEARCH.md Security Domain row 2 (XSS mitigation).
    var bodyP = pane.querySelector('[role="alert"] p');
    if (bodyP) {
      bodyP.textContent = 'Couldn’t load graph for ' + safeLabel + '. The server returned an error.';
    }
    var btn = pane.querySelector('.entity-graph-retry');
    if (btn && typeof onRetry === 'function') {
      btn.addEventListener('click', onRetry);
    }
    if (window.console && window.console.error) {
      window.console.error('[EntityGraph] failed to load graph for', safeLabel);
    }
  }

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

  // ---------------- ELK layout pipeline (Plan 07) ----------------
  // buildELKGraph adapts donor folio-enrich/frontend/index.html:8809-8840
  // to folio-api's ancestors-only payload shape.
  //
  // Per CONTEXT D-04 + UI-SPEC §spacing:
  //   - direction: DOWN (top-to-bottom); ancestors above the selected node
  //   - nodeNode: 32 px, nodeNodeBetweenLayers: 64 px, padding: 16 px
  // Per CONTEXT D-21 + GRAPH-07: the topmost ancestor (branch_root_type === 'ultimate')
  // is pinned to the FIRST ELK layer via elk.layered.layering.layerConstraint
  // (donor pattern from line 8882 of index.html).
  function buildELKGraph(graphData) {
    var selected = graphData.selected;
    var ancestors = graphData.ancestors || [];
    var children = graphData.children || [];

    // Set of node IRIs that are edge-targets — only non-targets may carry the
    // FIRST layerConstraint (ELK rejects layer constraints on nodes that are
    // already ordered by inbound edges).
    var targetIds = new Set();
    var edges = [];

    // Ancestor chain edges: ancestors[i] → ancestors[i+1] (root-first).
    for (var i = 0; i < ancestors.length - 1; i++) {
      edges.push({
        id: 'e_' + i,
        sources: [ancestors[i].iri],
        targets: [ancestors[i + 1].iri],
      });
      targetIds.add(ancestors[i + 1].iri);
    }
    // Last ancestor → selected.
    if (ancestors.length > 0) {
      var lastAnc = ancestors[ancestors.length - 1];
      edges.push({
        id: 'e_anc_sel',
        sources: [lastAnc.iri],
        targets: [selected.iri],
      });
      targetIds.add(selected.iri);
    }
    // Selected → each loaded child.
    for (var ci = 0; ci < children.length; ci++) {
      edges.push({
        id: 'e_child_' + ci,
        sources: [selected.iri],
        targets: [children[ci].iri],
      });
      targetIds.add(children[ci].iri);
    }

    var allNodes = [selected].concat(ancestors).concat(children);
    var elkChildren = allNodes.map(function (n) {
      var labelText = n.label || '';
      var w = Math.max(180, labelText.length * 7.5 + 32);
      var node = {
        id: n.iri,
        width: w,
        height: 36,
        labels: [{ text: labelText }],
      };
      // Donor pattern (index.html:8882): ultimate root pinned to FIRST layer
      // when it's not already a target of some edge.
      if (n.branch_root_type === 'ultimate' && !targetIds.has(n.iri)) {
        node.layoutOptions = { 'elk.layered.layering.layerConstraint': 'FIRST' };
      }
      return node;
    });

    return {
      id: 'root',
      layoutOptions: {
        'elk.algorithm': 'layered',
        'elk.direction': 'DOWN',
        'elk.spacing.nodeNode': '32',
        'elk.layered.spacing.nodeNodeBetweenLayers': '64',
        'elk.layered.spacing.edgeNodeBetweenLayers': '24',
        'elk.layered.spacing.edgeEdgeBetweenLayers': '12',
        'elk.layered.crossingMinimization.strategy': 'LAYER_SWEEP',
        'elk.layered.nodePlacement.strategy': 'NETWORK_SIMPLEX',
        'elk.edgeRouting': 'POLYLINE',
        'elk.padding': '[top=16,left=16,bottom=16,right=16]',
      },
      children: elkChildren,
      edges: edges,
    };
  }

  // runLayout — instantiates ELK lazily (via loadELK) and runs elk.layout(spec).
  // Returns a Promise that resolves to the laid-out spec; children carry x/y/width/height,
  // edges carry sections[] with startPoint/endPoint/(bendPoints).
  function runLayout(spec) {
    return loadELK().then(function (ELK) {
      var elk = new ELK();
      return elk.layout(spec);
    });
  }

  // ---------------- SVG renderer (Plan 08) ----------------
  // buildEdgePath — copied VERBATIM from donor folio-enrich/frontend/index.html:8976-8990,
  // simplified for D-04 (direction is always DOWN). Cubic bezier S-curve guarantees
  // 90° vertical entry/exit at both endpoints.
  // Per CONTEXT D-02 / D-08, GRAPH-08, and RESEARCH.md lines 692-703.
  function buildEdgePath(section) {
    var sp = section.startPoint;
    var ep = section.endPoint;
    var midY = (sp.y + ep.y) / 2;
    return 'M' + sp.x + ',' + sp.y + ' C' + sp.x + ',' + midY + ' ' + ep.x + ',' + midY + ' ' + ep.x + ',' + ep.y;
  }

  var SVG_NS = 'http://www.w3.org/2000/svg';

  // _findUltimateRootIri — locate the IRI of the ancestor with branch_root_type==='ultimate'
  // so renderGraph can stamp it with the .graph-node-root class (Plan 09 styles it).
  function _findUltimateRootIri(graphData) {
    var ancestors = (graphData && graphData.ancestors) || [];
    for (var i = 0; i < ancestors.length; i++) {
      if (ancestors[i] && ancestors[i].branch_root_type === 'ultimate') {
        return ancestors[i].iri;
      }
    }
    // Fallback: the ELK selected node itself can be marked as ultimate when a class
    // has no ancestors (root entity). Surface that via graphData.selected if present.
    if (graphData && graphData.selected && graphData.selected.branch_root_type === 'ultimate') {
      return graphData.selected.iri;
    }
    return null;
  }

  // _mountGraph — actual DOM construction; called inside requestAnimationFrame
  // by renderGraph so that #tab-panel-graph is visible (clientWidth > 0) before
  // we measure or mount (RESEARCH.md Pitfall 6).
  function _mountGraph(graphData) {
    var pane = _pane();
    if (!pane) return;
    var layout = graphData && graphData.layout;
    if (!layout) return;

    var children = layout.children || [];
    var edges = layout.edges || [];

    // Compute bounds with 16 px padding (UI-SPEC §spacing).
    var maxX = 0;
    var maxY = 0;
    for (var i = 0; i < children.length; i++) {
      var c = children[i];
      var rx = (c.x || 0) + (c.width || 0);
      var ry = (c.y || 0) + (c.height || 0);
      if (rx > maxX) maxX = rx;
      if (ry > maxY) maxY = ry;
    }
    maxX += 16;
    maxY += 16;

    // Reset pane (skeleton already cleared in renderGraph, but be defensive).
    pane.innerHTML = '';
    pane.removeAttribute('aria-busy');

    // Scaffolding: viewport > transform > (svg + nodes-div).
    var viewport = document.createElement('div');
    viewport.id = 'graph-viewport';
    viewport.className = 'absolute inset-0 overflow-hidden';

    var xform = document.createElement('div');
    xform.id = 'graph-transform';
    xform.className = 'absolute top-0 left-0';
    xform.style.transformOrigin = '0 0';

    var svg = document.createElementNS(SVG_NS, 'svg');
    svg.setAttribute('id', 'graph-svg');
    svg.setAttribute('width', String(maxX));
    svg.setAttribute('height', String(maxY));
    svg.setAttribute('viewBox', '0 0 ' + maxX + ' ' + maxY);
    svg.style.position = 'absolute';
    svg.style.top = '0';
    svg.style.left = '0';
    svg.style.pointerEvents = 'none';

    var edgesGroup = document.createElementNS(SVG_NS, 'g');
    edgesGroup.setAttribute('class', 'graph-edges');
    svg.appendChild(edgesGroup);

    var nodesDiv = document.createElement('div');
    nodesDiv.className = 'graph-nodes';
    nodesDiv.style.position = 'relative';
    nodesDiv.style.width = maxX + 'px';
    nodesDiv.style.height = maxY + 'px';

    // Edges — defensive `(edge.sections || []).forEach` guard per Pitfall 5.
    for (var ei = 0; ei < edges.length; ei++) {
      var edge = edges[ei] || {};
      var sections = edge.sections || [];
      for (var si = 0; si < sections.length; si++) {
        var section = sections[si];
        if (!section || !section.startPoint || !section.endPoint) continue;
        var path = document.createElementNS(SVG_NS, 'path');
        path.setAttribute('d', buildEdgePath(section));
        path.setAttribute('class', 'graph-edge');
        path.setAttribute('fill', 'none');
        path.setAttribute('stroke', 'currentColor');
        path.setAttribute('stroke-width', '1.5');
        edgesGroup.appendChild(path);
      }
    }

    // Selected + root markers.
    var selectedIri = (graphData.selected && graphData.selected.iri) || null;
    var rootIri = _findUltimateRootIri(graphData);

    // Nodes — DIVs positioned absolutely; label via textContent (XSS mitigation,
    // RESEARCH.md Security row 2 / threat T-1-W2-03).
    for (var ni = 0; ni < children.length; ni++) {
      var node = children[ni];
      if (!node) continue;
      var nodeDiv = document.createElement('div');
      var classes = ['graph-node'];
      if (selectedIri && node.id === selectedIri) classes.push('graph-node-selected');
      if (rootIri && node.id === rootIri) classes.push('graph-node-root');
      nodeDiv.className = classes.join(' ');
      nodeDiv.setAttribute('data-iri', node.id);
      nodeDiv.style.position = 'absolute';
      nodeDiv.style.left = (node.x || 0) + 'px';
      nodeDiv.style.top = (node.y || 0) + 'px';
      nodeDiv.style.width = (node.width || 0) + 'px';
      nodeDiv.style.height = (node.height || 0) + 'px';

      var labelText = '';
      if (node.labels && node.labels.length && node.labels[0] && node.labels[0].text != null) {
        labelText = String(node.labels[0].text);
      }
      nodeDiv.textContent = labelText;
      nodesDiv.appendChild(nodeDiv);
    }

    xform.appendChild(svg);
    xform.appendChild(nodesDiv);
    viewport.appendChild(xform);
    pane.appendChild(viewport);
  }

  // renderGraph — public-ish renderer. Defers DOM mount to the next animation
  // frame so #tab-panel-graph is un-hidden before we measure (Pitfall 6).
  // No-op if graphData has no layout (refreshFor failed before runLayout).
  function renderGraph(graphData) {
    if (!graphData || !graphData.layout) return;
    clearStates();
    requestAnimationFrame(function () {
      _mountGraph(graphData);
    });
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

  function refreshFor(iri, type, force) {
    // Plan 07 implementation: fetch /explore/api/entity-graph/{iri}, build ELK
    // spec, run layout, store on state.graphData. Plan 08 will consume
    // state.graphData.layout to draw the SVG.
    //
    // Dedupe per RESEARCH Pitfall 7: when called repeatedly with the same
    // (iri, type) and we already have graphData, return the cached payload
    // unless force=true (used by the Retry button in showError).
    if (!force && iri === state.currentIri && type === state.currentType && state.graphData) {
      return Promise.resolve(state.graphData);
    }

    showSkeleton();

    // Reset state for a new selection (D-11): each selection is a fresh graph;
    // pan/zoom resets and previously-expanded children are NOT preserved.
    state.transform = { x: 0, y: 0, scale: 1 };
    state.expandedIris = new Set();
    state.graphData = null;

    var url = '/explore/api/entity-graph/' + encodeURIComponent(iri);
    return fetch(url, { headers: { 'Accept': 'application/json' } })
      .then(function (res) {
        if (!res.ok) {
          // Best-effort label for the error UI; falls back to the raw IRI.
          var errLabel = (state.graphData && state.graphData.selected && state.graphData.selected.label) || iri;
          showError(errLabel, function () { refreshFor(iri, type, true); });
          throw new Error('HTTP ' + res.status);
        }
        return res.json();
      })
      .then(function (data) {
        state.graphData = data;
        state.currentIri = iri;
        state.currentType = type;
        var spec = buildELKGraph(data);
        return runLayout(spec).then(function (laid) {
          // Stash layout on graphData so Plan 08's renderer can read it.
          state.graphData.layout = laid;
          // Plan 08: mount the SVG + DIV scaffold. renderGraph defers the DOM
          // work to requestAnimationFrame, so the Promise still resolves
          // synchronously after the layout completes (callers can chain
          // post-render work via the resolved graphData).
          renderGraph(state.graphData);
          return state.graphData;
        });
      })
      .catch(function (err) {
        if (window.console && window.console.error) {
          window.console.error('[EntityGraph] refreshFor failed:', err);
        }
        throw err;
      });
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
    showEmpty: showEmpty,
    showSkeleton: showSkeleton,
    showError: showError,
    clearStates: clearStates,
    ICONS: ICONS,
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
