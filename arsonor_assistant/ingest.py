import os
import json
import pandas as pd

import minsearch


DATA_PATH = os.getenv("DATA_PATH", "../data/arsonor_chunks_id.json")


def load_index(data_path=DATA_PATH):
    with open(data_path, 'r', encoding='utf-8') as file:
        documents = json.load(file)

    index = minsearch.Index(
        text_fields=[
            'title', 
            'tags', 
            'chunk_text'
            ],
        keyword_fields=[
            'article_id', 
            'category', 
            'chunk_id'
            ]
    )

    index.fit(documents)
    return index