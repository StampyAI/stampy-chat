# ---------------------------------- web code ----------------------------------

import json

from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):

    # post request = calculate factorial of passed number
    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data)

        results = {}

        for i, block in enumerate(get_top_k_blocks(data['query'])):
            results[i] = json.dumps(block.__dict__)

        self.wfile.write(json.dumps(results).encode('utf-8'))


# -------------------------------- non-web-code --------------------------------
import time
import pickle
import os

import numpy as np

import openai
from openai.error import RateLimitError

from functools import wraps
from typing import Callable, List, Type

# OpenAI API key
try:
    import config
    openai.api_key = config.OPENAI_API_KEY
except ImportError:
    openai.api_key = os.environ.get('OPENAI_API_KEY')

# OpenAI models
EMBEDDING_MODEL = "text-embedding-ada-002"
COMPLETIONS_MODEL = "gpt-3.5-turbo"

# OpenAI parameters
LEN_EMBEDDINGS = 1536
MAX_LEN_PROMPT = 4095 # This may be 8191, unsure.

# Paths
from pathlib import Path
project_path = Path(__file__).parent.parent.parent
PATH_TO_DATA = project_path / "web" / "api" / "data" / "alignment_texts.jsonl" # Path to the dataset .jsonl file.
PATH_TO_EMBEDDINGS = project_path / "web" / "api" / "data" / "embeddings.npy" # Path to the saved embeddings (.npy) file.
PATH_TO_DATASET = project_path / "web" / "api" / "data" / "dataset.pkl" # Path to the saved dataset (.pkl) file, containing the dataset class object.


class Dataset:
    pass

class Block:
    def __init__(self, title: str, author: str, date: str, url: str, tags: str, text: str):
        self.title = title
        self.author = author
        self.date = date
        self.url = url
        self.tags = tags
        self.text = text

def retry_on_exception_types(exception_types: List[Type[Exception]], stop_after_attempt: int, max_wait_time: int) -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < stop_after_attempt:
                try:
                    return func(*args, **kwargs)
                except tuple(exception_types) as e:
                    if attempts + 1 == stop_after_attempt:
                        raise e
                    wait_time = min(max_wait_time, (2 ** attempts))  # Exponential backoff
                    time.sleep(wait_time)
                    attempts += 1
        return wrapper
    return decorator

@retry_on_exception_types(exception_types=[RateLimitError], stop_after_attempt=4, max_wait_time=10)
def get_embedding(text: str) -> np.ndarray:
    """Get the embedding for a given text. The wrapper function will retry with exponential backoffthe request if the API rate limit is reached, up to 4 times.

    Args:
        text (str): The text to get the embedding for.

    Returns:
        np.ndarray: The embedding for the given text.
    """
    result = openai.Embedding.create(
        model=EMBEDDING_MODEL,
        input=text
    )
    return result["data"][0]["embedding"]

def get_top_k_blocks(user_query: str, k: int = 10, HyDE: bool = False) -> List[Block]:
    """Get the top k blocks that are most semantically similar to the query, using the provided dataset. 

    Args:
        query (str): The query to be searched for.
        k (int, optional): The number of blocks to return.
        HyDE (bool, optional): Whether to use HyDE or not. Defaults to False.

    Returns:
        List[Block]: A list of the top k blocks that are most semantically similar to the query.
    """
    # Get the dataset
    with open(PATH_TO_DATASET, "rb") as f:
        metadataset = pickle.load(f)
    
    # Get the embedding for the query.
    query_embedding = get_embedding(user_query)
    
    # If HyDE is enabled, produce a no-context ChatCompletion to the query.
    if HyDE:
        messages = [
            {"role": "system", "content": "You are a knowledgeable AI Alignment assistant."},
            {"role": "user", "content": f"Do your best to answer the question/instruction, even if you don't know the correct answer or action for sure.\nQ: {user_query}"},
        ]
        HyDE_completion = openai.ChatCompletion.create(
            model=COMPLETIONS_MODEL,
            messages=messages
        )["choices"][0]["message"]["content"]
        HyDe_completion_embedding = get_embedding(f"Question: {user_query}\n\nAnswer: {HyDE_completion}")
        
        similarity_scores = np.dot(metadataset.embeddings, HyDe_completion_embedding)        
    else:
        similarity_scores = np.dot(metadataset.embeddings, query_embedding)
    
    ordered_blocks = np.argsort(similarity_scores)[::-1]  # Sort the blocks by similarity score
    top_k_text_indices = ordered_blocks[:k]  # Get the top k indices of the blocks
    top_k_metadata_indexes = [metadataset.embeddings_metadata_index[i] for i in top_k_text_indices]
    
    # Get the top k blocks (title, author, date, url, tags, text)
    top_k_texts = [metadataset.embedding_strings[i] for i in top_k_text_indices]  # Get the top k texts
    top_k_metadata = [metadataset.metadata[i] for i in top_k_metadata_indexes]  # Get the top k metadata (title, author, date, url, tags)
    
    print(f"Top {k} blocks for query: '{user_query}'")
    print("=========================================")
    print(f"Top_{k}_metadata: {top_k_metadata}")
    
    # Combine the top k texts and metadata into a list of Block objects
    top_k_metadata_and_text = [list(top_k_metadata[i]) + [top_k_texts[i]] for i in range(k)]
    
    top_k_blocks = [Block(*block) for block in top_k_metadata_and_text]
        
    return top_k_blocks


if __name__ == "__main__":
    # Test the embeddings function
    query = "What is the best way to learn about AI alignment?"
    k = 8
    HyDE = True
    
    blocks = get_top_k_blocks(query, k, HyDE)
    for block in blocks:
        print(f"Title: {block.title}")
        print(f"Author: {block.author}")
        print(f"Date: {block.date}")
        print(f"URL: {block.url}")
        print(f"Tags: {block.tags}")
        print(f"Text: {block.text}")
        print()
        print()