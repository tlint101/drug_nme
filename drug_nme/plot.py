"""
Script to plot information from drug_nme pd.DataFrames
"""

import pandas as pd
import numpy as np

__all__ = ["Plot"]


class Plot:
    def __init__(self, df: pd.DataFrame = None, source: str = None):
        """
        Initialize the Plot object. Need to indicate where the source is from. Either from openFDA or from Guide to
        Pharmacology.
        """
        self.df = df
        self.source = source

        if source is None:
            raise ValueError("Data source must be 'fda' or 'pharmacology'!")

    def bar(self, df, source):
        pass
