"""
Script to plot information from drug_nme pd.DataFrames
"""

import pandas as pd
import numpy as np

__all__ = ["Plot"]


class Plot:
    def __init__(self, df: pd.DataFrame = None, type_col: str = None):
        """
        Initialize the Plot object. Need to indicate where the source is from. Either from openFDA or from Guide to
        Pharmacology.

        :param df: pd.DataFrame
            Input pd.DataFrame containing drug approvals. The DataFrame must be obtained from the DataFetcher or Scrape
            classes.
        :param type_col: str
            The name of the column for processing. Name should match that of the existing column headers from the
            pd.DataFrame.
        """

        self.df = df
        self.source = type_col;

        # if type_col is None:
        #     raise ValueError("Data source must be 'fda' or 'pharmacology'!")

    def bar(self, df, source):
        pass
