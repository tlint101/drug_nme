"""
Script to plot information from drug_nme pd.DataFrames
"""

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from legendkit import legend

__all__ = ["Plot"]

# globally remove grid lines from plot
plt.rcParams['axes.grid'] = False


class Plot:
    def __init__(self, df: pd.DataFrame = None, sort_col: str or list = None):
        """
        Parameters to initialize the plots are optional. If given, the pd.DataFrame will be shaped and organized for
        plotting. The pd.DataFrame sources should come from either from openFDA or from Guide to Pharmacology.

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

    def show(self, head: int = None):
        """To view the processed pd.DataFrame given during initialization"""
        df = self.df
        if head:
            df = df.head(head)
        return pd.DataFrame(df)

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
        Generate bar plot. Ideally, the pd.DataFrame should be preprocessed upon initialization of Plot. However, it can
        be manually done if users prefer.

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

        # Add labels and padding
        image.set_xlabel(x, labelpad=15)
        image.set_ylabel(y, labelpad=15)

        if title:
            plt.title(title)

        # save fig
        if savepath:
            # adjust layout to prevent clipping
            plt.tight_layout()
            plt.savefig(savepath, dpi=300)
            plt.close()

        plt.tight_layout()
        plt.show()

        return image

    def stacked(self,
                data: pd.DataFrame = None,
                x: str = 'Year',
                y: str = 'Count',
                groups: str = 'type',
                title: str = None,
                label: bool = True,
                color_palette: str or list = None,
                fontsize: int = 8,
                fontcolor: str = 'black',
                legend_loc: str = None,
                figsize: tuple[float, float] = (10, 5),
                savepath: str = None
                ):
        """
        Generate stacked bar plot. Ideally, the pd.DataFrame should be preprocessed upon initialization of Plot. However, it can
        be manually done if users prefer.

        :param data: pd.DataFrame
            Input query pd.DataFrame. Should be processed. If not given, function will utilize the initialized processed
            pd.DataFrame.
        :param x: str
            The column header for the X-axis.
        :param y: str
            The column header for the Y-axis.
        :param groups: str
            The column header to set the hue.
        :param title: str
            Set the title of the plot.
        :param label: bool
            Determine annotations on the stacked bar chart.
        :param color_palette: str or list
            Set the color palette for the plot. Can be single palette name or a list of color names or hex codes.
        :param fontsize: int
            Set the fontsize for the annotations.
        :param fontcolor: str
            St the font color for the annotations.
        :param legend_loc: str
            Set the legend location for the plot.
        :param figsize: tuple
            Set the size of the figure.
        :param savepath: str
            Set the save location for the plot.
        """
        if data is None:
            data = self.df

        # Pivot the DataFrame to get types as columns and years as rows
        pivot_df = data.pivot_table(index=x, columns=groups, values=y, fill_value=0)

        # set color palette
        palette = sns.color_palette(color_palette)

        # Plot stacked bar plot
        image = pivot_df.plot(kind='bar', stacked=True, figsize=figsize, color=palette)

        # Add labels, padding and title
        image.set_xlabel('Year', labelpad=15)
        image.set_ylabel('Count', labelpad=15)
        image.set_title(title)

        if label is not False:
            # Add numbers on top of each bar segment
            for p in image.patches:
                height = p.get_height()
                if height > 0:  # Only add label if the height is greater than 0
                    image.text(
                        p.get_x() + p.get_width() / 2,  # x position in bar
                        p.get_y() + height / 2,  # y position in bar
                        int(height),
                        ha='center',  # horizontal alignment
                        va='center',  # vertical alignment
                        fontsize=fontsize,
                        color=fontcolor
                    )

        # replace plt legend with legendkit
        if legend_loc:
            image.legend_.remove()
            legend(loc=legend_loc)

        # save fig
        if savepath:
            # adjust layout to prevent clipping
            plt.tight_layout()
            plt.savefig(savepath, dpi=300)
            plt.close()

        plt.tight_layout()
        plt.show()

        return image

    def donut(self,
              data: pd.DataFrame = None,
              title: str = None,
              titlesize: int = 14,
              color_palette: str or list = None,
              pctdistance: int = 0.8,
              labeldistance: int = 1.1,
              fontsize: int = 10,
              annotsize: int = 10,
              annotcolor: str = 'black',
              legend_loc: str = None,
              figsize: tuple[float, float] = (10, 5),
              savepath: str = None
              ):
        """
        Generate a donut plot for drug approvals. Ideally, the pd.DataFrame should be preprocessed upon initialization
        of Plot. The preprocessed pd.DataFrame should then be filtered for the desire year before plotting.

        :param data: pd.DataFrame
            Input query pd.DataFrame. Should be processed. Function can only accept data that has been sliced by year.
        :param title: str
            Set the title of the plot.
        :param titlesize: int
            Set the titlesize for the plot.
        :param color_palette: str or list
            Set the color palette for the plot.
        :param pctdistance: int
            Set the position of the percentage labels.
        :param labeldistance: int
            Set the position of the category labels.
        :param fontsize: int
            Set the fontsize for the annotations.
        :param annotsize: int
            Set the annotation fontsize.
        :param annotcolor: str
            St the font color for the annotations.
        :param legend_loc: str
            Set the positions of the figure ligand.
        :param figsize: tuple
            Set the size of the figure.
        :param savepath: str
            Set the save location for the plot.
        """
        if data is None:
            data = self.df

        # Set Seaborn color palette
        color_palette = sns.color_palette(color_palette)

        plt.figure(figsize=figsize)

        # Plot the pie chart
        wedges, texts, autotexts = plt.pie(
            data['Count'],
            labels=data['type'],
            startangle=90,
            colors=color_palette,
            autopct=lambda pct: f"{int(pct / 100. * sum(data['Count']))}\n({pct:.1f}%)",
            wedgeprops=dict(width=0.4),  # Donut hole size
            textprops={'color': 'black'},
            pctdistance=pctdistance,
            labeldistance=labeldistance
        )

        for text in autotexts:
            text.set_fontsize(annotsize)
            text.set_color(annotcolor)

        # Draw a circle at the center of the plot
        image = plt.Circle((0, 0), 0.6, color='white')  # Smaller radius for a smaller hole
        plt.gca().add_artist(image)

        # Equal aspect ratio ensures that pie is drawn as a circle
        plt.axis('equal')

        if legend_loc:
            legend(loc=legend_loc)

        # set label font size
        plt.setp(texts, fontsize=fontsize)

        if title:
            plt.title(title, pad=15, fontsize=titlesize)

        if savepath:
            # adjust layout to prevent clipping
            plt.tight_layout()
            plt.savefig(savepath, dpi=300)
            plt.close()

        plt.tight_layout()
        plt.show()

        return image
