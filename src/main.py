import openai
"""
import config
from assistant.semantic_search import AlignmentSearch
from dataset.create_dataset import Dataset

openai.api_key = config.OPENAI_API_KEY

from settings import PATH_TO_RAW_DATA, PATH_TO_DATASET, EMBEDDING_MODEL, LEN_EMBEDDINGS
"""
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)

import numpy as np

import sys
import pickle
from pathlib import Path
import random

src_path = Path(__file__).resolve().parent
if str(src_path) not in sys.path:
    sys.path.append(str(src_path))

from dataset import create_dataset
#from assistant import semantic_search
from settings import EMBEDDING_MODEL, PATH_TO_DATASET_DICT_PKL, PATH_TO_DATASET_PKL

import numpy as np
import matplotlib.pyplot as plt


def load_rawdata_into_pkl():
    """ 
    # List of possible sources:
    all_sources = ["https://aipulse.org", "ebook", "https://qualiacomputing.com", "alignment forum", "lesswrong", "manual", "arxiv", "https://deepmindsafetyresearch.medium.com", "waitbutwhy.com", "GitHub", "https://aiimpacts.org", "arbital.com", "carado.moe", "nonarxiv_papers", "https://vkrakovna.wordpress.com", "https://jsteinhardt.wordpress.com", "audio-transcripts", "https://intelligence.org", "youtube", "reports", "https://aisafety.camp", "curriculum", "https://www.yudkowsky.net", "distill", 
                   "Cold Takes", "printouts", "gwern.net", "generative.ink", "greaterwrong.com"] # These last do not have a source field in the .jsonl file

    # List of sources we are using for the test run:
    custom_sources = [
        "https://aipulse.org", 
        "ebook", 
        "https://qualiacomputing.com", 
        "alignment forum", 
        "lesswrong", 
        "manual", 
        "arxiv", 
        "https://deepmindsafetyresearch.medium.com/", 
        "waitbutwhy.com", 
        "GitHub", 
        "https://aiimpacts.org", 
        "arbital.com", 
        "carado.moe", 
        "nonarxiv_papers", 
        "https://vkrakovna.wordpress.com", 
        "https://jsteinhardt.wordpress.com", 
        "audio-transcripts", 
        "https://intelligence.org", 
        "youtube", 
        "reports", 
        "https://aisafety.camp", 
        "curriculum", 
        "https://www.yudkowsky.net", 
        "distill",
        "Cold Takes",
        "printouts",
        "gwern.net",
        "generative.ink",
        "greaterwrong.com"
    ]
    """

    dataset = create_dataset.ChunkedARD(
        min_tokens_per_block=200, max_tokens_per_block=300
    )
    dataset.get_alignment_texts()
    dataset.get_embeddings()
    dataset.save_data()
    dataset.show_stats()

def load_pkl_and_display_stuff():
    with open(PATH_TO_DATASET_DICT_PKL, 'rb') as f:
        dataset_dict = pickle.load(f)    
    print(dataset_dict)

@retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(4))
def get_embedding(text: str) -> np.ndarray:
    result = openai.Embedding.create(model=EMBEDDING_MODEL, input=text)
    return np.array(result["data"][0]["embedding"])

if __name__ == "__main__":
    load_rawdata_into_pkl()
    #load_pkl_and_display_stuff()
    