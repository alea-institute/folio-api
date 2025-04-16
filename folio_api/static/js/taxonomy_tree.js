/**
 * Taxonomy Tree JavaScript - Handles the tree-based visualization of the FOLIO taxonomy
 */

// Initialize the tree on document ready
document.addEventListener('DOMContentLoaded', function() {
    if (typeof $ === 'undefined') {
        showFallbackMessage('JavaScript libraries needed for the taxonomy tree are not available');
        return;
    }

    initializeTree();
    // setupSearchHandlers(); - Removed to avoid interference with typeahead_search.js
    setupTreeControls();
    setupHistoryNavigation();
});

/**
 * Initialize the custom tree component
 */
function initializeTree() {
    const treeContainer = $('#taxonomy-tree');
    
    // Create root container
    treeContainer.html('<ul class="taxonomy-root-list"></ul>');
    
    // Load the root level nodes
    loadTreeNodes('#', $('.taxonomy-root-list'));
    
    // Style the tree
    applyTreeStyles();
}

/**
 * Load tree nodes recursively
 * @param {string} nodeId - The ID of the node to load children for
 * @param {jQuery} container - The container to append nodes to
 */
function loadTreeNodes(nodeId, container) {
    // Show loading indicator
    container.append('<li class="loading-indicator"><span>Loading...</span></li>');
    
    // Fetch nodes from API
    fetch('/taxonomy/tree/data?node_id=' + encodeURIComponent(nodeId))
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // Remove loading indicator
            container.find('.loading-indicator').remove();
            
            // Render each node
            data.forEach(node => {
                renderTreeNode(node, container);
            });
            
            // Set up click handlers
            setupNodeClickHandlers();
        })
        .catch(() => {
            container.find('.loading-indicator').html('<span class="text-red-500">Error loading. Try again.</span>');
        });
}

/**
 * Render a single tree node
 * @param {Object} node - The node data to render
 * @param {jQuery} container - The container to append the node to
 */
function renderTreeNode(node, container) {
    const hasChildren = node.children;
    const nodeClass = hasChildren ? 'has-children collapsed' : '';
    const expandIcon = hasChildren ? 
        '<span class="expand-icon mr-1">▸</span>' : 
        '<span class="ml-4"></span>';
    
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

/**
 * Set up click handlers for tree nodes
 */
function setupNodeClickHandlers() {
    try {
        // Handler for expand/collapse icons
        $('.expand-icon').off('click').on('click', function(e) {
            e.stopPropagation();
            const li = $(this).closest('li');
            if (li.length) {
                toggleNode(li);
            }
        });
        
        // Handler for single click node selection
        $('.node-content').off('click').on('click', function() {
            const li = $(this).closest('li');
            if (li.length) {
                selectNode(li);
            }
        });
        
        // Handler for double click expand/collapse
        $('.node-content').off('dblclick').on('dblclick', function(e) {
            e.stopPropagation();
            const li = $(this).closest('li');
            
            // Only toggle if this node has children
            if (li.length && li.hasClass('has-children')) {
                toggleNode(li);
            }
        });
    } catch (_) {
        // Silent fail - this prevents errors when jQuery or DOM elements are not ready
    }
}

/**
 * Toggle node expansion
 * @param {jQuery} li - The node's li element
 */
function toggleNode(li) {
    const nodeId = li.data('id');
    const childrenContainer = li.find('> .children-container');
    const expandIcon = li.find('> .node-content .expand-icon');
    
    if (li.hasClass('collapsed')) {
        // Expand the node
        li.removeClass('collapsed').addClass('expanded');
        expandIcon.html('▾');
        childrenContainer.slideDown(200);
        
        // Load children if not already loaded
        if (childrenContainer.children().length === 0) {
            loadTreeNodes(nodeId, childrenContainer);
        }
    } else {
        // Collapse the node
        li.removeClass('expanded').addClass('collapsed');
        expandIcon.html('▸');
        childrenContainer.slideUp(200);
    }
}

/**
 * Select a node and load its details
 * @param {jQuery} li - The node's li element
 * @param {boolean} updateUrl - Whether to update the URL
 */
function selectNode(li, updateUrl = true) {
    // Deselect current selection
    $('.tree-node.selected').removeClass('selected');
    
    // Select new node
    li.addClass('selected');
    
    // Load class details
    const nodeId = li.data('id');
    loadClassDetails(nodeId, updateUrl);
    
    // Ensure the node is visible (expand parent nodes if needed)
    ensureNodeVisible(li);
}

/**
 * Ensure a node is visible by expanding all its parents
 * @param {jQuery} li - The node's li element
 */
function ensureNodeVisible(li) {
    // Get all parent nodes
    const parents = li.parents('li.tree-node');
    
    // Expand each parent if collapsed
    parents.each(function() {
        const parent = $(this);
        if (parent.hasClass('collapsed')) {
            toggleNode(parent);
        }
    });
}

/**
 * Apply tree styles
 */
function applyTreeStyles() {
    // Add CSS styles for the tree
    const style = document.createElement('style');
    style.textContent = `
        .taxonomy-root-list, .children-container {
            list-style-type: none;
            padding-left: 0;
        }
        .children-container {
            padding-left: 20px;
        }
        .tree-node {
            margin: 4px 0;
        }
        .node-content {
            display: flex;
            align-items: center;
            padding: 6px 8px;
            border-radius: 4px;
            cursor: pointer;
            word-break: break-word;
            white-space: normal;
        }
        .node-content:hover {
            background-color: rgba(59, 130, 246, 0.1);
        }
        .tree-node.selected > .node-content {
            background-color: rgba(59, 130, 246, 0.2);
            font-weight: 600;
        }
        .expand-icon {
            cursor: pointer;
            width: 16px;
            display: inline-block;
            text-align: center;
            flex-shrink: 0;
        }
        .node-label {
            flex-grow: 1;
        }
        
        /* Responsive styles */
        @media (max-width: 768px) {
            .tree-explorer-container {
                flex-direction: column;
            }
            #tree-container, #detail-container {
                width: 100%;
                max-height: none;
            }
            #taxonomy-tree {
                max-height: 400px;
            }
        }
        
        /* Scrollbar styling */
        #taxonomy-tree::-webkit-scrollbar {
            width: 8px;
        }
        #taxonomy-tree::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 4px;
        }
        #taxonomy-tree::-webkit-scrollbar-thumb {
            background: #c1c1c1;
            border-radius: 4px;
        }
        #taxonomy-tree::-webkit-scrollbar-thumb:hover {
            background: #a8a8a8;
        }
        
        /* Search highlight styling */
        .node-label span.bg-yellow-200 {
            background-color: #FEFCBF;
            padding: 0 2px;
            border-radius: 2px;
            font-weight: bold;
        }
    `;
    document.head.appendChild(style);
}

/**
 * Set up search functionality for the TOP navigation search bar (not the taxonomy tree search)
 * This is for the global search bar with id="search-input" in the site header
 * 
 * NOTE: This function has been DISABLED to prevent it from interfering with the typeahead
 * search functionality that is initialized separately. The main site-wide search is handled
 * by typeahead_search.js and should not interact with the taxonomy tree.
 */
function setupSearchHandlers() {
    // This function is now a no-op to avoid duplicate event handlers
    // Original implementation has been removed to prevent interference with typeahead_search.js
    return;
}

/**
 * Reset search highlights and visibility
 */
function resetSearch() {
    // Remove all highlighting
    const highlightedNodes = document.querySelectorAll('.node-label span.bg-yellow-200');
    highlightedNodes.forEach(node => {
        const parent = node.parentElement;
        // Replace the HTML content with just the text content to remove span elements
        parent.innerHTML = parent.textContent;
    });
    
    // Reset hidden nodes
    const hiddenNodes = document.querySelectorAll('.tree-node.search-hidden');
    hiddenNodes.forEach(node => {
        node.classList.remove('search-hidden');
        node.style.display = '';
    });
}

/**
 * Search the tree for matching nodes
 * @param {string} query - The search query
 */
function searchTree(query) {
    if (!query || query.length < 2) {
        resetSearch();
        return;
    }
    
    // Count total nodes
    const totalNodes = $('.node-label').length;
    
    // Check if tree is initialized
    if (totalNodes === 0) {
        return;
    }
    
    // Normalize the query for better matching
    const normalizedQuery = query.toLowerCase();
    let foundMatches = false;
    
    // First, reset any previous search
    resetSearch();
    
    // Keep track of nodes with matches
    const matchingNodes = new Set();
    
    // Find nodes with labels containing the query
    $('.node-label').each(function() {
        const nodeLabel = $(this);
        const label = nodeLabel.text();
        const li = nodeLabel.closest('li');
        
        if (label.toLowerCase().includes(normalizedQuery)) {
            // Found a match
            foundMatches = true;
            matchingNodes.add(li[0]);
            
            // Highlight match
            const regex = new RegExp('(' + escapeRegExp(query) + ')', 'gi');
            nodeLabel.html(label.replace(regex, '<span class="bg-yellow-200">$1</span>'));
            
            // Add all parent nodes to matching set
            let parent = li.parents('li');
            while (parent.length) {
                matchingNodes.add(parent[0]);
                parent = parent.parents('li');
            }
        }
    });
    
    // If we found any matches
    if (foundMatches) {
        // Hide nodes that don't have matches and aren't parents of matches
        $('.tree-node').each(function() {
            if (!matchingNodes.has(this)) {
                $(this).addClass('search-hidden');
                $(this).hide();
            }
        });
        
        // Expand all nodes that contain matches
        matchingNodes.forEach(node => {
            const $node = $(node);
            if ($node.hasClass('collapsed')) {
                toggleNode($node);
            }
        });
    }
}

/**
 * Escape regular expression special characters
 * @param {string} string - The string to escape
 * @returns {string} - The escaped string
 */
function escapeRegExp(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * Set up tree control buttons (expand/collapse)
 */
function setupTreeControls() {
    // Expand all button in navbar
    const expandAllBtn = document.getElementById('expand-all-btn');
    if (expandAllBtn) {
        expandAllBtn.addEventListener('click', function() {
            expandAllNodes();
        });
    }
    
    // Collapse all button in navbar
    const collapseAllBtn = document.getElementById('collapse-all-btn');
    if (collapseAllBtn) {
        collapseAllBtn.addEventListener('click', function() {
            collapseAllNodes();
        });
    }
    
    // Expand all button in tree container
    const expandAllTreeBtn = document.getElementById('expand-all-tree');
    if (expandAllTreeBtn) {
        expandAllTreeBtn.addEventListener('click', function() {
            expandAllNodes();
        });
    }
    
    // Collapse all button in tree container
    const collapseAllTreeBtn = document.getElementById('collapse-all-tree');
    if (collapseAllTreeBtn) {
        collapseAllTreeBtn.addEventListener('click', function() {
            collapseAllNodes();
        });
    }
}

/**
 * Expand all tree nodes
 */
function expandAllNodes() {
    // Get all collapsed nodes
    const collapsedNodes = $('.tree-node.collapsed');
    
    // Expand each node
    collapsedNodes.each(function() {
        toggleNode($(this));
    });
    
    // No need to reset URL parameters when expanding all nodes
    // as the selected node is still visible and relevant
}

/**
 * Collapse all tree nodes
 */
function collapseAllNodes() {
    // Save selected node info before collapsing
    const selectedNodeId = getCurrentSelectedNodeId();
    let shouldResetUrl = false;
    
    if (selectedNodeId) {
        // Check if the selected node is a child node (will be hidden)
        const selectedNode = $(`.tree-node[data-id="${selectedNodeId}"]`);
        
        // Check if node is not a top-level node (has parent nodes)
        if (selectedNode.length > 0 && selectedNode.parents('.tree-node').length > 0) {
            shouldResetUrl = true; // Not a root node, will be hidden
        }
    }
    
    // Get all expanded nodes
    const expandedNodes = $('.tree-node.expanded');
    
    // Collapse each node
    expandedNodes.each(function() {
        toggleNode($(this));
    });
    
    // Only reset URL if the selected node is now hidden
    if (shouldResetUrl) {
        resetUrlParameters();
    }
}

/**
 * Get the currently selected node ID from the URL or UI
 * @returns {string|null} The currently selected node ID or null if none
 */
function getCurrentSelectedNodeId() {
    // First check the URL for a node parameter
    const url = new URL(window.location);
    const nodeParam = url.searchParams.get('node');
    
    if (nodeParam) {
        return nodeParam;
    }
    
    // If no URL parameter, check for selected node in the UI
    const selectedNode = $('.tree-node.selected');
    if (selectedNode.length > 0) {
        return selectedNode.data('id');
    }
    
    return null;
}

/**
 * Reset URL parameters to clean state
 */
function resetUrlParameters() {
    // Check if we have a node parameter
    const url = new URL(window.location);
    if (url.searchParams.has('node')) {
        // Remove the node parameter
        url.searchParams.delete('node');
        
        // Update URL without adding to browser history
        window.history.replaceState({}, '', url);
        // URL parameters updated - selected node is no longer visible
    }
}

/**
 * Set up browser history navigation
 */
function setupHistoryNavigation() {
    // Check if we have a node ID in the URL
    const urlParams = new URLSearchParams(window.location.search);
    const nodeId = urlParams.get('node');
    
    if (nodeId) {
        // Load and select the node
        loadAndSelectNode(nodeId, false);
    }
    
    // Listen for popstate events (back/forward navigation)
    window.addEventListener('popstate', function(event) {
        if (event.state && event.state.nodeId) {
            loadAndSelectNode(event.state.nodeId, false);
        }
    });
}

/**
 * Load and select a node by ID
 * @param {string} nodeId - The ID of the node to select
 * @param {boolean} updateUrl - Whether to update the URL
 */
function loadAndSelectNode(nodeId, updateUrl = true) {
    // Find the node if it's already in the DOM
    const node = $(`.tree-node[data-id="${nodeId}"]`);
    
    if (node.length > 0) {
        // Node exists in the DOM, select it
        selectNode(node, updateUrl);
    } else {
        // Node doesn't exist yet, we need to find its parents and load them first
        findNodePath(nodeId).then(path => {
            loadNodePath(path).then(() => {
                // Now the node should be in the DOM
                const loadedNode = $(`.tree-node[data-id="${nodeId}"]`);
                if (loadedNode.length > 0) {
                    selectNode(loadedNode, updateUrl);
                }
            });
        });
    }
}

/**
 * Extract the identifier from an IRI
 * @param {string} iri - The full IRI
 * @returns {string} - The extracted identifier
 */
function extractIdFromIri(iri) {
    if (!iri || !iri.startsWith('http')) return iri;
    
    // Split by "/" and get the last non-empty part
    const parts = iri.split('/').filter(p => p.trim().length > 0);
    if (parts.length > 0) {
        return parts[parts.length - 1];
    }
    return iri;
}

/**
 * Find the path to a node
 * @param {string} nodeId - The ID of the node to find
 * @returns {Promise<Array>} - A promise that resolves to an array of node IDs
 */
async function findNodePath(nodeId) {
    // This is a simplified implementation - in a real app, you'd likely have a dedicated API endpoint
    
    // Extract the ID part from the full IRI
    const extractedId = extractIdFromIri(nodeId);
    
    // Try loading the node data to get its parent(s)
    try {
        const response = await fetch(`/taxonomy/tree/node/${encodeURIComponent(extractedId)}`);
        if (!response.ok) throw new Error('Network response was not ok');
        
        const data = await response.json();
        const path = [];
        
        // Add parents in order (root first)
        if (data.parents && data.parents.length > 0) {
            // Find the top-level parent recursively
            const topParent = await findTopLevelParent(data.parents[0].iri);
            
            // Build path from top to current node
            const fullPath = await buildPathToNode(topParent, nodeId);
            path.push(...fullPath);
        }
        
        // Add the node itself
        path.push(nodeId);
        
        return path;
    } catch (_) {
        return [nodeId]; // Return just the node ID if we can't find its path
    }
}

/**
 * Find the top-level parent of a node
 * @param {string} nodeId - The ID of the node to find the parent for
 * @returns {Promise<string>} - A promise that resolves to the ID of the top-level parent
 */
async function findTopLevelParent(nodeId) {
    // Extract the ID part from the full IRI
    const extractedId = extractIdFromIri(nodeId);
    
    try {
        const response = await fetch(`/taxonomy/tree/node/${encodeURIComponent(extractedId)}`);
        if (!response.ok) throw new Error('Network response was not ok');
        
        const data = await response.json();
        
        // If node has no parents or is a direct child of owl:Thing, it's a top-level node
        if (!data.parents || data.parents.length === 0 || 
            data.parents.some(p => p.iri === "http://www.w3.org/2002/07/owl#Thing")) {
            return nodeId;
        }
        
        // Recursively find the parent of this node's parent
        return findTopLevelParent(data.parents[0].iri);
    } catch (_) {
        // Silently return the node ID if we can't find its parent
        return nodeId;
    }
}

/**
 * Build the path from a top-level node to a target node
 * @param {string} startId - The ID of the starting node
 * @param {string} targetId - The ID of the target node
 * @returns {Promise<Array>} - A promise that resolves to an array of node IDs
 */
async function buildPathToNode(startId, targetId) {
    if (startId === targetId) return [startId];
    
    // Extract the ID parts from the full IRIs
    const extractedStartId = extractIdFromIri(startId);
    const extractedTargetId = extractIdFromIri(targetId);
    
    try {
        const response = await fetch(`/taxonomy/tree/node/${encodeURIComponent(extractedStartId)}`);
        if (!response.ok) throw new Error('Network response was not ok');
        
        const data = await response.json();
        const path = [startId];
        
        // Check if any children are the target or lead to the target
        if (data.children && data.children.length > 0) {
            for (const child of data.children) {
                const childId = extractIdFromIri(child.iri);
                if (childId === extractedTargetId || child.iri === targetId) {
                    // Direct child
                    return [...path, child.iri];
                }
                
                // Check if this child might lead to the target
                const childPath = await buildPathToNode(child.iri, targetId);
                if (childPath.some(id => extractIdFromIri(id) === extractedTargetId)) {
                    return [...path, ...childPath];
                }
            }
        }
        
        return path;
    } catch (_) {
        // Silently return just the start ID if we can't build the path
        return [startId];
    }
}

/**
 * Load a path of nodes in the tree
 * @param {Array} path - An array of node IDs to load
 * @returns {Promise<void>}
 */
async function loadNodePath(path) {
    if (!path || path.length === 0) return;
    
    // Start from the root
    let container = $('.taxonomy-root-list');
    
    // Skip the last node (we'll select it after loading)
    for (let i = 0; i < path.length - 1; i++) {
        const nodeId = path[i];
        
        // Check if the node already exists
        const node = $(`.tree-node[data-id="${nodeId}"]`);
        
        if (node.length > 0) {
            // Node exists, expand it if needed
            if (node.hasClass('collapsed')) {
                toggleNode(node);
            }
            
            // Update container for next iteration
            container = node.find('> .children-container');
        } else {
            // Node doesn't exist, load its level
            await new Promise(resolve => {
                loadTreeNodes(nodeId === path[0] ? '#' : nodeId, container);
                
                // Wait for loading to complete
                const checkLoaded = setInterval(() => {
                    if (!container.find('.loading-indicator').length) {
                        clearInterval(checkLoaded);
                        
                        // Find the node now that it's loaded
                        const loadedNode = $(`.tree-node[data-id="${nodeId}"]`);
                        if (loadedNode.length > 0) {
                            // Expand it
                            if (loadedNode.hasClass('collapsed')) {
                                toggleNode(loadedNode);
                            }
                            
                            // Update container for next iteration
                            container = loadedNode.find('> .children-container');
                        }
                        
                        resolve();
                    }
                }, 100);
            });
        }
    }
}

/**
 * Load detailed information about a class
 * @param {string} iri - The IRI of the class to load details for
 * @param {boolean} updateUrl - Whether to update the URL
 */
function loadClassDetails(iri, updateUrl = true) {
    const detailsContainer = document.getElementById('class-details');
    if (!detailsContainer) return;
    
    // Update URL if needed
    if (updateUrl) {
        const url = new URL(window.location);
        url.searchParams.set('node', iri);
        history.pushState({ nodeId: iri }, '', url);
    }
    
    // Show loading indicator
    detailsContainer.innerHTML = `
        <div class="flex justify-center items-center h-64">
            <div class="spinner-border animate-spin inline-block w-8 h-8 border-4 rounded-full text-blue-600" role="status">
                <span class="sr-only">Loading...</span>
            </div>
        </div>
    `;
    
    // Extract the ID part from the full IRI
    let nodeId = iri;
    
    // If this is a full URL, just get the last part of the path
    if (iri.startsWith('http')) {
        // Split by "/" and get the last non-empty part
        const parts = iri.split('/').filter(p => p.trim().length > 0);
        if (parts.length > 0) {
            nodeId = parts[parts.length - 1];
        }
    }
    
    // Fetch details from the server
    fetch('/taxonomy/tree/node/' + encodeURIComponent(nodeId))
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            renderClassDetails(data);
        })
        .catch(() => {
            detailsContainer.innerHTML = `
                <div class="p-4 text-red-500">
                    <h3 class="text-xl font-medium mb-2">Error loading class details</h3>
                    <p>Unable to load details for this class. Please try again or select a different class.</p>
                </div>
            `;
        });
}

/**
 * Render the details of a class in the right panel
 * @param {Object} data - The class data to render
 */
function renderClassDetails(data) {
    const detailsContainer = document.getElementById('class-details');
    if (!detailsContainer) return;
    
    // Extract the ID part from the full IRI
    let nodeId = data.iri;
    
    // If this is a full URL, just get the last part of the path
    if (data.iri.startsWith('http')) {
        // Split by "/" and get the last non-empty part
        const parts = data.iri.split('/').filter(p => p.trim().length > 0);
        if (parts.length > 0) {
            nodeId = parts[parts.length - 1];
        }
    }
    
    // Fetch the template rendering from the server
    fetch(`/taxonomy/class-details/${encodeURIComponent(nodeId)}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Could not fetch rendered template');
            }
            return response.text();
        })
        .then(html => {
            detailsContainer.innerHTML = html;
            
            // Update links to use our custom node selection
            $(detailsContainer).find('a[onclick*="jstree"]').each(function() {
                const href = $(this).attr('onclick');
                if (href) {
                    const iriMatch = href.match(/'([^']+)'/);
                    if (iriMatch && iriMatch[1]) {
                        $(this).attr('onclick', `selectNodeByIri('${iriMatch[1]}'); return false;`);
                    }
                }
            });
        })
        .catch(() => {
            // Fallback to client-side rendering if server template fails
            fallbackRenderClassDetails(data, detailsContainer);
        });
}

/**
 * Select a node by its IRI
 * @param {string} iri - The IRI of the node to select
 */
function selectNodeByIri(iri) {
    loadAndSelectNode(iri);
}

/**
 * Fallback rendering function if the server-side template fails
 * @param {Object} data - The class data to render
 * @param {HTMLElement} container - The container to render into
 */
function fallbackRenderClassDetails(data, container) {
    // Build parents section if available
    let parentsHtml = '';
    if (data.parents && data.parents.length > 0) {
        parentsHtml = `
            <section class="card animate-fade-in mb-6">
                <h4 class="text-lg font-medium text-[--color-primary] mb-3">Parent Classes</h4>
                <ul class="list-disc pl-5 space-y-1">
                    ${data.parents.map(parent => 
                        `<li>
                            <a href="#" class="text-blue-600 hover:underline" 
                               onclick="selectNodeByIri('${parent.iri}'); return false;">
                               ${parent.label}
                            </a> - ${parent.definition}
                        </li>`
                    ).join('')}
                </ul>
            </section>
        `;
    }
    
    // Build children section if available
    let childrenHtml = '';
    if (data.children && data.children.length > 0) {
        childrenHtml = `
            <section class="card animate-fade-in mb-6">
                <h4 class="text-lg font-medium text-[--color-primary] mb-3">
                    Child Classes <span class="text-gray-500">(${data.children.length})</span>
                </h4>
                <div class="max-h-60 overflow-y-auto">
                    <ul class="list-disc pl-5 space-y-1">
                        ${data.children.map(child => 
                            `<li>
                                <a href="#" class="text-blue-600 hover:underline" 
                                   onclick="selectNodeByIri('${child.iri}'); return false;">
                                   ${child.label}
                                </a> - ${child.definition}
                            </li>`
                        ).join('')}
                    </ul>
                </div>
            </section>
        `;
    }
    
    // Build examples section if available
    const examplesHtml = data.examples && data.examples.length > 0 ? 
        `<section class="card animate-fade-in mb-6">
            <h4 class="text-lg font-medium text-[--color-primary] mb-3">Examples</h4>
            <ul class="list-disc pl-5 space-y-1">
                ${data.examples.map(example => `<li>${example}</li>`).join('')}
            </ul>
        </section>` : '';
    
    // Build notes section if available
    const notesHtml = data.notes && data.notes.length > 0 ? 
        `<section class="card animate-fade-in mb-6">
            <h4 class="text-lg font-medium text-[--color-primary] mb-3">Notes</h4>
            <ul class="list-disc pl-5 space-y-1">
                ${data.notes.map(note => `<li>${note}</li>`).join('')}
            </ul>
        </section>` : '';
    
    // Build see also section if available
    const seeAlsoHtml = data.see_also && data.see_also.length > 0 ? 
        `<section class="card animate-fade-in mb-6">
            <h4 class="text-lg font-medium text-[--color-primary] mb-3">See Also</h4>
            <ul class="list-disc pl-5 space-y-1">
                ${data.see_also.map(see => 
                    `<li>
                        <a href="${see}" class="text-blue-600 hover:underline" target="_blank">
                            ${see}
                        </a>
                    </li>`
                ).join('')}
            </ul>
        </section>` : '';
    
    // Build additional metadata HTML
    let metadataItems = [];
    
    if (data.preferred_label) {
        metadataItems.push(`
            <div>
                <p class="text-gray-500 text-sm font-medium">Preferred Label</p>
                <p>${data.preferred_label}</p>
            </div>
        `);
    }
    
    if (data.alternative_labels && data.alternative_labels.length) {
        metadataItems.push(`
            <div>
                <p class="text-gray-500 text-sm font-medium">Alternative Labels</p>
                <p>${data.alternative_labels.join(', ')}</p>
            </div>
        `);
    }
    
    if (data.identifier) {
        metadataItems.push(`
            <div>
                <p class="text-gray-500 text-sm font-medium">Identifier</p>
                <p>${data.identifier}</p>
            </div>
        `);
    }
    
    if (data.description) {
        metadataItems.push(`
            <div>
                <p class="text-gray-500 text-sm font-medium">Description</p>
                <p>${data.description}</p>
            </div>
        `);
    }
    
    if (data.comment) {
        metadataItems.push(`
            <div>
                <p class="text-gray-500 text-sm font-medium">Comment</p>
                <p>${data.comment}</p>
            </div>
        `);
    }
    
    // Always include deprecated status
    metadataItems.push(`
        <div>
            <p class="text-gray-500 text-sm font-medium">Deprecated</p>
            <p>${data.deprecated ? 'Yes' : 'No'}</p>
        </div>
    `);
    
    const metadataHtml = `
        <section class="card animate-fade-in mb-6">
            <h4 class="text-lg font-medium text-[--color-primary] mb-3">Additional Information</h4>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                ${metadataItems.join('')}
            </div>
        </section>
    `;
    
    // Main HTML structure for class details
    // Build translations section if available
    let translationsHtml = '';
    if (data.translations && Object.keys(data.translations).length > 0) {
        let translationItems = '';
        
        for (const [lang, translation] of Object.entries(data.translations)) {
            translationItems += `
                <div class="border-b pb-2">
                    <p class="text-gray-500 text-sm font-medium">${lang}</p>
                    <p class="mt-1">${translation}</p>
                </div>
            `;
        }
        
        translationsHtml = `
            <section class="card animate-fade-in mb-6">
                <h4 class="text-lg font-medium text-[--color-primary] mb-3">Translations</h4>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    ${translationItems}
                </div>
            </section>
        `;
    }

    const html = `
        <section class="card animate-fade-in mb-6">
            <h3 class="text-2xl font-semibold mb-2 text-[--color-primary]">${data.label}</h3>
            <p class="text-gray-500 text-sm mb-4 truncate" title="${data.iri}">
                IRI: ${data.iri} 
                <button onclick="navigator.clipboard.writeText('${data.iri}')" 
                        class="py-1 px-2 rounded text-sm" 
                        aria-label="Copy IRI to clipboard">📋</button>
            </p>
            <div class="prose max-w-none">
                <p>${data.definition}</p>
            </div>
        </section>
        
        <div class="space-y-6">
            ${parentsHtml}
            ${childrenHtml}
            ${examplesHtml}
            ${notesHtml}
            ${seeAlsoHtml}
            ${metadataHtml}
            ${translationsHtml}
        </div>
    `;
    
    container.innerHTML = html;
}

/**
 * Show a fallback message when something goes wrong with the tree
 * @param {string} message - The error message to display
 */
function showFallbackMessage(message) {
    const treeContainer = document.getElementById('taxonomy-tree');
    if (!treeContainer) return;
    
    treeContainer.innerHTML = `
        <div class="p-4 text-yellow-800 bg-yellow-100 rounded">
            <h3 class="font-medium">Unable to load taxonomy tree</h3>
            <p>${message}</p>
            <p class="mt-2">
                <a href="/taxonomy/browse" class="text-blue-600 hover:underline">
                    Switch to the standard browse view
                </a>
            </p>
        </div>
    `;
}

// Make functions available globally
window.selectNodeByIri = selectNodeByIri;