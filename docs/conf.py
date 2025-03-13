# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "folio-api"
copyright = "2024-2025, ALEA Institute"
author = "Michael Bommarito"
release = "0.1.1"
master_doc = "index"
language = "en"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "myst_parser",
    "sphinxcontrib.mermaid",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# html_theme = 'alabaster'
html_theme = "sphinx_book_theme"
html_static_path = ["_static"]

html_theme_options = {
    # "announcement": "<p class='mystyle'>Some custom HTML!</p>",
    "use_sidenotes": True,
    "collapse_navbar": True,
    "show_navbar_depth": 2,
    "repository_url": "https://github.com/alea-institute/folio-api",
    "repository_branch": "main",
    "path_to_docs": "sphinx",
    "use_issues_button": True,
    "use_repository_button": True,
    "home_page_in_toc": True,
}
