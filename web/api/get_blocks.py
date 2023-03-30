from typing import List, Tuple
import dataclasses
import itertools
import json
import pickle
import numpy as np
import openai
import regex as re
import time

EMBEDDING_MODEL = "text-embedding-ada-002"
COMPLETIONS_MODEL = "gpt-3.5-turbo"

import pathlib
project_path = pathlib.Path(__file__).parent
PATH_TO_DATASET_DICT = project_path / "dataset_dict.pkl"

class Dataset:
    pass
    # def __init__(self, path_to_dataset: str = PATH_TO_DATASET_PKL):
    #     self.path_to_dataset = path_to_dataset # .json
    #     with open(self.path_to_dataset, 'rb') as f:
    #         self.
    #     self.load_dataset()
        
    # def load_dataset(self): # Load the dataset from the saved .json file
    #     with open(self.path_to_dataset, 'rb') as f:
    #         dataset_dict = json.load(f)
    #     self.metadata = dataset_dict['metadata']
    #     self.embedding_strings = dataset_dict['embedding_strings']
    #     self.embeddings_metadata_index = dataset_dict['embeddings_metadata_index']
    #     self.articles_count = dataset_dict['articles_count']
    #     self.total_articles_count = dataset_dict['total_articles_count']
    #     self.total_char_count = dataset_dict['total_char_count']
    #     self.total_word_count = dataset_dict['total_word_count']
    #     self.total_sentence_count = dataset_dict['total_sentence_count']
    #     self.total_block_count = dataset_dict['total_block_count']
    #     self.sources_so_far = dataset_dict['sources_so_far']
    #     self.info_types = dataset_dict['info_types']
    #     self.embeddings = np.array(dataset_dict['embeddings'])

@dataclasses.dataclass
class Block:
    title: str
    author: str
    date: str
    url: str
    tags: str
    text: str

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
        except openai.error.RateLimitError as e:
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
    # metadataset = Dataset()
    # Get the dataset (in data/dataset_5percent.pkl)
    with open(PATH_TO_DATASET_DICT, 'rb') as f:
        metadataset = pickle.load(f)
    
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
        
        similarity_scores = np.dot(metadataset["embeddings"], HyDe_completion_embedding)        
    else:
        similarity_scores = np.dot(metadataset["embeddings"], query_embedding)
    
    ordered_blocks = np.argsort(similarity_scores)[::-1]  # Sort the blocks by similarity score

    top_k_block_indices = ordered_blocks[:k]  # Get the top k indices of the blocks
    top_k_metadata_indexes = [metadataset["embeddings_metadata_index"][i] for i in top_k_block_indices]

    # --------------------------------------------------------------------------

    # we've got some sort of truncation issue with the dataset. Ideally, delete these lines

    tkbi = []
    tkmi = []

    bl = len(metadataset["embedding_strings"])
    ml = len(metadataset["metadata"])

    for i in range(len(top_k_block_indices)):
        if top_k_block_indices[i] >= bl or top_k_metadata_indexes[i] >= ml:
            print("!!!TRUNCATION ERROR!!!")
            print(f"- top_k_block_indices: {top_k_block_indices}, sampling array of length {bl}")
            print(f"- top_k_metadata_indexes: {top_k_metadata_indexes}, sampling array of length {ml}")
        else:
            tkbi.append(top_k_block_indices[i])
            tkmi.append(top_k_metadata_indexes[i])



    # --------------------------------------------------------------------------

    top_k_texts = [metadataset["embedding_strings"][i] for i in tkbi]
    top_k_metadata = [metadataset["metadata"][i] for i in tkmi]


    # Combine the top k texts and metadata into a list of Block objects
    top_k_metadata_and_text = [list(top_k_metadata[i]) + [strip_block(top_k_texts[i])] for i in range(len(top_k_metadata))]
    blocks = [Block(*block) for block in top_k_metadata_and_text]

    return unify(blocks)



# for all blocks that are "the same" (same title, author, date, url, tags),
# combine their text with "\n\n.....\n\n" in between. Return them in order such
# that the combined block has the minimum index of the blocks combined.

def unify(blocks: List[Block]) -> List[Block]:

    key = lambda bi: (bi[0].title or "", bi[0].author or "", bi[0].date or "", bi[0].url or "", bi[0].tags or "")

    blocks_plus_old_index = [(block, i) for i, block in enumerate(blocks)]
    blocks_plus_old_index.sort(key=key)

    unified_blocks: List[Tuple[Block, int]] = []

    for key, group in itertools.groupby(blocks_plus_old_index, key=key):
        group = list(group)
        if len(group) == 0: continue

        text = "\n\n\n.....\n\n\n".join([block[0].text for block in group])

        min_index = min([block[1] for block in group])

        unified_blocks.append((Block(key[0], key[1], key[2], key[3], key[4], text), min_index))

    unified_blocks.sort(key=lambda bi: bi[1])
    blocks = [block for block, _ in unified_blocks]
    return blocks


# we the title and authors inside the contents of the block, so that searches for
# the title or author will pull it up. This strips it back out.
def strip_block(text: str) -> str:
    r = re.match(r"^\"(.*)\"\s*-\s*Title:.*$", text, re.DOTALL)
    if not r:
        print("Warning: couldn't strip block")
        print(text)
    return r.group(1) if r else text


