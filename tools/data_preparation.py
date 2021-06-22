"""
This module is to be used for data cleaning and preparation.
"""
import ast
import json
import string
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
RT_REVIEWS_PATH = "./data/rt.reviews.tsv"
RT_MOVIE_INFO = "./data/rt.movie_info.tsv"
BOM_GROSS = "./data/bom.movie_gross.csv"
IMDB_NAME_BASICS = "./data/imdb.name.basics.csv"
IMDB_TITLE_AKAS = "./data/imdb.title.akas.csv"
IMDB_TITLE_BASICS = "./data/imdb.title.basics.csv"
IMDB_TITLE_CREW = "./data/imdb.title.crew.csv"
IMDB_TITLE_PRINCIPALS = "./data/imdb.title.principals.csv"
IMDB_TITLE_RATINGS = "./data/imdb.title.ratings.csv"
TMDB_MOVIES = "./data/tmdb.movies.csv"
TN_BUDGETS = "./data/tn.movie_budgets.csv"

TMDB_GENRE_IDS = './data/tmdb_genre_ids.json'


#
# MISCELLANEOUS HELPER FUNCTIONS
#


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


def minutes_to_num(val):
    """Cast runtime minutes string as a numeric value"""
    if isinstance(val, str):
        return eval(val.replace('minutes', '').strip())


def dollars_to_num(val):
    """Cast formatted dollar amount string as a numeric value"""
    if isinstance(val, str):
        return eval(val.replace('$', '').replace(',', ''))


def remove_punctuation(text):
    """Remove punctuation from a string"""
    for char in string.punctuation:
        text = text.replace(char, '')
    return text.replace(' ', '').lower().strip()


#
# ROTTEN TOMATOES CLEANING AND MERGING FUNCTIONS
#

def clean_rt_reviews(path=RT_REVIEWS_PATH, na_action=None):
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


def clean_rt_movie_info(path=RT_MOVIE_INFO, dropna=False, subset=None):
    """Clean Rotten Tomatoes movie info dataset"""
    # Initialize info_df DataFrame object
    info_df = pd.read_csv(path, delimiter='\t')

    # Drop duplicates if they exist
    if info_df.duplicated().sum():
        info_df.drop_duplicates(inplace=True)

    # Drop unnecessary columns
    info_df.drop(['director', 'writer', 'currency', 'box_office', 'studio'], axis=1, inplace=True)

    # Fill NaN 'genre' values and create tuples of genre categories for each movie
    info_df['genre'].fillna('Not listed', inplace=True)
    info_df['genre'] = info_df['genre'].map(lambda x: tuple(x.split('|')))

    # Change date strings to pd.datetime objects
    date_cols = ['theater_date', 'dvd_date']
    info_df[date_cols] = info_df[date_cols].apply(pd.to_datetime, axis=1)

    # Format 'runtime' column and cast as integer
    info_df['runtime'] = info_df['runtime'].map(minutes_to_num, na_action='ignore')

    # Drop rows with NaN values in subset columns. If not specified, then all columns considered
    if dropna:
        info_df.dropna(subset=subset, inplace=True)

    return info_df


def merge_rt_data(focus=None):
    """Return inner-joined DataFrame, or a feature-engineered subset of it with the focus parameter"""
    # Initialize DataFrames
    reviews_df = clean_rt_reviews()
    info_df = clean_rt_movie_info()

    # Initialize merged DataFrame
    rt_df = info_df.merge(reviews_df, on='id')

    # If genre_popularity is passed, then subset with 'genre' and 'fresh' columns, then explode on 'genre'
    if focus == 'genre_popularity':
        exploded = rt_df[['genre', 'fresh']].explode('genre', ignore_index=True)

        # Group by genre and aggregate 'fresh' with 'count', 'sum' and 'mean'
        grouped = exploded.groupby('genre')['fresh'].aggregate(['count', 'sum', 'mean'])

        # Rename columns: count -> 'total_references', sum -> 'total_positive', mean -> 'percent_positive'
        grouped.rename(columns={'count': 'total_references',
                                'sum': 'total_positive',
                                'mean': 'percent_positive'}, inplace=True)

        # Sort values by quantity of positive reviews
        rt_df = grouped.sort_values('total_positive', ascending=False)

    # Handle similarly for rating popularity
    elif focus == 'rating_popularity':
        grouped = rt_df[['rating', 'fresh']].groupby('rating')['fresh'].aggregate(['count', 'sum', 'mean'])
        grouped.rename(columns={'count': 'total_references',
                                'sum': 'total_positive',
                                'mean': 'percent_positive'}, inplace=True)

        rt_df = grouped.sort_values('total_positive', ascending=False)

    # Return unmodified DataFrame if 'focus' parameter is not passed
    return rt_df


#
# TN MOVIE BUDGET CLEANING FUNCTIONS
#


def clean_tn_budgets():
    """Return a clean DataFrame from The Numbers information on budget"""
    # Initialize DataFrame
    tn_df = pd.read_csv(TN_BUDGETS)

    # Cast date strings as pd.datetime objects
    tn_df['release_date'] = pd.to_datetime(tn_df['release_date'])

    # Cast dollar amount strings as integer amounts
    dollar_cols = ['production_budget', 'domestic_gross', 'worldwide_gross']
    for col in dollar_cols:
        tn_df[col] = tn_df[col].map(dollars_to_num)

    return tn_df


#
# BOX OFFICE MOJO CLEANING FUNCTIONS
#


def clean_bom_gross():
    """Return a clean DataFrame from Box Office Mojo dataset"""
    # Initialize DataFrame
    bom_df = pd.read_csv(BOM_GROSS)

    # Cast foreign_gross column as integers
    bom_df['foreign_gross'] = (bom_df['foreign_gross'].map(dollars_to_num, na_action='ignore'))

    return bom_df


#
# TMDB CLEANING FUNCTIONS
#


def tmdb_genre_dict():
    with open(TMDB_GENRE_IDS) as f:
        return {int(i): genre for i, genre in json.load(f).items()}


def clean_tmdb_movies():
    tmdb_movies_df = pd.read_csv(TMDB_MOVIES)
    tmdb_movies_df.drop('Unnamed: 0', axis=1, inplace=True)
    # tmdb_movies_df = tmdb_movies_df.loc[tmdb_movies_df['genre_ids'] != '[]']
    tmdb_movies_df['genre_ids'] = tmdb_movies_df['genre_ids'].map(ast.literal_eval)

    genre_dict = tmdb_genre_dict()
    exploded = tmdb_movies_df.explode('genre_ids')
    exploded['genre_ids'] = exploded['genre_ids'].map(genre_dict)

    return exploded


#
# IMDB CLEANING FUNCTIONS
#


def clean_imdb_name_basics():
    imdb_name_basics_df = pd.read_csv(IMDB_NAME_BASICS)

    return imdb_name_basics_df


def clean_imdb_title_akas():
    imdb_title_akas_df = pd.read_csv(IMDB_TITLE_AKAS)

    return imdb_title_akas_df


def clean_imdb_title_basics():
    # Initialize DataFrame
    title_basics_df = pd.read_csv(IMDB_TITLE_BASICS)

    # Remove punctuation and spaces from title names and make new column, 'cleaned_title'
    title_basics_df['cleaned_title'] = title_basics_df['primary_title'].map(remove_punctuation)

    return title_basics_df


def clean_imdb_title_crew():
    imdb_title_crew_df = pd.read_csv(IMDB_TITLE_CREW)

    return imdb_title_crew_df


def clean_imdb_title_principals():
    imdb_title_principals_df = pd.read_csv(IMDB_TITLE_PRINCIPALS)

    return imdb_title_principals_df


def clean_imdb_title_ratings():
    imdb_title_ratings_df = pd.read_csv(IMDB_TITLE_RATINGS)

    return imdb_title_ratings_df
