"""
This module is to be used for data cleaning and preparation.
"""

import pandas as pd
import numpy as np

# Define test data for debugging
# n = np.NaN
# data = [[n, n, n, n, n],
#         [1, n, n, n, n],
#         [1, 1, n, n, n],
#         [1, 1, 1, n, n],
#         [1, 1, 1, 1, n]]
# test = pd.DataFrame(columns=['A', 'B', 'C', 'D', 'E'], data=data)


def percent_nan(df):
    """Return a Series of percent NaN values in each column of a DataFrame"""
    nulls = df.isnull().sum()
    length = len(df.index)
    return nulls / length if length != 0 else None

