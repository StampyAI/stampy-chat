# dataset/update_dataset.py

from typing import Dict, List, Union
import numpy as np
from tenacity import retry, stop_after_attempt
from tqdm.auto import tqdm
from datasets import load_dataset
import openai

from .text_splitter import TokenSplitter
from .sql_db_handler import SQLDB
from .pinecone_db_handler import PineconeDB

from .settings import USE_OPENAI_EMBEDDINGS, OPENAI_EMBEDDINGS_MODEL, SENTENCE_TRANSFORMER_EMBEDDINGS_MODEL, EMBEDDINGS_DIMS, OPENAI_EMBEDDINGS_RATE_LIMIT, ARD_DATASET_NAME, MAX_NUM_AUTHORS_IN_SIGNATURE

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
        
        if not USE_OPENAI_EMBEDDINGS:
            from langchain.embeddings import HuggingFaceEmbeddings
            self.hf_embeddings = HuggingFaceEmbeddings(
                model_name=SENTENCE_TRANSFORMER_EMBEDDINGS_MODEL,
            )

    def update(self, custom_sources: List[str] = ['all']):
        for source in custom_sources:
            self.update_source(source)

    def update_source(self, source: str, chunk_size: int = 100):
        logger.info(f"Updating {source} entries...")
        
        streamed_dataset = load_dataset(
            ARD_DATASET_NAME, source, split='train', streaming=True
        ).map(self.preprocess_and_validate).filter(
            self.is_valid_entry
        ).filter(
            self.is_sql_entry_upserted
        )
        
        for batch in self.batchify(streamed_dataset, chunk_size):
            entries_batch = batch['entries_batch']
            chunks_batch = batch['chunks_batch']
            chunks_ids_batch = batch['chunks_ids_batch']

            try:
                if USE_OPENAI_EMBEDDINGS:
                    embeddings = self.get_openai_embeddings(chunks_batch)
                else:
                    embeddings = np.array(self.hf_embeddings.embed_documents(chunks_batch))

                self.sql_db.upsert_chunks(chunks_ids_batch, chunks_batch)
                # self.pinecone_db.delete_entries([entry['id'] for entry in entries_batch])
                # self.pinecone_db.upsert_entries(entries_batch, chunks_batch, chunks_ids_batch, embeddings)
                
                logger.info(f"Successfully updated {len(entries_batch)} {source} entries with {len(chunks_batch)} total chunks.")
            except Exception as e:
                logger.error(f"An error occurred while updating source {source}: {str(e)}", exc_info=True)

        logger.info(f"Successfully updated {source} entries.")
    
    def batchify(self, iterable, chunk_size):
        entries_batch = []
        chunks_batch = []
        chunks_ids_batch = []

        for entry in iterable:
            chunks = self.token_splitter.split(entry['text'], f"Title: {entry['title']}, Authors: {get_authors_str(entry['authors'])}")
            chunks_ids = [f"{entry['id']}_{str(i).zfill(6)}" for i in range(len(chunks))]

            # Add this entry's chunks to the current batch, even if it causes the batch size to exceed chunk_size.
            entries_batch.append(entry)
            chunks_batch.extend(chunks)
            chunks_ids_batch.extend(chunks_ids)

            # If this batch is large enough, yield it and start a new one.
            if len(chunks_batch) >= chunk_size:
                yield {'entries_batch': entries_batch, 'chunks_batch': chunks_batch, 'chunks_ids_batch': chunks_ids_batch}

                entries_batch = []
                chunks_batch = []
                chunks_ids_batch = []

        # Yield any remaining items.
        if entries_batch:
            yield {'entries_batch': entries_batch, 'chunks_batch': chunks_batch, 'chunks_ids_batch': chunks_ids_batch}
        
    def preprocess_and_validate(self, entry):
        """Preprocesses and validates the entry data"""
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

    def validate_entry(self, entry: Dict[str, Union[str, list]], char_len_lower_limit: int = 0):
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
                
        if len(entry['text']) < char_len_lower_limit:
            raise ValueError(f"Entry text is too short (< {char_len_lower_limit} characters).")

    @staticmethod
    def is_valid_entry(entry):
        """Checks if the entry is valid"""
        return entry is not None

    def is_sql_entry_upserted(self, entry):
        """Upserts an entry to the SQL database and returns the success status"""
        return self.sql_db.upsert_entry(entry)
    
    @retry(stop=stop_after_attempt(3))
    def get_openai_embeddings(self, chunks):
        embeddings = np.zeros((len(chunks), EMBEDDINGS_DIMS))
        rate_limit = OPENAI_EMBEDDINGS_RATE_LIMIT  #  TODO: use this rate_limit
        
        openai_output = openai.Embedding.create(
            model=OPENAI_EMBEDDINGS_MODEL, 
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
        authors_lst = authors_lst[:MAX_NUM_AUTHORS_IN_SIGNATURE]
        authors_str = f"{', '.join(authors_lst[:-1])} and {authors_lst[-1]}"
    return authors_str