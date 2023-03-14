import jsonlines
import numpy as np
from typing import List, Dict, Tuple
import re
import time
import random
import pickle
import openai
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)  # for exponential backoff

import config

from dataset import Dataset
from semantic_search import AlignmentSearch

from settings import DATA_PATH


LEN_EMBEDDINGS = 1536
PATH_TO_DATA = r"C:\Users\Henri\Documents\GitHub\AlignmentSearch\src\Embeddings Search\data\alignment_texts.jsonl"
PATH_TO_EMBEDDINGS = r"C:\Users\Henri\Documents\GitHub\AlignmentSearch\src\Embeddings Search\data\embeddings.npy"
PATH_TO_DATASET = r"C:\Users\Henri\Documents\GitHub\AlignmentSearch\src\Embeddings Search\data\dataset.pkl"

COMPLETIONS_MODEL = "text-davinci-003"
EMBEDDING_MODEL = "text-embedding-ada-002"

openai.api_key = config.OPENAI_API_KEY

MAX_LEN_PROMPT = 5000


def main():
    with open(PATH_TO_DATASET, 'rb') as f:
        dataset = pickle.load(f)
    AS = AlignmentSearch(dataset=dataset)
    prompt = "What would be an idea to solve the Alignment Problem? Name the Lesswrong post by Quintin Pope that discusses this idea."
    answer = AS.search_and_answer(prompt, 3, HyDE=False)
    print(answer)

    
if __name__ == "__main__":
    main()