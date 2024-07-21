"""
Script to plot information from drug_nme pd.DataFrames
"""

import pandas as pd
import numpy as np

__all__ = ["Plot"]


class Plot:
    def __init__(self, df):
        self.df = df
