# dataset/pinecone_db_handler.py

import json
import pinecone
import os

from .settings import PINECONE_INDEX_NAME, PINECONE_VALUES_DIMS, PINECONE_METRIC, PINECONE_METADATA_ENTRIES

import logging
logger = logging.getLogger(__name__)


class PineconeDB:
    def __init__(
        self, 
        create_index: bool = False,
    ):
        self.index_name = PINECONE_INDEX_NAME
        
        PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
        PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")
        assert PINECONE_API_KEY, "PINECONE_API_KEY environment variable not set."
        assert PINECONE_ENVIRONMENT, "PINECONE_LOCATION environment variable not set."
        
        pinecone.init(
            api_key = PINECONE_API_KEY,
            environment = PINECONE_ENVIRONMENT,
        )
        
        if create_index:
            self.create_index()
        
        self.index = pinecone.Index(index_name=self.index_name)
    
    def __str__(self) -> str:
        index_stats_response = self.index.describe_index_stats()
        return f"{self.index_name}:\n{json.dumps(index_stats_response, indent=4)}"
    
    def upsert_entry(self, entry, chunks, embeddings, upsert_size=100):
        self.index.upsert(
            vectors=list(
            zip(
                [f"{entry['id']}_{str(i).zfill(6)}" for i in range(len(chunks))], 
                embeddings.tolist(), 
                [
                    {
                        'entry_id': entry['id'],
                        'source': entry['source'],
                        'title': entry['title'],
                        'authors': entry['authors'],
                        'text': chunk,
                    } for chunk in chunks
                ]
            )
        ),
            batch_size=upsert_size
        )
        
    def delete_entry(self, id):
        self.index.delete(
            filter={"entry_id": {"$eq": id}}
        )

    def create_index(self, replace_current_index: bool = True):
        if replace_current_index:
            self.delete_index()
        
        pinecone.create_index(
            name=self.index_name,
            dimension=PINECONE_VALUES_DIMS,
            metric=PINECONE_METRIC,
            metadata_config = {"indexed": PINECONE_METADATA_ENTRIES}
        )

    def delete_index(self):
        if self.index_name in pinecone.list_indexes():
            logger.info(f"Deleting index '{self.index_name}'.")
            pinecone.delete_index(self.index_name)