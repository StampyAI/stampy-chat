from pathlib import Path

EMBEDDING_MODEL = "text-embedding-ada-002"
COMPLETIONS_MODEL = "text-davinci-003"

LEN_EMBEDDINGS = 1536
MAX_LEN_PROMPT = 4095 # This may be 8191, unsure.

project_path = Path(__file__).parent.parent#.parent
PATH_TO_DATA = project_path / "src" / "data" / "alignment_texts.jsonl" # Path to the dataset .jsonl file.
PATH_TO_EMBEDDINGS = project_path / "src" / "data" / "embeddings.npy" # Path to the saved embeddings (.npy) file.
PATH_TO_DATASET = project_path / "src" / "data" / "dataset.pkl" # Path to the saved dataset (.pkl) file, containing the dataset class object.
