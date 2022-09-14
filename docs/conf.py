# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import re
import sys

import toml

ON_RTD = os.environ.get("READTHEDOCS", None) == "True"

# so we have single source of project info
_pyproject = toml.load("../pyproject.toml")

# needed for local extensions
sys.path.insert(0, os.path.abspath("./_ext"))
# needed for autodoc
sys.path.insert(0, os.path.abspath(".."))


# -- Project information -----------------------------------------------------

project = _pyproject["tool"]["poetry"]["name"]
copyright = "2021, The Pybricks Authors"
author = _pyproject["tool"]["poetry"]["authors"][0]
release = f"v{_pyproject['tool']['poetry']['version']}"
version = re.match(r"(v\d+\.\d+)", release)[0]


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "availability_ext",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.todo",
    "sphinx_rtd_theme",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

nitpicky = True
nitpick_ignore = [
    # TODO: remove BT and USB after https://github.com/sphinx-doc/sphinx/commit/86091934db5ec593b4b0c982b7f08f3231ef995b is released
    ("py:class", "BT"),
    ("py:class", "USB"),
    ("py:class", "abc.ABC"),
    ("py:class", "bleak.backends.bluezdbus.client.BleakClientBlueZDBus"),
    ("py:class", "bleak.backends.device.BLEDevice"),
    ("py:exc", "asyncio.TimeoutError"),
    ("py:class", "bleak.BleakClient"),
    ("py:obj", "typing.Union"),
    ("py:class", "os.PathLike"),
    ("py:obj", "typing.BinaryIO"),
    ("py:class", "BinaryIO"),  # yes, we need both!
]

add_module_names = False

pygments_style = "xcode"


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
if ON_RTD:
    html_theme = "default"
else:
    html_theme = "sphinx_rtd_theme"


# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

html_css_files = [
    "css/custom.css",
]


# -- Options for Python domain -----------------------------------------------

python_use_unqualified_type_names = True


# -- Options for autodoc extension -------------------------------------------

autodoc_mock_imports = [
    "aioserial",
    "appdirs",
    "argcomplete",
    "asyncssh",
    "bleak",
    "mpy_cross_v5",
    "mpy_cross_v6",
    "packaging",
    "prompt_toolkit",
    "semver",
    "tqdm",
    "usb",
    "validators",
]
autoclass_content = "both"
