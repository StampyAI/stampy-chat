from dataclasses import dataclass
from typing import List
from urllib.parse import quote
import requests

SIMILARITY_THRESHOLD = 0.5 # total shot in the dark - play with this later
MAX_FOLLOWUPS = 3

@dataclass
class Followup:
    text: str
    pageid: str
    score: float

# do a search like this:
# https://nlp.stampy.ai/api/search?query=what%20is%20agi

def search_authored(query: str, DEBUG_PRINT: bool = False):
    multisearch_authored([query], DEBUG_PRINT)

# search with multiple queries, combine results
def multisearch_authored(queries: List[str], DEBUG_PRINT: bool = False):

    followups = {}

    for query in queries:

        url = 'https://nlp.stampy.ai/api/search?query=' + quote(query)
        response = requests.get(url).json()
        for entry in response:
            followups[entry['pageid']] = Followup(entry['title'], entry['pageid'], entry['score'])

    followups = list(followups.values())

    followups.sort(key=lambda f: f.score, reverse=True)

    followups = followups[:MAX_FOLLOWUPS]

    if DEBUG_PRINT:
        print(" ------------------------------ suggested followups: -----------------------------")
        for followup in followups:
            if followup.score > SIMILARITY_THRESHOLD:
                print(f'{followup.score:.2f} - suggested to user')
            else:
                print(f'{followup.score:.2f} - not suggested')

            print(followup.text)
            print(followup.pageid)
            print()

    followups = [ f for f in followups if f.score > SIMILARITY_THRESHOLD ]

    return followups

    
