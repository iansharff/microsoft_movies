"""
This module is to be used for data cleaning and preparation.

CONTENTS
I. imports and path constants
II. merging functions
III. single file cleaning functions
IV. miscellaneous helper functions
"""
import ast
import json
import string
import pandas as pd

# Define global constants for relative paths from microsoft_movies_directory
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

"""
II.
MERGING FUNCTIONS:
These functions merge DataFrames produced by the single file cleaning functions
1. merge_rt_data
2. merge_bom_and_imdb
3. merge_imdb_title_and_ratings
4. merge_imdb_top_crew
5. merge_tn_tmdb
"""


def merge_rt_data(focus=None, by='total_positive'):
    """Return inner-joined DataFrame, or a feature-engineered subset of it with the focus parameter"""
    # Initialize DataFrames
    reviews_df = clean_rt_reviews()
    info_df = clean_rt_movie_info()

    # Initialize merged DataFrame
    rt_df = info_df.merge(reviews_df, on='id')

    # If genre_popularity is passed, then subset with 'genre' and 'fresh' columns, then explode on 'genre'
    if focus == 'genre_popularity':
        exploded = rt_df[['genre', 'fresh']].explode('genre')

        # Group by genre and aggregate 'fresh' with 'count', 'sum' and 'mean'
        grouped = exploded.groupby('genre')['fresh'].aggregate(['count', 'sum', 'mean'])

        # Rename columns: count -> 'total_references', sum -> 'total_positive', mean -> 'percent_positive'
        grouped.rename(columns={'count': 'total_references',
                                'sum': 'total_positive',
                                'mean': 'percent_positive'}, inplace=True)

        # Sort values by quantity of positive reviews
        rt_df = grouped.sort_values(by=by, ascending=False)

    # Handle similarly for rating popularity
    elif focus == 'rating_popularity':
        grouped = rt_df[['rating', 'fresh']].groupby('rating')['fresh'].aggregate(['count', 'sum', 'mean'])
        grouped.rename(columns={'count': 'total_references',
                                'sum': 'total_positive',
                                'mean': 'percent_positive'}, inplace=True)

        rt_df = grouped.sort_values(by=by, ascending=False)

    # Return DataFrame suitable for plotting
    elif focus == 'combined_popularity':
        exploded = rt_df[['genre', 'rating', 'fresh']].explode('genre')
        grouped = exploded.groupby(['genre', 'rating'])['fresh'].aggregate(['count', 'sum', 'mean'])
        grouped.rename(columns={'count': 'total_references',
                                'sum': 'total_positive',
                                'mean': 'percent_positive'}, inplace=True)
        grouped.reset_index(inplace=True)
        # To sort ratings in sequential order, the column was made into a Categorical Series
        grouped['rating'] = pd.Categorical(grouped['rating'], ['G', 'PG', 'PG-13', 'R', 'NR'])
        rt_df = grouped.sort_values(['genre', 'rating'])
    # Return unmodified DataFrame if 'focus' parameter is not passed
    return rt_df


# Arthur and Mia
def merge_bom_and_imdb():
    """Merge the Box Office Mojo and IMDB title ratings and basics DataFrames"""
    # Initialize DataFrames
    bom_df = clean_bom_gross()
    basics_df = clean_imdb_title_basics()
    ratings_df = clean_imdb_title_ratings()

    # Perform first merge
    bom_titles_df = pd.merge(basics_df, bom_df, how='inner', on='cleaned_title')

    # Explode DataFrame on 'genres' column
    bom_titles_df['genres'] = bom_titles_df['genres'].str.strip().str.split(',')
    exploded = bom_titles_df.explode('genres')

    # Merge with ratings DataFrame
    combined = pd.merge(exploded, ratings_df, how='inner', on='tconst')

    # Subset and add 'avgrating_x_numvotes', 'total_gross' columns
    eval_exp1 = '''
    avgrating_x_numvotes = averagerating * numvotes
    total_gross = domestic_gross + foreign_gross
    '''
    subset = combined[['genres', 'numvotes', 'averagerating', 'domestic_gross', 'foreign_gross']].eval(eval_exp1)

    # Create columns of interest with named aggregation
    final_df = subset.groupby('genres').aggregate(numvotes=pd.NamedAgg('numvotes', 'sum'),
                                                  avgrating_x_numvotes=pd.NamedAgg('avgrating_x_numvotes', 'sum'),
                                                  avgnumvotes=pd.NamedAgg('numvotes', 'mean'),
                                                  domestic_gross=pd.NamedAgg('domestic_gross', 'mean'),
                                                  foreign_gross=pd.NamedAgg('foreign_gross', 'mean'),
                                                  total_gross=pd.NamedAgg('total_gross', 'mean'))

    # Add more columns for weighted average rating and scaled gross for plotting
    eval_exp2 = '''
    wavg_rating = avgrating_x_numvotes / numvotes
    total_gross_scaled = total_gross / 10 ** 5
    '''
    final_df.eval(eval_exp2, inplace=True)

    # Reset the index for easier control over plotting
    final_df.reset_index(inplace=True)

    return final_df


# Arthur
def merge_imdb_title_and_ratings():
    """Merge, clean and sort combined IMDB title and ratings DataFrame"""
    # Initialize DataFrames, exploding and not cleaning the titles of 'basics_df'
    basics_df = clean_imdb_title_basics(clean_titles=False, explode=True)
    ratings_df = clean_imdb_title_ratings()

    # Merge the DataFrames
    combined = pd.merge(basics_df, ratings_df, how='inner', on='tconst')

    # Create column for averagerating * numvotes and aggregate
    eval_exp1 = '''
    avgrating_x_numvotes = averagerating * numvotes
    '''
    subset = combined[['genres', 'numvotes', 'averagerating']].eval(eval_exp1)
    main_df = subset.groupby('genres').aggregate(numvotes=pd.NamedAgg('numvotes', 'sum'),
                                                 avgrating_x_numvotes=pd.NamedAgg('avgrating_x_numvotes', 'sum'),
                                                 avgnumvotes=pd.NamedAgg('numvotes', 'mean'))

    # Create column for weighted average rating
    eval_exp2 = '''
    wavg_rating = avgrating_x_numvotes / numvotes
    '''
    main_df.eval(eval_exp2, inplace=True)

    # Drop the 'Adult' genre row, which was a significant outlier that will not be part of the recommendation
    main_df.drop(index='Adult', inplace=True)

    # Reset the index and sort by 'numvotes' in descending order
    main_df.reset_index(inplace=True)
    main_df.sort_values('numvotes', ascending=False, inplace=True)

    return main_df


def merge_imdb_top_crew(select_genre=None, select_role=None):
    """
    Return a filtered dataframe containing the top choices for cast/producers for movies of a given genre

    @param select_genre: {'Drama', 'Action', 'Adventure', 'Comedy'}
    @param select_role: {'actor', 'actress', 'director', 'writer'}
    @return: pd.DataFrame
    """
    # Initialize DataFrames, exploding and not cleaning the titles of the title_basics file
    title_basics_df = clean_imdb_title_basics(clean_titles=False, explode=True)
    ratings_df = clean_imdb_title_ratings()
    principals_df = clean_imdb_title_principals()
    name_basics_df = clean_imdb_name_basics()

    # Filter genres not in the top four, determined from other data
    filtered_title_basics = title_basics_df[(title_basics_df['genres'] == 'Sci-Fi') |
                                            (title_basics_df['genres'] == 'Action') |
                                            (title_basics_df['genres'] == 'Adventure') |
                                            (title_basics_df['genres'] == 'Fantasy') |
                                            (title_basics_df['genres'] == 'Animation')]
    # Combine the four DataFrames by inner merge
    combined = pd.merge(filtered_title_basics, ratings_df, how='inner', on='tconst')
    combined = pd.merge(combined, principals_df, how='inner', on='tconst')
    combined = pd.merge(combined, name_basics_df, how='inner', on='nconst')

    # Filter by 'start_year' and only include actors, actresses, directors, and writers
    combined = combined[combined['start_year'] > 2014]
    combined = combined[(combined['category'] == 'actor') |
                        (combined['category'] == 'actress') |
                        (combined['category'] == 'director') |
                        (combined['category'] == 'writer')]

    # Keep rows where the number of votes is higher than the average
    final_df = combined[combined['numvotes'] > 100000]

    if select_genre:
        final_df = final_df[final_df['genres'] == select_genre]
        if select_role:
            final_df = final_df[final_df['category'] == select_role]

    return final_df.sort_values(['averagerating', 'numvotes'], ascending=(False, False))


# Eddie
# def merge_tn_imdb():
# """Merge The Numbers and TMDB datasets and return a clean DataFrame"""
# # Initialize DataFrames
# imdb_movies_df = clean_imdb_title_basics(explode=True)
# tmdb_df = clean_tmdb_movies()
# tn_df = clean_tn_budgets()
#
# # Merge DataFrames
# combined = pd.merge(imdb_movies_df, tn_df, how='inner', left_on='cleaned_title', right_on='movie')
#
# simplified = combined[['genres', 'production_budget', 'domestic_gross', 'worldwide_gross']]
# eval_exp = '''
# international_gross = worldwide_gross - domestic_gross
# net_gain = worldwide_gross - production_budget
# '''
# simplified.eval(eval_exp, inplace=True)
# final_df = simplified.groupby('genres').mean() / 10 ** 6
# final_df.sort_values('net_gain', ascending=False, inplace=True)
# return final_df
# return eddies_function()


"""
III.

SINGLE FILE CLEANING FUNCTIONS
These functions each clean one of the provided csv files, and one obtains genre ids from a .json file

1. clean_rt_reviews
2. clean_rt_movie_info
3. clean_tn_budgets
4. clean_bom_gross
5. clean_tmdb_movies
6. merge_tn_tmdb
7. clean_imdb_name_basics
8. clean_imdb_title_akas
9. clean_imdb_title_crew
10. clean_imdb_title_principals
11. clean_imdb_title_ratings
12. clean_imdb_title_basics
"""


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


def clean_bom_gross():
    """Return a clean DataFrame from Box Office Mojo dataset"""
    # Initialize DataFrame
    bom_df = pd.read_csv(BOM_GROSS)

    # Cast foreign_gross column as integers
    bom_df['foreign_gross'] = (bom_df['foreign_gross'].map(dollars_to_num, na_action='ignore'))

    # Fill NaN values
    bom_df['foreign_gross'].fillna(0, inplace=True)
    bom_df['domestic_gross'].fillna(0, inplace=True)

    # Remove punctuation and spaces from title names and make new column, 'cleaned_title'
    bom_df['cleaned_title'] = bom_df['title'].map(remove_punctuation)

    return bom_df


def tmdb_genre_dict():
    with open(TMDB_GENRE_IDS) as f:
        return {int(i): genre for i, genre in json.load(f).items()}


def clean_tmdb_movies():
    tmdb_movies_df = pd.read_csv(TMDB_MOVIES)
    tmdb_movies_df.drop('Unnamed: 0', axis=1, inplace=True)
    tmdb_movies_df['genre_ids'] = tmdb_movies_df['genre_ids'].map(ast.literal_eval)

    genre_dict = tmdb_genre_dict()
    exploded = tmdb_movies_df.explode('genre_ids')
    exploded['genre_ids'] = exploded['genre_ids'].map(genre_dict)

    return exploded


def clean_imdb_name_basics():
    """Read DataFrame from IMDB name basics file: already clean"""
    return pd.read_csv(IMDB_NAME_BASICS)


def clean_imdb_title_akas():
    """Read DataFrame from IMDB title akas file: already clean"""
    return pd.read_csv(IMDB_TITLE_AKAS)


def clean_imdb_title_crew():
    """Read DataFrame from IMDB title crew file: already clean"""
    return pd.read_csv(IMDB_TITLE_CREW)


def clean_imdb_title_principals():
    """Read DataFrame from IMDB title principles file: already clean"""
    return pd.read_csv(IMDB_TITLE_PRINCIPALS)


def clean_imdb_title_ratings():
    """Read DataFrame from IMDB title ratings file: already clean"""
    return pd.read_csv(IMDB_TITLE_RATINGS)


def clean_imdb_title_basics(clean_titles=True, explode=False):
    """ Return cleaned IMDB title basics DataFrame"""
    # Initialize DataFrame
    title_basics_df = pd.read_csv(IMDB_TITLE_BASICS)

    # Drop rows without genres
    title_basics_df.dropna(subset=['genres'], inplace=True)

    # Remove punctuation and spaces from title names and make new column, 'cleaned_title', if specified
    if clean_titles:
        title_basics_df['cleaned_title'] = title_basics_df['primary_title'].map(remove_punctuation)
    # Explode DataFrame on 'genres' column if specified
    if explode:
        title_basics_df['genres'] = title_basics_df['genres'].str.strip().str.split(',')
        title_basics_df = title_basics_df.explode('genres')

    return title_basics_df


"""
MISCELLANEOUS HELPER FUNCTIONS:

These were used for formatting and other general purposes in EDA. 
1. percent_nan
2. display_percent_nan
3. minutes_to_num
4. dollars_to_num
5. remove_punctuation
"""


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
    """Remove punctuation from a string and make lowercase"""
    for char in string.punctuation:
        text = text.replace(char, '')
    return text.strip().lower().replace(' ', '')
