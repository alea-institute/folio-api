"""
Basic HTML template for direct rendering of FOLIO class information in a
user-friendly format.  Don't do this at home.
"""

# imports
import json
from pathlib import Path
from typing import Dict, List, Tuple

# packages
from folio import FOLIO, OWLClass

# project

# JavaScript sources
CYTOSCAPE_JS_SOURCE = (Path(__file__).parent / "cytoscape_graph.js").read_text(encoding="utf-8")
TYPEAHEAD_JS_SOURCE = (Path(__file__).parent / "typeahead_search.js").read_text(
    encoding="utf-8"
)
COPY_IRI_JS_SOURCE = (Path(__file__).parent / "copy_iri.js").read_text(encoding="utf-8")


def format_label(owl_class: OWLClass) -> str:
    """
    Format the label of the class for display  in HTML.
     - Order: preferred_label, label, alt label, IRI

    Args:
        owl_class (OWLClass): FOLIO OWLClass object

    Returns:
        str: Formatted label
    """
    if owl_class.preferred_label:
        return owl_class.preferred_label
    elif owl_class.label:
        return owl_class.label
    elif owl_class.alternative_labels:
        return owl_class.alternative_labels[0]
    else:
        return owl_class.iri


def format_description(owl_class: OWLClass) -> str:
    """
    Format the description of the class for display in HTML.

    Args:
        owl_class (OWLClass): FOLIO OWLClass object

    Returns:
        str: Formatted description
    """

    if owl_class.label and owl_class.definition:
        return owl_class.label + " - " + owl_class.definition
    elif owl_class.label:
        return owl_class.label
    elif owl_class.definition:
        return owl_class.definition
    else:
        return "No description available."



def get_node_neighbors(
    owl_class: OWLClass, folio_graph: FOLIO
) -> Tuple[List[Dict], List[Dict]]:
    """
    Get the neighbors of a class in the FOLIO graph.

    Args:
        owl_class (OWLClass): FOLIO OWLClass object
        folio_graph (FOLIO): FOLIO graph object

    Returns:
        Tuple[List[Dict], List[Dict]]: Tuple with lists of nodes and edges
    """
    nodes = {}
    edges = []

    # add self
    nodes[owl_class.iri] = {
        "id": owl_class.iri,
        "label": owl_class.label,
        "description": format_description(owl_class),
        "color": "#000000",
        "relationship": "self",
    }

    # add sub_class_of parents
    for sub_class in owl_class.sub_class_of:
        if folio_graph[sub_class]:
            nodes[sub_class] = {
                "id": sub_class,
                "label": folio_graph[sub_class].label,
                "description": format_description(folio_graph[sub_class]),
                "color": "#000000",
                "relationship": "sub_class_of",
            }
            edges.append(
                {"source": sub_class, "target": owl_class.iri, "type": "sub_class_of"}
            )

    # add parent_class_of children
    for parent_class in owl_class.parent_class_of:
        if folio_graph[parent_class]:
            nodes[parent_class] = {
                "id": parent_class,
                "label": folio_graph[parent_class].label,
                "description": format_description(folio_graph[parent_class]),
                "color": "#000000",
                "relationship": "parent_class_of",
            }
            edges.append(
                {
                    "source": owl_class.iri,
                    "target": parent_class,
                    "type": "parent_class_of",
                }
            )

    # add see_also
    for see_also in owl_class.see_also:
        if folio_graph[see_also]:
            nodes[see_also] = {
                "id": see_also,
                "label": folio_graph[see_also].label,
                "description": format_description(folio_graph[see_also]),
                "color": "#000000",
                "relationship": "see_also",
            }
            edges.append(
                {"source": owl_class.iri, "target": see_also, "type": "see_also"}
            )

    # add is_defined_by
    if owl_class.is_defined_by:
        if folio_graph[owl_class.is_defined_by]:
            nodes[owl_class.is_defined_by] = {
                "id": owl_class.is_defined_by,
                "label": folio_graph[owl_class.is_defined_by].label,
                "description": format_description(folio_graph[owl_class.is_defined_by]),
                "color": "#000000",
                "relationship": "is_defined_by",
            }
            edges.append(
                {
                    "source": owl_class.iri,
                    "target": owl_class.is_defined_by,
                    "type": "is_defined_by",
                }
            )

    return list(nodes.values()), edges


def render_tailwind_html(owl_class: OWLClass, folio_graph: FOLIO, config: dict = None) -> str:
    """
    Render a complete HTML document with the class information
    in a user-friendly format using Tailwind CSS.

    Args:
        owl_class (OWLClass): FOLIO OWLClass object
        folio_graph (FOLIO): FOLIO graph object

    Returns:
        str: HTML document as a string
    """
    # get graph data
    nodes, edges = get_node_neighbors(owl_class, folio_graph)
    node_js = f"var nodes = {json.dumps(nodes)};"
    edge_js = f"var edges = {json.dumps(edges)};"

    # HTML template
    return f"""
<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{format_label(owl_class)} - FOLIO Ontology</title>
        <script src="https://cdn.tailwindcss.com?plugins=forms,typography,aspect-ratio"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.7.1/jquery.min.js" integrity="sha512-v2CJ7UaYy4JwqLDIrZUI/4hqeoQieOmAZNXBeQyjo21dadnwR+8ZaIJVT8EE2iyI61OV8e6M8PP2/4hpQINQ/g==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/typeahead.js/0.11.1/typeahead.bundle.min.js" integrity="sha512-qOBWNAMfkz+vXXgbh0Wz7qYSLZp6c14R0bZeVX2TdQxWpuKr6yHjBIM69fcF8Ve4GUX6B6AKRQJqiiAmwvmUmQ==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.31.2/cytoscape.min.js" integrity="sha512-Rjwq+hpL29wg7pieBf5SnXryZHHVSPZ75BtfgoBQJWvFOeh2j34AmAObOri1S51J1MdrW/gesC1kBejhOzvU6Q==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/dagre/0.8.5/dagre.min.js" integrity="sha512-psLUZfcgPmi012lcpVHkWoOqyztollwCGu4w/mXijFMK/YcdUdP06voJNVOJ7f/dUIlO2tGlDLuypRyXX2lcvQ==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/popper.js/2.11.8/umd/popper.min.js" integrity="sha512-TPh2Oxlg1zp+kz3nFA0C5vVC6leG/6mm1z9+mA81MI5eaUVqasPLO8Cuk4gMF4gUfP5etR73rgU/8PNMsSesoQ==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/tippy.js/6.3.7/tippy.umd.min.js" integrity="sha512-2TtfktSlvvPzopzBA49C+MX6sdc7ykHGbBQUTH8Vk78YpkXVD5r6vrNU+nOmhhl1MyTWdVfxXdZfyFsvBvOllw==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
        <meta name="description" content="{format_description(owl_class)}">
        <meta name="author" content="FOLIO - The Federated Open Legal Information Ontology">
        <meta name="keywords" content="legal, ontology, standard, open, information, {format_label(owl_class)}">
        <meta name="robots" content="index, follow">
        <meta property="og:title" content="{format_label(owl_class)} - FOLIO Ontology">
        <meta property="og:description" content="{format_description(owl_class)}">
        <meta property="og:type" content="website">
        <meta property="og:url" content="{owl_class.iri}">
        <meta property="og:image" content="https://openlegalstandard.org/_astro/soli-2x1-accent.DYUFAzgH_1CFhgX.webp">
        <meta property="og:image:alt" content="FOLIO Logo">
        <meta property="og:image:width" content="400">
        <meta property="og:site_name" content="FOLIO - The Federated Open Legal Information Ontology">
        <style type="text/css">
            @import url('https://fonts.googleapis.com/css2?family=Public+Sans:ital,wght@0,100..900;1,100..900&display=swap');
            :root {{
                --font-sans: 'Public Sans Variable';
                --font-serif: 'Public Sans Variable';
                --font-heading: 'Public Sans Variable';
                --color-primary: rgb(24 70 120);
                --color-secondary: rgb(134, 147, 171);
                --color-accent: rgb(234, 82, 111);
                --color-text-heading: rgb(0 0 0);
                --color-text-default: rgb(16 16 16);
                --color-text-muted: rgb(16 16 16 / 66%);
                --color-bg-page: rgb(255 255 255);
                --color-bg-page-dark: rgb(12 35 60);
            }}

            .dark {{
                --color-primary: rgb(24 70 120);
                --color-secondary: rgb(134 147 171);
                --color-accent: rgb(234 82 111);
                --color-text-heading: rgb(247 248 248);
                --color-text-default: rgb(229 236 246);
                --color-text-muted: rgba(229, 236, 246, 0.66);
                --color-bg-page: rgb(12 35 60);
            }}
            .dark ::selection {{
                background-color: black;
                color: snow;
            }}

            .twitter-typeahead {{
                width: 100%;
            }}
            .tt-menu {{
                width: 100%;
                margin-top: 0.5rem;
                background-color: white;
                border: 1px solid var(--color-secondary);
                border-radius: 0.5rem;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            }}
            .tt-suggestion {{
                padding: 0.75rem 1rem;
                cursor: pointer;
            }}
            .tt-suggestion:hover, .tt-suggestion.tt-cursor {{
                background-color: rgba(24, 70, 120, 0.1);
            }}
        </style>
    </head>
    <body class="font-['Public_Sans'] bg-gray-100 min-h-screen">
        <header class="bg-[--color-primary] py-6 text-white">
            <div class="container mx-auto px-4">
                <div class="flex justify-between items-start">
                    <div>
                        <h1 class="text-3xl font-bold mb-2">{format_label(owl_class)}</h1>
                        <p class="text-xl text-white opacity-80">{format_description(owl_class)}</p>
                    </div>
                    <div class="hidden md:block">
                        <a href="https://openlegalstandard.org/" target="_blank" class="inline-block bg-white text-[--color-primary] font-semibold px-4 py-2 rounded hover:bg-opacity-90 transition-colors duration-200 mr-2">FOLIO Website</a>
                        <a href="https://openlegalstandard.org/education/" target="_blank" class="inline-block bg-transparent text-white border border-white font-semibold px-4 py-2 rounded hover:bg-white hover:bg-opacity-10 transition-colors duration-200">Learn More</a>
                    </div>
                </div>
                
                <div class="mt-6 max-w-3xl">
                    <div class="relative">
                        <input id="search-input" type="text" placeholder="Search for FOLIO classes..." class="w-full p-3 rounded-lg border border-white focus:outline-none focus:ring-2 focus:ring-white focus:ring-opacity-50 text-gray-800">
                        <div id="search-results" class="absolute top-14 left-0 w-full bg-white dark:bg-[--color-bg-page] shadow-lg rounded-lg overflow-hidden mt-2 border border-[--color-secondary] border-opacity-20"></div>
                    </div>
                </div>
            </div>
        </header>
        
        <div class="bg-white border-b">
            <div class="container mx-auto px-4 py-4">
                <div class="flex flex-wrap gap-2">
                    <a href="{owl_class.iri}" class="bg-[--color-primary] hover:bg-[--color-accent] text-white font-semibold py-2 px-4 rounded transition-colors duration-200">JSON</a>
                    <a href="{owl_class.iri}/jsonld" class="bg-[--color-primary] hover:bg-[--color-accent] text-white font-semibold py-2 px-4 rounded transition-colors duration-200">JSON-LD</a>
                    <a href="{owl_class.iri}/xml" class="bg-[--color-primary] hover:bg-[--color-accent] text-white font-semibold py-2 px-4 rounded transition-colors duration-200">OWL XML</a>
                    <a href="{owl_class.iri}/markdown" class="bg-[--color-primary] hover:bg-[--color-accent] text-white font-semibold py-2 px-4 rounded transition-colors duration-200">Markdown</a>
                    <a href="/taxonomy/browse" class="bg-white hover:bg-gray-100 text-gray-800 font-semibold py-2 px-4 rounded border border-gray-300 transition-colors duration-200">← Back to Browse</a>
                </div>
            </div>
        </div>
        
        <main class="container mx-auto px-4 py-8">
            <div class="max-w-4xl mx-auto space-y-6">
                <!-- Identification -->
                <section class="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow">
                    <h3 class="text-xl font-semibold mb-4 text-[--color-primary]">Identification</h3>
                    <div class="space-y-4">
                        <div>
                            <p class="text-gray-500 text-sm mb-1">IRI <button onclick="copyIRI()" class="copy-button py-1 px-2 rounded text-sm">📋</button></p>
                            <p id="iri-value" class="truncate font-mono text-sm" title="{owl_class.iri}">{owl_class.iri}</p>
                        </div>
                        
                        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div>
                                <p class="text-gray-500 text-sm mb-1">Label</p>
                                <p class="font-medium">{owl_class.label or "N/A"}</p>
                            </div>
                            
                            <div>
                                <p class="text-gray-500 text-sm mb-1">Preferred Label</p>
                                <p>{owl_class.preferred_label or "N/A"}</p>
                            </div>
                            
                            <div>
                                <p class="text-gray-500 text-sm mb-1">Identifier</p>
                                <p>{owl_class.identifier or "N/A"}</p>
                            </div>
                        </div>
                        
                        <div>
                            <p class="text-gray-500 text-sm mb-1">Alternative Labels</p>
                            <p>{", ".join(owl_class.alternative_labels) or "None"}</p>
                        </div>
                    </div>
                </section>
                
                <!-- Definition and Examples -->
                <section class="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow">
                    <h3 class="text-xl font-semibold mb-4 text-[--color-primary]">Definition</h3>
                    <p class="text-gray-700 mb-6">{owl_class.definition or "No definition available."}</p>
                    
                    {f"""
                    <h4 class="text-lg font-medium mb-3 text-[--color-primary]">Examples</h4>
                    <ul class="list-disc pl-5 space-y-2 mb-4">
                        {"\n".join([f"<li>{example}</li>" for example in owl_class.examples])}
                    </ul>
                    """ if owl_class.examples else ""}
                </section>
                
                <!-- Class Relationships -->
                <section class="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow">
                    <h3 class="text-xl font-semibold mb-4 text-[--color-primary]">Class Relationships</h3>
                    
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                            <p class="text-gray-500 text-sm mb-2">Sub Class Of</p>
                            <ul class="list-disc pl-5 space-y-1">
                                {"\n".join(f"""<li><a class="text-blue-500 hover:text-blue-700 hover:underline" href="{sub_class}/html">{folio_graph[sub_class].label}</a></li>""" for sub_class in owl_class.sub_class_of if folio_graph[sub_class]) or "<li>None</li>"}
                            </ul>
                        </div>
                        
                        <div>
                            <p class="text-gray-500 text-sm mb-2">Is Defined By</p>
                            <p>{owl_class.is_defined_by or "N/A"}</p>
                            
                            <p class="text-gray-500 text-sm mt-4 mb-2">See Also</p>
                            <p>{", ".join(owl_class.see_also) or "None"}</p>
                        </div>
                    </div>
                    
                    <div class="mt-6">
                        <p class="text-gray-500 text-sm mb-2">Parent Class Of ({len(owl_class.parent_class_of) if hasattr(owl_class, 'parent_class_of') else 0})</p>
                        <div class="max-h-60 overflow-y-auto border border-gray-200 rounded p-2 bg-gray-50">
                            <ul class="list-disc pl-5 space-y-1">
                                {"\n".join(f"""<li><a class="text-blue-500 hover:text-blue-700 hover:underline" href="{parent_class}/html">{folio_graph[parent_class].label}</a></li>""" for parent_class in owl_class.parent_class_of if folio_graph[parent_class]) or "<li>None</li>"}
                            </ul>
                        </div>
                    </div>
                </section>
                
                <!-- Translations -->
                {f"""
                <section class="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow">
                    <h3 class="text-xl font-semibold mb-4 text-[--color-primary]">Translations</h3>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {"\n".join([f"""
                        <div class="border-b pb-2">
                            <p class="text-gray-500 text-sm font-medium">{language}</p>
                            <p class="mt-1">{translation}</p>
                        </div>
                        """ for language, translation in owl_class.translations.items()])}
                    </div>
                </section>
                """ if owl_class.translations else ""}
                
                <!-- Graph Visualization -->
                <section class="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow">
                    <h3 class="text-xl font-semibold mb-4 text-[--color-primary]">
                        Class Hierarchy Visualization
                        <span class="text-sm font-normal text-gray-500 ml-2">Interactive class hierarchy powered by Cytoscape</span>
                    </h3>
                    <div id="hierarchy-container" class="h-96 w-full border border-gray-200 rounded-lg relative"></div>
                </section>
                
                <!-- Additional Information -->
                <section class="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow">
                    <h3 class="text-xl font-semibold mb-4 text-[--color-primary]">Additional Information</h3>
                    
                    <div class="space-y-6">
                        <div>
                            <h4 class="text-lg font-medium mb-2 text-[--color-primary]">Metadata</h4>
                            <div class="space-y-3">
                                <div>
                                    <p class="text-gray-500 text-sm">Comment</p>
                                    <p>{owl_class.comment or "None"}</p>
                                </div>
                                <div>
                                    <p class="text-gray-500 text-sm">Description</p>
                                    <p>{owl_class.description or "None"}</p>
                                </div>
                                <div>
                                    <p class="text-gray-500 text-sm">Notes</p>
                                    <ul class="list-disc pl-5">
                                        {"\n".join([f"<li>{note}</li>" for note in owl_class.notes]) or "<li>None</li>"}
                                    </ul>
                                </div>
                            </div>
                        </div>
                        
                        <div>
                            <h4 class="text-lg font-medium mb-2 text-[--color-primary]">Editorial Information</h4>
                            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <div>
                                    <p class="text-gray-500 text-sm">History Note</p>
                                    <p>{owl_class.history_note or "None"}</p>
                                </div>
                                <div>
                                    <p class="text-gray-500 text-sm">Editorial Note</p>
                                    <p>{owl_class.editorial_note or "None"}</p>
                                </div>
                                <div>
                                    <p class="text-gray-500 text-sm">Deprecated</p>
                                    <p>{str(owl_class.deprecated)}</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>
            </div>
        </main>
        
        <footer class="bg-[--color-primary] text-white py-8 mt-8">
            <div class="container mx-auto px-4 text-center">
                <a href="https://openlegalstandard.org/" target="_blank"><img src="https://openlegalstandard.org/_astro/soli-2x1-accent.DYUFAzgH_1CFhgX.webp" alt="FOLIO Logo" class="w-16 mx-auto mt-4"></a>
                <p>The FOLIO ontology is licensed under the CC-BY 4.0 license.</p>
                <p>Any FOLIO software is licensed under the MIT license.</p>
                
                <div class="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4 max-w-3xl mx-auto">
                    <div class="text-left">
                        <h3 class="font-bold text-lg mb-2">FOLIO Resources</h3>
                        <ul class="space-y-2">
                            <li><a href="https://openlegalstandard.org/" class="text-[--color-secondary] hover:text-white transition-colors duration-200">FOLIO Official Website</a></li>
                            <li><a href="https://openlegalstandard.org/education/" class="text-[--color-secondary] hover:text-white transition-colors duration-200">FOLIO Education</a></li>
                            <li><a href="https://openlegalstandard.org/resources/folio-python-library/" class="text-[--color-secondary] hover:text-white transition-colors duration-200">FOLIO Python Library</a></li>
                            <li><a href="https://github.com/alea-institute/folio-api" class="text-[--color-secondary] hover:text-white transition-colors duration-200">FOLIO API (GitHub)</a></li>
                        </ul>
                    </div>
                    <div class="text-left">
                        <h3 class="font-bold text-lg mb-2">About FOLIO</h3>
                        <p class="text-sm mb-2">FOLIO is an open standard for legal concepts and knowledge, designed to make legal information more accessible and interoperable.</p>
                        <p class="text-sm">Learn more about how FOLIO is being used to improve legal technology and access to justice by visiting the <a href="https://openlegalstandard.org/" class="text-[--color-secondary] hover:text-white transition-colors duration-200">Open Legal Standard website</a>.</p>
                    </div>
                </div>
                
                <p class="mt-4 text-small">Copyright &copy; 2024-2025. <a href="https://aleainstitute.ai/" target="_blank">The Institute for the Advancement of Legal and Ethical AI</a>.</p>
                <p class="mt-2 text-xs">FOLIO Version: <span class="font-mono">{config["folio"]["branch"] if config else "2.0.0"}</span> | Repository: <a href="https://github.com/{config["folio"]["repository"] if config else "alea-institute/folio"}" class="text-[--color-secondary] hover:text-white transition-colors duration-200">{config["folio"]["repository"] if config else "alea-institute/folio"}</a></p>
            </div>
        </footer>
        
        <script>
            {COPY_IRI_JS_SOURCE}
        </script>
        <script>
            {TYPEAHEAD_JS_SOURCE}
        </script>
        <script>
            {CYTOSCAPE_JS_SOURCE}

            {node_js}
            {edge_js}

            setupCytoscapeGraph("hierarchy-container", nodes, edges);
        </script>
    </body>
</html>
""".strip()
