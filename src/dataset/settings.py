from pathlib import Path

### FILE PATHS ###
current_file_path = Path(__file__).resolve()
SQL_DB_PATH = str(current_file_path.parent / 'data' / 'ARD.db')

### DATASET ###
ARD_DATASET_NAME = "StampyAI/alignment-research-dataset"

### EMBEDDINGS ###
EMBEDDINGS_MODEL = "text-embedding-ada-002"
EMBEDDINGS_DIMS = 1536
EMBEDDINGS_RATE_LIMIT = 3500

### PINECONE ###
PINECONE_INDEX_NAME = "stampy-chat-embeddings-test"
PINECONE_VALUES_DIMS = EMBEDDINGS_DIMS
PINECONE_METRIC = "cosine"
PINECONE_METADATA_ENTRIES = ["entry_id", "source", "title", "authors", "text"]

### MISC ###
RESET_DBS = False