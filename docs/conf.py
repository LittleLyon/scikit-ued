#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
from datetime import datetime

import alabaster

currentpath = os.path.dirname(__file__)
sys.path.append(os.path.join(currentpath, ".."))

from skued import __version__


# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#
needs_sphinx = "1.0"

year = datetime.now().year

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "alabaster",
    "sphinx.ext.todo",
    "sphinx.ext.intersphinx",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.mathjax",
    "sphinx.ext.autosummary",
    "matplotlib.sphinxext.plot_directive",
    "sphinx.ext.doctest",
]

intersphinx_mapping = {"numpy": ("http://docs.scipy.org/doc/numpy/", None)}

napoleon_google_docstring = False
autosummary_generate = True

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
# source_suffix = ['.rst', '.md']
source_suffix = ".rst"

# The master toctree document.
master_doc = "index"

# Releases changelog extension
releases_release_uri = "https://github.com/LaurentRDC/scikit-ued/tree/%s"
releases_issue_uri = "https://github.com/LaurentRDC/scikit-ued/issues/%s"

# General information about the project.
project = "scikit-ued"
copyright = "%d Laurent P. René de Cotret" % year
author = "Laurent P. René de Cotret"

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = __version__
# The full version, including alpha/beta/rc tags.
release = version

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = None

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This patterns also effect to html_static_path and html_extra_path
exclude_patterns = []
exclude_trees = ["_build"]

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "sphinx"

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = True


# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"
html_theme_path = ["_themes"]
html_sidebars = {"**": ["about.html", "navigation.html", "searchbox.html"]}

# Everything intersphinx's to Python.
_python_version_str = "{0.major}.{0.minor}".format(sys.version_info)
_python_doc_base = "https://docs.python.org/" + _python_version_str
intersphinx_mapping = {
    "python": (_python_doc_base, None),
}

# Autodoc settings
autodoc_default_flags = ["members"]
autoclass_content = "both"
autodoc_member_order = "groupwise"


def autodoc_skip_member(app, what, name, obj, skip, options):
    exclusions = {"__weakref__", "__doc__", "__module__", "__dict__"}
    exclude = name in exclusions
    return skip or exclude


def setup(app):
    app.connect("autodoc-skip-member", autodoc_skip_member)


# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = []

# Suppress the warning about a non-local URI for status shields.
suppress_warnings = ["image.nonlocal_uri"]

# Enable releases 'unstable prehistory' mode.
releases_unstable_prehistory = True
