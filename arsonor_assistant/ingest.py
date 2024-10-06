import os
import json
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
from db import init_db

load_dotenv()

ELASTIC_URL = os.getenv("ELASTIC_URL_LOCAL")
INDEX_NAME = os.getenv("INDEX_NAME")
DATA_PATH = os.getenv("DATA_PATH", "../data/arsonor_chunks_300_50.json")

def fetch_documents(data_path=DATA_PATH):
    print("Fetching documents...")
    with open(data_path, 'r', encoding='utf-8') as file:
        documents = json.load(file)
    print(f"Fetched {len(documents)} documents")
    return documents


def setup_elasticsearch():
    print("Setting up Elasticsearch...")
    es_client = Elasticsearch(ELASTIC_URL)

    index_settings = {
        "settings": {"number_of_shards": 1, "number_of_replicas": 0},
        "mappings": {
            "properties": {
                "article_id": {"type": "keyword"},
                "title": {"type": "text"},
                "url": {"type": "keyword"},
                "category": {"type": "keyword"},
                "tags": {"type": "text"},
                "chunk_id": {"type": "keyword"},
                "chunk_text": {"type": "text"},
            }
        }
    }

    try:
        if es_client.indices.exists(index=INDEX_NAME):
            es_client.indices.delete(index=INDEX_NAME)
        es_client.indices.create(index=INDEX_NAME, body=index_settings)
        print(f"Elasticsearch index '{INDEX_NAME}' created successfully")
    except Exception as e:
        print(f"Error setting up Elasticsearch: {str(e)}")
        raise

    return es_client
    

def index_documents(es_client, documents):
    print("Indexing documents...")
    try:
        for doc in documents:
            es_client.index(index=INDEX_NAME, document=doc)
        print(f"Indexed {len(documents)} documents successfully")
    except Exception as e:
        print(f"Error indexing documents: {str(e)}")
        raise



def main():
    print("Starting the indexing process...")
    try:
        documents = fetch_documents()
        es_client = setup_elasticsearch()
        index_documents(es_client, documents)
        
        print("Initializing database...")
        if init_db():
            print("Database initialized successfully!")
        else:
            print("Failed to initialize database")
            return 1
        
        print("Indexing process completed successfully!")
        return 0
    except Exception as e:
        print(f"An error occurred during the indexing process: {str(e)}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)