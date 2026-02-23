/**
 * Unified Tree JavaScript — Combined class + property tree in one view.
 * Parameterized by section config so both types share the same tree logic.
 */

// Section configuration — maps each entity type to its API endpoints and DOM ids
const SECTIONS = {
    class: {
        rootListId: 'class-tree-root',
        sectionId: 'class-section',
        countId: 'class-count',
        treeDataEndpoint: '/taxonomy/tree/data',
        nodeDataEndpoint: '/taxonomy/tree/node/',
        detailsEndpoint: '/taxonomy/class-details/',
        searchEndpoint: '/taxonomy/tree/search',
        pathEndpoint: '/taxonomy/tree/path/',
        type: 'class'
    },
    property: {
        rootListId: 'property-tree-root',
        sectionId: 'property-section',
        countId: 'property-count',
        treeDataEndpoint: '/properties/tree/data',
        nodeDataEndpoint: '/properties/tree/node/',
        detailsEndpoint: '/properties/property-details/',
        searchEndpoint: '/properties/tree/search',
        pathEndpoint: '/properties/tree/path/',
        type: 'property'
    }
};

// Cache and state
const nodeDataCache = new Map();
const MAX_CACHE_SIZE = 200;
let isLoadingTree = false;

// ---------- Cache helper ----------
async function getNodeData(nodeId, sectionType) {
    const cacheKey = sectionType + ':' + nodeId;
    if (nodeDataCache.has(cacheKey)) return nodeDataCache.get(cacheKey);

    const cfg = SECTIONS[sectionType];
    const extractedId = extractIdFromIri(nodeId);
    const response = await fetch(cfg.nodeDataEndpoint + encodeURIComponent(extractedId));
    if (!response.ok) throw new Error('Failed to fetch node data: ' + response.status);
    const data = await response.json();

    nodeDataCache.set(cacheKey, data);
    nodeDataCache.set(sectionType + ':' + extractedId, data);

    // Prune cache
    if (nodeDataCache.size > MAX_CACHE_SIZE) {
        const keys = [...nodeDataCache.keys()];
        const deleteCount = Math.ceil(MAX_CACHE_SIZE * 0.2);
        for (let i = 0; i < deleteCount; i++) nodeDataCache.delete(keys[i]);
    }
    return data;
}

// ---------- IRI helpers ----------
function extractIdFromIri(iri) {
    if (!iri || !iri.startsWith('http')) return iri;
    const parts = iri.split('/').filter(p => p.trim().length > 0);
    return parts.length > 0 ? parts[parts.length - 1] : iri;
}

// ---------- Section collapse/expand ----------
function setupSectionHeaders() {
    document.querySelectorAll('.section-header').forEach(header => {
        header.addEventListener('click', () => {
            const sectionType = header.dataset.section;
            const cfg = SECTIONS[sectionType];
            const rootList = document.getElementById(cfg.rootListId);
            const chevron = header.querySelector('.section-chevron');
            if (rootList.style.display === 'none') {
                rootList.style.display = '';
                chevron.classList.remove('collapsed');
            } else {
                rootList.style.display = 'none';
                chevron.classList.add('collapsed');
            }
        });
    });
}

// ---------- Tree node rendering ----------
function renderTreeNode(node, container, sectionType) {
    const hasChildren = node.children;
    const nodeClass = hasChildren ? 'has-children collapsed' : '';
    const expandIcon = hasChildren
        ? '<span class="expand-icon"><svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 3 11 8 6 13"></polyline></svg></span>'
        : '<span class="leaf-indicator"><span class="leaf-dot"></span></span>';

    const li = $(`
        <li class="tree-node ${nodeClass}" data-id="${node.id}" data-type="${sectionType}">
            <div class="node-content">
                ${expandIcon}
                <span class="node-label">${node.text}</span>
            </div>
            ${hasChildren ? '<ul class="children-container" style="display:none;"></ul>' : ''}
        </li>
    `);
    container.append(li);
}

function loadTreeNodes(nodeId, container, sectionType) {
    if (container.children('.tree-node').length > 0) return;
    container.append('<li class="loading-indicator"><span>Loading...</span></li>');

    const cfg = SECTIONS[sectionType];
    fetch(cfg.treeDataEndpoint + '?node_id=' + encodeURIComponent(nodeId))
        .then(r => { if (!r.ok) throw new Error('Network error'); return r.json(); })
        .then(data => {
            container.find('.loading-indicator').remove();
            container.children('.tree-node').remove();
            data.forEach(node => {
                if (container.children('.tree-node[data-id="' + node.id + '"]').length === 0) {
                    renderTreeNode(node, container, sectionType);
                }
            });
            // Update count badge for root level
            if (nodeId === '#') {
                const countEl = document.getElementById(cfg.countId);
                if (countEl) countEl.textContent = data.length;
            }
            setupNodeClickHandlers();
        })
        .catch(() => {
            container.find('.loading-indicator').html('<span class="text-red-500">Error loading. Try again.</span>');
        });
}

// ---------- Click handlers ----------
function setupNodeClickHandlers() {
    try {
        $('.expand-icon').off('click.unified').on('click.unified', function(e) {
            e.stopPropagation();
            const li = $(this).closest('li');
            if (li.length) toggleNode(li);
        });
        $('.node-content').off('click.unified').on('click.unified', function() {
            const li = $(this).closest('li');
            if (li.length) selectNode(li);
        });
        $('.node-content').off('dblclick.unified').on('dblclick.unified', function(e) {
            e.stopPropagation();
            const li = $(this).closest('li');
            if (li.length && li.hasClass('has-children')) toggleNode(li);
        });
    } catch (_) {}
}

function toggleNode(li) {
    const nodeId = li.data('id');
    const sectionType = li.data('type');
    const childrenContainer = li.find('> .children-container');
    const expandIcon = li.find('> .node-content .expand-icon');

    if (li.hasClass('collapsed')) {
        li.removeClass('collapsed').addClass('expanded');
        expandIcon.addClass('expanded');
        childrenContainer.slideDown(200);
        if (childrenContainer.children('.tree-node').length === 0) {
            loadTreeNodes(nodeId, childrenContainer, sectionType);
        }
        setTimeout(function() {
            childrenContainer.find('> li:not(.selected):not(.tree-node-highlighted):not(.tree-node-match) > .node-content').css({
                'background-color': 'white',
                'color': 'var(--color-text-default, rgb(16, 16, 16))'
            });
        }, 250);
    } else {
        li.removeClass('expanded').addClass('collapsed');
        expandIcon.removeClass('expanded');
        childrenContainer.slideUp(200);
    }
}

function selectNode(li, updateUrl) {
    if (updateUrl === undefined) updateUrl = true;
    $('.tree-node.selected').removeClass('selected');
    li.addClass('selected');
    const nodeId = li.data('id');
    const sectionType = li.data('type');
    loadDetails(nodeId, sectionType, updateUrl);
    ensureNodeVisible(li);
}

function ensureNodeVisible(li) {
    li.parents('li.tree-node').each(function() {
        const parent = $(this);
        if (parent.hasClass('collapsed')) toggleNode(parent);
    });
}

// ---------- Detail loading ----------
function loadDetails(iri, sectionType, updateUrl) {
    if (updateUrl === undefined) updateUrl = true;
    const detailsContainer = document.getElementById('class-details');
    if (!detailsContainer) return;

    if (updateUrl) {
        const url = new URL(window.location);
        url.searchParams.set('node', iri);
        url.searchParams.set('type', sectionType);
        history.pushState({ nodeId: iri, type: sectionType }, '', url);
    }

    detailsContainer.innerHTML = '<div class="flex justify-center items-center h-64"><div class="spinner-border animate-spin inline-block w-8 h-8 border-4 rounded-full text-blue-600" role="status"><span class="sr-only">Loading...</span></div></div>';

    const cfg = SECTIONS[sectionType];
    let nodeId = iri;
    if (iri.startsWith('http')) {
        const parts = iri.split('/').filter(p => p.trim().length > 0);
        if (parts.length > 0) nodeId = parts[parts.length - 1];
    }

    // Fetch the server-rendered HTML fragment
    fetch(cfg.detailsEndpoint + encodeURIComponent(nodeId))
        .then(response => {
            if (!response.ok) throw new Error('Could not fetch rendered template');
            return response.text();
        })
        .then(html => {
            detailsContainer.innerHTML = html;
        })
        .catch(() => {
            // Fallback: fetch JSON and render client-side
            fetch(cfg.nodeDataEndpoint + encodeURIComponent(nodeId))
                .then(r => { if (!r.ok) throw new Error('Network error'); return r.json(); })
                .then(data => {
                    detailsContainer.innerHTML = '<div class="p-4"><h3 class="text-2xl font-semibold mb-2 text-[--color-primary]">' + (data.label || 'Unknown') + '</h3><p class="text-gray-700">' + (data.definition || '') + '</p></div>';
                })
                .catch(() => {
                    detailsContainer.innerHTML = '<div class="p-4 text-red-500"><h3 class="text-xl font-medium mb-2">Error loading details</h3><p>Unable to load details. Please try again or select a different item.</p></div>';
                });
        });
}

// Alias for cross-type navigation from detail panel links
function loadClassDetails(iri, updateUrl) {
    // Determine which section this IRI belongs to by checking DOM first
    const existingNode = document.querySelector('.tree-node[data-id="' + iri + '"]');
    if (existingNode) {
        loadDetails(iri, existingNode.dataset.type, updateUrl);
    } else {
        // Default to class type (matches backward-compat from taxonomy tree)
        loadDetails(iri, 'class', updateUrl);
    }
}

// ---------- selectNodeByIri: cross-type navigation ----------
function selectNodeByIri(iri) {
    // First check if node already exists in DOM
    const existingNode = document.querySelector('.tree-node[data-id="' + iri + '"]');
    if (existingNode) {
        const li = $(existingNode);
        selectNode(li, true);
        existingNode.scrollIntoView({ behavior: 'smooth', block: 'center' });
        return;
    }

    // Node not in DOM — try both path APIs in parallel to find it
    const classPath = fetch(SECTIONS.class.pathEndpoint + encodeURIComponent(extractIdFromIri(iri)))
        .then(r => r.ok ? r.json() : null).catch(() => null);
    const propertyPath = fetch(SECTIONS.property.pathEndpoint + encodeURIComponent(extractIdFromIri(iri)))
        .then(r => r.ok ? r.json() : null).catch(() => null);

    Promise.all([classPath, propertyPath]).then(([classResult, propertyResult]) => {
        let sectionType = null;
        let pathData = null;
        if (classResult && classResult.path && classResult.path.length > 0) {
            sectionType = 'class';
            pathData = classResult;
        } else if (propertyResult && propertyResult.path && propertyResult.path.length > 0) {
            sectionType = 'property';
            pathData = propertyResult;
        }

        if (sectionType && pathData) {
            // Ensure the section is visible
            const rootList = document.getElementById(SECTIONS[sectionType].rootListId);
            if (rootList && rootList.style.display === 'none') {
                rootList.style.display = '';
                const header = document.querySelector('.section-header[data-section="' + sectionType + '"]');
                if (header) header.querySelector('.section-chevron').classList.remove('collapsed');
            }
            loadAndSelectNode(iri, sectionType, true);
        } else {
            // Last resort: just load details
            loadDetails(iri, 'class', true);
        }
    });
}
window.selectNodeByIri = selectNodeByIri;

// ---------- Load and select node (expand path) ----------
function loadAndSelectNode(nodeId, sectionType, updateUrl) {
    if (updateUrl === undefined) updateUrl = true;
    if (isLoadingTree) {
        setTimeout(() => loadAndSelectNode(nodeId, sectionType, updateUrl), 500);
        return;
    }

    const cfg = SECTIONS[sectionType];
    const rootList = $('#' + cfg.rootListId);

    // Ensure root nodes are loaded
    if (rootList.children('.tree-node').length === 0) {
        loadTreeNodes('#', rootList, sectionType);
    }

    // Check if node already in DOM
    const node = $('.tree-node[data-id="' + nodeId + '"]');
    if (node.length > 0) {
        selectNode(node, updateUrl);
        node[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
        return;
    }

    // Need to find and expand path
    isLoadingTree = true;
    const detailsContainer = document.getElementById('class-details');
    if (detailsContainer) {
        detailsContainer.innerHTML = '<div class="flex justify-center items-center h-64"><div class="flex flex-col items-center"><div class="spinner-border animate-spin inline-block w-8 h-8 border-4 rounded-full text-blue-600 mb-4" role="status"><span class="sr-only">Loading...</span></div><p class="text-gray-600">Finding and loading node...</p></div></div>';
    }

    findNodePath(nodeId, sectionType)
        .then(path => loadNodePath(path, sectionType))
        .then(() => {
            const loadedNode = $('.tree-node[data-id="' + nodeId + '"]');
            if (loadedNode.length > 0) {
                $('.tree-node.selected').removeClass('selected');
                loadedNode.addClass('selected');
                loadedNode[0].scrollIntoView({ block: 'center', behavior: 'smooth' });
                selectNode(loadedNode, updateUrl);
            } else {
                loadDetails(nodeId, sectionType, updateUrl);
            }
        })
        .catch(() => {
            const finalNode = $('.tree-node[data-id="' + nodeId + '"]');
            if (finalNode.length > 0) {
                $('.tree-node.selected').removeClass('selected');
                finalNode.addClass('selected');
                finalNode[0].scrollIntoView({ block: 'center', behavior: 'smooth' });
                selectNode(finalNode, updateUrl);
            } else {
                loadDetails(nodeId, sectionType, updateUrl);
            }
        })
        .finally(() => {
            setTimeout(() => {
                const finalNode = $('.tree-node[data-id="' + nodeId + '"]');
                if (finalNode.length > 0 && !finalNode.hasClass('selected')) {
                    $('.tree-node.selected').removeClass('selected');
                    finalNode.addClass('selected');
                }
                isLoadingTree = false;
            }, 200);
        });
}

async function findNodePath(nodeId, sectionType) {
    try {
        const data = await getNodeData(nodeId, sectionType);
        const path = [];
        if (data.parents && data.parents.length > 0) {
            let currentNode = data.parents[0].iri;
            const parentChain = [currentNode];
            try {
                for (let i = 0; i < 5; i++) {
                    const parentData = await getNodeData(currentNode, sectionType);
                    if (!parentData.parents || parentData.parents.length === 0) break;
                    currentNode = parentData.parents[0].iri;
                    parentChain.unshift(currentNode);
                }
            } catch (_) {}
            path.push(...parentChain);
        }
        if (path.length === 0 || path[path.length - 1] !== nodeId) {
            path.push(nodeId);
        }
        return path;
    } catch (_) {
        return [nodeId];
    }
}

async function loadNodePath(path, sectionType) {
    if (!path || path.length === 0) return;
    const cfg = SECTIONS[sectionType];
    const rootList = $('#' + cfg.rootListId);

    if (rootList.children('.tree-node').length === 0) {
        await new Promise(resolve => {
            loadTreeNodes('#', rootList, sectionType);
            const check = setInterval(() => {
                if (!rootList.find('.loading-indicator').length) { clearInterval(check); resolve(); }
            }, 100);
        });
    }

    let currentContainer = rootList;
    for (let i = 0; i < path.length; i++) {
        const nodeId = path[i];
        const isLast = (i === path.length - 1);
        let node = currentContainer.children('.tree-node[data-id="' + nodeId + '"]');
        if (node.length === 0) node = $('.tree-node[data-id="' + nodeId + '"]');

        if (node.length > 0) {
            if (!isLast && node.hasClass('collapsed')) toggleNode(node);
            if (!isLast) {
                currentContainer = node.find('> .children-container');
                if (currentContainer.length === 0) {
                    node.append('<ul class="children-container" style="display:block;"></ul>');
                    currentContainer = node.find('> .children-container');
                }
            }
        } else {
            const parentNodeId = i > 0 ? path[i - 1] : '#';
            await new Promise(resolve => {
                if (currentContainer.children('.tree-node').length > 0) { resolve(); return; }
                loadTreeNodes(parentNodeId, currentContainer, sectionType);
                const check = setInterval(() => {
                    if (!currentContainer.find('> .loading-indicator').length) {
                        clearInterval(check);
                        node = currentContainer.children('.tree-node[data-id="' + nodeId + '"]');
                        if (node.length === 0) node = $('.tree-node[data-id="' + nodeId + '"]');
                        if (node.length > 0) {
                            if (!isLast && node.hasClass('collapsed')) toggleNode(node);
                            if (!isLast) {
                                currentContainer = node.find('> .children-container');
                                if (currentContainer.length === 0) {
                                    node.append('<ul class="children-container" style="display:block;"></ul>');
                                    currentContainer = node.find('> .children-container');
                                }
                            }
                        }
                        resolve();
                    }
                }, 100);
            });
        }
    }

    const targetNode = $('.tree-node[data-id="' + path[path.length - 1] + '"]');
    if (targetNode.length > 0) targetNode[0].scrollIntoView({ block: 'center', behavior: 'smooth' });
}

// ---------- Tree styles ----------
function applyTreeStyles() {
    const style = document.createElement('style');
    style.textContent = `
        .section-tree-root, .children-container { list-style-type: none; padding-left: 0; }
        .children-container { padding-left: 14px; border-left: 1px solid rgba(209, 213, 219, 0.7); margin-left: 6px; }
        .children-container .tree-node:not(.selected):not(.tree-node-highlighted) > .node-content { background-color: white; color: var(--color-text-default, rgb(16, 16, 16)); }
        .tree-node { margin: 1px 0; position: relative; }
        .node-content { display: flex; align-items: center; padding: 2px 6px; border-radius: 3px; cursor: pointer; word-break: break-word; white-space: normal; border-bottom: 1px solid rgba(229, 231, 235, 0.3); line-height: 1.2; }
        .node-content:hover { background-color: rgba(59, 130, 246, 0.1); }
        .tree-node.selected > .node-content { background-color: var(--color-primary, rgb(24, 70, 120)) !important; color: white !important; font-weight: 600; }
        .node-label { flex-grow: 1; }
        @media (max-width: 768px) {
            .tree-explorer-container { flex-direction: column; }
            #tree-container, #detail-container { width: 100%; max-height: none; }
            #explore-tree { max-height: 400px; }
        }
        #explore-tree::-webkit-scrollbar { width: 8px; }
        #explore-tree::-webkit-scrollbar-track { background: #f1f1f1; border-radius: 4px; }
        #explore-tree::-webkit-scrollbar-thumb { background: #c1c1c1; border-radius: 4px; }
        #explore-tree::-webkit-scrollbar-thumb:hover { background: #a8a8a8; }
        .node-label span.bg-blue-100 { background-color: rgba(229, 231, 235, 0.7); padding: 0 2px; border-radius: 2px; font-weight: bold; color: var(--color-primary, rgb(24, 70, 120)); }
    `;
    document.head.appendChild(style);
}

function applyArrowStyles() {
    if (document.getElementById('unified-tree-arrow-styles')) return;
    const s = document.createElement('style');
    s.id = 'unified-tree-arrow-styles';
    s.textContent = `
        .expand-icon { cursor: pointer; width: 20px; height: 20px; display: inline-flex !important; align-items: center !important; justify-content: center; flex-shrink: 0; border-radius: 3px; transition: transform 0.15s ease; color: #6b7280; margin-right: 4px; }
        .expand-icon:hover { background-color: rgba(107, 114, 128, 0.12); color: #374151; }
        .expand-icon.expanded { transform: rotate(90deg); }
        .expand-icon svg { display: block; }
        .leaf-indicator { width: 20px; height: 20px; display: inline-flex !important; align-items: center !important; justify-content: center; flex-shrink: 0; margin-right: 4px; }
        .leaf-dot { width: 6px; height: 6px; border-radius: 50%; background-color: #d1d5db; }
        .tree-node.selected > .node-content .leaf-dot { background-color: rgba(255, 255, 255, 0.6); }
        .tree-node.selected > .node-content .expand-icon { color: white; }
    `;
    document.head.appendChild(s);
}

// ---------- Expand / Collapse all ----------
function expandAllNodes() {
    $('.tree-node.collapsed').each(function() { toggleNode($(this)); });
}

function collapseAllNodes() {
    const selectedNodeId = getCurrentSelectedNodeId();
    let shouldResetUrl = false;
    if (selectedNodeId) {
        const selectedNode = $('.tree-node[data-id="' + selectedNodeId + '"]');
        if (selectedNode.length > 0 && selectedNode.parents('.tree-node').length > 0) shouldResetUrl = true;
    }
    $('.tree-node.expanded').each(function() { toggleNode($(this)); });
    if (shouldResetUrl) resetUrlParameters();
}

function getCurrentSelectedNodeId() {
    const url = new URL(window.location);
    const nodeParam = url.searchParams.get('node');
    if (nodeParam) return nodeParam;
    const selectedNode = $('.tree-node.selected');
    return selectedNode.length > 0 ? selectedNode.data('id') : null;
}

function resetUrlParameters() {
    const url = new URL(window.location);
    if (url.searchParams.has('node')) {
        url.searchParams.delete('node');
        url.searchParams.delete('type');
        window.history.replaceState({}, '', url);
    }
}

// ---------- Tree controls ----------
function setupTreeControls() {
    const expandBtn = document.getElementById('expand-all-tree');
    if (expandBtn) expandBtn.addEventListener('click', expandAllNodes);
    const collapseBtn = document.getElementById('collapse-all-tree');
    if (collapseBtn) collapseBtn.addEventListener('click', collapseAllNodes);
}

// ---------- Keyboard navigation ----------
function setupKeyboardNavigation() {
    document.addEventListener('keydown', function(event) {
        if (document.activeElement.tagName === 'INPUT' || document.activeElement.tagName === 'TEXTAREA') return;
        const selectedNode = document.querySelector('.tree-node.selected');
        if (!selectedNode) return;

        if (event.key === ' ') {
            event.preventDefault();
            if (selectedNode.classList.contains('has-children')) {
                const icon = selectedNode.querySelector('.expand-icon');
                if (icon) icon.click();
            }
        } else if (event.key === 'ArrowRight') {
            event.preventDefault();
            if (selectedNode.classList.contains('has-children') && selectedNode.classList.contains('collapsed')) {
                const icon = selectedNode.querySelector('.expand-icon');
                if (icon) icon.click();
            }
        } else if (event.key === 'ArrowLeft') {
            event.preventDefault();
            if (selectedNode.classList.contains('has-children') && selectedNode.classList.contains('expanded')) {
                const icon = selectedNode.querySelector('.expand-icon');
                if (icon) icon.click();
            }
        } else if (event.key === 'ArrowDown') {
            event.preventDefault();
            const visible = Array.from(document.querySelectorAll('.tree-node')).filter(n => window.getComputedStyle(n).display !== 'none');
            const idx = visible.indexOf(selectedNode);
            if (idx < visible.length - 1) {
                const nc = visible[idx + 1].querySelector('.node-content');
                if (nc) nc.click();
            }
        } else if (event.key === 'ArrowUp') {
            event.preventDefault();
            const visible = Array.from(document.querySelectorAll('.tree-node')).filter(n => window.getComputedStyle(n).display !== 'none');
            const idx = visible.indexOf(selectedNode);
            if (idx > 0) {
                const nc = visible[idx - 1].querySelector('.node-content');
                if (nc) nc.click();
            }
        }
    });
}

// ---------- History navigation ----------
function setupHistoryNavigation() {
    // Handle initial URL params
    const urlParams = new URLSearchParams(window.location.search);
    const nodeId = urlParams.get('node');
    const nodeType = urlParams.get('type') || 'class';

    if (nodeId) {
        // Ensure the right section is visible
        const cfg = SECTIONS[nodeType];
        if (cfg) {
            const rootList = document.getElementById(cfg.rootListId);
            if (rootList && rootList.style.display === 'none') {
                rootList.style.display = '';
                const header = document.querySelector('.section-header[data-section="' + nodeType + '"]');
                if (header) header.querySelector('.section-chevron').classList.remove('collapsed');
            }
        }
        loadAndSelectNode(nodeId, nodeType, false);
    }

    // Listen for back/forward
    window.addEventListener('popstate', function(event) {
        if (event.state && event.state.nodeId) {
            const type = event.state.type || 'class';
            loadAndSelectNode(event.state.nodeId, type, false);
        } else {
            const params = new URLSearchParams(window.location.search);
            const nid = params.get('node');
            const ntype = params.get('type') || 'class';
            if (nid) {
                loadAndSelectNode(nid, ntype, false);
            } else {
                $('.tree-node.selected').removeClass('selected');
                const dc = document.getElementById('class-details');
                if (dc) {
                    dc.innerHTML = '<div class="flex items-center justify-center h-full text-gray-500"><div class="text-center"><svg class="w-16 h-16 mx-auto text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" /></svg><h3 class="mt-2 text-xl font-medium">Select an item</h3><p class="mt-1">Choose a class or property from the tree to view its details</p></div></div>';
                }
            }
        }
    });
}

// ---------- Search ----------
function setupSearch() {
    const input = document.getElementById('explore-search-input');
    const button = document.getElementById('explore-search-button');
    if (!input || !button) return;

    function doSearch() {
        const query = input.value;
        if (query && query.length >= 2) {
            resetTreeSearch();
            searchUnified(query);
        } else if (query.length > 0 && query.length < 2) {
            alert('Please enter at least 2 characters for search');
        } else {
            resetTreeSearch();
        }
    }

    button.addEventListener('click', doSearch);
    input.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') { e.preventDefault(); doSearch(); }
        if (e.key === 'Escape') { input.value = ''; resetTreeSearch(); }
    });

    // Wire up the inline clear (X) button
    const clearBtn = document.getElementById('explore-search-clear');
    if (clearBtn) {
        clearBtn.addEventListener('click', function() {
            resetTreeSearch();
            input.focus();
        });
    }
}

function searchUnified(query) {
    if (!query || query.length < 2) return;

    // Show loading
    const treeEl = document.getElementById('explore-tree');
    const classSec = document.getElementById('class-section');
    const propSec = document.getElementById('property-section');

    // Fire both searches in parallel
    const classSearch = fetch(SECTIONS.class.searchEndpoint + '?query=' + encodeURIComponent(query))
        .then(r => r.json()).catch(() => ({ matches: [], tree: {} }));
    const propSearch = fetch(SECTIONS.property.searchEndpoint + '?query=' + encodeURIComponent(query))
        .then(r => r.json()).catch(() => ({ matches: [], tree: {} }));

    Promise.all([classSearch, propSearch]).then(([classData, propData]) => {
        const classMatches = classData.matches || [];
        const propMatches = propData.matches || [];
        const totalMatches = classMatches.length + propMatches.length;

        // Add filter controls
        addFilterModeControls(totalMatches, query, classMatches.length, propMatches.length);

        // Render class section
        const classRoot = document.getElementById(SECTIONS.class.rootListId);
        classRoot.innerHTML = '';
        if (classMatches.length > 0 && classData.tree) {
            renderFilteredTree(classData.tree, classRoot, 'class', query);
            classSec.style.display = '';
            // Ensure section is expanded
            const classChevron = classSec.querySelector('.section-chevron');
            if (classChevron) classChevron.classList.remove('collapsed');
            classRoot.style.display = '';
        } else {
            // Collapse empty class section
            classRoot.style.display = 'none';
            const classChevron = classSec.querySelector('.section-chevron');
            if (classChevron) classChevron.classList.add('collapsed');
        }

        // Render property section
        const propRoot = document.getElementById(SECTIONS.property.rootListId);
        propRoot.innerHTML = '';
        if (propMatches.length > 0 && propData.tree) {
            renderFilteredTree(propData.tree, propRoot, 'property', query);
            propSec.style.display = '';
            const propChevron = propSec.querySelector('.section-chevron');
            if (propChevron) propChevron.classList.remove('collapsed');
            propRoot.style.display = '';
        } else {
            propRoot.style.display = 'none';
            const propChevron = propSec.querySelector('.section-chevron');
            if (propChevron) propChevron.classList.add('collapsed');
        }

        // Update count badges
        document.getElementById('class-count').textContent = classMatches.length || '';
        document.getElementById('property-count').textContent = propMatches.length || '';

        setupNodeClickHandlers();

        // Highlight matches
        document.querySelectorAll('.tree-node-match').forEach(node => {
            node.classList.add('tree-node-highlighted');
            const label = node.querySelector('.node-label');
            if (label) label.innerHTML = highlightText(label.textContent, query);
        });

        // Select first match
        const firstMatch = document.querySelector('.tree-node-highlighted');
        if (firstMatch) {
            const li = $(firstMatch);
            const sectionType = firstMatch.dataset.type;
            loadDetails(firstMatch.dataset.id, sectionType, true);
            li.addClass('selected');
            firstMatch.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }

        if (totalMatches === 0) {
            // No results — restore trees
            clearFilterMode();
        }
    });
}

function renderFilteredTree(treeData, container, sectionType, query) {
    if (!treeData || !treeData.root_nodes) return;
    treeData.root_nodes.forEach(nodeId => {
        renderFilteredNode(nodeId, treeData, container, sectionType, true);
    });
}

function renderFilteredNode(nodeId, treeData, container, sectionType, isExpanded) {
    const node = treeData.nodes[nodeId];
    if (!node) return;
    const hasChildren = node.children && node.children.length > 0;
    const nodeClass = hasChildren ? (isExpanded ? 'has-children expanded' : 'has-children collapsed') : '';
    const isMatch = node.is_match ? 'tree-node-match' : '';
    const expandIcon = hasChildren
        ? '<span class="expand-icon' + (isExpanded ? ' expanded' : '') + '"><svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 3 11 8 6 13"></polyline></svg></span>'
        : '<span class="leaf-indicator"><span class="leaf-dot"></span></span>';

    const li = document.createElement('li');
    li.className = 'tree-node ' + nodeClass + ' ' + isMatch;
    li.dataset.id = node.id;
    li.dataset.type = sectionType;
    li.innerHTML = '<div class="node-content">' + expandIcon + '<span class="node-label">' + node.label + '</span></div>' +
        (hasChildren ? '<ul class="children-container" style="display:' + (isExpanded ? 'block' : 'none') + ';"></ul>' : '');
    container.appendChild(li);

    if (hasChildren && isExpanded) {
        const childrenContainer = li.querySelector('.children-container');
        node.children.forEach(childId => {
            const childNode = treeData.nodes[childId];
            const shouldExpand = childNode && (childNode.is_match || hasMatchDescendant(childId, treeData));
            renderFilteredNode(childId, treeData, childrenContainer, sectionType, shouldExpand);
        });
    }
}

function hasMatchDescendant(nodeId, treeData) {
    const node = treeData.nodes[nodeId];
    if (!node) return false;
    if (node.is_match) return true;
    if (node.children) {
        for (const childId of node.children) {
            if (hasMatchDescendant(childId, treeData)) return true;
        }
    }
    return false;
}

function addFilterModeControls(totalCount, query, classCount, propCount) {
    // Show the inline clear (X) button inside the search input
    const clearBtn = document.getElementById('explore-search-clear');
    if (clearBtn) clearBtn.style.display = 'flex';

    // Build match-count text
    let detail = totalCount + ' match' + (totalCount !== 1 ? 'es' : '');
    if (classCount > 0 && propCount > 0) {
        detail += ' (' + classCount + ' class' + (classCount !== 1 ? 'es' : '') + ', ' + propCount + ' propert' + (propCount !== 1 ? 'ies' : 'y') + ')';
    } else if (classCount > 0) {
        detail += ' in classes';
    } else if (propCount > 0) {
        detail += ' in properties';
    }

    // Show the match-count line below the search input
    const countEl = document.getElementById('search-match-count');
    if (countEl) {
        countEl.textContent = detail;
        countEl.style.display = '';
    }

    // Mark filter as active (used by resetTreeSearch to detect filter state)
    document.getElementById('explore-search-input').dataset.filtering = 'true';

    addFilterModeStyles();
}

function clearFilterMode() {
    // Hide inline clear button and match count
    const clearBtn = document.getElementById('explore-search-clear');
    if (clearBtn) clearBtn.style.display = 'none';
    const countEl = document.getElementById('search-match-count');
    if (countEl) { countEl.textContent = ''; countEl.style.display = 'none'; }

    // Clear the search input text and filtering flag
    const input = document.getElementById('explore-search-input');
    if (input) { input.value = ''; delete input.dataset.filtering; }

    // Restore both sections
    ['class', 'property'].forEach(sectionType => {
        const cfg = SECTIONS[sectionType];
        const rootList = document.getElementById(cfg.rootListId);
        rootList.innerHTML = '';
        rootList.style.display = '';
        const section = document.getElementById(cfg.sectionId);
        section.style.display = '';
        const chevron = section.querySelector('.section-chevron');
        if (chevron) chevron.classList.remove('collapsed');
        loadTreeNodes('#', $(rootList), sectionType);
    });

    // Reset detail panel
    const dc = document.getElementById('class-details');
    if (dc) {
        dc.innerHTML = '<div class="flex items-center justify-center h-full text-gray-500"><div class="text-center"><svg class="w-16 h-16 mx-auto text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" /></svg><h3 class="mt-2 text-xl font-medium">Select an item</h3><p class="mt-1">Choose a class or property from the tree to view its details</p></div></div>';
    }
}

function resetTreeSearch() {
    const input = document.getElementById('explore-search-input');
    const isFilterMode = input && input.dataset.filtering === 'true';
    if (isFilterMode) {
        clearFilterMode();
    } else {
        document.querySelectorAll('.tree-node-highlighted').forEach(node => {
            node.classList.remove('tree-node-highlighted');
            const label = node.querySelector('.node-label');
            if (label) label.textContent = label.textContent;
        });
    }
}

function addFilterModeStyles() {
    if (document.getElementById('filter-mode-styles')) return;
    const style = document.createElement('style');
    style.id = 'filter-mode-styles';
    style.textContent = '.tree-node-highlighted>.node-content,.tree-node-match>.node-content{background-color:var(--color-primary,rgb(24,70,120))!important;color:white!important;border-left-color:rgba(255,255,255,0.8)!important}.tree-node-match>.node-content{font-weight:500}';
    document.head.appendChild(style);
}

function highlightText(text, query) {
    const regex = new RegExp('(' + escapeRegEx(query) + ')', 'gi');
    return text.replace(regex, '<span class="bg-blue-100">$1</span>');
}

function escapeRegEx(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// ---------- Main initialization ----------
function initializeUnifiedTree() {
    if (typeof $ === 'undefined') {
        const treeEl = document.getElementById('explore-tree');
        if (treeEl) treeEl.innerHTML = '<div class="p-4 text-yellow-800 bg-yellow-100 rounded"><h3 class="font-medium">Unable to load tree</h3><p>JavaScript libraries needed for the tree are not available.</p></div>';
        return;
    }

    applyTreeStyles();
    applyArrowStyles();
    setupSectionHeaders();

    // Load both sections eagerly
    loadTreeNodes('#', $('#class-tree-root'), 'class');
    loadTreeNodes('#', $('#property-tree-root'), 'property');

    setupNodeClickHandlers();
    setupTreeControls();
    setupKeyboardNavigation();
    setupHistoryNavigation();
    setupSearch();
}
