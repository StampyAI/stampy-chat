from pathlib import Path

EMBEDDING_MODEL = "text-embedding-ada-002"
COMPLETIONS_MODEL = "text-davinci-003"

LEN_EMBEDDINGS = 1536
MAX_LEN_PROMPT = 8191

project_path = Path(__file__).parent.parent.parent
PATH_TO_DATA = project_path / "data" / "alignment_texts.jsonl" # Path to the dataset .jsonl file.
PATH_TO_EMBEDDINGS = project_path / "src" / "Embeddings Search" / "data" / "embeddings.npy" # Path to the saved embeddings (.npy) file.
PATH_TO_DATA = project_path / "src" / "Embeddings Search" / "data" / "dataset.pkl" # Path to the saved dataset (.pkl) file.
