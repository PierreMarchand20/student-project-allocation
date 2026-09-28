import os
import sys

sys.path.insert(0, os.path.abspath(".."))

project = "student-project-allocation"
author = "Pierre Marchand"
extensions = ["sphinx.ext.autodoc", "sphinx.ext.mathjax"]
autodoc_member_order = "bysource"
