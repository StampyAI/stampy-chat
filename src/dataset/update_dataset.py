# dataset/update_dataset.py

import time
from typing import Dict, List
import numpy as np
import logging
from tqdm.auto import tqdm
import openai
from datasets import load_dataset

from .text_splitter import TokenSplitter
from .pinecone_handler import PineconeHandler
from .database_handler import DatabaseHandler

class ARDUpdater:
    def __init__(
        self, 
        min_tokens_per_block: int = 200, # Minimum number of tokens per block.
        max_tokens_per_block: int = 400, # Maximum number of tokens per block.
        rate_limit_per_minute: int = 3_500,  # Rate limit for the OpenAI API.
        embedding_model="text-embedding-ada-002",
        embedding_dims=1536,
    ):
        self.rate_limit_per_minute = rate_limit_per_minute
        self.delay_in_seconds = 60.0 / self.rate_limit_per_minute

        self.embedding_model = embedding_model
        self.embedding_dims = embedding_dims
        
        self.token_splitter = TokenSplitter(
            min_tokens=min_tokens_per_block,
            max_tokens=max_tokens_per_block
        )
        self.db = DatabaseHandler()
        self.pinecone_handler = PineconeHandler()
        
        ### initialization code ###
        
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        # File handler
        file_handler = logging.FileHandler(r'src/dataset/logs/ard_updater.log')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        self.logger.info("ARDUpdater initialized.")


    def update(self, custom_sources: List[str] = ['all']):
        for source in custom_sources:
            self.update_source(source)
        
    def update_source(self, source: str):
        self.logger.info(f"Updating {source} entries...")

        iterable_data = load_dataset('StampyAI/alignment-research-dataset', source, split='train', streaming=True)
        iterable_data = iterable_data.map(self.preprocess)
        iterable_data = iterable_data.filter(lambda entry: entry is not None)
        iterable_data = iterable_data.filter(lambda entry: self.db.upsert_entry(entry))
        
        for entry in tqdm(iterable_data):
            t_entry_start = time.time()
            try:
                self.pinecone_handler.delete_entry(entry['id'])

                signature = f"Title: {entry['title']}, Authors: {get_authors_str(entry['authors'])}"
                chunks = self.token_splitter.split(entry['text'], signature)
                embeddings = self.get_embeddings(chunks)
                
                self.db.upsert_chunks(entry['id'], chunks)
                self.pinecone_handler.insert_entry(entry, chunks, embeddings)
            except Exception as e:
                self.logger.error(f"An error occurred while updating source {source}: {str(e)}", exc_info=True)
            
            t_entry_end = time.time()
            self.logger.info(f"Time for processing one entry: {t_entry_end - t_entry_start} seconds")

        self.logger.info(f"Successfully updated {source} entries.")
        
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
            self.logger.error(f"Entry validation failed: {str(e)}", exc_info=True)
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
        embeddings = np.zeros((len(chunks), self.embedding_dims))
        
        openai_output = openai.Embedding.create(
            model=self.embedding_model, 
            input=chunks
        )['data']
        
        for i, embedding in enumerate(openai_output):
            embeddings[i] = embedding['embedding']
        
        return embeddings

    def show_stats(self): #TODO
        # Show index
        # Show database
        pass


##### Helper functions #####

def get_authors_str(authors_lst: List[str]) -> str:
    if authors_lst == []: return 'n/a'
    if len(authors_lst) == 1: return authors_lst[0]
    else:
        authors_lst = authors_lst[:3]
        authors_str = ", ".join(authors_lst[:-1]) + " and " + authors_lst[-1]
    return authors_str