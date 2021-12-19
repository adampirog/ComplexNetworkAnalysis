import ast
from itertools import combinations
import time

import arxiv
import pandas as pd
from tqdm.auto import tqdm
from unidecode import unidecode

columns = ["published", "title", "authors", "summary", "doi", "primary_category", "link", "pdf_url"]

def normalize_name(name):
    name = unidecode(name)
    split = name.split()

    new = split[0][0].upper()
    new += '. '
    new += split[-1].title()

    if new == 'P. Kazienkol':  # xd
        new = 'P. Kazienko'

    return new


def get_query(name):
    return "au:" + name.split()[-1].lower()


def prepare_names_df(filename):
    df = pd.read_csv(filename)
    df['name_normalized'] = df.name.apply(normalize_name)
    df['query_string'] = df.name_normalized.apply(get_query)

    return df


def parse_result(result):
    result = result.__dict__
    result = {k: v for k, v in result.items() if k in columns}

    result['authors'] = [normalize_name(item.name) for item in result['authors']]

    return result


def get_publications(queries):
    result = []
    for query in tqdm(queries):
        time.sleep(3)

        search = arxiv.Search(query=query)
        batch = []
        try:
            batch = [parse_result(item) for item in search.results()]
        except Exception:
            pass

        if len(batch) > 0:
            result += batch
    return result


def get_next_neighbours(df, valid_names):
    authors = df.authors.values.tolist()
    next_neighbours = []
    for item in authors:
        for author in item:
            if author not in valid_names:
                next_neighbours.append(author)
    return list(set(next_neighbours))


def has_valid_authors(authors, valid_names):
    for author in authors:
        if author in valid_names:
            return True
    return False

def clean_data(df):
    df.authors = df.authors.apply(ast.literal_eval)
    print(f"Initial length: {len(df)}")

    df = df[df.authors.apply(has_valid_authors)]
    print(f"Valid authors: {len(df)}")

    df.drop_duplicates(['pdf_url'], inplace=True)
    print(f"After duplicates: {len(df)}")

    df['no_authors'] = df.authors.apply(len)
    df = df[df.no_authors < 15]
    print(f"After coops: {len(df)}")

    df.reset_index(inplace=True, drop=True)


def to_graph(df):
    result = []
    for _, row in tqdm(df.iterrows(), total=len(df)):
        for source, target in combinations(row.authors, 2):
            new_row = row.copy()
            del new_row['authors']
            new_row['source'] = unidecode(source)
            new_row['target'] = unidecode(target)
            result.append(new_row)

    return pd.DataFrame(result)


def to_graph_alternative(df):
    result = []
    for index, row in tqdm(df.iterrows(), total=len(df)):
        for index2, row2 in df.iterrows():
            if index != index2:
                intersect = list(set(row.authors) & set(row2.authors))
                if intersect:
                    result.append([row.title, row2.title])

    return pd.DataFrame(result, columns=['source', 'target'])
