"""
Script to plot information from drug_nme pd.DataFrames
"""

import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

__all__ = ["Plot"]


class Plot:
    def __init__(self, df: pd.DataFrame = None, sort_col: str or list = None):
        """
        Parameters to initialize the plots are optional. If given, the pd.DataFrame will be shaped and organized for
        plotting. The pd.DataFrames should come from either from openFDA or from Guide to Pharmacology sources.

        :param df: pd.DataFrame
            Input pd.DataFrame containing drug approvals. The DataFrame must be obtained from the DataFetcher or Scrape
            classes.
        :param sort_col: str
            The name of the column for processing. Name should match that of the existing column headers from the
            pd.DataFrame.
        """
        # count values from the input pd.DataFrame
        count_df = df.groupby(sort_col).size().reset_index(name='Count')
        self.df = count_df

    def show(self):
        """To view the processed pd.DataFrame given during initialization"""
        return self.df

    def bar(self, data: pd.DataFrame = None, x='Year', y='Count', hue='type'):

        if data is None:
            data = self.df

        x = 'Year'
        y = 'Count'
        hue = 'type'
        sns.barplot(x='Year', y='Count', hue='type', data=data)

        plt.show()

    def stacked(self, df, source):
        pass
