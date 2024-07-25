"""
Script to plot information from drug_nme pd.DataFrames
"""

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from legendkit import legend

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

    def bar(self,
            data: pd.DataFrame = None,
            x: str = 'Year',
            y: str = 'Count',
            hue: str = 'type',
            title: str = None,
            color_palette: str or list = None,
            legend_loc: str = None,
            figsize: tuple[float, float] = (10, 5),
            savepath: str = None):
        """
        :param data: pd.DataFrame
            Input query pd.DataFrame. Should be processed. If not given, function will utilize the initialized processed
            pd.DataFrame.
        :param x: str
            The column header for the X-axis.
        :param y: str
            The column header for the Y-axis.
        :param hue: str
            The column header to set the hue.
        :param title: str
            Set the title of the plot.
        :param color_palette: str or list
            Set the color palette for the plot. Can be single palette name or a list of color names or hex codes.
        :param legend_loc: str
            Set the legend location for the plot.
        :param figsize: tuple
            Set the size of the figure.
        :param savepath: str
            Set the save location for the plot.
        """

        if data is None:
            data = self.df

        plt.figure(figsize=figsize)

        if color_palette:
            sns.set_palette(color_palette)

        image = sns.barplot(x=x, y=y, hue=hue, data=data)

        # replace plt legend with legendkit
        image.legend_.remove()
        if legend_loc:
            legend(loc=legend_loc)

        if title:
            plt.title(title)

        # save fig
        if savepath:
            # adjust layout to prevent clipping
            plt.tight_layout()
            plt.savefig(savepath)
            plt.close()

        return image

    def stacked(self, df, source):
        pass
