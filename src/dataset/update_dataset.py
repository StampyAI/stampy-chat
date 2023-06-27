# dataset/update_dataset.py

from typing import Dict, List
import numpy as np
from tqdm.auto import tqdm
import openai
from datasets import load_dataset

from .text_splitter import TokenSplitter
from .sql_db_handler import SQLDB
from .pinecone_db_handler import PineconeDB

from .settings import EMBEDDINGS_MODEL, EMBEDDINGS_DIMS, EMBEDDINGS_RATE_LIMIT, ARD_DATASET_NAME

import logging
logger = logging.getLogger(__name__)


class ARDUpdater:
    def __init__(
        self, 
        min_tokens_per_block: int = 200, # Minimum number of tokens per block.
        max_tokens_per_block: int = 400, # Maximum number of tokens per block.
    ):
        self.token_splitter = TokenSplitter(min_tokens_per_block, max_tokens_per_block)
        self.sql_db = SQLDB()
        self.pinecone_db = PineconeDB()

    def update(self, custom_sources: List[str] = ['all']):
        for source in custom_sources:
            self.update_source(source)
        
    def update_source(self, source: str):
        logger.info(f"Updating {source} entries...")

        iterable_data = load_dataset(ARD_DATASET_NAME, source, split='train', streaming=True)
        iterable_data = iterable_data.map(self.preprocess)
        iterable_data = iterable_data.filter(lambda entry: entry is not None)
        iterable_data = iterable_data.filter(lambda entry: self.sql_db.upsert_entry(entry))
        
        for entry in tqdm(iterable_data):
            try:
                self.pinecone_db.delete_entry(entry['id'])

                signature = f"Title: {entry['title']}, Authors: {get_authors_str(entry['authors'])}"
                chunks = self.token_splitter.split(entry['text'], signature)
                embeddings = self.get_embeddings(chunks)
                
                self.sql_db.upsert_chunks(entry['id'], chunks)
                self.pinecone_db.upsert_entry(entry, chunks, embeddings)
            except Exception as e:
                logger.error(f"An error occurred while updating source {source}: {str(e)}", exc_info=True)
            
        logger.info(f"Successfully updated {source} entries.")
        
    def preprocess(self, entry):
        try:
            self.validate_entry(entry)
            
            return {
                'id': entry['id'],
                'source': entry['source'],
                'title': entry['title'],
                'text': entry['text'],
                'url': entry['url'],
                'date_published': entry['date_published'],
                'authors': entry['authors']
            }
        except ValueError as e:
            logger.error(f"Entry validation failed: {str(e)}", exc_info=True)
            return None

    def validate_entry(self, entry: Dict[str, str | list], len_lower_limit: int = 0):
        metadata_types = {
            'id': str,
            'source': str,
            'title': str,
            'text': str,
            'url': str,
            'date_published': str,
            'authors': list
        }

        for metadata_type, metadata_type_type in metadata_types.items():
            if not isinstance(entry.get(metadata_type), metadata_type_type):
                raise ValueError(f"Entry metadata '{metadata_type}' is not of type '{metadata_type_type}' or is missing.")
                
        if len(entry['text']) < len_lower_limit:
            raise ValueError(f"Entry text is too short (< {len_lower_limit} tokens).")

    def get_embeddings(self, chunks):
        embeddings = np.zeros((len(chunks), EMBEDDINGS_DIMS))
        rate_limit = EMBEDDINGS_RATE_LIMIT  #TODO: use this rate_limit
        
        openai_output = openai.Embedding.create(
            model=EMBEDDINGS_MODEL, 
            input=chunks
        )['data']
        
        for i, embedding in enumerate(openai_output):
            embeddings[i] = embedding['embedding']
        
        return embeddings

    def reset_dbs(self):
        self.sql_db.create_tables(True)
        self.pinecone_db.create_index(True)


##### Helper functions #####

def get_authors_str(authors_lst: List[str]) -> str:
    if authors_lst == []: return 'n/a'
    if len(authors_lst) == 1: return authors_lst[0]
    else:
        authors_lst = authors_lst[:3]
        authors_str = ", ".join(authors_lst[:-1]) + " and " + authors_lst[-1]
    return authors_str