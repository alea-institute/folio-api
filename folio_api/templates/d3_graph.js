function setup_graph(container_id, nodes, edges) {
    /**
     * Function to set up a basic graph visualization using D3.js library.
     * This is designed to work with the (nodes, edges) structure returned from
     * basic_html.py:get_node_neighbors() function.
     *
     * @param container_id: ID of the container element where the graph will be rendered
     * @param nodes: Array of node objects with properties 'id', 'label', 'description', 'relationship'
     * @param edges: Array of edge objects with properties 'source', 'target', 'type'
     */

        // Select the container element
    const container = d3.select(`#${container_id}`);

    // Function to get current dimensions of the container
    function getContainerDimensions() {
        return {
            width: container.node().getBoundingClientRect().width,
            height: container.node().getBoundingClientRect().height
        };
    }

    // Get initial dimensions
    let {width, height} = getContainerDimensions();

    // Create SVG container
    const svg = d3.select(`#${container_id}`)
        .append("svg")
        .attr("width", width)
        .attr("height", height);

    // Create a group for the graph elements
    const g = svg.append("g");

    // Add zoom behavior
    const zoom = d3.zoom()
        .scaleExtent([0.1, 4])
        .on("zoom", (event) => {
            g.attr("transform", event.transform);
        });

    svg.call(zoom);

    // Define color scales for edges and nodes
    const edgeColorScale = d3.scaleOrdinal()
        .domain(['sub_class_of', 'parent_class_of', 'see_also', 'is_defined_by'])
        .range(['#ff7f0e', '#2ca02c', '#d62728', '#9467bd']);

    const nodeColorScale = d3.scaleOrdinal()
        .domain(['self', 'sub_class_of', 'parent_class_of', 'see_also', 'is_defined_by'])
        .range(['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']);

    // Create a force simulation with increased node separation
    const simulation = d3.forceSimulation(nodes)
        .force("link", d3.forceLink(edges).id(d => d.id).distance(200))
        .force("charge", d3.forceManyBody().strength(-500))
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("collision", d3.forceCollide().radius(50));

    svg.append("defs").append("marker")
        .attr("id", "arrowhead")
        .attr("viewBox", "0 -5 10 10")
        .attr("refX", 20) // Adjust based on the node radius
        .attr("refY", 0)
        .attr("markerWidth", 6)
        .attr("markerHeight", 6)
        .attr("orient", "auto")
        .append("path")
        .attr("d", "M0,-5L10,0L0,5")
        .attr("fill", "#999"); // Adjust color as needed

    // Create edges
    const link = g.selectAll(".link")
        .data(edges)
        .enter().append("line")
        .attr("class", "link")
        .style("stroke", d => edgeColorScale(d.type))
        .style("stroke-opacity", 0.6)
        .style("stroke-width", 2)
        .attr("marker-end", "url(#arrowhead)"); // Add this line to attach the marker

    // Create nodes
    const node = g.selectAll(".node")
        .data(nodes)
        .enter().append("g")
        .attr("class", "node")
        .call(d3.drag()
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended))
        .on("click", clicked)
        .on("mouseover", mouseovered)
        .on("mouseout", mouseouted);

    // Add circles to nodes
    node.append("circle")
        .attr("r", 15)
        .style("fill", d => nodeColorScale(d.relationship || 'self'))
        .style("cursor", "pointer");

    // Add labels to nodes
    node.append("text")
        .attr("dy", -20)
        .attr("text-anchor", "middle")
        .text(d => d.label || "")
        .style("font-size", "12px")
        .style("fill", "black")
        .style("pointer-events", "none");

    // Add title for hover effect
    node.append("title")
        .text(d => d.description || d.label || "");

    // Update positions on each tick of the simulation
    simulation.on("tick", () => {
        link
            .attr("x1", d => d.source.x)
            .attr("y1", d => d.source.y)
            .attr("x2", d => d.target.x)
            .attr("y2", d => d.target.y);

        node
            .attr("transform", d => `translate(${d.x},${d.y})`);
    });

    // Drag functions
    let dragStartTime;

    function dragstarted(event, d) {
        dragStartTime = new Date();
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }

    function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }

    function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;

        // Prevent click event if the drag duration is more than a short threshold
        if (new Date() - dragStartTime > 200) {
            event.sourceEvent.stopPropagation();
        }
    }

    // Click function for nodes
    function clicked(event, d) {
        const url = d.id;
        if (url && url.startsWith("https://")) {
            // Prevent the default action
            event.preventDefault();
            // Navigate to the URL in the same tab
            window.location.href = url + "/html";
        } else {
            console.log("Node clicked:", d);
            // You can add alternative behavior here if the id is not a valid HTTPS URL
        }
    }

    // Mouseover function for nodes
    function mouseovered(event, d) {
        d3.select(this).select("circle")
            .transition()
            .duration(300)
            .attr("r", 20)
            .style("stroke", "#000")
            .style("stroke-width", 2);
    }

    // Mouseout function for nodes
    function mouseouted(event, d) {
        d3.select(this).select("circle")
            .transition()
            .duration(300)
            .attr("r", 15)
            .style("stroke", null)
            .style("stroke-width", null);

        d3.select(this).select("text")
            .text(d => d.label || "")
            .attr("dy", -20)
            .style("fill", "black")
            .style("font-weight", null);
    }

    // Add a legend for edge colors
    const edgeLegend = svg.append("g")
        .attr("class", "legend")
        .attr("transform", "translate(20, 20)");

    const edgeTypes = ['sub_class_of', 'parent_class_of', 'see_also', 'is_defined_by'];
    edgeTypes.forEach((type, i) => {
        const legendItem = edgeLegend.append("g")
            .attr("transform", `translate(0, ${i * 20})`);

        legendItem.append("line")
            .attr("x1", 0)
            .attr("y1", 0)
            .attr("x2", 20)
            .attr("y2", 0)
            .style("stroke", edgeColorScale(type))
            .style("stroke-width", 2);

        legendItem.append("text")
            .attr("x", 25)
            .attr("y", 5)
            .text(type)
            .style("font-size", "12px");
    });

    // Add a legend for node colors
    const nodeLegend = svg.append("g")
        .attr("class", "legend")
        .attr("transform", `translate(${width - 150}, 20)`);

    const nodeTypes = ['self', 'sub_class_of', 'parent_class_of', 'see_also', 'is_defined_by'];
    nodeTypes.forEach((type, i) => {
        const legendItem = nodeLegend.append("g")
            .attr("transform", `translate(0, ${i * 20})`);

        legendItem.append("circle")
            .attr("r", 6)
            .attr("cx", 0)
            .attr("cy", 0)
            .style("fill", nodeColorScale(type));

        legendItem.append("text")
            .attr("x", 10)
            .attr("y", 5)
            .text(type)
            .style("font-size", "12px");
    });
}
