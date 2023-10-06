import requests
from dataclasses import dataclass
from typing import List
from urllib.parse import quote


from stampy_chat import logging

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.4 # bit of a shot in the dark - play with this later
MAX_FOLLOWUPS = 3

@dataclass
class Followup:
    text: str
    pageid: str
    score: float

# do a search like this:
# https://nlp.stampy.ai/api/search?query=what%20is%20agi

def search_authored(query: str):
    return multisearch_authored([query])


def get_followups(query):
    if not query.strip():
        return []

    url = 'https://nlp.stampy.ai/api/search?query=' + quote(query)
    response = requests.get(url).json()
    return [Followup(entry['title'], entry['pageid'], entry['score']) for entry in response]


# search with multiple queries, combine results
def multisearch_authored(queries: List[str]):
    # sort the followups from lowest to highest score
    followups = [entry for query in queries for entry in get_followups(query)]
    followups = sorted(followups, key=lambda entry: entry.score)

    # Remove any duplicates by making a map from the pageids. This should result in highest scored entry being used
    followups = {entry.pageid: entry for entry in followups if entry.score > SIMILARITY_THRESHOLD}

    # Get the first `MAX_FOLLOWUPS`
    followups = sorted(followups.values(), reverse=True, key=lambda e: e.score)
    followups = list(followups)[:MAX_FOLLOWUPS]

    if logger.is_debug():
        logger.debug(" ------------------------------ suggested followups: -----------------------------")
        for followup in followups:
            if followup.score > SIMILARITY_THRESHOLD:
                logger.debug(f'{followup.score:.2f} - suggested to user')
            else:
                logger.debug(f'{followup.score:.2f} - not suggested')
            logger.debug(followup.text)
            logger.debug(followup.pageid)
            logger.debug('')

    return followups
