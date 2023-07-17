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
USE_OPENAI_EMBEDDINGS = True  # If false, SentenceTransformer embeddings will be used.

OPENAI_EMBEDDINGS_MODEL = "text-embedding-ada-002"
OPENAI_EMBEDDINGS_DIMS = 1536
OPENAI_EMBEDDINGS_RATE_LIMIT = 3500

SENTENCE_TRANSFORMER_EMBEDDINGS_MODEL = "sentence-transformers/multi-qa-mpnet-base-cos-v1"
SENTENCE_TRANSFORMER_EMBEDDINGS_DIMS = 768

### PINECONE ###
PINECONE_INDEX_NAME = "stampy-chat-ard"
PINECONE_VALUES_DIMS = OPENAI_EMBEDDINGS_DIMS if USE_OPENAI_EMBEDDINGS else SENTENCE_TRANSFORMER_EMBEDDINGS_DIMS
PINECONE_METRIC = "dotproduct"
PINECONE_METADATA_ENTRIES = ["entry_id", "source", "title", "authors", "text"]
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY", None)
PINECONE_ENVIRONMENT = os.environ.get("PINECONE_ENVIRONMENT", None)

### MISCELLANEOUS ###
CHUNK_SIZE = 1750
MAX_NUM_AUTHORS_IN_SIGNATURE = 3
EMBEDDING_LENGTH_BIAS = {
    "aisafety.info": 1.05,  # In search, favor AISafety.info entries.
}