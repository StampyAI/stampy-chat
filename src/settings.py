from pathlib import Path

EMBEDDING_MODEL = "text-embedding-ada-002"
COMPLETIONS_MODEL = "gpt-3.5-turbo"

LEN_EMBEDDINGS = 1536
MAX_LEN_PROMPT = 4095 # This may be 8191, unsure.


def get_rawdata_file_path():
    current_file_path = Path(__file__).resolve()
    data_file_path = current_file_path.parent / 'dataset' / 'data' / 'alignment_texts.jsonl'
    return str(data_file_path)

def get_dataset_file_path():
    current_file_path = Path(__file__).resolve()
    data_file_path = current_file_path.parent / 'dataset' / 'data' / 'dataset.pkl'
    return str(data_file_path)


PATH_TO_RAW_DATA = get_rawdata_file_path()

PATH_TO_DATASET = get_dataset_file_path()

