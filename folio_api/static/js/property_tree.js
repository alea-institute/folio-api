/**
 * Property Tree JavaScript - Handles the tree-based visualization of FOLIO object properties
 * Adapted from taxonomy_tree.js for property hierarchy navigation
 */

// Initialize a cache for node data to prevent redundant requests
const nodeDataCache = new Map();
const MAX_CACHE_SIZE = 100;
let isLoadingTree = false;
const REQUEST_DELAY = 100;

async function getNodeData(nodeId) {
    if (nodeDataCache.has(nodeId)) {
        return nodeDataCache.get(nodeId);
    }
    const extractedId = extractIdFromIri(nodeId);
    try {
        const response = await fetch(`/properties/tree/node/${encodeURIComponent(extractedId)}`);
        if (!response.ok) throw new Error(`Failed to fetch node data: ${response.status}`);
        const data = await response.json();
        nodeDataCache.set(nodeId, data);
        nodeDataCache.set(extractedId, data);
        if (nodeDataCache.size > MAX_CACHE_SIZE) {
            const keys = [...nodeDataCache.keys()];
            const deleteCount = Math.ceil(MAX_CACHE_SIZE * 0.2);
            for (let i = 0; i < deleteCount; i++) {
                nodeDataCache.delete(keys[i]);
            }
        }
        return data;
    } catch (error) {
        throw error;
    }
}

document.addEventListener('DOMContentLoaded', function() {
    if (typeof $ === 'undefined') {
        showFallbackMessage('JavaScript libraries needed for the property tree are not available');
        return;
    }
    const urlParams = new URLSearchParams(window.location.search);
    const nodeId = urlParams.get('node');
    if (nodeId) {
        setupTreeControls();
        setupKeyboardNavigation();
        loadAndSelectNode(nodeId, false);
    } else {
        initializeTree();
        setupTreeControls();
        setupKeyboardNavigation();
    }
    setupHistoryNavigation();
});

function initializeTree() {
    const treeContainer = $('#taxonomy-tree');
    treeContainer.html('<ul class="taxonomy-root-list"></ul>');
    loadTreeNodes('#', $('.taxonomy-root-list'));
    applyTreeStyles();
    applyArrowStyles();
}

function loadTreeNodes(nodeId, container) {
    const existingNodes = container.children('.tree-node');
    if (existingNodes.length > 0) return;
    container.append('<li class="loading-indicator"><span>Loading...</span></li>');
    fetch('/properties/tree/data?node_id=' + encodeURIComponent(nodeId))
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok');
            return response.json();
        })
        .then(data => {
            container.find('.loading-indicator').remove();
            container.children('.tree-node').remove();
            data.forEach(node => {
                const existingNode = container.children(`.tree-node[data-id="${node.id}"]`);
                if (existingNode.length === 0) {
                    renderTreeNode(node, container);
                }
            });
            setupNodeClickHandlers();
        })
        .catch(() => {
            container.find('.loading-indicator').html('<span class="text-red-500">Error loading. Try again.</span>');
        });
}

function renderTreeNode(node, container) {
    const hasChildren = node.children;
    const nodeClass = hasChildren ? 'has-children collapsed' : '';
    const expandIcon = hasChildren ?
        '<span class="expand-icon"><svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 3 11 8 6 13"></polyline></svg></span>' :
        '<span class="leaf-indicator"><span class="leaf-dot"></span></span>';
    const li = $(`
        <li class="tree-node ${nodeClass}" data-id="${node.id}">
            <div class="node-content">
                ${expandIcon}
                <span class="node-label">${node.text}</span>
            </div>
            ${hasChildren ? '<ul class="children-container" style="display:none;"></ul>' : ''}
        </li>
    `);
    container.append(li);
}

function setupNodeClickHandlers() {
    try {
        $('.expand-icon').off('click').on('click', function(e) {
            e.stopPropagation();
            const li = $(this).closest('li');
            if (li.length) toggleNode(li);
        });
        $('.node-content').off('click').on('click', function() {
            const li = $(this).closest('li');
            if (li.length) selectNode(li);
        });
        $('.node-content').off('dblclick').on('dblclick', function(e) {
            e.stopPropagation();
            const li = $(this).closest('li');
            if (li.length && li.hasClass('has-children')) toggleNode(li);
        });
    } catch (_) {}
}

function toggleNode(li) {
    const nodeId = li.data('id');
    const childrenContainer = li.find('> .children-container');
    const expandIcon = li.find('> .node-content .expand-icon');
    if (li.hasClass('collapsed')) {
        li.removeClass('collapsed').addClass('expanded');
        expandIcon.addClass('expanded');
        childrenContainer.slideDown(200);
        if (childrenContainer.children('.tree-node').length === 0) {
            loadTreeNodes(nodeId, childrenContainer);
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

function selectNode(li, updateUrl = true) {
    $('.tree-node.selected').removeClass('selected');
    li.addClass('selected');
    const nodeId = li.data('id');
    loadClassDetails(nodeId, updateUrl);
    ensureNodeVisible(li);
}

function ensureNodeVisible(li) {
    const parents = li.parents('li.tree-node');
    parents.each(function() {
        const parent = $(this);
        if (parent.hasClass('collapsed')) toggleNode(parent);
    });
}

function applyTreeStyles() {
    const style = document.createElement('style');
    style.textContent = `
        .taxonomy-root-list, .children-container { list-style-type: none; padding-left: 0; }
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
            #taxonomy-tree { max-height: 400px; }
        }
        #taxonomy-tree::-webkit-scrollbar { width: 8px; }
        #taxonomy-tree::-webkit-scrollbar-track { background: #f1f1f1; border-radius: 4px; }
        #taxonomy-tree::-webkit-scrollbar-thumb { background: #c1c1c1; border-radius: 4px; }
        #taxonomy-tree::-webkit-scrollbar-thumb:hover { background: #a8a8a8; }
        .node-label span.bg-blue-100 { background-color: rgba(229, 231, 235, 0.7); padding: 0 2px; border-radius: 2px; font-weight: bold; color: var(--color-primary, rgb(24, 70, 120)); }
    `;
    document.head.appendChild(style);
}

function applyArrowStyles() {
    if (!document.getElementById('taxonomy-tree-arrow-styles')) {
        const arrowStyle = document.createElement('style');
        arrowStyle.id = 'taxonomy-tree-arrow-styles';
        arrowStyle.textContent = `
            .expand-icon { cursor: pointer; width: 20px; height: 20px; display: inline-flex !important; align-items: center !important; justify-content: center; flex-shrink: 0; border-radius: 3px; transition: transform 0.15s ease; color: #6b7280; margin-right: 4px; }
            .expand-icon:hover { background-color: rgba(107, 114, 128, 0.12); color: #374151; }
            .expand-icon.expanded { transform: rotate(90deg); }
            .expand-icon svg { display: block; }
            .leaf-indicator { width: 20px; height: 20px; display: inline-flex !important; align-items: center !important; justify-content: center; flex-shrink: 0; margin-right: 4px; }
            .leaf-dot { width: 6px; height: 6px; border-radius: 50%; background-color: #d1d5db; }
            .tree-node.selected > .node-content .leaf-dot { background-color: rgba(255, 255, 255, 0.6); }
            .tree-node.selected > .node-content .expand-icon { color: white; }
        `;
        document.head.appendChild(arrowStyle);
    }
}

function setupSearchHandlers() { return; }

function resetSearch() {
    const highlightedNodes = document.querySelectorAll('.node-label span.bg-yellow-200');
    highlightedNodes.forEach(node => {
        const parent = node.parentElement;
        parent.innerHTML = parent.textContent;
    });
    const hiddenNodes = document.querySelectorAll('.tree-node.search-hidden');
    hiddenNodes.forEach(node => {
        node.classList.remove('search-hidden');
        node.style.display = '';
    });
}

function searchTree(query) {
    if (!query || query.length < 2) { resetSearch(); return; }
    const totalNodes = $('.node-label').length;
    if (totalNodes === 0) return;
    const normalizedQuery = query.toLowerCase();
    let foundMatches = false;
    resetSearch();
    const matchingNodes = new Set();
    $('.node-label').each(function() {
        const nodeLabel = $(this);
        const label = nodeLabel.text();
        const li = nodeLabel.closest('li');
        if (label.toLowerCase().includes(normalizedQuery)) {
            foundMatches = true;
            matchingNodes.add(li[0]);
            const regex = new RegExp('(' + escapeRegExp(query) + ')', 'gi');
            nodeLabel.html(label.replace(regex, '<span class="bg-blue-100">$1</span>'));
            let parent = li.parents('li');
            while (parent.length) {
                matchingNodes.add(parent[0]);
                parent = parent.parents('li');
            }
        }
    });
    if (foundMatches) {
        $('.tree-node').each(function() {
            if (!matchingNodes.has(this)) {
                $(this).addClass('search-hidden');
                $(this).hide();
            }
        });
        matchingNodes.forEach(node => {
            const $node = $(node);
            if ($node.hasClass('collapsed')) toggleNode($node);
        });
    }
}

function escapeRegExp(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function setupTreeControls() {
    const expandAllBtn = document.getElementById('expand-all-btn');
    if (expandAllBtn) expandAllBtn.addEventListener('click', function() { expandAllNodes(); });
    const collapseAllBtn = document.getElementById('collapse-all-btn');
    if (collapseAllBtn) collapseAllBtn.addEventListener('click', function() { collapseAllNodes(); });
    const expandAllTreeBtn = document.getElementById('expand-all-tree');
    if (expandAllTreeBtn) expandAllTreeBtn.addEventListener('click', function() { expandAllNodes(); });
    const collapseAllTreeBtn = document.getElementById('collapse-all-tree');
    if (collapseAllTreeBtn) collapseAllTreeBtn.addEventListener('click', function() { collapseAllNodes(); });
}

function expandAllNodes() {
    const collapsedNodes = $('.tree-node.collapsed');
    collapsedNodes.each(function() { toggleNode($(this)); });
}

function collapseAllNodes() {
    const selectedNodeId = getCurrentSelectedNodeId();
    let shouldResetUrl = false;
    if (selectedNodeId) {
        const selectedNode = $(`.tree-node[data-id="${selectedNodeId}"]`);
        if (selectedNode.length > 0 && selectedNode.parents('.tree-node').length > 0) {
            shouldResetUrl = true;
        }
    }
    const expandedNodes = $('.tree-node.expanded');
    expandedNodes.each(function() { toggleNode($(this)); });
    if (shouldResetUrl) resetUrlParameters();
}

function getCurrentSelectedNodeId() {
    const url = new URL(window.location);
    const nodeParam = url.searchParams.get('node');
    if (nodeParam) return nodeParam;
    const selectedNode = $('.tree-node.selected');
    if (selectedNode.length > 0) return selectedNode.data('id');
    return null;
}

function resetUrlParameters() {
    const url = new URL(window.location);
    if (url.searchParams.has('node')) {
        url.searchParams.delete('node');
        window.history.replaceState({}, '', url);
    }
}

function setupHistoryNavigation() {
    window.addEventListener('popstate', function(event) {
        if (event.state && event.state.nodeId) {
            loadAndSelectNode(event.state.nodeId, false);
        } else {
            const urlParams = new URLSearchParams(window.location.search);
            const nodeId = urlParams.get('node');
            if (nodeId) {
                loadAndSelectNode(nodeId, false);
            } else {
                const selectedNode = $('.tree-node.selected');
                if (selectedNode.length > 0) selectedNode.removeClass('selected');
                const detailsContainer = document.getElementById('class-details');
                if (detailsContainer) {
                    detailsContainer.innerHTML = `
                        <div class="flex items-center justify-center h-full text-gray-500">
                            <div class="text-center">
                                <svg class="w-16 h-16 mx-auto text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                                </svg>
                                <h3 class="mt-2 text-xl font-medium">Select a property</h3>
                                <p class="mt-1">Choose a property from the tree to view its details</p>
                            </div>
                        </div>
                    `;
                }
            }
        }
    });
}

function setupKeyboardNavigation() {
    document.addEventListener('keydown', function(event) {
        if (document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
            const selectedNode = document.querySelector('.tree-node.selected');
            if (selectedNode) {
                if (event.key === ' ') {
                    event.preventDefault();
                    if (selectedNode.classList.contains('has-children')) {
                        const expandIcon = selectedNode.querySelector('.expand-icon');
                        if (expandIcon) expandIcon.click();
                    }
                } else if (event.key === 'ArrowRight') {
                    event.preventDefault();
                    if (selectedNode.classList.contains('has-children') && selectedNode.classList.contains('collapsed')) {
                        const expandIcon = selectedNode.querySelector('.expand-icon');
                        if (expandIcon) expandIcon.click();
                    }
                } else if (event.key === 'ArrowLeft') {
                    event.preventDefault();
                    if (selectedNode.classList.contains('has-children') && selectedNode.classList.contains('expanded')) {
                        const expandIcon = selectedNode.querySelector('.expand-icon');
                        if (expandIcon) expandIcon.click();
                    }
                } else if (event.key === 'ArrowDown') {
                    event.preventDefault();
                    const visibleNodes = Array.from(document.querySelectorAll('.tree-node')).filter(node => window.getComputedStyle(node).display !== 'none');
                    const currentIndex = visibleNodes.indexOf(selectedNode);
                    if (currentIndex < visibleNodes.length - 1) {
                        const nextNode = visibleNodes[currentIndex + 1];
                        const nodeContent = nextNode.querySelector('.node-content');
                        if (nodeContent) nodeContent.click();
                    }
                } else if (event.key === 'ArrowUp') {
                    event.preventDefault();
                    const visibleNodes = Array.from(document.querySelectorAll('.tree-node')).filter(node => window.getComputedStyle(node).display !== 'none');
                    const currentIndex = visibleNodes.indexOf(selectedNode);
                    if (currentIndex > 0) {
                        const prevNode = visibleNodes[currentIndex - 1];
                        const nodeContent = prevNode.querySelector('.node-content');
                        if (nodeContent) nodeContent.click();
                    }
                }
            }
        }
    });
}

function loadAndSelectNode(nodeId, updateUrl = true) {
    if (isLoadingTree) {
        setTimeout(() => loadAndSelectNode(nodeId, updateUrl), 500);
        return;
    }
    const treeContainer = $('#taxonomy-tree');
    const needsInitialization = treeContainer.find('.taxonomy-root-list').length === 0;
    if (needsInitialization) {
        treeContainer.html('<ul class="taxonomy-root-list"></ul>');
        applyTreeStyles();
        applyArrowStyles();
    }
    const node = $(`.tree-node[data-id="${nodeId}"]`);
    if (node.length > 0) {
        selectNode(node, updateUrl);
    } else {
        isLoadingTree = true;
        const detailsContainer = document.getElementById('class-details');
        if (detailsContainer) {
            detailsContainer.innerHTML = `
                <div class="flex justify-center items-center h-64">
                    <div class="flex flex-col items-center">
                        <div class="spinner-border animate-spin inline-block w-8 h-8 border-4 rounded-full text-blue-600 mb-4" role="status">
                            <span class="sr-only">Loading...</span>
                        </div>
                        <p class="text-gray-600">Finding and loading property...</p>
                    </div>
                </div>
            `;
        }
        findNodePath(nodeId)
            .then(path => loadNodePath(path))
            .then(() => {
                const loadedNode = $(`.tree-node[data-id="${nodeId}"]`);
                if (loadedNode.length > 0) {
                    $('.tree-node.selected').removeClass('selected');
                    loadedNode.addClass('selected');
                    loadedNode[0].scrollIntoView({ block: 'center', behavior: 'smooth' });
                    selectNode(loadedNode, updateUrl);
                } else {
                    loadClassDetails(nodeId, updateUrl);
                }
            })
            .catch(err => {
                const finalCheckNode = $(`.tree-node[data-id="${nodeId}"]`);
                if (finalCheckNode.length > 0) {
                    $('.tree-node.selected').removeClass('selected');
                    finalCheckNode.addClass('selected');
                    finalCheckNode[0].scrollIntoView({ block: 'center', behavior: 'smooth' });
                    selectNode(finalCheckNode, updateUrl);
                } else {
                    loadClassDetails(nodeId, updateUrl);
                }
            })
            .finally(() => {
                setTimeout(() => {
                    const finalNode = $(`.tree-node[data-id="${nodeId}"]`);
                    if (finalNode.length > 0 && !finalNode.hasClass('selected')) {
                        $('.tree-node.selected').removeClass('selected');
                        finalNode.addClass('selected');
                    }
                    isLoadingTree = false;
                }, 200);
            });
    }
}

function extractIdFromIri(iri) {
    if (!iri || !iri.startsWith('http')) return iri;
    const parts = iri.split('/').filter(p => p.trim().length > 0);
    if (parts.length > 0) return parts[parts.length - 1];
    return iri;
}

async function findNodePath(nodeId) {
    const extractedId = extractIdFromIri(nodeId);
    try {
        const data = await getNodeData(nodeId);
        const path = [];
        if (data.parents && data.parents.length > 0) {
            const topParent = await findTopLevelParent(data.parents[0].iri);
            const fullPath = await buildPathToNode(topParent, nodeId);
            if (fullPath && fullPath.length > 1) {
                path.push(...fullPath);
            } else {
                let currentNode = data.parents[0].iri;
                const parentChain = [currentNode];
                try {
                    for (let i = 0; i < 5; i++) {
                        const parentData = await getNodeData(currentNode);
                        if (!parentData.parents || parentData.parents.length === 0) break;
                        currentNode = parentData.parents[0].iri;
                        parentChain.unshift(currentNode);
                    }
                } catch (error) {}
                path.push(...parentChain);
            }
        }
        if (path.length === 0 || path[path.length - 1] !== nodeId) {
            path.push(nodeId);
        }
        return path;
    } catch (error) {
        return [nodeId];
    }
}

async function findTopLevelParent(nodeId) {
    try {
        const data = await getNodeData(nodeId);
        if (!data.parents || data.parents.length === 0 ||
            data.parents.some(p => p.iri === "http://www.w3.org/2002/07/owl#topObjectProperty")) {
            return nodeId;
        }
        return findTopLevelParent(data.parents[0].iri);
    } catch (error) {
        return nodeId;
    }
}

async function buildPathToNode(startId, targetId) {
    if (startId === targetId) return [startId];
    const extractedStartId = extractIdFromIri(startId);
    const extractedTargetId = extractIdFromIri(targetId);
    if (extractedStartId === extractedTargetId) return [startId];
    const visited = new Set();
    visited.add(startId);
    visited.add(extractedStartId);
    const queue = [[startId, [startId]]];
    const MAX_DEPTH = 3;
    try {
        while (queue.length > 0) {
            const [currentId, currentPath] = queue.shift();
            if (currentPath.length > MAX_DEPTH) return [startId];
            try {
                const data = await getNodeData(currentId);
                if (data.children && data.children.length > 0) {
                    const sortedChildren = [...data.children].sort((a, b) => (a.label || "").localeCompare(b.label || ""));
                    for (const child of sortedChildren) {
                        const childId = child.iri;
                        const extractedChildId = extractIdFromIri(childId);
                        if (visited.has(childId) || visited.has(extractedChildId)) continue;
                        visited.add(childId);
                        visited.add(extractedChildId);
                        if (childId === targetId || extractedChildId === extractedTargetId) {
                            return [...currentPath, childId];
                        }
                        if (currentPath.length < MAX_DEPTH) {
                            queue.push([childId, [...currentPath, childId]]);
                        }
                    }
                }
            } catch (error) { continue; }
        }
        return [startId];
    } catch (error) {
        return [startId];
    }
}

async function loadNodePath(path) {
    if (!path || path.length === 0) return;
    const rootList = $('.taxonomy-root-list');
    let needsRootLoading = rootList.children('.tree-node').length === 0;
    let container = rootList;
    if (needsRootLoading) {
        await new Promise(resolve => {
            loadTreeNodes('#', container);
            const checkLoaded = setInterval(() => {
                if (!container.find('.loading-indicator').length) {
                    clearInterval(checkLoaded);
                    resolve();
                }
            }, 100);
        });
    }
    let currentContainer = rootList;
    const startIndex = 0;
    for (let i = startIndex; i < path.length; i++) {
        const nodeId = path[i];
        const isLastNode = (i === path.length - 1);
        let node = currentContainer.children(`.tree-node[data-id="${nodeId}"]`);
        if (node.length === 0) node = $(`.tree-node[data-id="${nodeId}"]`);
        if (node.length > 0) {
            if (!isLastNode && node.hasClass('collapsed')) toggleNode(node);
            if (!isLastNode) {
                currentContainer = node.find('> .children-container');
                if (currentContainer.length === 0) {
                    node.append('<ul class="children-container" style="display:block;"></ul>');
                    currentContainer = node.find('> .children-container');
                }
            }
        } else {
            const parentNodeId = i > startIndex ? path[i - 1] : '#';
            await new Promise(resolve => {
                if (currentContainer.children('.tree-node').length > 0) { resolve(); return; }
                loadTreeNodes(parentNodeId, currentContainer);
                const checkLoaded = setInterval(() => {
                    if (!currentContainer.find('> .loading-indicator').length) {
                        clearInterval(checkLoaded);
                        node = currentContainer.children(`.tree-node[data-id="${nodeId}"]`);
                        if (node.length === 0) node = $(`.tree-node[data-id="${nodeId}"]`);
                        if (node.length > 0) {
                            if (!isLastNode && node.hasClass('collapsed')) toggleNode(node);
                            if (!isLastNode) {
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
    const targetNodeId = path[path.length - 1];
    const targetNode = $(`.tree-node[data-id="${targetNodeId}"]`);
    if (targetNode.length > 0) {
        targetNode[0].scrollIntoView({ block: 'center', behavior: 'smooth' });
    }
}

function loadClassDetails(iri, updateUrl = true) {
    const detailsContainer = document.getElementById('class-details');
    if (!detailsContainer) return;
    if (updateUrl) {
        const url = new URL(window.location);
        url.searchParams.set('node', iri);
        history.pushState({ nodeId: iri }, '', url);
    }
    detailsContainer.innerHTML = `
        <div class="flex justify-center items-center h-64">
            <div class="spinner-border animate-spin inline-block w-8 h-8 border-4 rounded-full text-blue-600" role="status">
                <span class="sr-only">Loading...</span>
            </div>
        </div>
    `;
    let nodeId = iri;
    if (iri.startsWith('http')) {
        const parts = iri.split('/').filter(p => p.trim().length > 0);
        if (parts.length > 0) nodeId = parts[parts.length - 1];
    }
    // Fetch the rendered HTML from the server
    fetch('/properties/property-details/' + encodeURIComponent(nodeId))
        .then(response => {
            if (!response.ok) throw new Error('Could not fetch rendered template');
            return response.text();
        })
        .then(html => {
            detailsContainer.innerHTML = html;
        })
        .catch(() => {
            // Fallback: try fetching JSON data and render client-side
            fetch('/properties/tree/node/' + encodeURIComponent(nodeId))
                .then(response => {
                    if (!response.ok) throw new Error('Network response was not ok');
                    return response.json();
                })
                .then(data => {
                    fallbackRenderPropertyDetails(data, detailsContainer);
                })
                .catch(() => {
                    detailsContainer.innerHTML = `
                        <div class="p-4 text-red-500">
                            <h3 class="text-xl font-medium mb-2">Error loading property details</h3>
                            <p>Unable to load details for this property. Please try again or select a different property.</p>
                        </div>
                    `;
                });
        });
}

function selectNodeByIri(iri) {
    loadAndSelectNode(iri);
}

function fallbackRenderPropertyDetails(data, container) {
    let parentsHtml = '';
    if (data.parents && data.parents.length > 0) {
        parentsHtml = `
            <section class="card animate-fade-in mb-6">
                <h4 class="text-lg font-medium text-[--color-primary] mb-3">Parent Properties</h4>
                <div class="max-h-[200px] overflow-y-auto pr-1">
                    <ul class="space-y-2">
                        ${data.parents.map(parent =>
                            `<li class="group p-1.5 -ml-1.5 rounded-md hover:bg-blue-50">
                                <div class="flex items-start">
                                    <svg class="w-4 h-4 mt-1 mr-2 text-blue-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 11l5-5m0 0l5 5m-5-5v12" />
                                    </svg>
                                    <div>
                                        <a href="#" class="font-medium text-blue-600 hover:text-blue-800 group-hover:underline" onclick="selectNodeByIri('${parent.iri}'); return false;">${parent.label}</a>
                                        <p class="text-sm text-gray-600 mt-0.5 line-clamp-2">${parent.definition}</p>
                                    </div>
                                </div>
                            </li>`
                        ).join('')}
                    </ul>
                </div>
            </section>
        `;
    }

    let childrenHtml = '';
    if (data.children && data.children.length > 0) {
        childrenHtml = `
            <section class="card animate-fade-in mb-6">
                <h4 class="text-lg font-medium text-[--color-primary] mb-3 flex items-center">
                    Child Properties
                    <span class="ml-2 px-1.5 py-0.5 text-xs font-semibold bg-blue-100 text-blue-800 rounded-full">${data.children.length}</span>
                </h4>
                <div class="max-h-[300px] overflow-y-auto pr-1">
                    <ul class="space-y-2">
                        ${data.children.map(child =>
                            `<li class="group p-1.5 -ml-1.5 rounded-md hover:bg-blue-50">
                                <div class="flex items-start">
                                    <svg class="w-4 h-4 mt-1 mr-2 text-green-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 13l-5 5m0 0l-5-5m5 5V6" />
                                    </svg>
                                    <div>
                                        <a href="#" class="font-medium text-blue-600 hover:text-blue-800 group-hover:underline" onclick="selectNodeByIri('${child.iri}'); return false;">${child.label}</a>
                                        <p class="text-sm text-gray-600 mt-0.5 line-clamp-2">${child.definition}</p>
                                    </div>
                                </div>
                            </li>`
                        ).join('')}
                    </ul>
                </div>
            </section>
        `;
    }

    let domainHtml = '';
    if (data.domain_classes && data.domain_classes.length > 0) {
        domainHtml = `
            <section class="card animate-fade-in mb-6">
                <h4 class="text-lg font-medium text-[--color-primary] mb-3">Domain Classes <span class="ml-2 px-1.5 py-0.5 text-xs font-semibold bg-teal-100 text-teal-800 rounded-full">${data.domain_classes.length}</span></h4>
                <div class="max-h-[200px] overflow-y-auto pr-1">
                    <ul class="space-y-1">
                        ${data.domain_classes.map(cls =>
                            `<li class="flex items-center"><span class="text-teal-500 mr-2">&bull;</span><a href="${cls.iri}/html" class="text-teal-700 hover:underline">${cls.label}</a></li>`
                        ).join('')}
                    </ul>
                </div>
            </section>
        `;
    }

    let rangeHtml = '';
    if (data.range_classes && data.range_classes.length > 0) {
        rangeHtml = `
            <section class="card animate-fade-in mb-6">
                <h4 class="text-lg font-medium text-[--color-primary] mb-3">Range Classes <span class="ml-2 px-1.5 py-0.5 text-xs font-semibold bg-orange-100 text-orange-800 rounded-full">${data.range_classes.length}</span></h4>
                <div class="max-h-[200px] overflow-y-auto pr-1">
                    <ul class="space-y-1">
                        ${data.range_classes.map(cls =>
                            `<li class="flex items-center"><span class="text-orange-500 mr-2">&bull;</span><a href="${cls.iri}/html" class="text-orange-700 hover:underline">${cls.label}</a></li>`
                        ).join('')}
                    </ul>
                </div>
            </section>
        `;
    }

    let inverseHtml = '';
    if (data.inverse) {
        inverseHtml = `
            <section class="card animate-fade-in mb-6">
                <h4 class="text-lg font-medium text-[--color-primary] mb-3">Inverse Property</h4>
                <div class="bg-purple-50 rounded-lg p-4">
                    <a href="#" class="font-medium text-purple-700 hover:underline" onclick="selectNodeByIri('${data.inverse.iri}'); return false;">${data.inverse.label}</a>
                </div>
            </section>
        `;
    }

    const examplesHtml = data.examples && data.examples.length > 0 ?
        `<section class="card animate-fade-in mb-6">
            <h4 class="text-lg font-medium text-[--color-primary] mb-3">Examples</h4>
            <div class="bg-green-50 border border-green-100 rounded-md p-2">
                <ul class="space-y-2.5">
                    ${data.examples.map(example => `<li class="flex items-start"><span class="text-green-500 mr-2">&bull;</span><span>${example}</span></li>`).join('')}
                </ul>
            </div>
        </section>` : '';

    container.innerHTML = `
        <section class="card animate-fade-in mb-6 border-t-4 border-[--color-primary]">
            <div class="flex items-center mb-2">
                <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800 mr-2">Property</span>
                <h3 class="text-2xl font-semibold text-[--color-primary]">${data.label}</h3>
            </div>
            <div class="flex items-center text-gray-500 text-sm mb-4">
                <span class="font-medium mr-1.5">IRI:</span>
                <span class="font-mono truncate max-w-[450px]" title="${data.iri}">${data.iri}</span>
                <button onclick="navigator.clipboard.writeText('${data.iri}')" class="ml-2 py-1 px-2 rounded text-blue-600 hover:bg-blue-50" aria-label="Copy IRI">
                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                    </svg>
                </button>
            </div>
            <div class="prose max-w-none mt-2 bg-gray-50 p-3 rounded-md border-l-4 border-blue-200">
                <p class="text-gray-800">${data.definition}</p>
            </div>
        </section>
        <div class="grid grid-cols-1 xl:grid-cols-2 gap-6 w-full" id="detail-grid">
            <div>${parentsHtml}${inverseHtml}${domainHtml}</div>
            <div>${childrenHtml}${rangeHtml}${examplesHtml}</div>
        </div>
    `;
}

function showFallbackMessage(message) {
    const treeContainer = document.getElementById('taxonomy-tree');
    if (!treeContainer) return;
    treeContainer.innerHTML = `
        <div class="p-4 text-yellow-800 bg-yellow-100 rounded">
            <h3 class="font-medium">Unable to load property tree</h3>
            <p>${message}</p>
            <p class="mt-2"><a href="/properties/browse" class="text-blue-600 hover:underline">Switch to the standard browse view</a></p>
        </div>
    `;
}

window.selectNodeByIri = selectNodeByIri;
