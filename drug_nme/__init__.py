from .fetch import *
from .scrape import *
from .plot import *
from .target import *

"""
Author: Tony E. Lin

Pull information from OpenFDA or GuidetoPharmacology
"""

import importlib

__version__ = "0.1.2"

_submodules = ["target", "fetch", "plot", "scrape"]


# lazy import of modules
def __getattr__(name):
    if name in _submodules:
        return importlib.import_module(f"drug_nme.{name}")
    else:
        try:
            return globals()[name]
        except KeyError:
            raise AttributeError(f"Module 'drug_nme' has no attribute '{name}'")
