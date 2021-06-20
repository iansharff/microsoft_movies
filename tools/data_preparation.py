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

# Define global constants for relative paths from within the tools package
RT_REVIEWS_PATH = "../data/rt.reviews.tsv"
RT_MOVIE_INFO = "../data/rt.movie_info.tsv"
BOM_GROSS = "../data/bom.movie_gross.csv"
IMDB_NAME_BASICS = "../data/imdb.name.basics.csv"
IMDB_TITLE_AKAS = "../data/imdb.title.akas.csv"
IMDB_TITLE_BASICS = "../data/imdb.title.basics.csv"
IMDB_TITLE_CREW = "../data/imdb.title.crew.csv"
IMDB_TITLE_PRINCIPALS = "../data/imdb.title.principals.csv"
IMDB_TITLE_RATINGS = "../data/imdb.title.ratings.csv"
TMDB_MOVIES = "../data/tmdb.movies.csv"
TN_BUDGETS = "../data/tn.movie_budgets.csv"


def percent_nan(df):
    """Return a Series of percent NaN values in each column of a DataFrame"""
    nulls = df.isnull().sum()
    length = len(df.index)
    return nulls / length if length != 0 else None


def display_percent_nan(df):
    """Display formatted percent-NaN-values for each column of a DataFrame"""
    series = percent_nan(df)
    for column in series.index:
        print(f"{column}: {100 * series.at[column]:.2f} % null")


def clean_rt_reviews(path, na_action=None):
    """Drop duplicate reviews, drop 'rating', 'publisher', and 'critic' columns, and cast to useful data types"""
    # Initialize pd.DataFrame object
    reviews_df = pd.read_csv(path, delimiter='\t', encoding='latin-1')

    # Drop duplicates and unnecessary columns
    reviews_df.drop_duplicates(inplace=True)
    reviews_df.drop(['rating', 'publisher', 'critic'], axis=1, inplace=True)

    # Cast dates as pd.datetime objects
    reviews_df['date'] = pd.to_datetime(reviews_df['date'])

    # Change 'fresh' column to 1 if fresh, 0 if rotten
    reviews_df['fresh'] = reviews_df['fresh'].map({'rotten': 0, 'fresh': 1})

    if na_action:
        # Fill NaN values in 'review' column with 'Empty', if specified
        if na_action == 'drop':
            reviews_df.dropna(subset=['review'], inplace=True)

        # Drop rows with NaN 'review' values, if specified
        if na_action == 'fill':
            reviews_df['review'].fillna('Empty', inplace=True)

    return reviews_df
