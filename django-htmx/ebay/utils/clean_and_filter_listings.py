import pandas as pd
from .search import Search

def get_listings():
    s = Search().search()
    df = pd.DataFrame(s['itemSummaries'])
    df = df[['title', 'currentBidPrice', 'itemCreationDate']]
    return df

def get_titles(df):
    return df['title'].to_list()


# need to parse dates