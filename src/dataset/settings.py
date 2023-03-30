from pathlib import Path

EMBEDDING_MODEL = "text-embedding-ada-002"
COMPLETIONS_MODEL = "gpt-3.5-turbo"

LEN_EMBEDDINGS = 1536
MAX_LEN_PROMPT = 4095 # This may be 8191, unsure.

current_file_path = Path(__file__).resolve()
PATH_TO_RAW_DATA = str(current_file_path.parent / 'data' / 'alignment_texts.jsonl')
PATH_TO_DATASET_PKL = str(current_file_path.parent / 'data' / 'dataset.pkl')
PATH_TO_DATASET_DICT_PKL = str(current_file_path.parent / 'data' / 'dataset_dict.pkl')