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

D3_JS_SOURCE = (Path(__file__).parent / "d3_graph.js").read_text(encoding="utf-8")
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
        Tuple[List[Dict], List[Dict]]: Tuple with lists of sub-class and parent-class neighbors
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


def render_tailwind_html(owl_class: OWLClass, folio_graph: FOLIO) -> str:
    """
    Render a complete HTML document with the class information
    in a user-friendly format using Tailwind CSS.

    This is an abomination. Don't do this at home.

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

    # chad html
    return f"""
<!doctype html>
<html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.tailwindcss.com?plugins=forms,typography,aspect-ratio"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.7.1/jquery.min.js" integrity="sha512-v2CJ7UaYy4JwqLDIrZUI/4hqeoQieOmAZNXBeQyjo21dadnwR+8ZaIJVT8EE2iyI61OV8e6M8PP2/4hpQINQ/g==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/typeahead.js/0.11.1/typeahead.bundle.min.js" integrity="sha512-qOBWNAMfkz+vXXgbh0Wz7qYSLZp6c14R0bZeVX2TdQxWpuKr6yHjBIM69fcF8Ve4GUX6B6AKRQJqiiAmwvmUmQ==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js" integrity="sha512-vc58qvvBdrDR4etbxMdlTt4GBQk1qjvyORR2nrsPsFPyrs+/u5c3+1Ct6upOgdZoIl7eq6k3a1UPDSNAQi/32A==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
        <title>{format_label(owl_class)} - FOLIO Ontology</title>
        <meta name="description" content="{format_description(owl_class)}">
        <meta name="author" content="FOLIO - The Federated Open Legal Information Ontology">
        <meta name="keywords" content="legal, ontology, standard, open, information, {format_label(owl_class)}">
        <meta name="robots" content="index, follow">
        <meta property="og:title" content="{format_label(owl_class)} - FOLIO Ontology">
        <meta property="og:description" content="{format_description(owl_class)}">
        <meta property="og:type" content="website">
        <meta property="og:url" content="https://folio.openlegalstandard.org/{owl_class.iri}">
        <meta property="og:image" content="https://folio.openlegalstandard.org/images/folio_logo.png">
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
    <body class="font-['Public_Sans'] bg-white dark:bg-[--color-bg-page] ">
        <header class="bg-primary py-4 sm:py-8">
            <div class="container mx-auto px-4">
                <h1 class="text-2xl sm:text-4xl font-bold mb-2 text-[--color-primary]">{format_label(owl_class)}</h1>
                <p class="text-lg sm:text-xl text-[--color-text-muted]">{format_description(owl_class)}</p>
            </div>
            <div class="container mx-auto px-4 mt-4">
                <div class="relative">
                    <input id="search-input" type="text" placeholder="Search for FOLIO classes..." class="w-full p-2 rounded-lg border border-[--color-secondary] focus:outline-none focus:border-[--color-primary] focus:ring-2 focus:ring-[--color-primary] focus:ring-opacity-50">
                    <div id="search-results" class="absolute top-12 left-0 w-full bg-white dark:bg-[--color-bg-page] shadow-lg rounded-lg overflow-hidden mt-2 border border-[--color-secondary] border-opacity-20"></div>
                </div>
            </div>
        </header>
        <main class="container mx-auto px-4 py-8">
            <div class="bg-white dark:bg-[--color-bg-page] shadow-lg rounded-lg overflow-hidden">
                <div class="bg-[--color-primary] bg-opacity-20 px-6 py-4 border-b border-[--color-secondary] border-opacity-30">
                    <h2 class="text-2xl font-semibold text-white">Class Information</h2>
                    <div class="text-[--color-text-muted] text-sm mt-1 flex flex-wrap items-center gap-2">
                        <a href="{owl_class.iri}" class="bg-[--color-primary] hover:bg-[--color-accent] text-white font-semibold py-2 px-4 rounded-lg transition-colors duration-200">JSON</a>
                        <a href="{owl_class.iri}/jsonld" class="bg-[--color-primary] hover:bg-[--color-accent] text-white font-semibold py-2 px-4 rounded-lg transition-colors duration-200">JSON-LD</a>
                        <a href="{owl_class.iri}/xml" class="bg-[--color-primary] hover:bg-[--color-accent] text-white font-semibold py-2 px-4 rounded-lg transition-colors duration-200">OWL XML</a>
                        <a href="{owl_class.iri}/markdown" class="bg-[--color-primary] hover:bg-[--color-accent] text-white font-semibold py-2 px-4 rounded-lg transition-colors duration-200">Markdown</a>
                    </div>
                </div>

                <div class="p-6 grid gap-6">
                <!-- Identification -->
                <section class="bg-[--color-bg-page] bg-opacity-50 rounded-lg p-4 border border-[--color-secondary] border-opacity-20">
                <h3 class="text-lg font-semibold mb-3 text-[--color-primary]">Identification</h3>
                <dl class="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-2">
                <div>
                  <dt class="font-medium text-gray-500">IRI <button onclick="copyIRI()" class="py-1 px-2 rounded text-sm">📋</button></dt>
                  <dd class="mt-1 flex items-center">
                    <a href="{owl_class.iri}" class="mr-2">{owl_class.iri}</a>

                  </dd>
                </div>
                <div>
                <dt class="font-medium text-[--color-text-muted]">Label (rdfs)</dt>
                <dd class="mt-1">{owl_class.label}</dd>
                </div>
                <div>
                <dt class="font-medium text-[--color-text-muted]">Preferred Label</dt>
                <dd class="mt-1">{owl_class.preferred_label}</dd>
                </div>
                <div>
                <dt class="font-medium text-[--color-text-muted]">Alternative Labels</dt>
                <dd class="mt-1">{", ".join(owl_class.alternative_labels) or "N/A"}</dd>
                </div>
                <div>
                <dt class="font-medium text-[--color-text-muted]">Identifier</dt>
                <dd class="mt-1">{owl_class.identifier or "N/A"}</dd>
                </div>
                </dl>
                </section>

                <!-- Definition and Examples -->
                <section class="bg-[--color-bg-page] bg-opacity-50 rounded-lg p-4 border border-[--color-secondary] border-opacity-20">
                <h3 class="text-lg font-semibold mb-3 text-[--color-primary]">Definition and Examples</h3>
                <dl class="grid gap-y-2">
                <div>
                <dt class="font-medium text-[--color-text-muted]">Definition</dt>
                <dd class="mt-1">{owl_class.definition or "N/A"}</dd>
                </div>
                <div>
                <dt class="font-medium text-[--color-text-muted]">Examples</dt>
                <dd class="mt-1">
                <ul class="list-disc pl-5">
                {"\n".join([f"<li>{example}</li>" for example in owl_class.examples]) or "<li>N/A</li>"}
                </ul>
                </dd>
                </div>
                </dl>
                </section>

                <!-- Translations -->
                <section class="bg-[--color-bg-page] bg-opacity-50 rounded-lg p-4 border border-[--color-secondary] border-opacity-20">
                <h3 class="text-lg font-semibold mb-3 text-[--color-primary]">Translations</h3>
                <!-- div table version -->
                <!-- language and translation side by side with grid spacing -->
                <div class="grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-2">
                {"\n".join([f"""<div><dt class="font-medium text-[--color-text-muted]">{language}</dt><dd class="mt-1">{translation}</dd></div>""" for language, translation in owl_class.translations.items()]) or "<div><dt class='font-medium text-[--color-text-muted]'>N/A</dt></div>"}
                </div>
                </section>

                <!-- Class Relationships -->
                <section class="bg-[--color-bg-page] bg-opacity-50 rounded-lg p-4 border border-[--color-secondary] border-opacity-20">
                <h3 class="text-lg font-semibold mb-3 text-[--color-primary]">Class Relationships</h3>
                <dl class="grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-2">
                <div>
                <dt class="font-medium text-[--color-text-muted]">Sub Class Of</dt>
                <dd class="mt-1"><ul>
                {"\n".join(f"""<li><a class="underline underline-offset-4 hover:text-primary" href="{sub_class}/html">{folio_graph[sub_class].label}</a></li>""" for sub_class in owl_class.sub_class_of if folio_graph[sub_class]) or "<li>N/A</li>"}
                </ul></dd>
                </div>
                <div>
                <dt class="font-medium text-[--color-text-muted]">Parent Class Of</dt>
                <dd class="mt-1"><ul>
                {"\n".join(f"""<li><a class="underline underline-offset-4 hover:text-primary" href="{parent_class}/html">{folio_graph[parent_class].label}</a></li>""" for parent_class in owl_class.parent_class_of if folio_graph[parent_class]) or "<li>N/A</li>"}
                </ul></dd>
                </div>
                <div>
                <dt class="font-medium text-[--color-text-muted]">Is Defined By</dt>
                <dd class="mt-1">{owl_class.is_defined_by or "N/A"}</dd>
                </div>
                <div>
                <dt class="font-medium text-[--color-text-muted]">See Also</dt>
                <dd class="mt-1">{", ".join(owl_class.see_also) or "N/A"}</dd>
                </div>
                </dl>
                </section>

                <!-- Additional Information -->
                <section class="bg-[--color-bg-page] bg-opacity-50 rounded-lg p-4 border border-[--color-secondary] border-opacity-20">
                <h3 class="text-lg font-semibold mb-3 text-[--color-primary]">Additional Information</h3>
                <dl class="grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-2">
                <div>
                <dt class="font-medium text-[--color-text-muted]">Comment</dt>
                <dd class="mt-1">{owl_class.comment or "N/A"}</dd>
                </div>
                <div>
                <dt class="font-medium text-[--color-text-muted]">Description</dt>
                <dd class="mt-1">{owl_class.description or "N/A"}</dd>
                </div>
                <div>
                <dt class="font-medium text-[--color-text-muted]">Notes</dt>
                <dd class="mt-1">
                <ul class="list-disc pl-5">
                {"\n".join([f"<li>{note}</li>" for note in owl_class.notes]) or "<li>N/A</li>"}
                </ul>
                </dd>
                </div>
                <div>
                <dt class="font-medium text-[--color-text-muted]">Deprecated</dt>
                <dd class="mt-1">{str(owl_class.deprecated)}</dd>
                </div>
                </dl>
                </section>

                <!-- Metadata -->
                <section class="bg-[--color-bg-page] bg-opacity-50 rounded-lg p-4 border border-[--color-secondary] border-opacity-20">
                <h3 class="text-lg font-semibold mb-3 text-[--color-primary]">Metadata</h3>
                <dl class="grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-2">
                <div>
                <dt class="font-medium text-[--color-text-muted]">History Note</dt>
                <dd class="mt-1">{owl_class.history_note or "N/A"}</dd>
                </div>
                <div>
                <dt class="font-medium text-[--color-text-muted]">Editorial Note</dt>
                <dd class="mt-1">{owl_class.editorial_note or "N/A"}</dd>
                </div>
                <div>
                <dt class="font-medium text-[--color-text-muted]">In Scheme</dt>
                <dd class="mt-1">{owl_class.in_scheme or "N/A"}</dd>
                </div>
                <div>
                <dt class="font-medium text-[--color-text-muted]">Source</dt>
                <dd class="mt-1">{owl_class.source or "N/A"}</dd>
                </div>
                <div>
                <dt class="font-medium text-[--color-text-muted]">Country</dt>
                <dd class="mt-1">{owl_class.country or "N/A"}</dd>
                </div>
                </dl>
                </section>

                <!-- Graph -->
                <section class="bg-[--color-bg-page] bg-opacity-50 rounded-lg p-4 border border-[--color-secondary] border-opacity-20">
                <h3 class="text-lg font-semibold mb-3 text-[--color-primary]">Graph</h3>
                <div id="graph-container" class="h-96 w-full"></div>
                </section>
                </div>
            </div>
        </main>
        <footer class="bg-[--color-primary] text-white py-8 mt-8">
            <div class="container mx-auto px-4 text-center">
                <a href="https://openlegalstandard.org/" target="_blank"><img src="https://openlegalstandard.org/_astro/soli-2x1-accent.B8_1Hd3M_NsFb5.webp" alt="FOLIO Logo" class="w-16 mx-auto mt-4"></a>
                <p>The FOLIO ontology is licensed under the CC-BY 4.0 license.</p>
                <p>Any FOLIO software is licensed under the MIT license.</p>
                <div class="mt-1">
                    <p>View the source code for this API <a href="https://github.com/alea-institute/folio-api" class="text-[--color-secondary] hover:text-white transition-colors duration-200">on GitHub</a>.</p>
                </div>
                <p class="mt-1 text-small">Copyright &copy; 2024. <a href="https://aleainstitute.ai/" target="_blank">The Institute for the Advancement of Legal and Ethical AI</a>.</p>
            </div>
        </footer>
        <script>
            {COPY_IRI_JS_SOURCE}
        </script>
        <script>
            {TYPEAHEAD_JS_SOURCE}
        </script>
        <script>
            {D3_JS_SOURCE}

            {node_js}
            {edge_js}

            setup_graph("graph-container", nodes, edges, 600, 400);
        </script>
    </body>
</html>
""".strip()
