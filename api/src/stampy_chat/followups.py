import requests
from typing import TypedDict
from urllib.parse import quote

from stampy_chat import logging
from stampy_chat.callbacks import CallbackHandler

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.4  # bit of a shot in the dark - play with this later
MAX_FOLLOWUPS = 3


class Followup(TypedDict):
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

    url = "https://nlp.stampy.ai/api/search?query=" + quote(
        query[:4093]
    )  # make sure there aren't too many characters
    response = requests.get(url)
    if response.status_code == 200:
        return [
            Followup(text=entry["title"], pageid=entry["pageid"], score=entry["score"])
            for entry in response.json()
        ]
    return []


# search with multiple queries, combine results
def multisearch_authored(queries: list[str]) -> list[Followup]:
    # sort the followups from lowest to highest score
    followups = [entry for query in queries for entry in get_followups(query)]
    followups = sorted(followups, key=lambda entry: entry["score"])

    # Remove any duplicates by making a map from the pageids. This should result in highest scored entry being used
    followups = {
        entry["pageid"]: entry
        for entry in followups
        if entry["score"] > SIMILARITY_THRESHOLD
    }

    # Get the first `MAX_FOLLOWUPS`
    followups = sorted(followups.values(), reverse=True, key=lambda e: e["score"])
    followups = list(followups)[:MAX_FOLLOWUPS]

    if logger.is_debug():
        logger.debug(
            " ------------------------------ suggested followups: -----------------------------"
        )
        for followup in followups:
            if followup["score"] > SIMILARITY_THRESHOLD:
                logger.debug(f"{followup['score']:.2f} - suggested to user")
            else:
                logger.debug(f"{followup['score']:.2f} - not suggested")
            logger.debug(followup["text"])
            logger.debug(followup["pageid"])
            logger.debug("")

    return followups


def search_followups(query: str, response: str, callbacks: list[CallbackHandler]):
    for call in callbacks:
        call.on_followups_start({"query": query, "response": response})

    follows = multisearch_authored([query, response])
    for call in callbacks:
        call.on_followups_end(follows)

    return follows
