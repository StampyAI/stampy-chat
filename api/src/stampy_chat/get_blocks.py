import dataclasses
import datetime
import numpy as np
import openai
import regex as re
import requests
import time
from itertools import groupby
from typing import Iterable, List
from stampy_chat.env import PINECONE_NAMESPACE, REMOTE_CHAT_INSTANCE, EMBEDDING_MODEL
from stampy_chat import logging


logger = logging.getLogger(__name__)

# ------------------------------------ types -----------------------------------

@dataclasses.dataclass
class Block:
    id: str
    title: str
    authors: List[str]
    date: str
    url: str
    tags: str
    text: str

# ------------------------------------------------------------------------------

# Get the embedding for a given text. The function will retry with exponential backoff if the API rate limit is reached, up to 4 times.
def get_embedding(text: str) -> np.ndarray:

    max_retries = 4
    max_wait_time = 10
    attempt = 0

    while True:
        try:
            result = openai.Embedding.create(model=EMBEDDING_MODEL, input=text)
            return result["data"][0]["embedding"]

        except openai.error.RateLimitError as e:

            attempt += 1

            if attempt > max_retries: raise e

            time.sleep(min(max_wait_time, 2 ** attempt))


def parse_block(match) -> Block:
    metadata = match['metadata']

    date = metadata.get('date_published') or metadata.get('date')

    if isinstance(date, datetime.datetime):
        date = date.date().isoformat()
    elif isinstance(date, datetime.date):
        date = date.isoformat()
    elif isinstance(date, (int, float)):
        date = datetime.datetime.fromtimestamp(date).date().isoformat()

    authors = metadata.get('authors')
    if not authors and metadata.get('author'):
        authors = [metadata.get('author')]

    return Block(
        id = metadata.get('hash_id') or metadata.get('id'),
        title = metadata['title'],
        authors = authors,
        date = date,
        url = metadata['url'],
        tags = metadata.get('tags'),
        text = strip_block(metadata['text'])
    )


def join_blocks(blocks: Iterable[Block]) -> List[Block]:
    # for all blocks that are "the same" (same title, author, date, url, tags),
    # combine their text with "....." in between. Return them in order such
    # that the combined block has the minimum index of the blocks combined.

    def to_tuple(block):
        return (block.title or "", block.authors or [], block.date or "", block.url or "", block.tags or "")

    def merge_texts(blocks):
        return "\n.....\n".join(sorted(block.text for block in blocks))

    # There are sometimes duplicates in the dataset, but which have different ids, so the id
    # is ignored when making sorting the blocks.
    def make_block(key, group):
        group = list(group)
        # Just use the id of the first item - it doesn't matter that much in this case, as the other data points
        # will be the same
        return Block(group[0].id, *key, merge_texts(group))

    blocks = sorted(blocks, key=to_tuple)
    blocks = [make_block(key, group) for key, group in groupby(blocks, key=to_tuple)]
    return blocks


# Get the k blocks most semantically similar to the query using Pinecone.
def get_top_k_blocks(index, user_query: str, k: int) -> List[Block]:

    # Default to querying embeddings from live website if pinecone url not
    # present in .env
    #
    # This helps people getting started developing or messing around with the
    # site, since setting up a vector DB with the embeddings is by far the
    # hardest part for those not already on the team.

    if index is None:

        logger.info('Pinecone index not found, performing semantic search on chat.stampy.ai endpoint.')
        response = requests.post(
            REMOTE_CHAT_INSTANCE,
            json = {
                "query": user_query,
                "k": k
            }
        )

        return [parse_block({'metadata': block}) for block in response.json()]

    # print time
    t = time.time()

    # Get the embedding for the query.
    query_embedding = get_embedding(user_query)

    t1 = time.time()
    logger.debug(f'Time to get embedding: {t1-t:.2f}s')

    query_response = index.query(
        namespace=PINECONE_NAMESPACE,
        top_k=k,
        include_values=False,
        include_metadata=True,
        vector=query_embedding
    )
    blocks = [parse_block(match) for match in query_response['matches']]
    t2 = time.time()

    logger.debug(f'Time to get top-k blocks: {t2-t1:.2f}s')

    return join_blocks(blocks)


# we add the title and authors inside the contents of the block, so that
# searches for the title or author will be more likely to pull it up. This
# strips it back out.
def strip_block(text: str) -> str:
    r = re.match(r"^\"(.*)\"\s*-\s*Title:.*$", text, re.DOTALL)
    if not r:
        logger.warning("couldn't strip block:\n%s", text)
    return r.group(1) if r else text
