# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "NOEMA_Combine"
copyright = "2025, Jaime E. Pineda"
author = "Jaime E. Pineda"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "myst_parser",
    "sphinx.ext.autosectionlabel",
    "sphinx_copybutton",
]
autosectionlabel_prefix_document = True
# 'sphinx_toolbox.shields',
source_suffix = {
    ".rst": "restructuredtext",
    ".txt": "markdown",
    ".md": "markdown",
}

templates_path = ["_templates"]
exclude_patterns = ["requirements.txt"]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "alabaster"
html_static_path = ["_static"]

# Keep interactive prompts out of copied Python and shell examples.
copybutton_prompt_text = r"\$ |>>> |\.\.\. |In \[[0-9]+\]: |\.\.\.: "
copybutton_prompt_is_regexp = True
copybutton_remove_prompts = True
