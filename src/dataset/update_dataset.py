# dataset/update_dataset.py

from typing import Any, Dict, List
import numpy as np
import logging
from tqdm.auto import tqdm
from datasets import load_dataset
import openai

from .text_splitter import TokenSplitter
from .pinecone_handler import PineconeHandler
from .database_handler import DatabaseHandler

class ARDUpdater:
    def __init__(
        self, 
        min_tokens_per_block: int = 300, # Minimum number of tokens per block.
        max_tokens_per_block: int = 400, # Maximum number of tokens per block.
        rate_limit_per_minute: int = 3_500,  # Rate limit for the OpenAI API.
        embedding_model="text-embedding-ada-002",
        embedding_dims=1536,
        index_name="stampy-chat-embeddings-test",
        update_all=False
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
        self.pinecone_handler = PineconeHandler(index_name=index_name)
        
        self.update_all = update_all
        
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

        for entry in tqdm(iterable_data):
            try:
                entry = self.process_entry(entry)
                if entry is None:
                    continue
                
                # If the upsertion produces a change to the sql database, update the pinecone db accordingly
                if self.update_all or self.db.upsert_entry(entry):
                    self.pinecone_handler.delete_entry(entry['id'])

                    signature = f"Title: {entry['title']}, Authors: {get_authors_str(entry['authors'])}"

                    chunks = self.token_splitter.split(entry['text'], signature)
                    
                    self.db.upsert_chunks(entry['id'], chunks)
                    
                    embeddings = self.get_embeddings(chunks)

                    self.pinecone_handler.insert_entry(entry, chunks, embeddings)
                    
                    self.logger.info(f"Successfully modified entry {entry['id']}.")
                    
            except Exception as e:
                self.logger.error(f"An error occurred while updating source {source}: {str(e)}", exc_info=True)

        self.logger.info(f"Successfully updated {source} entries.")

    def process_entry(self, entry):
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

    def validate_entry(self, entry: Dict[str, str | List[str]], len_lower_limit: int = 0):
        metadata_types = {
            'id': str,
            'source': str,
            'title': str,
            'text': str,
            'url': str,
            'date_published': str,
            'authors': List[str]
        }

        for metadata_type, metadata_type_type in metadata_types.items():
            if metadata_type not in entry:
                raise ValueError(f"Entry is missing required metadata '{metadata_type}'.")
            if not isinstance(entry[metadata_type], metadata_type_type):
                raise ValueError(f"Entry metadata '{metadata_type}' is not of type '{metadata_type_type}'.")
        
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