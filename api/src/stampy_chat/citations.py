import datetime
from typing import Dict, List, Any

from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.prompts import (
    SemanticSimilarityExampleSelector
)
from langchain.pydantic_v1 import Extra
from langchain.vectorstores import Pinecone

from stampy_chat.env import PINECONE_INDEX, PINECONE_NAMESPACE


embeddings = OpenAIEmbeddings()
vectorstore = Pinecone(PINECONE_INDEX, embeddings.embed_query, "hash_id", namespace=PINECONE_NAMESPACE)


class ReferencesSelector(SemanticSimilarityExampleSelector):
    """Get examples with enumerated indexes added."""

    class Config:
        """This is needed for extra fields to be added... """
        extra = Extra.forbid
        arbitrary_types_allowed = True

    @staticmethod
    def make_reference(i: int) -> str:
        """Make the reference used in citations - basically translate i -> 'a + i'"""
        return chr(i + 97)

    def select_examples(self, input_variables: Dict[str, str]) -> List[dict]:
        """Fetch the top matching items from the underlying storage and add indexes.

        :param Dict[str, str] input_variables: a dict of {<field>: <query>} pairs to look through the dataset
        :returns: a list of example objects
        """
        ### Copied from parent - for some reason they ignore the ids of the returned items, so
        # it has to be added manually here...
        if self.input_keys:
            input_variables = {key: input_variables[key] for key in self.input_keys}
        query = " ".join(v for v in input_variables.values())
        example_docs = self.vectorstore.similarity_search(query, k=self.k)
        return [
            dict(
                e.metadata,
                id=e.page_content,
                reference=self.make_reference(i)
            ) for i, e in enumerate(example_docs)
        ]


def make_example_selector(k: int, **params) -> ReferencesSelector:
    return ReferencesSelector(vectorstore=vectorstore, **params)


def format_block(block) -> Dict[str, Any]:
    date = block.get('date_published') or block.get('date')

    if isinstance(date, datetime.datetime):
        date = date.date().isoformat()
    elif isinstance(date, datetime.date):
        date = date.isoformat()
    elif isinstance(date, (int, float)):
        date = datetime.datetime.fromtimestamp(date).date().isoformat()

    authors = block.get('authors')
    if not authors and block.get('author'):
        authors = [block.get('author')]

    return {
        "id": block.get('hash_id') or block.get('id'),
        "title": block['title'],
        "authors": authors,
        "date": date,
        "url": block['url'],
        "tags": block.get('tags'),
        "text": block['text']
    }


def get_top_k_blocks(query, k):
    blocks = make_example_selector(k=k).select_examples({'query': query})
    return list(map(format_block, blocks))
