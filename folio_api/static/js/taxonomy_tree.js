/**
 * Taxonomy Tree JavaScript - Handles the tree-based visualization of the FOLIO taxonomy
 */

// Initialize the tree on document ready
// Initialize a cache for node data to prevent redundant requests
const nodeDataCache = new Map();

// Maximum cache size to prevent memory issues
const MAX_CACHE_SIZE = 100;

// Flag to prevent multiple tree loading attempts occurring simultaneously
let isLoadingTree = false;

// For rate-limiting API requests
const REQUEST_DELAY = 100; // milliseconds between API requests

// Function to get node data with caching
async function getNodeData(nodeId) {
    // Check cache first
    if (nodeDataCache.has(nodeId)) {
        return nodeDataCache.get(nodeId);
    }
    
    // Extract ID if it's a full IRI
    const extractedId = extractIdFromIri(nodeId);
    
    try {
        // Fetch from server
        const response = await fetch(`/taxonomy/tree/node/${encodeURIComponent(extractedId)}`);
        if (!response.ok) throw new Error(`Failed to fetch node data: ${response.status}`);
        
        const data = await response.json();
        
        // Add to cache
        nodeDataCache.set(nodeId, data);
        nodeDataCache.set(extractedId, data);
        
        // Prune cache if it gets too large
        if (nodeDataCache.size > MAX_CACHE_SIZE) {
            // Remove oldest entries (first 20% of entries)
            const keys = [...nodeDataCache.keys()];
            const deleteCount = Math.ceil(MAX_CACHE_SIZE * 0.2);
            for (let i = 0; i < deleteCount; i++) {
                nodeDataCache.delete(keys[i]);
            }
        }
        
        return data;
    } catch (error) {
        // Error silently handled
        throw error;
    }
}

document.addEventListener('DOMContentLoaded', function() {
    if (typeof $ === 'undefined') {
        showFallbackMessage('JavaScript libraries needed for the taxonomy tree are not available');
        return;
    }

    // Check if we have a node ID in the URL first
    const urlParams = new URLSearchParams(window.location.search);
    const nodeId = urlParams.get('node');
    
    if (nodeId) {
        // If we have a node ID, we'll initialize the tree as part of loadAndSelectNode
        setupTreeControls();
        setupKeyboardNavigation();
        loadAndSelectNode(nodeId, false);
    } else {
        // Otherwise, initialize the tree normally
        initializeTree();
        setupTreeControls();
        setupKeyboardNavigation();
    }
    
    // Set up history navigation in either case
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
    
    // Apply global styles for arrows to ensure consistency
    applyArrowStyles();
}

/**
 * Load tree nodes recursively
 * @param {string} nodeId - The ID of the node to load children for
 * @param {jQuery} container - The container to append nodes to
 */
function loadTreeNodes(nodeId, container) {
    // Check if container already has nodes (other than loading indicators)
    const existingNodes = container.children('.tree-node');
    if (existingNodes.length > 0) {
        return;
    }
    
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
            
            // Remove any existing nodes to prevent duplicates
            container.children('.tree-node').remove();
            
            // Render each node
            data.forEach(node => {
                // Check if this node already exists in this container
                const existingNode = container.children(`.tree-node[data-id="${node.id}"]`);
                if (existingNode.length === 0) {
                    renderTreeNode(node, container);
                }
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
        '<span class="leaf-indicator ml-1 mr-3 inline-flex shrink-0 items-center justify-center w-[8px] h-[8px] rounded-full bg-gray-200"></span>';
    
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
        
        // Load children if not already loaded - only if there are no tree nodes
        // Loading indicators don't count as children for this check
        if (childrenContainer.children('.tree-node').length === 0) {
            loadTreeNodes(nodeId, childrenContainer);
        }
        
        // Ensure child nodes have correct styling
        setTimeout(function() {
            childrenContainer.find('> li:not(.selected):not(.tree-node-highlighted):not(.tree-node-match) > .node-content').css({
                'background-color': 'white',
                'color': 'var(--color-text-default, rgb(16, 16, 16))'
            });
        }, 250); // Wait a bit for animation to complete
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
            padding-left: 14px;
            border-left: 1px solid rgba(209, 213, 219, 0.7);
            margin-left: 6px;
        }
        .children-container .tree-node:not(.selected):not(.tree-node-highlighted) > .node-content {
            background-color: white;
            color: var(--color-text-default, rgb(16, 16, 16));
        }
        .tree-node {
            margin: 1px 0;
            position: relative;
        }
        .node-content {
            display: flex;
            align-items: center;
            padding: 2px 6px;
            border-radius: 3px;
            cursor: pointer;
            word-break: break-word;
            white-space: normal;
            border-bottom: 1px solid rgba(229, 231, 235, 0.3);
            line-height: 1.2;
        }
        .node-content:hover {
            background-color: rgba(59, 130, 246, 0.1);
        }
        .tree-node.selected > .node-content {
            background-color: var(--color-primary, rgb(24, 70, 120)) !important;
            color: white !important;
            font-weight: 600;
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
        .node-label span.bg-blue-100 {
            background-color: rgba(229, 231, 235, 0.7);
            padding: 0 2px;
            border-radius: 2px;
            font-weight: bold;
            color: var(--color-primary, rgb(24, 70, 120));
        }
    `;
    document.head.appendChild(style);
}

/**
 * Apply consistent arrow styles throughout the tree
 */
function applyArrowStyles() {
    // Create a style element for arrow styling
    if (!document.getElementById('taxonomy-tree-arrow-styles')) {
        const arrowStyle = document.createElement('style');
        arrowStyle.id = 'taxonomy-tree-arrow-styles';
        arrowStyle.textContent = `
            .expand-icon {
                cursor: pointer;
                width: 16px;
                display: inline-flex !important;
                align-items: center !important;
                justify-content: center;
                text-align: center;
                flex-shrink: 0;
                font-size: 24px !important;
                line-height: 16px !important;
                vertical-align: middle !important;
                position: relative !important;
                top: -2px !important;
            }
        `;
        document.head.appendChild(arrowStyle);
    }
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
            nodeLabel.html(label.replace(regex, '<span class="bg-blue-100">$1</span>'));
            
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
    // We no longer need to check for node ID here as it's handled in the DOMContentLoaded event
    // This function now only sets up the popstate event listener
    
    // Listen for popstate events (back/forward navigation)
    window.addEventListener('popstate', function(event) {
        if (event.state && event.state.nodeId) {
            loadAndSelectNode(event.state.nodeId, false);
        } else {
            // If no state, check URL parameters
            const urlParams = new URLSearchParams(window.location.search);
            const nodeId = urlParams.get('node');
            
            if (nodeId) {
                loadAndSelectNode(nodeId, false);
            } else {
                // No node in state or URL, possibly went back to initial state
                // Reset the view if needed
                const selectedNode = $('.tree-node.selected');
                if (selectedNode.length > 0) {
                    selectedNode.removeClass('selected');
                }
                
                // Clear the details panel
                const detailsContainer = document.getElementById('class-details');
                if (detailsContainer) {
                    detailsContainer.innerHTML = `
                        <div class="flex items-center justify-center h-full text-gray-500">
                            <div class="text-center">
                                <svg class="w-16 h-16 mx-auto text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                                </svg>
                                <h3 class="mt-2 text-xl font-medium">Select a class</h3>
                                <p class="mt-1">Choose a class from the tree to view its details</p>
                            </div>
                        </div>
                    `;
                }
            }
        }
    });
}

/**
 * Setup keyboard navigation for the tree
 */
function setupKeyboardNavigation() {
    // Add keydown event listener to handle spacebar and arrow keys
    document.addEventListener('keydown', function(event) {
        // Only proceed if we're not in an input field or textarea
        if (document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
            const selectedNode = document.querySelector('.tree-node.selected');
            
            if (selectedNode) {
                // Handle spacebar - toggle expand/collapse
                if (event.key === ' ') {
                    // Prevent default scroll behavior of space bar
                    event.preventDefault();
                    
                    if (selectedNode.classList.contains('has-children')) {
                        // Get the expand icon
                        const expandIcon = selectedNode.querySelector('.expand-icon');
                        if (expandIcon) {
                            // Directly trigger a click on the expand icon
                            expandIcon.click();
                        }
                    }
                }
                // Handle right arrow - expand node
                else if (event.key === 'ArrowRight') {
                    event.preventDefault();
                    
                    if (selectedNode.classList.contains('has-children') && selectedNode.classList.contains('collapsed')) {
                        const expandIcon = selectedNode.querySelector('.expand-icon');
                        if (expandIcon) {
                            expandIcon.click();
                        }
                    }
                }
                // Handle left arrow - collapse node
                else if (event.key === 'ArrowLeft') {
                    event.preventDefault();
                    
                    if (selectedNode.classList.contains('has-children') && selectedNode.classList.contains('expanded')) {
                        const expandIcon = selectedNode.querySelector('.expand-icon');
                        if (expandIcon) {
                            expandIcon.click();
                        }
                    }
                }
                // Handle down arrow - navigate to next visible node
                else if (event.key === 'ArrowDown') {
                    event.preventDefault();
                    
                    // Find all visible tree nodes
                    const visibleNodes = Array.from(document.querySelectorAll('.tree-node')).filter(node => {
                        return window.getComputedStyle(node).display !== 'none';
                    });
                    
                    // Find index of current selected node
                    const currentIndex = visibleNodes.indexOf(selectedNode);
                    
                    // Select next node if available
                    if (currentIndex < visibleNodes.length - 1) {
                        const nextNode = visibleNodes[currentIndex + 1];
                        const nodeContent = nextNode.querySelector('.node-content');
                        if (nodeContent) {
                            nodeContent.click();
                        }
                    }
                }
                // Handle up arrow - navigate to previous visible node
                else if (event.key === 'ArrowUp') {
                    event.preventDefault();
                    
                    // Find all visible tree nodes
                    const visibleNodes = Array.from(document.querySelectorAll('.tree-node')).filter(node => {
                        return window.getComputedStyle(node).display !== 'none';
                    });
                    
                    // Find index of current selected node
                    const currentIndex = visibleNodes.indexOf(selectedNode);
                    
                    // Select previous node if available
                    if (currentIndex > 0) {
                        const prevNode = visibleNodes[currentIndex - 1];
                        const nodeContent = prevNode.querySelector('.node-content');
                        if (nodeContent) {
                            nodeContent.click();
                        }
                    }
                }
            }
        }
    });
}

/**
 * Load and select a node by ID
 * @param {string} nodeId - The ID of the node to select
 * @param {boolean} updateUrl - Whether to update the URL
 */
function loadAndSelectNode(nodeId, updateUrl = true) {
    // First check if the request is already in progress
    if (isLoadingTree) {
        // Wait for the current operation to complete before trying again
        setTimeout(() => loadAndSelectNode(nodeId, updateUrl), 500);
        return;
    }
    
    // Check if we need to initialize the tree first
    const treeContainer = $('#taxonomy-tree');
    const needsInitialization = treeContainer.find('.taxonomy-root-list').length === 0;
    
    if (needsInitialization) {
        // Create root container if it doesn't exist
        treeContainer.html('<ul class="taxonomy-root-list"></ul>');
        
        // Style the tree
        applyTreeStyles();
        
        // Apply global styles for arrows to ensure consistency
        applyArrowStyles();
    }
    
    // Find the node if it's already in the DOM
    const node = $(`.tree-node[data-id="${nodeId}"]`);
    
    if (node.length > 0) {
        // Node exists in the DOM, select it
        selectNode(node, updateUrl);
    } else {
        // Set the loading flag
        isLoadingTree = true;
        
        // Show loading indicator
        const detailsContainer = document.getElementById('class-details');
        if (detailsContainer) {
            detailsContainer.innerHTML = `
                <div class="flex justify-center items-center h-64">
                    <div class="flex flex-col items-center">
                        <div class="spinner-border animate-spin inline-block w-8 h-8 border-4 rounded-full text-blue-600 mb-4" role="status">
                            <span class="sr-only">Loading...</span>
                        </div>
                        <p class="text-gray-600">Finding and loading node...</p>
                    </div>
                </div>
            `;
        }
        
        // Node doesn't exist yet, we need to find its parents and load them first
        findNodePath(nodeId)
            .then(path => {
                return loadNodePath(path);
            })
            .then(() => {
                // Now the node should be in the DOM
                const loadedNode = $(`.tree-node[data-id="${nodeId}"]`);
                if (loadedNode.length > 0) {
                    // Make sure we always select the node after loading it
                    $('.tree-node.selected').removeClass('selected');
                    loadedNode.addClass('selected');
                    
                    // Scroll to make the node visible
                    loadedNode[0].scrollIntoView({ block: 'center', behavior: 'smooth' });
                    
                    // Properly call selectNode to update URL and load details
                    selectNode(loadedNode, updateUrl);
                } else {
                    // Node not found in DOM
                    
                    // Try a direct load of the node details even if we can't find it in the tree
                    loadClassDetails(nodeId, updateUrl);
                }
            })
            .catch(err => {
                // Error handled silently
                
                // Double-check one more time if the node is in the DOM before falling back
                const finalCheckNode = $(`.tree-node[data-id="${nodeId}"]`);
                if (finalCheckNode.length > 0) {
                    // Make sure we always select the node
                    $('.tree-node.selected').removeClass('selected');
                    finalCheckNode.addClass('selected');
                    
                    // Scroll to make the node visible
                    finalCheckNode[0].scrollIntoView({ block: 'center', behavior: 'smooth' });
                    
                    // Properly call selectNode to update URL and load details
                    selectNode(finalCheckNode, updateUrl);
                } else {
                    // Still try to load the details
                    loadClassDetails(nodeId, updateUrl);
                }
            })
            .finally(() => {
                // Final check to ensure the node is selected
                setTimeout(() => {
                    const finalNode = $(`.tree-node[data-id="${nodeId}"]`);
                    if (finalNode.length > 0 && !finalNode.hasClass('selected')) {
                        $('.tree-node.selected').removeClass('selected');
                        finalNode.addClass('selected');
                    }
                    
                    // Clear the loading flag
                    isLoadingTree = false;
                }, 200);
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
    // Add caching and rate limiting to prevent excessive calls
    
    // Extract the ID part from the full IRI
    const extractedId = extractIdFromIri(nodeId);
    
    // Try loading the node data to get its parent(s)
    try {
        // Use cached data function instead of direct fetch
        const data = await getNodeData(nodeId);
        const path = [];
        
        // Add parents in order (root first)
        if (data.parents && data.parents.length > 0) {
            // Find the top-level parent recursively (but limit depth)
            const topParent = await findTopLevelParent(data.parents[0].iri);
            
            // Build path from top to current node
            const fullPath = await buildPathToNode(topParent, nodeId);
            
            // Only add the path if it's valid and contains more than just the starting node
            if (fullPath && fullPath.length > 1) {
                path.push(...fullPath);
            } else {
                // If we couldn't build a proper path, just use the parent chain
                let currentNode = data.parents[0].iri;
                const parentChain = [currentNode];
                
                // Add parent chain in reverse (from immediate parent to root)
                try {
                    for (let i = 0; i < 5; i++) { // Limit to 5 levels to prevent excessive calls
                        const parentData = await getNodeData(currentNode);
                        if (!parentData.parents || parentData.parents.length === 0) break;
                        
                        currentNode = parentData.parents[0].iri;
                        parentChain.unshift(currentNode); // Add parent to beginning of chain
                    }
                } catch (error) {
                    // Error handled silently
                }
                
                path.push(...parentChain);
            }
        }
        
        // Only add the node itself if it's not already the last item in the path
        if (path.length === 0 || path[path.length - 1] !== nodeId) {
            path.push(nodeId);
        }
        
        return path;
    } catch (error) {
        // Error handled silently
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
        // Use the cached data function instead of direct fetch
        const data = await getNodeData(nodeId);
        
        // If node has no parents or is a direct child of owl:Thing, it's a top-level node
        if (!data.parents || data.parents.length === 0 || 
            data.parents.some(p => p.iri === "http://www.w3.org/2002/07/owl#Thing")) {
            return nodeId;
        }
        
        // Recursively find the parent of this node's parent
        return findTopLevelParent(data.parents[0].iri);
    } catch (error) {
        // Error handled silently
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
    // Early termination for identical nodes
    if (startId === targetId) return [startId];
    
    // Also check for matches with extracted IDs
    const extractedStartId = extractIdFromIri(startId);
    const extractedTargetId = extractIdFromIri(targetId);
    if (extractedStartId === extractedTargetId) return [startId];
    
    
    // Set to keep track of visited nodes to prevent cycles
    const visited = new Set();
    visited.add(startId);
    visited.add(extractedStartId);
    
    // Queue for breadth-first search with path tracking
    // Each entry is [nodeId, pathSoFar]
    const queue = [[startId, [startId]]];
    
    // Maximum depth to search to prevent excessive API calls
    const MAX_DEPTH = 3;
    
    try {
        // Process queue with breadth-first search (shorter paths first)
        while (queue.length > 0) {
            const [currentId, currentPath] = queue.shift();
            
            // Stop if we've reached maximum depth
            if (currentPath.length > MAX_DEPTH) {
                return [startId]; // Return just the start node
            }
            
            // Get the extracted ID
            const extractedCurrentId = extractIdFromIri(currentId);
            
            try {
                // Fetch node data using cache
                const data = await getNodeData(currentId);
                
                // Check children (if any)
                if (data.children && data.children.length > 0) {
                    // Sort children by label to help find more meaningful paths
                    const sortedChildren = [...data.children].sort((a, b) => {
                        return (a.label || "").localeCompare(b.label || "");
                    });
                    
                    for (const child of sortedChildren) {
                        const childId = child.iri;
                        const extractedChildId = extractIdFromIri(childId);
                        
                        // Skip if we've already visited this node
                        if (visited.has(childId) || visited.has(extractedChildId)) {
                            continue;
                        }
                        
                        // Mark as visited
                        visited.add(childId);
                        visited.add(extractedChildId);
                        
                        // Check if this is our target
                        if (childId === targetId || extractedChildId === extractedTargetId) {
                            return [...currentPath, childId];
                        }
                        
                        // Add to queue with updated path (but only if we're not too deep)
                        if (currentPath.length < MAX_DEPTH) {
                            queue.push([childId, [...currentPath, childId]]);
                        }
                    }
                }
            } catch (error) {
                // Error handled silently
                // Continue to next node in queue
                continue;
            }
        }
        
        // If we exhausted the queue without finding the target, return just the start node
        return [startId];
    } catch (error) {
        // Error handled silently
        return [startId]; // Return just the start ID if we can't build the path
    }
}

/**
 * Load a path of nodes in the tree
 * @param {Array} path - An array of node IDs to load
 * @returns {Promise<void>}
 */
async function loadNodePath(path) {
    if (!path || path.length === 0) return;
    
    
    // Check if we need to load the root level first
    const rootList = $('.taxonomy-root-list');
    let needsRootLoading = rootList.children('.tree-node').length === 0;
    
    // Start from the root
    let container = rootList;
    
    // Load root level if needed
    if (needsRootLoading) {
        await new Promise(resolve => {
            loadTreeNodes('#', container);
            
            // Wait for loading to complete
            const checkLoaded = setInterval(() => {
                if (!container.find('.loading-indicator').length) {
                    clearInterval(checkLoaded);
                    resolve();
                }
            }, 100);
        });
    }
    
    // Process the path node by node, keeping track of the current container
    let currentContainer = rootList;
    let currentLevel = 0;
    
    // Skip OWL:Thing if it's the first node, as it's not in our tree
    const startIndex = path[0] === "http://www.w3.org/2002/07/owl#Thing" ? 1 : 0;
    
    for (let i = startIndex; i < path.length; i++) {
        const nodeId = path[i];
        const isLastNode = (i === path.length - 1);
        
        
        // Find the node in the current container or globally
        let node = currentContainer.children(`.tree-node[data-id="${nodeId}"]`);
        
        // If not found in the current container, try a global search
        if (node.length === 0) {
            node = $(`.tree-node[data-id="${nodeId}"]`);
        }
        
        if (node.length > 0) {
            // If it's not the last node, expand it if collapsed
            if (!isLastNode && node.hasClass('collapsed')) {
                toggleNode(node);
            }
            
            // Update current container for next iteration
            if (!isLastNode) {
                currentContainer = node.find('> .children-container');
                // Check if the container exists, if not create it
                if (currentContainer.length === 0) {
                    node.append('<ul class="children-container" style="display:block;"></ul>');
                    currentContainer = node.find('> .children-container');
                }
            }
        } else {
            // Get the parent node ID
            const parentNodeId = i > startIndex ? path[i - 1] : '#';
            
            // Load the children of the parent
            await new Promise(resolve => {
                // Check if the current container already has children other than loading indicators
                if (currentContainer.children('.tree-node').length > 0) {
                    resolve();
                    return;
                }
                
                loadTreeNodes(parentNodeId, currentContainer);
                
                // Wait for loading to complete
                const checkLoaded = setInterval(() => {
                    if (!currentContainer.find('> .loading-indicator').length) {
                        clearInterval(checkLoaded);
                        
                        // Find the node now that its parent level is loaded
                        node = currentContainer.children(`.tree-node[data-id="${nodeId}"]`);
                        
                        if (node.length === 0) {
                            // Try a global search as a fallback
                            node = $(`.tree-node[data-id="${nodeId}"]`);
                        }
                        
                        if (node.length > 0) {
                            // If not the last node, expand it
                            if (!isLastNode && node.hasClass('collapsed')) {
                                toggleNode(node);
                            }
                            
                            // Update container for next iteration
                            if (!isLastNode) {
                                currentContainer = node.find('> .children-container');
                                // Check if the container exists, if not create it
                                if (currentContainer.length === 0) {
                                    node.append('<ul class="children-container" style="display:block;"></ul>');
                                    currentContainer = node.find('> .children-container');
                                }
                            }
                        } else {
                            // Node not found
                        }
                        
                        resolve();
                    }
                }, 100);
            });
        }
    }
    
    // By this point, all nodes in the path should be loaded and expanded
    // Make sure the last node is visible in the viewport
    const targetNodeId = path[path.length - 1];
    const targetNode = $(`.tree-node[data-id="${targetNodeId}"]`);
    if (targetNode.length > 0) {
        // Scroll to make the target node visible
        targetNode[0].scrollIntoView({ block: 'center', behavior: 'smooth' });
    } else {
        // Target node not found
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
                <h4 class="text-lg font-medium text-[--color-primary] mb-3 flex items-center">
                    <svg class="w-4 h-4 mr-2 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 10l7-7m0 0l7 7m-7-7v18" />
                    </svg>
                    Parent Classes
                </h4>
                <div class="max-h-[200px] overflow-y-auto pr-1">
                    <ul class="space-y-2">
                        ${data.parents.map(parent => 
                            `<li class="group p-1.5 -ml-1.5 rounded-md hover:bg-blue-50 transition-colors duration-150">
                                <div class="flex items-start">
                                    <svg class="w-4 h-4 mt-1 mr-2 text-blue-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 11l5-5m0 0l5 5m-5-5v12" />
                                    </svg>
                                    <div>
                                        <a href="#" 
                                           class="font-medium text-blue-600 hover:text-blue-800 transition-colors duration-150 group-hover:underline" 
                                           onclick="selectNodeByIri('${parent.iri}'); return false;">
                                           ${parent.label}
                                        </a>
                                        <p class="text-sm text-gray-600 mt-0.5 line-clamp-2">
                                            ${parent.definition}
                                        </p>
                                    </div>
                                </div>
                            </li>`
                        ).join('')}
                    </ul>
                </div>
            </section>
        `;
    }
    
    // Build children section if available
    let childrenHtml = '';
    if (data.children && data.children.length > 0) {
        childrenHtml = `
            <section class="card animate-fade-in mb-6">
                <h4 class="text-lg font-medium text-[--color-primary] mb-3 flex items-center">
                    <svg class="w-4 h-4 mr-2 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                    </svg>
                    Child Classes 
                    <span class="ml-2 px-1.5 py-0.5 text-xs font-semibold bg-blue-100 text-blue-800 rounded-full">
                        ${data.children.length}
                    </span>
                </h4>
                <div class="max-h-[300px] overflow-y-auto pr-1">
                    <ul class="space-y-2">
                        ${data.children.map(child => 
                            `<li class="group p-1.5 -ml-1.5 rounded-md hover:bg-blue-50 transition-colors duration-150">
                                <div class="flex items-start">
                                    <svg class="w-4 h-4 mt-1 mr-2 text-green-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 13l-5 5m0 0l-5-5m5 5V6" />
                                    </svg>
                                    <div>
                                        <a href="#" 
                                           class="font-medium text-blue-600 hover:text-blue-800 transition-colors duration-150 group-hover:underline" 
                                           onclick="selectNodeByIri('${child.iri}'); return false;">
                                           ${child.label}
                                        </a>
                                        <p class="text-sm text-gray-600 mt-0.5 line-clamp-2">
                                            ${child.definition}
                                        </p>
                                    </div>
                                </div>
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
            <h4 class="text-lg font-medium text-[--color-primary] mb-3 flex items-center">
                <svg class="w-4 h-4 mr-2 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 20l4-16m2 16l4-16M6 9h14M4 15h14" />
                </svg>
                Examples
            </h4>
            <div class="max-h-[200px] overflow-y-auto pr-1">
                <div class="bg-green-50 border border-green-100 rounded-md p-2">
                    <ul class="space-y-2.5">
                        ${data.examples.map(example => `
                            <li class="flex items-start">
                                <svg class="w-5 h-5 mr-2 text-green-500 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                                <span class="text-gray-800">${example}</span>
                            </li>
                        `).join('')}
                    </ul>
                </div>
            </div>
        </section>` : '';
    
    // Build notes section if available
    const notesHtml = data.notes && data.notes.length > 0 ? 
        `<section class="card animate-fade-in mb-6">
            <h4 class="text-lg font-medium text-[--color-primary] mb-3 flex items-center">
                <svg class="w-4 h-4 mr-2 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
                Notes
            </h4>
            <div class="max-h-[200px] overflow-y-auto pr-1">
                <div class="bg-amber-50 border border-amber-100 rounded-md p-2">
                    <ul class="space-y-2.5">
                        ${data.notes.map(note => `
                            <li class="flex items-start">
                                <svg class="w-5 h-5 mr-2 text-amber-500 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                                </svg>
                                <span class="text-gray-800">${note}</span>
                            </li>
                        `).join('')}
                    </ul>
                </div>
            </div>
        </section>` : '';
    
    // Build see also section if available
    const hasSeeAlso = (data.see_also_items && data.see_also_items.length > 0) || (data.see_also && data.see_also.length > 0);
    
    const seeAlsoHtml = hasSeeAlso ?
        `<section class="card animate-fade-in mb-6">
            <h4 class="text-lg font-medium text-[--color-primary] mb-3 flex items-center">
                <svg class="w-4 h-4 mr-2 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
                See Also
            </h4>
            <div class="max-h-[200px] overflow-y-auto pr-1">
                <ul class="list-disc pl-5 space-y-1.5">
                    ${data.see_also_items ? 
                      // Use the enhanced see_also_items if available
                      data.see_also_items.map(item => {
                          if (item.iri.startsWith('http')) {
                              if (!item.is_external) {
                                  return `<li class="group">
                                      <a href="${item.iri}/html" 
                                         class="inline-flex items-center text-blue-600 hover:text-blue-800 transition-colors duration-150 font-medium">
                                          <span class="group-hover:underline">${item.label}</span>
                                      </a>
                                  </li>`;
                              } else {
                                  return `<li class="group">
                                      <a href="${item.iri}" 
                                         class="inline-flex items-center text-blue-600 hover:text-blue-800 transition-colors duration-150 font-medium" 
                                         target="_blank"
                                         title="Open in new tab">
                                          <span class="truncate max-w-[250px] group-hover:underline">
                                              ${item.label.length > 60 ? item.label.substring(0, 60) + 'WTF' : item.label}
                                          </span>
                                          <svg class="inline-block ml-1 w-3.5 h-3.5 text-blue-400 group-hover:text-blue-600 transition-colors duration-150" 
                                               viewBox="0 0 20 20" 
                                               fill="currentColor"
                                               aria-hidden="true">
                                              <path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z" />
                                              <path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" />
                                          </svg>
                                      </a>
                                  </li>`;
                              }
                          } else {
                              return `<li class="text-gray-700">${item.label}</li>`;
                          }
                      }).join('') :
                      
                      // Fallback to the original see_also if see_also_items is not available
                      data.see_also.map(see => {
                          // Check if the IRI exists in folio_data if available
                          let displayText = see;
                          
                          // First, look in data.folio_graph if available
                          if (data.folio_graph && data.folio_graph[see] && data.folio_graph[see].label) {
                              displayText = data.folio_graph[see].label;
                          } 
                          // Second, check in nodes if available
                          else if (data.nodes && data.nodes.find(node => node.id === see)) {
                              const matchingNode = data.nodes.find(node => node.id === see);
                              displayText = matchingNode.label;
                          }
                          // Third, try to find in data.related_nodes if available
                          else if (data.related_nodes && data.related_nodes.find(node => node.iri === see)) {
                              const matchingNode = data.related_nodes.find(node => node.iri === see);
                              displayText = matchingNode.label;
                          }
                          
                          // Determine if this is an internal or external link
                          const isInternalLink = 
                              (data.folio_graph && data.folio_graph[see]) ||
                              (data.nodes && data.nodes.find(node => node.id === see)) ||
                              (data.related_nodes && data.related_nodes.find(node => node.iri === see)) ||
                              see.includes('folio.openlegalstandard.org');
                          
                          if (see.startsWith('http')) {
                              if (isInternalLink) {
                                  return `<li class="group">
                                      <a href="${see}/html" 
                                         class="inline-flex items-center text-blue-600 hover:text-blue-800 transition-colors duration-150 font-medium">
                                          <span class="group-hover:underline">${displayText}</span>
                                      </a>
                                  </li>`;
                              } else {
                                  return `<li class="group">
                                      <a href="${see}" 
                                         class="inline-flex items-center text-blue-600 hover:text-blue-800 transition-colors duration-150 font-medium" 
                                         target="_blank"
                                         title="Open in new tab">
                                          <span class="truncate max-w-[250px] group-hover:underline">
                                              ${displayText !== see ? displayText : (see.length > 60 ? see.substring(0, 60) + '...' : see)}</span>
                                          <svg class="inline-block ml-1 w-3.5 h-3.5 text-blue-400 group-hover:text-blue-600 transition-colors duration-150" 
                                               viewBox="0 0 20 20" 
                                               fill="currentColor"
                                               aria-hidden="true">
                                              <path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z" />
                                              <path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" />
                                          </svg>
                                      </a>
                                  </li>`;
                              }
                          } else {
                              return `<li class="text-gray-700">${displayText}</li>`;
                          }
                      }).join('')
                    }
                </ul>
            </div>
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
        
        // Language code to flag mapping for full locale codes
        const languageFlags = {
            // English variants
            "en": "🇬🇧", "en-gb": "🇬🇧", "en-us": "🇺🇸", "en-ca": "🇨🇦", "en-au": "🇦🇺", "en-nz": "🇳🇿", 
            // European languages
            "de": "🇩🇪", "de-de": "🇩🇪", "de-at": "🇦🇹", "de-ch": "🇨🇭",
            "fr": "🇫🇷", "fr-fr": "🇫🇷", "fr-ca": "🇨🇦", "fr-ch": "🇨🇭", "fr-be": "🇧🇪",
            "es": "🇪🇸", "es-es": "🇪🇸", "es-mx": "🇲🇽", "es-ar": "🇦🇷", "es-co": "🇨🇴",
            "it": "🇮🇹", "it-it": "🇮🇹", "it-ch": "🇨🇭",
            "pt": "🇵🇹", "pt-pt": "🇵🇹", "pt-br": "🇧🇷",
            "nl": "🇳🇱", "nl-nl": "🇳🇱", "nl-be": "🇧🇪",
            "ru": "🇷🇺", "ru-ru": "🇷🇺",
            "pl": "🇵🇱", "sv": "🇸🇪", "no": "🇳🇴", "fi": "🇫🇮", "da": "🇩🇰", "el": "🇬🇷",
            // Asian languages
            "zh": "🇨🇳", "zh-cn": "🇨🇳", "zh-tw": "🇹🇼", "zh-hk": "🇭🇰", "zh-sg": "🇸🇬",
            "ja": "🇯🇵", "ja-jp": "🇯🇵",
            "ko": "🇰🇷", "ko-kr": "🇰🇷",
            "hi": "🇮🇳", "hi-in": "🇮🇳",
            "ar": "🇸🇦", "ar-sa": "🇸🇦", "ar-eg": "🇪🇬", "ar-dz": "🇩🇿",
            "he": "🇮🇱", "he-il": "🇮🇱", 
            "th": "🇹🇭", "vi": "🇻🇳"
        };
        
        for (const [lang, translation] of Object.entries(data.translations)) {
            const langLower = lang.toLowerCase();
            const flag = languageFlags[langLower] || "🌐";
            
            translationItems += `
                <div class="bg-gray-50 rounded p-3 border-l-2 border-blue-300">
                    <div class="flex items-center mb-2">
                        <span class="text-lg mr-2">${flag}</span>
                        <p class="text-gray-700 font-medium">${lang}</p>
                    </div>
                    <p class="text-gray-800 italic">${translation}</p>
                </div>
            `;
        }
        
        translationsHtml = `
            <section class="card animate-fade-in mb-6">
                <h4 class="text-lg font-medium text-[--color-primary] mb-3 flex items-center">
                    <svg class="w-4 h-4 mr-2 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
                    </svg>
                    Translations
                </h4>
                <div class="max-h-[200px] overflow-y-auto pr-1">
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                        ${translationItems}
                    </div>
                </div>
            </section>
        `;
    }

    const html = `
        <section class="card animate-fade-in mb-6 border-t-4 border-[--color-primary]">
            <div class="flex justify-between items-start">
                <div>
                    <h3 class="text-2xl font-semibold mb-2 text-[--color-primary]">${data.label}</h3>
                    <div class="flex items-center text-gray-500 text-sm mb-4">
                        <span class="font-medium mr-1.5">IRI:</span>
                        <span class="font-mono truncate max-w-[450px]" id="iri-value" title="${data.iri}">
                            ${data.iri}
                        </span>
                        <button onclick="navigator.clipboard.writeText('${data.iri}')" 
                                class="ml-2 py-1 px-2 rounded text-blue-600 hover:bg-blue-50 transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-blue-500" 
                                aria-label="Copy IRI to clipboard">
                            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                            </svg>
                        </button>
                    </div>
                </div>
                
                ${data.deprecated ? `
                <div class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                    <svg class="w-3.5 h-3.5 mr-1.5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    Deprecated
                </div>
                ` : ''}
            </div>
            
            <div class="prose max-w-none mt-2 bg-gray-50 p-3 rounded-md border-l-4 border-blue-200">
                <p class="text-gray-800">${data.definition}</p>
            </div>
        </section>
        
        <div class="grid grid-cols-1 xl:grid-cols-2 gap-6 w-full" style="width: 100%; max-width: 100%;" id="detail-grid">
            <!-- Column 1 -->
            <div>
                ${parentsHtml}
                ${translationsHtml}
                ${seeAlsoHtml}
            </div>
            
            <!-- Column 2 -->
            <div>
                ${childrenHtml}
                ${examplesHtml}
                ${notesHtml}
                ${metadataHtml}
            </div>
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