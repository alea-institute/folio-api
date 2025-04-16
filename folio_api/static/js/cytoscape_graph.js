/**
 * Cytoscape.js graph visualization module for FOLIO class relationships
 * Displays class hierarchies with interactive navigation
 */

// Module for creating and managing the Cytoscape graph
const CytoscapeGraph = (function() {
  /**
   * Sets up a hierarchical graph visualization using Cytoscape.js with Dagre
   * 
   * @param {string} container_id - ID of the container element where the graph will be rendered
   * @param {Array} nodes - Array of node objects with properties 'id', 'label', 'description', 'relationship'
   * @param {Array} edges - Array of edge objects with properties 'source', 'target', 'type'
   * @returns {Object} - The Cytoscape instance
   */
  function setupCytoscapeGraph(container_id, nodes, edges) {
    // Collect nodes and edges for Cytoscape
    const cy_nodes = [];
    const cy_edges = [];
    
    // Add nodes
    nodes.forEach(node => {
      cy_nodes.push({
        data: {
          id: node.id,
          label: node.label || 'Unnamed',
          description: node.description,
          relationship: node.relationship
        },
        classes: node.relationship
      });
    });
    
    // Add edges
    edges.forEach(edge => {
      cy_edges.push({
        data: {
          id: `${edge.source}-${edge.target}`,
          source: edge.source,
          target: edge.target,
          type: edge.type
        },
        classes: edge.type
      });
    });
    
    // Initialize Cytoscape instance
    const cy = cytoscape({
      container: document.getElementById(container_id),
      elements: [...cy_nodes, ...cy_edges],
      style: [
        // Node styles
        {
          selector: 'node',
          style: {
            'label': 'data(label)',
            'text-valign': 'center',
            'text-halign': 'center',
            'background-color': '#f0f9ff',
            'border-width': 2,
            'border-color': '#0369a1',
            'shape': 'roundrectangle',
            'padding': '10px',
            'text-wrap': 'wrap',
            'text-max-width': '150px',
            'font-size': '12px',
            'width': 'label',
            'height': 'label',
            'text-margin-y': 5
          }
        },
        // Self node (current class)
        {
          selector: 'node.self',
          style: {
            'background-color': '#0369a1',
            'color': 'white',
            'border-color': '#0284c7',
            'border-width': 3,
            'font-weight': 'bold'
          }
        },
        // Parent classes
        {
          selector: 'node.sub_class_of',
          style: {
            'background-color': '#eff6ff',
            'border-color': '#1d4ed8'
          }
        },
        // Child classes
        {
          selector: 'node.parent_class_of',
          style: {
            'background-color': '#f0fdfa',
            'border-color': '#0d9488'
          }
        },
        // See also
        {
          selector: 'node.see_also',
          style: {
            'background-color': '#fdf4ff',
            'border-color': '#c026d3'
          }
        },
        // Is defined by
        {
          selector: 'node.is_defined_by',
          style: {
            'background-color': '#fff7ed',
            'border-color': '#ea580c'
          }
        },
        // Edge styles
        {
          selector: 'edge',
          style: {
            'curve-style': 'bezier',
            'target-arrow-shape': 'triangle',
            'width': 2,
            'line-color': '#94a3b8',
            'target-arrow-color': '#94a3b8'
          }
        },
        // Subclass relationship
        {
          selector: 'edge.sub_class_of',
          style: {
            'line-color': '#1d4ed8',
            'target-arrow-color': '#1d4ed8',
            'line-style': 'solid'
          }
        },
        // Parent class relationship
        {
          selector: 'edge.parent_class_of',
          style: {
            'line-color': '#0d9488',
            'target-arrow-color': '#0d9488',
            'line-style': 'solid'
          }
        },
        // See also relationship
        {
          selector: 'edge.see_also',
          style: {
            'line-color': '#c026d3',
            'target-arrow-color': '#c026d3',
            'line-style': 'dashed'
          }
        },
        // Is defined by relationship
        {
          selector: 'edge.is_defined_by',
          style: {
            'line-color': '#ea580c',
            'target-arrow-color': '#ea580c',
            'line-style': 'dotted'
          }
        }
      ],
      
      // Basic options
      minZoom: 0.2,
      maxZoom: 3,
      wheelSensitivity: 0.3
    });
    
    // Apply initial layout
    applyDagreLayout(cy);
    
    // Add click handler for nodes (navigation)
    cy.on('tap', 'node', function(evt) {
      var node = evt.target;
      if (node.id() && node.id().startsWith('http')) {
        window.location.href = node.id() + '/html';
      }
    });
    
    // Add keyboard navigation
    setupKeyboardNavigation(cy, container_id);
    
    // Add hover effects and tooltips
    setupNodeTooltips(cy);
    
    // Add controls
    addGraphControls(container_id, cy);
    
    // Create legend
    createLegend(container_id);
    
    // Window resize handler
    window.addEventListener('resize', () => {
      cy.resize();
    });
    
    // Return the graph instance for external use if needed
    return cy;
  }

  /**
   * Apply dagre layout with specific direction
   * 
   * @param {Object} cy - Cytoscape instance
   * @param {string} customRankDir - Optional custom direction ('TB' or 'LR')
   * @returns {Object} - The Cytoscape instance with layout applied
   */
  function applyDagreLayout(cy, customRankDir = null) {
    // Create a dagre.js graph
    const dagreGraph = new dagre.graphlib.Graph();
    
    // Count nodes to determine best layout direction
    const nodeCount = cy.nodes().length;
    const hasLotsOfParents = cy.nodes('.sub_class_of').length > 3;
    const hasLotsOfChildren = cy.nodes('.parent_class_of').length > 5;
    
    // Automatically determine best layout direction
    let rankdir = 'TB'; // Default: Top to bottom
    
    // Switch to left-to-right for wide graphs
    if (hasLotsOfChildren || hasLotsOfParents || nodeCount > 8) {
      rankdir = 'LR'; // Left to right for wider graphs
    }
    
    // Override with custom direction if provided
    if (customRankDir) {
      rankdir = customRankDir;
    }
    
    // Store the current direction for later use
    cy.rankdir = rankdir;
    
    // Set graph direction and spacing
    dagreGraph.setGraph({
      rankdir: rankdir,
      ranksep: rankdir === 'TB' ? 80 : 100,   // Vertical/horizontal spacing between ranks
      nodesep: rankdir === 'TB' ? 40 : 30,    // Horizontal/vertical spacing between nodes
      edgesep: 10,                            // Edge spacing
      marginx: 40,                            // Margin x
      marginy: 40,                            // Margin y
      acyclicer: 'greedy',                    // Minimize edge crossings
      ranker: 'network-simplex'               // Use better ranker algorithm
    });
    
    // Set default node size 
    dagreGraph.setDefaultEdgeLabel(() => ({}));
    
    // Add nodes to dagre graph with dimensions
    cy.nodes().forEach(node => {
      const label = node.data('label') || '';
      // Measure actual text width and add padding
      const textWidth = measureTextWidth(label, 12) + 40;
      const nodeWidth = Math.max(textWidth, 100);
      const nodeHeight = rankdir === 'TB' ? 40 : 50;
      
      dagreGraph.setNode(node.id(), {
        width: nodeWidth,
        height: nodeHeight,
        labelpos: 'c'
      });
    });
    
    // Add edges to dagre graph
    cy.edges().forEach(edge => {
      dagreGraph.setEdge(edge.source().id(), edge.target().id());
    });
    
    // Run the dagre layout
    dagre.layout(dagreGraph);
    
    // Apply the dagre positions to Cytoscape nodes
    cy.nodes().forEach(node => {
      const dagreNodeInfo = dagreGraph.node(node.id());
      
      if (dagreNodeInfo) {
        node.position({
          x: dagreNodeInfo.x,
          y: dagreNodeInfo.y
        });
      }
    });
    
    // Fit the graph to the viewport
    cy.fit();
    
    return cy;
  }

  /**
   * Measure text width for more accurate node sizing
   * 
   * @param {string} text - Text to measure
   * @param {number} fontSize - Font size in pixels
   * @param {string} fontFamily - Font family
   * @returns {number} - Width of text in pixels
   */
  function measureTextWidth(text, fontSize = 12, fontFamily = 'sans-serif') {
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    context.font = `${fontSize}px ${fontFamily}`;
    return context.measureText(text).width;
  }

  /**
   * Setup keyboard navigation for the graph
   * 
   * @param {Object} cy - Cytoscape instance
   * @param {string} container_id - ID of the container element
   */
  function setupKeyboardNavigation(cy, container_id) {
    const container = document.getElementById(container_id);
    
    // Make container focusable
    container.tabIndex = 0;
    container.setAttribute('role', 'application');
    container.setAttribute('aria-label', 'Class hierarchy visualization');
    
    // Track currently focused node
    let focusedNodeId = null;
    
    // Focus the container to activate keyboard navigation
    container.addEventListener('focus', () => {
      // Focus the "self" node by default
      const selfNode = cy.nodes('.self');
      if (selfNode.length > 0) {
        focusedNodeId = selfNode[0].id();
        highlightFocusedNode(cy, focusedNodeId);
      }
    });
    
    // Handle keyboard navigation
    container.addEventListener('keydown', (e) => {
      if (!focusedNodeId) return;
      
      const focusedNode = cy.getElementById(focusedNodeId);
      if (!focusedNode) return;
      
      let newFocusNode = null;
      
      switch (e.key) {
        case 'ArrowUp':
          // Navigate to parent node (sub_class_of edge)
          newFocusNode = focusedNode.outgoers('edge[type="sub_class_of"]').targets();
          break;
        case 'ArrowDown':
          // Navigate to child node (parent_class_of edge)
          newFocusNode = focusedNode.outgoers('edge[type="parent_class_of"]').targets();
          break;
        case 'ArrowLeft':
        case 'ArrowRight':
          // Navigate to sibling nodes based on layout direction
          const neighbors = focusedNode.neighborhood().nodes();
          const currentIndex = neighbors.indexOf(focusedNode);
          
          if (cy.rankdir === 'TB') {
            // In top-bottom layout, left/right move between siblings
            newFocusNode = e.key === 'ArrowLeft' 
              ? neighbors[Math.max(0, currentIndex - 1)]
              : neighbors[Math.min(neighbors.length - 1, currentIndex + 1)];
          } else {
            // In left-right layout, up/down move between siblings
            newFocusNode = e.key === 'ArrowUp' 
              ? neighbors[Math.max(0, currentIndex - 1)]
              : neighbors[Math.min(neighbors.length - 1, currentIndex + 1)];
          }
          break;
        case 'Enter':
        case ' ':
          // Activate node (navigate to it)
          if (focusedNodeId.startsWith('http')) {
            window.location.href = focusedNodeId + '/html';
          }
          break;
      }
      
      if (newFocusNode && newFocusNode.length > 0) {
        focusedNodeId = newFocusNode[0].id();
        highlightFocusedNode(cy, focusedNodeId);
        e.preventDefault();
      }
    });
  }

  /**
   * Highlight the currently focused node
   * 
   * @param {Object} cy - Cytoscape instance
   * @param {string} nodeId - ID of the node to highlight
   */
  function highlightFocusedNode(cy, nodeId) {
    // Reset styles for all nodes
    cy.nodes().forEach(node => {
      resetNodeStyle(node);
    });
    
    // Highlight the focused node
    const focusedNode = cy.getElementById(nodeId);
    if (focusedNode) {
      focusedNode.style({
        'border-width': 4,
        'border-color': '#f97316',
        'z-index': 999
      });
      
      // Pan to center the focused node
      cy.animate({
        center: {
          eles: focusedNode
        },
        duration: 300
      });
      
      // Announce for screen readers
      const nodeLabel = focusedNode.data('label');
      const relationship = focusedNode.data('relationship');
      
      const announcement = document.createElement('div');
      announcement.setAttribute('aria-live', 'polite');
      announcement.className = 'sr-only';
      announcement.textContent = `Focused on ${nodeLabel}, ${relationship} class`;
      document.body.appendChild(announcement);
      
      setTimeout(() => {
        document.body.removeChild(announcement);
      }, 1000);
    }
  }

  /**
   * Reset a node's style based on its relationship type
   * 
   * @param {Object} node - Cytoscape node
   */
  function resetNodeStyle(node) {
    if (node.hasClass('self')) {
      node.style({
        'border-width': 3,
        'border-color': '#0284c7'
      });
    } else if (node.hasClass('sub_class_of')) {
      node.style({
        'border-width': 2,
        'border-color': '#1d4ed8'
      });
    } else if (node.hasClass('parent_class_of')) {
      node.style({
        'border-width': 2,
        'border-color': '#0d9488'
      });
    } else if (node.hasClass('see_also')) {
      node.style({
        'border-width': 2,
        'border-color': '#c026d3'
      });
    } else if (node.hasClass('is_defined_by')) {
      node.style({
        'border-width': 2,
        'border-color': '#ea580c'
      });
    } else {
      node.style({
        'border-width': 2,
        'border-color': '#0369a1'
      });
    }
  }

  /**
   * Setup tooltips for nodes on hover
   * 
   * @param {Object} cy - Cytoscape instance
   */
  function setupNodeTooltips(cy) {
    cy.nodes().forEach(node => {
      // Create tooltip
      const tooltip = document.createElement('div');
      tooltip.classList.add('cy-tooltip');
      tooltip.setAttribute('role', 'tooltip');
      tooltip.textContent = node.data('description');
      
      document.body.appendChild(tooltip);
      node.data('tooltip', tooltip);
    });
    
    cy.on('mouseover', 'node', function(e) {
      const node = e.target;
      
      // Highlight node
      node.style({
        'border-width': 4,
        'border-color': '#f97316',
        'z-index': 999
      });
      
      // Show tooltip
      const tooltip = node.data('tooltip');
      if (tooltip) {
        const pos = node.renderedPosition();
        const rect = document.getElementById(cy.container().id).getBoundingClientRect();
        
        tooltip.style.left = `${rect.left + pos.x}px`;
        tooltip.style.top = `${rect.top + pos.y + 40}px`; // Position below the node
        tooltip.style.display = 'block';
      }
    });
    
    cy.on('mouseout', 'node', function(e) {
      const node = e.target;
      
      // Reset styles based on node type
      resetNodeStyle(node);
      
      // Hide tooltip
      const tooltip = node.data('tooltip');
      if (tooltip) {
        tooltip.style.display = 'none';
      }
    });
  }

  /**
   * Add graph controls (zoom, layout)
   * 
   * @param {string} container_id - ID of the container element
   * @param {Object} cy - Cytoscape instance
   */
  function addGraphControls(container_id, cy) {
    const container = document.getElementById(container_id);
    
    // Create controls container
    const controlsContainer = document.createElement('div');
    controlsContainer.id = 'cy-controls';
    controlsContainer.style.position = 'absolute';
    controlsContainer.style.bottom = '10px';
    controlsContainer.style.right = '10px';
    controlsContainer.style.display = 'flex';
    controlsContainer.style.gap = '5px';
    controlsContainer.style.zIndex = '10';
    
    // Create zoom in button
    const zoomInBtn = document.createElement('button');
    zoomInBtn.id = 'zoom-in';
    zoomInBtn.innerHTML = '+';
    zoomInBtn.className = 'bg-white hover:bg-gray-100 text-gray-800 font-semibold py-1 px-2 border border-gray-400 rounded shadow text-lg';
    zoomInBtn.style.width = '30px';
    zoomInBtn.style.height = '30px';
    zoomInBtn.setAttribute('aria-label', 'Zoom in');
    zoomInBtn.onclick = function() {
      cy.zoom({
        level: cy.zoom() * 1.2,
        renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 }
      });
    };
    
    // Create zoom out button
    const zoomOutBtn = document.createElement('button');
    zoomOutBtn.id = 'zoom-out';
    zoomOutBtn.innerHTML = '−';
    zoomOutBtn.className = 'bg-white hover:bg-gray-100 text-gray-800 font-semibold py-1 px-2 border border-gray-400 rounded shadow text-lg';
    zoomOutBtn.style.width = '30px';
    zoomOutBtn.style.height = '30px';
    zoomOutBtn.setAttribute('aria-label', 'Zoom out');
    zoomOutBtn.onclick = function() {
      cy.zoom({
        level: cy.zoom() / 1.2,
        renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 }
      });
    };
    
    // Create fit button
    const fitBtn = document.createElement('button');
    fitBtn.id = 'fit';
    fitBtn.innerHTML = '⟲';
    fitBtn.className = 'bg-white hover:bg-gray-100 text-gray-800 font-semibold py-1 px-2 border border-gray-400 rounded shadow';
    fitBtn.style.width = '30px';
    fitBtn.style.height = '30px';
    fitBtn.setAttribute('aria-label', 'Reset view');
    fitBtn.onclick = function() {
      cy.fit();
    };
    
    // Create layout direction button (horizontal)
    const horizontalBtn = document.createElement('button');
    horizontalBtn.id = 'horizontal-layout';
    horizontalBtn.innerHTML = '⇌';
    horizontalBtn.title = 'Switch to horizontal layout';
    horizontalBtn.className = 'bg-white hover:bg-gray-100 text-gray-800 font-semibold py-1 px-2 border border-gray-400 rounded shadow';
    horizontalBtn.style.width = '30px';
    horizontalBtn.style.height = '30px';
    horizontalBtn.setAttribute('aria-label', 'Horizontal layout');
    horizontalBtn.onclick = function() {
      applyLayout(cy, 'LR');
    };
    
    // Create layout direction button (vertical)
    const verticalBtn = document.createElement('button');
    verticalBtn.id = 'vertical-layout';
    verticalBtn.innerHTML = '⇅';
    verticalBtn.title = 'Switch to vertical layout';
    verticalBtn.className = 'bg-white hover:bg-gray-100 text-gray-800 font-semibold py-1 px-2 border border-gray-400 rounded shadow';
    verticalBtn.style.width = '30px';
    verticalBtn.style.height = '30px';
    verticalBtn.setAttribute('aria-label', 'Vertical layout');
    verticalBtn.onclick = function() {
      applyLayout(cy, 'TB');
    };
    
    // Add buttons to controls
    controlsContainer.appendChild(zoomInBtn);
    controlsContainer.appendChild(zoomOutBtn);
    controlsContainer.appendChild(fitBtn);
    controlsContainer.appendChild(document.createTextNode(' ')); // Spacer
    controlsContainer.appendChild(horizontalBtn);
    controlsContainer.appendChild(verticalBtn);
    
    // Add controls to container
    container.appendChild(controlsContainer);
  }

  /**
   * Function to re-apply layout with a specific direction
   * 
   * @param {Object} cy - Cytoscape instance
   * @param {string} direction - Layout direction ('TB' or 'LR')
   */
  function applyLayout(cy, direction) {
    // Only apply if direction is different from current
    if (cy.rankdir !== direction) {
      applyDagreLayout(cy, direction);
      
      // Announce for screen readers
      const announcement = document.createElement('div');
      announcement.setAttribute('aria-live', 'polite');
      announcement.className = 'sr-only';
      announcement.textContent = `Layout changed to ${direction === 'TB' ? 'vertical' : 'horizontal'}`;
      document.body.appendChild(announcement);
      
      setTimeout(() => {
        document.body.removeChild(announcement);
      }, 1000);
    }
  }

  /**
   * Create a legend for the graph
   * 
   * @param {string} container_id - ID of the container element
   */
  function createLegend(container_id) {
    const container = document.getElementById(container_id);
    
    // Create legend container
    const legendContainer = document.createElement('div');
    legendContainer.id = 'cy-legend';
    legendContainer.style.position = 'absolute';
    legendContainer.style.top = '10px';
    legendContainer.style.right = '10px';
    legendContainer.style.backgroundColor = 'rgba(255, 255, 255, 0.9)';
    legendContainer.style.padding = '8px';
    legendContainer.style.borderRadius = '4px';
    legendContainer.style.border = '1px solid #ccc';
    legendContainer.style.fontSize = '11px';
    legendContainer.style.zIndex = '10';
    
    // Add ARIA description
    legendContainer.setAttribute('role', 'region');
    legendContainer.setAttribute('aria-label', 'Graph legend');
    
    // Legend content
    legendContainer.innerHTML = `
      <div style="font-weight: bold; margin-bottom: 5px;">Legend</div>
      <div style="display: flex; align-items: center; margin-bottom: 3px;">
        <div style="width: 12px; height: 12px; background-color: #0369a1; border-radius: 3px; margin-right: 5px;"></div>
        <div>Current Class</div>
      </div>
      <div style="display: flex; align-items: center; margin-bottom: 3px;">
        <div style="width: 12px; height: 12px; background-color: #eff6ff; border: 1px solid #1d4ed8; border-radius: 3px; margin-right: 5px;"></div>
        <div>Parent Classes</div>
      </div>
      <div style="display: flex; align-items: center; margin-bottom: 3px;">
        <div style="width: 12px; height: 12px; background-color: #f0fdfa; border: 1px solid #0d9488; border-radius: 3px; margin-right: 5px;"></div>
        <div>Child Classes</div>
      </div>
      <div style="display: flex; align-items: center; margin-bottom: 3px;">
        <div style="width: 12px; height: 12px; background-color: #fdf4ff; border: 1px solid #c026d3; border-radius: 3px; margin-right: 5px;"></div>
        <div>See Also</div>
      </div>
      <div style="display: flex; align-items: center;">
        <div style="width: 12px; height: 12px; background-color: #fff7ed; border: 1px solid #ea580c; border-radius: 3px; margin-right: 5px;"></div>
        <div>Is Defined By</div>
      </div>
    `;
    
    // Add legend to container
    container.appendChild(legendContainer);
  }

  // Return public methods
  return {
    setupCytoscapeGraph,
    applyDagreLayout,
    applyLayout
  };
})();

// Export for global use
window.setupCytoscapeGraph = CytoscapeGraph.setupCytoscapeGraph;