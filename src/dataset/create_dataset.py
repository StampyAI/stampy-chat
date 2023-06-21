import numpy as np
from typing import List, Dict, Tuple, DefaultDict, Any
from collections import defaultdict
import time
import random
import pickle
import os
import concurrent.futures
from pathlib import Path
from tqdm.auto import tqdm
from dateutil.parser import parse, ParserError
import openai
from datasets import load_dataset
from langchain.document_loaders import HuggingFaceDatasetLoader


try:
    import config
    openai.api_key = config.OPENAI_API_KEY
except ImportError:
    openai.api_key = os.environ.get('OPENAI_API_KEY')


from .settings import PATH_TO_DATASET_DICT_PKL, EMBEDDING_MODEL, LEN_EMBEDDINGS

from .text_splitter import TokenSplitter, split_into_sentences



error_count_dict = {
    "Entry has no id.": 0,
    "Entry has no source.": 0,
    "Entry has no title.": 0,
    "Entry has no text.": 0,
    "Entry has non-string required key.": 0
}


class MissingDataException(Exception):
    pass


class ChunkedARD:
    def __init__(self,
            min_tokens_per_block: int = 300, # Minimum number of tokens per block.
            max_tokens_per_block: int = 400, # Maximum number of tokens per block.
            custom_sources: List[str] = None,  # List of sources to include, like "alignmentforum", "lesswrong", "arxiv",etc.
            rate_limit_per_minute: int = 3_500,  # Rate limit for the OpenAI API.
        ):       
        self.min_tokens_per_block = min_tokens_per_block  # for the text splitter
        self.max_tokens_per_block = max_tokens_per_block  # for the text splitter

        self.custom_sources = custom_sources
        self.rate_limit_per_minute = rate_limit_per_minute
        self.delay_in_seconds = 60.0 / self.rate_limit_per_minute
        
        self.metadata: List[Dict[str, Any]] = []  # List of dicts, each containing: id, entry_id, source, title, text, url, date_published, authors.

        self.entries_per_source_count: DefaultDict[str, int] = defaultdict(int)  # Number of entries per source. E.g.: {'source1': 10, 'source2': 20, 'total': 30}
        self.total_counts = {
            'chars': 0,
            'words': 0,
            'sentences': 0,
            'chunks': 0,
            'entries': 0,
        }

        if self.custom_sources is not None:
            for source in self.custom_sources:
                self.entries_per_source_count[source] = 0
        
    def contains_required_metadata(self, entry: Dict[str, Any]):
        metadata_types = {
            'id': str,
            'source': str,
            'title': str,
            'url': str,
            'date_published': str,
            'authors': list, # It appears to be a list, but actually it's a list-looking string. Like "['apple', 'orange', 'tomato']" is a string.
#            'summary': str  # see previous comment
        }
        required_metadata_keys = ['id', 'source', 'title', 'text']

        # Check that the 8 primary metadata keys all have the correct type
        for key, key_type in metadata_types.items():
            if type(entry[key]) != key_type:
                raise MissingDataException(f"Entry {entry['id']} has key {key} of type {type(entry[key])} when it should be {key_type}.")

        # Check that the 4 required metadata keys are non-empty
        for key in required_metadata_keys:
            if not entry[key]:
                raise MissingDataException(f"Entry {entry['id']} has no {key}.")

           
    def get_alignment_texts(self):
        text_splitter = TokenSplitter(self.min_tokens_per_block, self.max_tokens_per_block)

        # Load the dataset. streaming allows you to load one entry at a time, 
        # so entries can be processed before the entire dataset has been saved.
        # iterable_data = load_dataset('StampyAI/alignment-research-dataset', 'aisafety.info', split='train', streaming=True)

        iterable_data = load_dataset('StampyAI/alignment-research-dataset', 'all', split='train', streaming=True)
        
        for entry in tqdm(iterable_data):            
            """Checks"""

            # if we specified custom sources, only include entries from those sources
            if (self.custom_sources is not None) and (entry['source'] not in self.custom_sources):
                continue

            # raise error if the entry does not contain the required metadata
            self.contains_required_metadata(entry)

            #if the text is too short, ignore this text
            if len(entry['text']) < 500:
                continue


            """Checks are done, so we construct the metadata."""

            # Get id, source, title, text, url, date_published, authors, and summary
            entry_id: str = entry['id']
            source: str = entry['source']
            title: str = entry['title']
            text: str = entry['text']
            url: str = entry['url']
            date_published: str = entry['date_published']
            authors: list = entry['authors']
            
            # Get signature
            if authors:
                signature = f"Title: {title}, Authors: {get_authors_str(authors)}"
            else:
                signature = f"Title: {title}"

            # We use the text_splitter to get the chunks from the entry, 
            # and we add a metadata element for each new chunk we add to the dataset.
            chunks = text_splitter.split(text, signature)
            num_chunks = len(chunks)
            
            for i in range(num_chunks):
                self.metadata.append({
                    'id': f"{entry_id}_{str(i+1).zfill(6)}",
                    'entry_id': entry_id,
                    'source': source,
                    'title': title,
                    'text': chunks[i],
                    'url': url,
                    'date_published': date_published,
                    'authors': authors
                })
            
            # Update counts
            self.entries_per_source_count[entry['source']] += 1
            self.total_counts['entries'] += 1
            self.total_counts['chars'] += len(text)
            self.total_counts['words'] += len(text.split())
            self.total_counts['sentences'] += len(split_into_sentences(text))
            self.total_counts['chunks'] += len(chunks)

    def show_stats(self):
        print(f'Number of entries by source: {self.entries_per_source_count}')
        print(f'Total entries count: {self.total_counts["entries"]}')
        print(f'Total character count: {self.total_counts["chars"]}')
        print(f'Total word count: {self.total_counts["words"]}')
        print(f'Total sentence count: {self.total_counts["sentences"]}')
        print(f'Total chunk count: {self.total_counts["chunks"]}')

    def get_embeddings(self):
        def get_embeddings_at_index(texts: str, batch_idx: int, batch_size: int = 200): # int, np.ndarray
            embeddings = np.zeros((batch_size, 1536))
            openai_output = openai.Embedding.create(
                model=EMBEDDING_MODEL, 
                input=texts
            )['data']
            for i, embedding in enumerate(openai_output):
                embeddings[i] = embedding['embedding']
            return batch_idx, embeddings

        batch_size = 500
        rate_limit = 3500 / 60  # Maximum embeddings per second

        start = time.time()
        embedding_strings = [chunk_data['text'] for chunk_data in self.metadata]
        self.embeddings = np.zeros((len(embedding_strings), LEN_EMBEDDINGS))

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(
                get_embeddings_at_index, 
                embedding_strings[batch_idx:batch_idx+batch_size], 
                batch_idx,
                len(embedding_strings[batch_idx:batch_idx+batch_size])
            ) for batch_idx in range(0, len(embedding_strings), batch_size)]
            num_completed = 0
            for future in concurrent.futures.as_completed(futures):
                batch_idx, embeddings = future.result()
                num_completed += embeddings.shape[0]
                self.embeddings[batch_idx:batch_idx+embeddings.shape[0]] = embeddings

                elapsed_time = time.time() - start
                expected_time = num_completed / rate_limit
                sleep_time = max(expected_time - elapsed_time, 0)
                time.sleep(sleep_time)

                print(f"Completed {num_completed}/{len(embedding_strings)} embeddings in {elapsed_time:.2f} seconds.")

    def save_data(self, path: str = PATH_TO_DATASET_DICT_PKL):
        # Save the data to a pickle file
        print(f"Saving data to {path}...")
        data = {
            "metadata": self.metadata,
            "embeddings": self.embeddings.astype(np.float32),
            "total_counts": self.total_counts,
            "entries_per_source_count": self.entries_per_source_count            
        }
        with open(path, 'wb') as f:
            pickle.dump(data, f)


def get_authors_str(authors_lst: List[str]) -> str:
    if authors_lst == []: return 'n/a'
    if len(authors_lst) == 1: return authors_lst[0]
    else:
        authors_lst = authors_lst[:3]
        authors_str = ", ".join(authors_lst[:-1]) + " and " + authors_lst[-1]
    return authors_str

def standardize_date(date_string, default_date='n/a'):
    try:
        dt = parse(date_string)
        return dt.strftime('%Y-%m-%d')
    except (ParserError, ValueError):
        return default_date