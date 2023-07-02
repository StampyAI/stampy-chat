# dataset/settings.py

import os
import torch
from pathlib import Path

### FILE PATHS ###
current_file_path = Path(__file__).resolve()
SQL_DB_PATH = str(current_file_path.parent / 'data' / 'ARD.db')

### DATASET ###
ARD_DATASET_NAME = "StampyAI/alignment-research-dataset"

### EMBEDDINGS ###
USE_OPENAI_EMBEDDINGS = False
OPENAI_EMBEDDINGS_MODEL = "text-embedding-ada-002"
EMBEDDINGS_DIMS = 1536
OPENAI_EMBEDDINGS_RATE_LIMIT = 3500
SENTENCE_TRANSFORMER_EMBEDDINGS_MODEL = "sentence-transformers/multi-qa-mpnet-base-cos-v1"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

### PINECONE ###
PINECONE_INDEX_NAME = "stampy-chat-embeddings-test"
PINECONE_VALUES_DIMS = EMBEDDINGS_DIMS
PINECONE_METRIC = "cosine"
PINECONE_METADATA_ENTRIES = ["entry_id", "source", "title", "authors", "text"]
PINECONE_API_KEY = os.environ["PINECONE_API_KEY"]
PINECONE_ENVIRONMENT = os.environ["PINECONE_ENVIRONMENT"]

### MISCELLANEOUS ###
MAX_NUM_AUTHORS_IN_SIGNATURE = 3