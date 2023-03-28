# ---------------------------------- web code ----------------------------------

import json
import dataclasses
from http.server import BaseHTTPRequestHandler

@dataclasses.dataclass
class Block:
    title: str
    author: str
    date: str
    url: str
    tags: str
    text: str

class Encoder(json.JSONEncoder):
    def default(self, o):
        return dataclasses.asdict(o) if dataclasses.is_dataclass(o) else super().default(o)

class handler(BaseHTTPRequestHandler):

    def do_POST(self):

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data)

        self.wfile.write(json.dumps(get_top_k_blocks(data['query']), cls = Encoder).encode('utf-8'))
        

# -------------------------------- non-web-code --------------------------------
import time
import os
import json
import numpy as np
from typing import List

import openai
from openai.error import RateLimitError
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
MAX__TOKEN_LEN_PROMPT = 4095 # This may be 8191, unsure.

# Paths
import pathlib
project_path = pathlib.Path(__file__).parent
PATH_TO_DATASET_JSON = project_path / "data" / "dataset.json" # Path to the saved dataset (.json) file, containing the dataset class object.


class Dataset:
    def __init__(self, path_to_dataset: str = PATH_TO_DATASET_JSON):
        self.path_to_dataset = path_to_dataset # .json
        self.load_dataset()
        
    def load_dataset(self): # Load the dataset from the saved .json file
        with open(self.path_to_dataset, 'rb') as f:
            dataset_dict = json.load(f)
        self.metadata = dataset_dict['metadata']
        self.embedding_strings = dataset_dict['embedding_strings']
        self.embeddings_metadata_index = dataset_dict['embeddings_metadata_index']
        self.articles_count = dataset_dict['articles_count']
        self.total_articles_count = dataset_dict['total_articles_count']
        self.total_char_count = dataset_dict['total_char_count']
        self.total_word_count = dataset_dict['total_word_count']
        self.total_sentence_count = dataset_dict['total_sentence_count']
        self.total_block_count = dataset_dict['total_block_count']
        self.sources_so_far = dataset_dict['sources_so_far']
        self.info_types = dataset_dict['info_types']
        self.embeddings = np.array(dataset_dict['embeddings'])

def get_embedding(text: str) -> np.ndarray:
    """Get the embedding for a given text. The function will retry with exponential backoff if the API rate limit is reached, up to 4 times.

    Args:
        text (str): The text to get the embedding for.

    Returns:
        np.ndarray: The embedding for the given text.
    """
    max_retries = 4
    max_wait_time = 10

    for attempt in range(max_retries):
        try:
            result = openai.Embedding.create(
                model=EMBEDDING_MODEL,
                input=text
            )
            return result["data"][0]["embedding"]
        except RateLimitError as e:
            if attempt + 1 == max_retries:
                raise e
            wait_time = min(max_wait_time, (2 ** attempt))  # Exponential backoff
            time.sleep(wait_time)

def get_top_k_blocks(user_query: str, k: int = 10, HyDE: bool = False) -> List[Block]:
    """Get the top k blocks that are most semantically similar to the query, using the provided dataset. 

    Args:
        query (str): The query to be searched for.
        k (int, optional): The number of blocks to return.
        HyDE (bool, optional): Whether to use HyDE or not. Defaults to False.

    Returns:
        List[Block]: A list of the top k blocks that are most semantically similar to the query.
    """
    # Get the dataset (in data/dataset.json)
    metadataset = Dataset()
    
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
    top_k_block_indices = ordered_blocks[:k]  # Get the top k indices of the blocks
    top_k_metadata_indexes = [metadataset.embeddings_metadata_index[i] for i in top_k_block_indices]
    
    # Get the top k blocks (title, author, date, url, tags, text)
    top_k_texts = [metadataset.embedding_strings[i] for i in top_k_block_indices]  # Get the top k texts
    top_k_metadata = [metadataset.metadata[i] for i in top_k_metadata_indexes]  # Get the top k metadata (title, author, date, url, tags)
    
    # Combine the top k texts and metadata into a list of Block objects
    top_k_metadata_and_text = [list(top_k_metadata[i]) + [top_k_texts[i]] for i in range(k)]
    blocks = [Block(*block) for block in top_k_metadata_and_text]
    
    return blocks

