# main.py

import os
if os.path.exists('src/.env'):
    from dotenv import load_dotenv
    load_dotenv()
else:
    raise Exception("'src/.env' not found. Rename the 'src/.env.example' file and fill in values.")

import openai
openai.api_key = os.environ['OPENAI_API_KEY']

import logging
logging.basicConfig(level=logging.INFO)

from dataset.update_dataset import ARDUpdater


def update_sql_and_pinecone_dbs():
    updater = ARDUpdater(
        min_tokens_per_block=200,
        max_tokens_per_block=300,
    )
    updater.update(['gwern_blog'])


if __name__ == "__main__":
    update_sql_and_pinecone_dbs()