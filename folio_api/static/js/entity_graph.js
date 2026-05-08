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
 * Visual polish (v1.1 post-ship): arrowhead markers on subClassOf edges, dotted
 * background, canvas minimap, legend bar, red branch-root borders, blue selected
 * border + bg — ported from folio-enrich/folio-mapper reference implementations.
 */
(function () {
  'use strict';

  // ---------------- Performance instrumentation (Plan 14) ----------------
  function _perfMark(name) {
    if (typeof performance === 'undefined') return;
    if (typeof performance.mark !== 'function') return;
    try { performance.mark(name); } catch (_) {}
  }
  function _perfMeasure(name, startMark, endMark) {
    if (typeof performance === 'undefined') return;
    if (typeof performance.measure !== 'function') return;
    try { performance.measure(name, startMark, endMark); } catch (_) {}
  }

  // ---------------- Internal state ----------------
  const state = {
    activeTab: 'details',
    currentIri: null,
    currentType: null,
    graphData: null,
    transform: { x: 0, y: 0, scale: 1 },
    expandedIris: new Set(),
    isFullscreen: false,
    lastSelectedIri: null,
    lastSelectedType: null,
    // Node positions for minimap rendering: { iri: { x, y, w, h } }
    nodePositions: {},
    // Live node map shared between _mountGraph and drag handlers: { iri: { x, y, w, h } }
    // Updated in-place when a node is dragged.
    liveNodeMap: {},
  };

  function _readUrlSelection() {
    try {
      var params = new URLSearchParams(window.location.search || '');
      var iri = params.get('node');
      var type = params.get('type');
      if (!iri) return null;
      return { iri: iri, type: (type === 'property' ? 'property' : 'class') };
    } catch (e) {
      return null;
    }
  }

  // ---------------- Heroicons v2 outline (inline SVG markup) ----------------
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
        _elkLoadPromise = null;
        reject(new Error('Failed to load /static/js/vendor/elk.bundled.js'));
      };
      document.head.appendChild(s);
    });
    return _elkLoadPromise;
  }

  // ---------------- ELK layout pipeline (Plan 07) ----------------
  function buildELKGraph(graphData) {
    var selected = graphData.selected;
    var children = graphData.children || [];

    state.edgeRelationships = {};

    var targetIds = new Set();
    var edges = [];

    var apiNodes = Array.isArray(graphData.nodes) ? graphData.nodes : null;
    var apiEdges = Array.isArray(graphData.edges) ? graphData.edges : null;
    var hasNewShape = apiNodes && apiEdges;

    if (hasNewShape) {
      for (var ei = 0; ei < apiEdges.length; ei++) {
        var e = apiEdges[ei] || {};
        if (!e.source || !e.target) continue;
        var eid = 'e_api_' + ei;
        var rel = e.relationship || 'subClassOf';
        edges.push({ id: eid, sources: [e.source], targets: [e.target] });
        state.edgeRelationships[eid] = rel;
        if (rel === 'subClassOf') {
          targetIds.add(e.target);
        }
      }
    } else {
      var ancestors = graphData.ancestors || [];
      for (var i = 0; i < ancestors.length - 1; i++) {
        var lid = 'e_' + i;
        edges.push({
          id: lid,
          sources: [ancestors[i].iri],
          targets: [ancestors[i + 1].iri],
        });
        state.edgeRelationships[lid] = 'subClassOf';
        targetIds.add(ancestors[i + 1].iri);
      }
      if (ancestors.length > 0) {
        var lastAnc = ancestors[ancestors.length - 1];
        edges.push({
          id: 'e_anc_sel',
          sources: [lastAnc.iri],
          targets: [selected.iri],
        });
        state.edgeRelationships['e_anc_sel'] = 'subClassOf';
        targetIds.add(selected.iri);
      }
    }

    for (var ci = 0; ci < children.length; ci++) {
      var cid = 'e_child_' + ci;
      edges.push({
        id: cid,
        sources: [selected.iri],
        targets: [children[ci].iri],
      });
      state.edgeRelationships[cid] = 'subClassOf';
      targetIds.add(children[ci].iri);
    }

    var extraNodes = [];
    var seenExtraIris = new Set();
    if (graphData.expandedChildren) {
      var parentIris = Object.keys(graphData.expandedChildren);
      for (var pi = 0; pi < parentIris.length; pi++) {
        var parentIri = parentIris[pi];
        if (parentIri === selected.iri) continue;
        var expChildren = graphData.expandedChildren[parentIri] || [];
        for (var xi = 0; xi < expChildren.length; xi++) {
          var xc = expChildren[xi];
          if (!xc || !xc.iri) continue;
          var xid = 'e_exp_' + parentIri + '_' + xi;
          edges.push({
            id: xid,
            sources: [parentIri],
            targets: [xc.iri],
          });
          state.edgeRelationships[xid] = 'subClassOf';
          targetIds.add(xc.iri);
          if (!seenExtraIris.has(xc.iri)) {
            seenExtraIris.add(xc.iri);
            extraNodes.push(xc);
          }
        }
      }
    }

    var baseNodes;
    if (hasNewShape) {
      baseNodes = apiNodes.slice();
      var hasSelected = false;
      for (var nsi = 0; nsi < baseNodes.length; nsi++) {
        if (baseNodes[nsi] && baseNodes[nsi].iri === selected.iri) {
          hasSelected = true;
          break;
        }
      }
      if (!hasSelected) baseNodes.unshift(selected);
    } else {
      var legacyAncestors = graphData.ancestors || [];
      baseNodes = [selected].concat(legacyAncestors);
    }
    var seenIris = {};
    var allNodes = [];
    baseNodes.concat(children).concat(extraNodes).forEach(function (n) {
      if (n && n.iri && !seenIris[n.iri]) {
        seenIris[n.iri] = true;
        allNodes.push(n);
      }
    });
    var elkChildren = allNodes.map(function (n) {
      var labelText = n.label || '';
      var w = Math.max(180, labelText.length * 7.5 + 32);
      var node = {
        id: n.iri,
        width: w,
        height: 36,
        labels: [{ text: labelText }],
      };
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

  function runLayout(spec) {
    return loadELK().then(function (ELK) {
      var elk = new ELK();
      return elk.layout(spec);
    });
  }

  // ---------------- SVG renderer (Plan 08) ----------------

  // recenterSection — override ELK's spread port positions so every edge
  // leaves from the bottom-center of its source node and arrives at the
  // top-center of its target node (TB direction).
  // Ported from folio-enrich/frontend/index.html lines 8977-8998.
  function recenterSection(section, edge, nodeMap) {
    var srcId = edge.sources && edge.sources[0];
    var tgtId = edge.targets && edge.targets[0];
    var src = srcId && nodeMap[srcId];
    var tgt = tgtId && nodeMap[tgtId];
    if (!src || !tgt) return section;

    // TB (top-to-bottom) direction — folio-api always uses DOWN.
    var srcCx = src.x + src.w / 2;
    var tgtCx = tgt.x + tgt.w / 2;
    var downward = (tgt.y + tgt.h / 2) >= (src.y + src.h / 2);
    var sp = { x: srcCx, y: downward ? src.y + src.h : src.y };
    var ep = { x: tgtCx, y: downward ? tgt.y : tgt.y + tgt.h };
    return { startPoint: sp, endPoint: ep, bendPoints: [] };
  }

  function buildEdgePath(section) {
    var sp = section.startPoint;
    var ep = section.endPoint;
    // Cubic Bezier S-curve: 90° exit from source bottom, 90° entry at target top.
    var midY = (sp.y + ep.y) / 2;
    return 'M' + sp.x + ',' + sp.y + ' C' + sp.x + ',' + midY + ' ' + ep.x + ',' + midY + ' ' + ep.x + ',' + ep.y;
  }

  var SVG_NS = 'http://www.w3.org/2000/svg';

  // _findUltimateRootIris — locate ALL IRIs marked branch_root_type==='ultimate'.
  function _findUltimateRootIris(graphData) {
    var roots = new Set();
    var nodes = (graphData && graphData.nodes) || [];
    for (var i = 0; i < nodes.length; i++) {
      if (nodes[i] && nodes[i].branch_root_type === 'ultimate' && nodes[i].iri) {
        roots.add(nodes[i].iri);
      }
    }
    var ancestors = (graphData && graphData.ancestors) || [];
    for (var j = 0; j < ancestors.length; j++) {
      if (ancestors[j] && ancestors[j].branch_root_type === 'ultimate' && ancestors[j].iri) {
        roots.add(ancestors[j].iri);
      }
    }
    if (graphData && graphData.selected && graphData.selected.branch_root_type === 'ultimate' && graphData.selected.iri) {
      roots.add(graphData.selected.iri);
    }
    return roots;
  }

  // _findAncillaryRootIris — locate all IRIs marked branch_root_type==='ancillary'.
  // These are intermediate ancestor branch roots — styled with gray 3px border
  // (matching folio-enrich .graph-node.branch-root-ancillary pattern).
  function _findAncillaryRootIris(graphData) {
    var roots = new Set();
    var nodes = (graphData && graphData.nodes) || [];
    for (var i = 0; i < nodes.length; i++) {
      if (nodes[i] && nodes[i].branch_root_type === 'ancillary' && nodes[i].iri) {
        roots.add(nodes[i].iri);
      }
    }
    var ancestors = (graphData && graphData.ancestors) || [];
    for (var j = 0; j < ancestors.length; j++) {
      if (ancestors[j] && ancestors[j].branch_root_type === 'ancillary' && ancestors[j].iri) {
        roots.add(ancestors[j].iri);
      }
    }
    return roots;
  }

  // _buildTypeMap — derive a per-IRI 'class' | 'property' map from graphData.
  function _buildTypeMap(graphData) {
    var map = {};
    var selectedType = (graphData && graphData.selected && graphData.selected.type) || 'class';
    if (graphData && graphData.selected && graphData.selected.iri) {
      map[graphData.selected.iri] = selectedType;
    }
    var ancestors = (graphData && graphData.ancestors) || [];
    for (var i = 0; i < ancestors.length; i++) {
      if (ancestors[i] && ancestors[i].iri) {
        map[ancestors[i].iri] = ancestors[i].type || selectedType;
      }
    }
    var children = (graphData && graphData.children) || [];
    for (var j = 0; j < children.length; j++) {
      if (children[j] && children[j].iri) {
        map[children[j].iri] = children[j].type || 'class';
      }
    }
    return map;
  }

  // renderMinimap — draws node rectangles + current viewport rect onto the
  // #graph-minimap canvas. Ported from folio-enrich renderMinimap() pattern.
  // No-op if the canvas or node positions are not available.
  function renderMinimap() {
    var canvas = document.getElementById('graph-minimap');
    if (!canvas) return;
    var ctx = canvas.getContext('2d');
    var cw = canvas.width;
    var ch = canvas.height;
    ctx.clearRect(0, 0, cw, ch);

    var positions = Object.values(state.nodePositions || {});
    if (positions.length === 0) return;

    var minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (var i = 0; i < positions.length; i++) {
      var p = positions[i];
      if (p.x < minX) minX = p.x;
      if (p.y < minY) minY = p.y;
      if (p.x + p.w > maxX) maxX = p.x + p.w;
      if (p.y + p.h > maxY) maxY = p.y + p.h;
    }
    var gw = (maxX - minX) || 1;
    var gh = (maxY - minY) || 1;
    var scale = Math.min((cw - 8) / gw, (ch - 8) / gh);
    var ox = (cw - gw * scale) / 2;
    var oy = (ch - gh * scale) / 2;

    // Draw node rectangles (blue-tinted fill)
    ctx.fillStyle = 'rgba(59,130,246,0.35)';
    for (var j = 0; j < positions.length; j++) {
      var q = positions[j];
      ctx.fillRect(
        ox + (q.x - minX) * scale,
        oy + (q.y - minY) * scale,
        Math.max(q.w * scale, 2),
        Math.max(q.h * scale, 2)
      );
    }

    // Draw viewport rect
    var vp = document.getElementById('graph-viewport');
    if (vp && state.transform) {
      var vpW = vp.clientWidth;
      var vpH = vp.clientHeight;
      var t = state.transform;
      var rx = ox + (-t.x / t.scale - minX) * scale;
      var ry = oy + (-t.y / t.scale - minY) * scale;
      var rw = (vpW / t.scale) * scale;
      var rh = (vpH / t.scale) * scale;
      ctx.strokeStyle = 'rgba(107,114,128,0.5)';
      ctx.lineWidth = 1;
      ctx.strokeRect(rx, ry, rw, rh);
    }
  }

  // _mountGraph — actual DOM construction.
  function _mountGraph(graphData, opts) {
    opts = opts || {};
    var preserveZoom = !!opts.preserveZoom;
    var pane = _pane();
    if (!pane) return;
    var layout = graphData && graphData.layout;
    if (!layout) return;

    var children = layout.children || [];
    var edges = layout.edges || [];

    // Compute bounds with 16 px padding.
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

    pane.innerHTML = '';
    pane.removeAttribute('aria-busy');

    // Scaffolding: viewport > transform > (svg + nodes-div).
    var viewport = document.createElement('div');
    viewport.id = 'graph-viewport';
    // CSS owns cursor:grab; absolute+inset fill pane minus legend bar (28px).
    viewport.style.position = 'absolute';
    viewport.style.top = '0';
    viewport.style.left = '0';
    viewport.style.right = '0';
    viewport.style.bottom = '28px';   // reserve space for legend bar
    viewport.style.overflow = 'hidden';

    var xform = document.createElement('div');
    xform.id = 'graph-transform';
    xform.className = 'absolute top-0 left-0';
    xform.style.transformOrigin = '0 0';

    // SVG layer: arrowhead defs + edge paths.
    var svg = document.createElementNS(SVG_NS, 'svg');
    svg.setAttribute('id', 'graph-svg');
    svg.setAttribute('width', String(maxX));
    svg.setAttribute('height', String(maxY));
    svg.setAttribute('viewBox', '0 0 ' + maxX + ' ' + maxY);
    svg.style.position = 'absolute';
    svg.style.top = '0';
    svg.style.left = '0';
    svg.style.pointerEvents = 'none';
    svg.style.overflow = 'visible';

    // Arrowhead marker for subClassOf edges — ported from folio-enrich.
    // Color: blue-500 (#3b82f6) matching .graph-edge stroke.
    var defs = document.createElementNS(SVG_NS, 'defs');
    var marker = document.createElementNS(SVG_NS, 'marker');
    marker.setAttribute('id', 'arrow-sub');
    marker.setAttribute('viewBox', '0 0 10 10');
    marker.setAttribute('refX', '9');
    marker.setAttribute('refY', '5');
    marker.setAttribute('markerWidth', '7');
    marker.setAttribute('markerHeight', '7');
    marker.setAttribute('orient', 'auto');
    var arrowPath = document.createElementNS(SVG_NS, 'path');
    arrowPath.setAttribute('d', 'M0 0 L10 5 L0 10z');
    arrowPath.setAttribute('fill', '#3b82f6');
    marker.appendChild(arrowPath);
    defs.appendChild(marker);
    svg.appendChild(defs);

    // Accessibility label.
    svg.setAttribute('role', 'img');
    var _selectedLabel = (graphData.selected && graphData.selected.label) || '';
    var _rootLabel = '';
    if (graphData.ancestors && graphData.ancestors.length > 0 && graphData.ancestors[0].label) {
      _rootLabel = graphData.ancestors[0].label;
    } else {
      _rootLabel = _selectedLabel;
    }
    var _nodeCount = children.length;
    svg.setAttribute(
      'aria-label',
      'Entity graph for ' + _selectedLabel +
      ', rooted at ' + _rootLabel +
      ', showing ' + _nodeCount + ' nodes'
    );

    var edgesGroup = document.createElementNS(SVG_NS, 'g');
    edgesGroup.setAttribute('class', 'graph-edges');
    svg.appendChild(edgesGroup);

    var nodesDiv = document.createElement('div');
    nodesDiv.className = 'graph-nodes';
    nodesDiv.style.position = 'relative';
    nodesDiv.style.width = maxX + 'px';
    nodesDiv.style.height = maxY + 'px';

    // Build node position map for recenterSection (id → {x, y, w, h}).
    // Also populate state.liveNodeMap so drag handlers can read/write positions.
    var nodeMap = {};
    state.liveNodeMap = {};
    for (var nmi = 0; nmi < children.length; nmi++) {
      var nm = children[nmi];
      if (nm && nm.id) {
        var nmEntry = { x: nm.x || 0, y: nm.y || 0, w: nm.width || 0, h: nm.height || 0 };
        nodeMap[nm.id] = nmEntry;
        state.liveNodeMap[nm.id] = nmEntry;
      }
    }

    // Edges. Tag each path with data-src and data-tgt so drag handlers can
    // efficiently find and redraw only the edges incident to the dragged node.
    for (var ei = 0; ei < edges.length; ei++) {
      var edge = edges[ei] || {};
      var sections = edge.sections || [];
      var rel = (state.edgeRelationships && state.edgeRelationships[edge.id]) || 'subClassOf';
      var edgeClass = 'graph-edge' + (rel === 'seeAlso' ? ' graph-edge--seealso' : '');
      for (var si = 0; si < sections.length; si++) {
        var section = sections[si];
        if (!section || !section.startPoint || !section.endPoint) continue;
        // Override ELK's spread port positions — converge all edges at node centers.
        var centeredSection = recenterSection(section, edge, nodeMap);
        var pathEl = document.createElementNS(SVG_NS, 'path');
        pathEl.setAttribute('d', buildEdgePath(centeredSection));
        pathEl.setAttribute('class', edgeClass);
        // Tag source and target IRIs for efficient incident-edge lookup during drag.
        var edgeSrc = edge.sources && edge.sources[0];
        var edgeTgt = edge.targets && edge.targets[0];
        if (edgeSrc) pathEl.setAttribute('data-src', edgeSrc);
        if (edgeTgt) pathEl.setAttribute('data-tgt', edgeTgt);
        // Arrowhead only on subClassOf hierarchy edges (not seeAlso dashed links).
        if (rel !== 'seeAlso') {
          pathEl.setAttribute('marker-end', 'url(#arrow-sub)');
        }
        edgesGroup.appendChild(pathEl);
      }
    }

    // Selected + root markers.
    var selectedIri = (graphData.selected && graphData.selected.iri) || null;
    var ultimateRootIris = _findUltimateRootIris(graphData);
    var ancillaryRootIris = _findAncillaryRootIris(graphData);

    var selectedChildCount = (graphData.selected && typeof graphData.selected.child_count === 'number')
      ? graphData.selected.child_count : 0;

    var childCountMap = {};
    var allChildrenForBadge = (graphData.children || []).slice();
    if (graphData.expandedChildren) {
      Object.keys(graphData.expandedChildren).forEach(function (parentIri) {
        (graphData.expandedChildren[parentIri] || []).forEach(function (c) {
          allChildrenForBadge.push(c);
        });
      });
    }
    for (var bi = 0; bi < allChildrenForBadge.length; bi++) {
      var bc = allChildrenForBadge[bi];
      if (bc && bc.iri && typeof bc.child_count === 'number') {
        childCountMap[bc.iri] = bc.child_count;
      }
    }

    // Reset node positions for minimap.
    state.nodePositions = {};

    for (var ni = 0; ni < children.length; ni++) {
      var node = children[ni];
      if (!node) continue;
      var isSelected = !!(selectedIri && node.id === selectedIri);
      var isUltimateRoot = !!(ultimateRootIris && ultimateRootIris.has && ultimateRootIris.has(node.id));
      var isAncillaryRoot = !!(ancillaryRootIris && ancillaryRootIris.has && ancillaryRootIris.has(node.id));
      var isRoot = isUltimateRoot || isAncillaryRoot;

      // Store position for minimap.
      state.nodePositions[node.id] = {
        x: node.x || 0,
        y: node.y || 0,
        w: node.width || 0,
        h: node.height || 0,
      };

      // Outer classes drive CSS-based border/bg overrides.
      var outerClasses = ['graph-node'];
      if (isSelected) outerClasses.push('graph-node-selected');
      if (isUltimateRoot) outerClasses.push('graph-node-root');
      if (isAncillaryRoot && !isUltimateRoot) outerClasses.push('graph-node-ancillary');

      // Label weight: bold for roots/selected, normal for others.
      var labelClass;
      if (isRoot) {
        labelClass = 'graph-node-label text-xs font-bold text-gray-900';
      } else if (isSelected) {
        labelClass = 'graph-node-label text-xs font-semibold text-blue-900';
      } else {
        labelClass = 'graph-node-label text-xs font-normal text-gray-700';
      }

      // Root nodes are visually distinguished by a thick border (CSS classes above).
      // No text badge — folio-enrich omits ROOT labels entirely.

      // +N Children button on selected node.
      var showChildrenBtn = isSelected && selectedChildCount > 0;
      var childrenBtnHtml = showChildrenBtn
        ? '<button type="button" class="graph-node-children-btn mt-1 self-start ' +
          'bg-blue-50 text-blue-700 border border-blue-200 rounded-md ' +
          'px-2 py-1 text-xs font-semibold hover:bg-blue-100 ' +
          'focus-visible:outline-none focus-visible:ring-2 ' +
          'focus-visible:ring-blue-500 focus-visible:ring-offset-1"></button>'
        : '';

      // Hover-only +N badge for non-selected nodes with children.
      var nodeChildCount = childCountMap[node.id];
      var showHoverBadge = !isSelected && typeof nodeChildCount === 'number' && nodeChildCount > 0;
      var hoverBadgeHtml = showHoverBadge
        ? '<span class="graph-node-hover-badge absolute -top-2 -right-2 ' +
          'bg-blue-50 text-blue-700 border border-blue-200 rounded-full ' +
          'px-1.5 py-0.5 text-[10px] font-bold ' +
          'opacity-0 pointer-events-none transition-opacity duration-100 cursor-pointer"></span>'
        : '';

      var nodeDiv = document.createElement('div');
      nodeDiv.className = outerClasses.join(' ') + ' relative flex flex-col';
      nodeDiv.setAttribute('data-iri', node.id);
      nodeDiv.style.position = 'absolute';
      nodeDiv.style.left = (node.x || 0) + 'px';
      nodeDiv.style.top = (node.y || 0) + 'px';
      nodeDiv.style.width = (node.width || 0) + 'px';
      if (showChildrenBtn) {
        nodeDiv.style.minHeight = (node.height || 0) + 'px';
      } else {
        nodeDiv.style.height = (node.height || 0) + 'px';
      }
      nodeDiv.style.cursor = 'grab';

      // Inner wrapper: rounded-lg for polished look; border/bg overridden by CSS class rules.
      // No leading icon, no ROOT badge — matches folio-enrich which uses label text only.
      // white-space:nowrap (via .graph-node CSS) keeps the label on one line.
      // flex:1 + text-align:center on the label span centers text like folio-enrich.
      nodeDiv.innerHTML =
        '<div class="flex items-center px-2 py-1.5 h-full bg-white border border-gray-300 rounded-lg">' +
          '<span class="' + labelClass + '" style="flex:1;text-align:center;overflow:hidden;text-overflow:ellipsis;"></span>' +
        '</div>' +
        childrenBtnHtml +
        hoverBadgeHtml;

      var labelText = '';
      if (node.labels && node.labels.length && node.labels[0] && node.labels[0].text != null) {
        labelText = String(node.labels[0].text);
      }
      var labelSpan = nodeDiv.querySelector('.graph-node-label');
      if (labelSpan) {
        labelSpan.textContent = labelText;
        labelSpan.title = labelText;  // tooltip for truncated labels
      }

      if (showChildrenBtn) {
        var childrenBtn = nodeDiv.querySelector('.graph-node-children-btn');
        if (childrenBtn) {
          childrenBtn.textContent = '+' + selectedChildCount + ' Children';
          childrenBtn.setAttribute(
            'aria-label',
            'Show ' + selectedChildCount + ' children of ' + labelText
          );
          childrenBtn.addEventListener('click', (function (capturedIri) {
            return function (e) {
              e.stopPropagation();
              expand(capturedIri);
            };
          })(node.id));
        }
      }

      if (showHoverBadge) {
        var hoverBadge = nodeDiv.querySelector('.graph-node-hover-badge');
        if (hoverBadge) {
          hoverBadge.textContent = '+' + nodeChildCount;
          hoverBadge.setAttribute(
            'aria-label',
            'Show ' + nodeChildCount + ' children of ' + labelText
          );
          hoverBadge.addEventListener('click', (function (capturedIri) {
            return function (e) {
              e.stopPropagation();
              expand(capturedIri);
            };
          })(node.id));
        }
      }

      // Wire drag on this node (per-node mousedown captured via IIFE).
      nodeDiv.addEventListener('mousedown', (function (capturedNodeEl, capturedIri) {
        return function (e) {
          if (e.button !== 0) return;
          // Don't start drag on the +N children button or hover badge.
          if (e.target.closest && (
            e.target.closest('.graph-node-children-btn') ||
            e.target.closest('.graph-node-hover-badge')
          )) return;
          _nodeDragStart(e, capturedNodeEl, capturedIri, edgesGroup);
        };
      })(nodeDiv, node.id));

      nodesDiv.appendChild(nodeDiv);
    }

    // Delegated click listener for graph node navigation.
    // Suppresses click if a drag just finished (mouse moved > 3px).
    nodesDiv.addEventListener('click', function (ev) {
      if (_dragState.wasDragged) return;   // suppress post-drag click
      var nodeEl = ev.target.closest && ev.target.closest('.graph-node');
      if (!nodeEl) return;
      if (ev.target.closest('.graph-node-children-btn')) return;
      if (ev.target.closest('.graph-node-hover-badge')) return;
      var iri = nodeEl.getAttribute('data-iri');
      if (!iri) return;
      if (iri === state.currentIri) return;
      if (typeof window.selectNodeByIri === 'function') {
        window.selectNodeByIri(iri);
      } else if (window.console && window.console.warn) {
        window.console.warn('[EntityGraph] selectNodeByIri not available on window');
      }
    });

    xform.appendChild(svg);
    xform.appendChild(nodesDiv);
    viewport.appendChild(xform);

    // Minimap canvas (bottom-right corner, above legend bar).
    var minimapCanvas = document.createElement('canvas');
    minimapCanvas.id = 'graph-minimap';
    minimapCanvas.width = 140;
    minimapCanvas.height = 90;
    minimapCanvas.setAttribute('aria-hidden', 'true');
    viewport.appendChild(minimapCanvas);

    pane.appendChild(viewport);

    // Legend bar — ported from folio-enrich graph-modal-legend + folio-mapper legend footer.
    var legend = document.createElement('div');
    legend.id = 'graph-legend';
    legend.innerHTML =
      '<div class="graph-legend-item">' +
        '<svg width="22" height="10" aria-hidden="true" style="flex-shrink:0">' +
          '<line x1="0" y1="5" x2="15" y2="5" stroke="#3b82f6" stroke-width="2"/>' +
          '<polygon points="13,2 20,5 13,8" fill="#3b82f6"/>' +
        '</svg>' +
        '<span>subClassOf</span>' +
      '</div>' +
      '<div class="graph-legend-item">' +
        '<svg width="22" height="10" aria-hidden="true" style="flex-shrink:0">' +
          '<line x1="0" y1="5" x2="22" y2="5" stroke="#8b5cf6" stroke-width="1.5" stroke-dasharray="4,2"/>' +
        '</svg>' +
        '<span>seeAlso</span>' +
      '</div>' +
      '<div class="graph-legend-item">' +
        '<span style="display:inline-block;width:10px;height:10px;border-radius:2px;border:2px solid #3b82f6;background:#eff6ff;flex-shrink:0"></span>' +
        '<span>Focus</span>' +
      '</div>' +
      '<div class="graph-legend-item">' +
        '<span style="display:inline-block;width:10px;height:10px;border-radius:2px;border:3px solid #ef4444;background:#fef2f2;flex-shrink:0"></span>' +
        '<span>Ultimate Ancestor</span>' +
      '</div>' +
      '<div class="graph-legend-item">' +
        '<span style="display:inline-block;width:10px;height:10px;border-radius:2px;border:3px solid #6b7280;background:#f9fafb;flex-shrink:0"></span>' +
        '<span>Ancillary Ancestor</span>' +
      '</div>' +
      '<span class="graph-legend-hint">Click to select • Drag node to rearrange • Scroll to zoom • Drag canvas to pan</span>';
    pane.appendChild(legend);

    wirePanZoom();
    if (preserveZoom) {
      applyTransform();
    } else {
      requestAnimationFrame(fitGraph);
    }
    // Initial minimap render (deferred so layout is measured).
    requestAnimationFrame(renderMinimap);

    _perfMark('eg:render:end');
    _perfMeasure('eg:render', 'eg:render:start', 'eg:render:end');
    _perfMeasure('eg:total', 'eg:fetch:start', 'eg:render:end');
  }

  // ---------------- Pan / Zoom (Plan 10) ----------------

  function applyTransform() {
    var el = document.getElementById('graph-transform');
    if (!el) return;
    var t = state.transform;
    el.style.transform = 'translate(' + t.x + 'px, ' + t.y + 'px) scale(' + t.scale + ')';
    // Re-render minimap on every transform change so viewport rect stays current.
    renderMinimap();
  }

  function fitGraph() {
    var vp = document.getElementById('graph-viewport');
    if (!vp) return;
    var rect = vp.getBoundingClientRect();
    var vw = rect.width;
    var vh = rect.height;
    if (vw === 0 || vh === 0) {
      requestAnimationFrame(fitGraph);
      return;
    }

    var gd = state.graphData;
    var layout = gd && gd.layout;
    if (!layout) return;
    var laidChildren = layout.children || [];
    var gw = 0;
    var gh = 0;
    for (var i = 0; i < laidChildren.length; i++) {
      var c = laidChildren[i];
      var rx = (c.x || 0) + (c.width || 0);
      var ry = (c.y || 0) + (c.height || 0);
      if (rx > gw) gw = rx;
      if (ry > gh) gh = ry;
    }
    if (gw === 0 || gh === 0) return;

    var pad = 16;
    var availW = vw - 2 * pad;
    var availH = vh - 2 * pad;
    var scale = Math.min(availW / gw, availH / gh, 1);
    if (scale < 0.2) scale = 0.2;

    var tx = (vw - gw * scale) / 2;
    var ty = (vh - gh * scale) / 2;
    state.transform = { x: tx, y: ty, scale: scale };
    applyTransform();
  }

  function _onWheel(e) {
    e.preventDefault();
    var vp = document.getElementById('graph-viewport');
    if (!vp) return;
    var rect = vp.getBoundingClientRect();
    var mx = e.clientX - rect.left;
    var my = e.clientY - rect.top;
    var oldScale = state.transform.scale;
    var zoomFactor = e.deltaY < 0 ? 1.12 : 1 / 1.12;
    var newScale = Math.max(0.2, Math.min(4.0, oldScale * zoomFactor));
    state.transform.x = mx - (mx - state.transform.x) * (newScale / oldScale);
    state.transform.y = my - (my - state.transform.y) * (newScale / oldScale);
    state.transform.scale = newScale;
    applyTransform();
  }

  var _panning = false;
  var _panStart = { x: 0, y: 0 };
  var _panStartXform = { x: 0, y: 0 };

  function _panMouseDown(e) {
    if (e.button !== 0) return;
    if (e.target && e.target.closest && e.target.closest('.graph-node')) return;
    _panning = true;
    _panStart = { x: e.clientX, y: e.clientY };
    _panStartXform = { x: state.transform.x, y: state.transform.y };
    var vp = document.getElementById('graph-viewport');
    if (vp) vp.classList.add('graph-grabbing');
    document.addEventListener('mousemove', _panMouseMove);
    document.addEventListener('mouseup', _panMouseUp);
  }

  function _panMouseMove(e) {
    if (!_panning) return;
    state.transform.x = _panStartXform.x + (e.clientX - _panStart.x);
    state.transform.y = _panStartXform.y + (e.clientY - _panStart.y);
    applyTransform();
  }

  function _panMouseUp() {
    _panning = false;
    var vp = document.getElementById('graph-viewport');
    if (vp) vp.classList.remove('graph-grabbing');
    document.removeEventListener('mousemove', _panMouseMove);
    document.removeEventListener('mouseup', _panMouseUp);
  }

  function wirePanZoom() {
    var vp = document.getElementById('graph-viewport');
    if (!vp || vp.dataset.panZoomWired === '1') return;
    vp.dataset.panZoomWired = '1';
    vp.addEventListener('wheel', _onWheel, { passive: false });
    vp.addEventListener('mousedown', _panMouseDown);
  }

  // ---------------- Node drag-to-rearrange (client-side only) ----------------
  // State is module-level so _nodeDragMove/_nodeDragUp can be removed from
  // document without passing them as arguments.

  var _dragState = {
    active: false,
    nodeEl: null,        // DOM div being dragged
    iri: null,           // IRI of the dragged node
    edgesGroup: null,    // SVG <g> containing all edge <path>s
    startClientX: 0,
    startClientY: 0,
    startNodeX: 0,       // ELK x coordinate at drag start
    startNodeY: 0,       // ELK y coordinate at drag start
    wasDragged: false,   // set to true once mouse moves > 3px
  };

  function _nodeDragStart(e, nodeEl, iri, edgesGroup) {
    e.stopPropagation();   // prevent pan handler from also activating
    _dragState.active = true;
    _dragState.nodeEl = nodeEl;
    _dragState.iri = iri;
    _dragState.edgesGroup = edgesGroup;
    _dragState.startClientX = e.clientX;
    _dragState.startClientY = e.clientY;
    var pos = state.liveNodeMap[iri];
    _dragState.startNodeX = pos ? pos.x : 0;
    _dragState.startNodeY = pos ? pos.y : 0;
    _dragState.wasDragged = false;
    document.body.style.userSelect = 'none';
    document.body.style.cursor = 'grabbing';
    document.addEventListener('mousemove', _nodeDragMove);
    document.addEventListener('mouseup', _nodeDragUp);
  }

  function _nodeDragMove(e) {
    if (!_dragState.active) return;
    var dx = e.clientX - _dragState.startClientX;
    var dy = e.clientY - _dragState.startClientY;
    // Only activate drag mode once mouse moves more than 3 px (avoids click suppression on micro-jitter).
    if (!_dragState.wasDragged && Math.abs(dx) < 3 && Math.abs(dy) < 3) return;
    _dragState.wasDragged = true;

    // Scale deltas by inverse of viewport zoom so node moves 1:1 with mouse.
    var scale = state.transform.scale || 1;
    var newX = _dragState.startNodeX + dx / scale;
    var newY = _dragState.startNodeY + dy / scale;

    // Update live position map (used by recenterSection when redrawing edges).
    var pos = state.liveNodeMap[_dragState.iri];
    if (pos) {
      pos.x = newX;
      pos.y = newY;
    }
    // Also update the minimap position map.
    var miniPos = state.nodePositions[_dragState.iri];
    if (miniPos) {
      miniPos.x = newX;
      miniPos.y = newY;
    }

    // Move the node DOM element via CSS transform (avoids reflow of position properties).
    var offsetX = newX - _dragState.startNodeX;
    var offsetY = newY - _dragState.startNodeY;
    _dragState.nodeEl.style.transform = 'translate(' + offsetX + 'px,' + offsetY + 'px)';

    // Redraw only the incident edges (edges where data-src or data-tgt === dragged IRI).
    _redrawIncidentEdges(_dragState.iri, _dragState.edgesGroup);

    // Update minimap to reflect new position.
    renderMinimap();
  }

  function _nodeDragUp() {
    if (!_dragState.active) return;
    _dragState.active = false;
    document.body.style.userSelect = '';
    document.body.style.cursor = '';
    document.removeEventListener('mousemove', _nodeDragMove);
    document.removeEventListener('mouseup', _nodeDragUp);

    // Commit final position: convert transform to actual left/top, clear transform.
    var nodeEl = _dragState.nodeEl;
    if (nodeEl && _dragState.wasDragged) {
      var pos = state.liveNodeMap[_dragState.iri];
      if (pos) {
        nodeEl.style.left = pos.x + 'px';
        nodeEl.style.top = pos.y + 'px';
      }
      nodeEl.style.transform = '';
      // Restore grab cursor now that drag is complete.
      nodeEl.style.cursor = 'grab';
    }

    // Clear wasDragged flag after a tick so the click handler (which fires after
    // mouseup) can read it, then reset it.
    setTimeout(function () { _dragState.wasDragged = false; }, 0);
  }

  // _redrawIncidentEdges — update d attribute on all <path>s in edgesGroup
  // whose data-src or data-tgt matches the given IRI, using the current
  // state.liveNodeMap positions. Only these paths are touched — O(edges) but
  // each update is a single setAttribute call.
  function _redrawIncidentEdges(iri, edgesGroup) {
    if (!edgesGroup) return;
    // Attribute value selectors (double-quoted) do NOT need CSS.escape —
    // special chars like `:`, `/`, `#` are literal inside quoted values.
    // We only need to escape embedded double-quotes (rare in IRIs but safe to handle).
    var safeIri = iri.replace(/\\/g, '\\\\').replace(/"/g, '\\"');
    var paths = edgesGroup.querySelectorAll('path[data-src="' + safeIri + '"],path[data-tgt="' + safeIri + '"]');
    for (var i = 0; i < paths.length; i++) {
      var pathEl = paths[i];
      var src = pathEl.getAttribute('data-src');
      var tgt = pathEl.getAttribute('data-tgt');
      var srcPos = src && state.liveNodeMap[src];
      var tgtPos = tgt && state.liveNodeMap[tgt];
      if (!srcPos || !tgtPos) continue;
      var section = {
        startPoint: null,
        endPoint: null,
      };
      // Replicate recenterSection logic inline using liveNodeMap.
      var srcCx = srcPos.x + srcPos.w / 2;
      var tgtCx = tgtPos.x + tgtPos.w / 2;
      var downward = (tgtPos.y + tgtPos.h / 2) >= (srcPos.y + srcPos.h / 2);
      section.startPoint = { x: srcCx, y: downward ? srcPos.y + srcPos.h : srcPos.y };
      section.endPoint   = { x: tgtCx, y: downward ? tgtPos.y : tgtPos.y + tgtPos.h };
      pathEl.setAttribute('d', buildEdgePath(section));
    }
  }

  function renderGraph(graphData, opts) {
    if (!graphData || !graphData.layout) return;
    clearStates();
    requestAnimationFrame(function () {
      _mountGraph(graphData, opts);
    });
  }

  // ---------------- Public API ----------------

  function init() {
    document.addEventListener('entity:selected', _onEntitySelected);
    var fromUrl = _readUrlSelection();
    if (fromUrl) {
      state.lastSelectedIri = fromUrl.iri;
      state.lastSelectedType = fromUrl.type;
    }
    _wireFullscreenChrome();
  }

  function _onEntitySelected(ev) {
    var detail = (ev && ev.detail) || {};
    if (detail.iri) {
      state.lastSelectedIri = detail.iri;
      state.lastSelectedType = detail.type || 'class';
    }
    if (state.activeTab !== 'graph') return;
    if (!detail.iri) return;
    if (detail.iri === state.currentIri && detail.type === state.currentType) return;
    refreshFor(detail.iri, detail.type).catch(function (err) {
      if (window.console && window.console.error) {
        window.console.error('[EntityGraph] _onEntitySelected refreshFor failed:', err);
      }
    });
  }

  function onTabActivated() {
    var iri = null;
    var type = 'class';
    var sel = document.querySelector('.tree-node.selected[data-id]');
    if (sel && sel.getAttribute('data-id')) {
      iri = sel.getAttribute('data-id');
      type = sel.getAttribute('data-type') || 'class';
    } else if (state.lastSelectedIri) {
      iri = state.lastSelectedIri;
      type = state.lastSelectedType || 'class';
    }
    if (!iri) {
      showEmpty();
      return;
    }
    if (state.currentIri === iri && state.graphData && state.graphData.layout) {
      return;
    }
    refreshFor(iri, type).catch(function (err) {
      if (window.console && window.console.error) {
        window.console.error('[EntityGraph] onTabActivated refreshFor failed:', err);
      }
    });
  }

  function refreshFor(iri, type, force) {
    if (!force && iri === state.currentIri && type === state.currentType && state.graphData) {
      return Promise.resolve(state.graphData);
    }

    _perfMark('eg:fetch:start');
    showSkeleton();

    state.transform = { x: 0, y: 0, scale: 1 };
    state.expandedIris = new Set();
    state.graphData = null;

    var url = '/explore/api/entity-graph/' + encodeURIComponent(iri);
    return fetch(url, { headers: { 'Accept': 'application/json' } })
      .then(function (res) {
        if (!res.ok) {
          var errLabel = (state.graphData && state.graphData.selected && state.graphData.selected.label) || iri;
          showError(errLabel, function () { refreshFor(iri, type, true); });
          throw new Error('HTTP ' + res.status);
        }
        return res.json();
      })
      .then(function (data) {
        _perfMark('eg:fetch:end');
        _perfMeasure('eg:fetch', 'eg:fetch:start', 'eg:fetch:end');
        _perfMark('eg:layout:start');

        state.graphData = data;
        state.currentIri = iri;
        state.currentType = type;
        var spec = buildELKGraph(data);
        return runLayout(spec).then(function (laid) {
          state.graphData.layout = laid;
          _perfMark('eg:layout:end');
          _perfMeasure('eg:layout', 'eg:layout:start', 'eg:layout:end');
          _perfMark('eg:render:start');
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
    if (!state.graphData) {
      return Promise.reject(new Error('No graph loaded'));
    }
    if (state.expandedIris.has(iri)) {
      return Promise.resolve(state.graphData);
    }

    var url = '/explore/api/entity-graph/' + encodeURIComponent(iri) + '?mode=children';
    return fetch(url, { headers: { 'Accept': 'application/json' } })
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      })
      .then(function (data) {
        var fetchedChildren = (data && data.children) || [];
        state.expandedIris.add(iri);
        if (state.graphData.selected && iri === state.graphData.selected.iri) {
          state.graphData.children = fetchedChildren;
        } else {
          state.graphData.expandedChildren = state.graphData.expandedChildren || {};
          state.graphData.expandedChildren[iri] = fetchedChildren;
        }
        var spec = buildELKGraph(state.graphData);
        return runLayout(spec).then(function (laid) {
          state.graphData.layout = laid;
          renderGraph(state.graphData, { preserveZoom: true });
          return state.graphData;
        });
      })
      .catch(function (err) {
        if (window.console && window.console.error) {
          window.console.error('[EntityGraph] expand failed for', iri, err);
        }
        throw err;
      });
  }

  function close() {
    // No-op.
  }

  function toggleFullscreen() {
    var modalRoot = document.getElementById('graph-modal-root');
    var modalHost = document.getElementById('graph-modal-host');
    var inPaneHost = document.getElementById('tab-panel-graph');
    var pane = document.getElementById('entity-graph-pane');
    var fsBtn = document.getElementById('tab-fullscreen');
    if (!modalRoot || !modalHost || !inPaneHost || !pane) return;
    if (state.isFullscreen) {
      inPaneHost.appendChild(pane);
      modalRoot.classList.add('hidden');
      modalRoot.setAttribute('aria-hidden', 'true');
      state.isFullscreen = false;
      if (fsBtn) fsBtn.focus();
      applyTransform();
    } else {
      modalHost.appendChild(pane);
      modalRoot.classList.remove('hidden');
      modalRoot.setAttribute('aria-hidden', 'false');
      state.isFullscreen = true;
      var closeBtn = document.getElementById('graph-modal-close');
      if (closeBtn) closeBtn.focus();
      applyTransform();
    }
  }

  function _wireFullscreenChrome() {
    var fsBtn = document.getElementById('tab-fullscreen');
    var closeBtn = document.getElementById('graph-modal-close');
    var scrim = document.getElementById('graph-modal-scrim');
    var panel = document.getElementById('graph-modal-panel');
    if (fsBtn && fsBtn.dataset.fsWired !== '1') {
      fsBtn.dataset.fsWired = '1';
      var iconHost = fsBtn.querySelector('.full-screen-icon-host');
      if (iconHost) iconHost.innerHTML = ICONS.arrowsPointingOut;
      fsBtn.addEventListener('click', toggleFullscreen);
    }
    if (closeBtn && closeBtn.dataset.fsWired !== '1') {
      closeBtn.dataset.fsWired = '1';
      var xHost = closeBtn.querySelector('.x-mark-icon-host');
      if (xHost) xHost.innerHTML = ICONS.xMark;
      closeBtn.addEventListener('click', toggleFullscreen);
    }
    if (scrim && scrim.dataset.fsWired !== '1') {
      scrim.dataset.fsWired = '1';
      scrim.addEventListener('click', toggleFullscreen);
    }
    if (!document.body.dataset.fsEscWired) {
      document.body.dataset.fsEscWired = '1';
      document.addEventListener('keydown', function (e) {
        if (e.key !== 'Escape') return;
        if (state.isFullscreen) {
          e.preventDefault();
          toggleFullscreen();
        }
      });
    }
    if (panel && panel.dataset.fsTrapWired !== '1') {
      panel.dataset.fsTrapWired = '1';
      panel.addEventListener('keydown', function (e) {
        if (e.key !== 'Tab' || !state.isFullscreen) return;
        var focusables = panel.querySelectorAll(
          'button:not([disabled]), [href], [tabindex="0"], input:not([disabled])'
        );
        if (focusables.length === 0) return;
        var first = focusables[0];
        var last = focusables[focusables.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      });
    }
  }

  // ---------------- Export ----------------
  window.EntityGraph = {
    init: init,
    loadELK: loadELK,
    refreshFor: refreshFor,
    expand: expand,
    close: close,
    toggleFullscreen: toggleFullscreen,
    onTabActivated: onTabActivated,
    showEmpty: showEmpty,
    showSkeleton: showSkeleton,
    showError: showError,
    clearStates: clearStates,
    applyTransform: applyTransform,
    fitGraph: fitGraph,
    renderMinimap: renderMinimap,
    ICONS: ICONS,
    get state() { return state; },
  };

  // ---------------- Boot ----------------
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
