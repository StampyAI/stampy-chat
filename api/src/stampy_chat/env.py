import os
import openai
import pinecone
from discord_webhook import DiscordWebhook

if os.path.exists('.env'):
    from dotenv import load_dotenv
    load_dotenv()
else:
    print("'api/.env' not found. Rename the 'api/.env.example' file and fill in values.")


OPENAI_API_KEY   = os.environ.get('OPENAI_API_KEY')
PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY')
LOGGING_URL      = os.environ.get('LOGGING_URL')
PINECONE_INDEX   = None

FLASK_PORT = int(os.environ.get('FLASK_PORT', '3001'))

openai.api_key = OPENAI_API_KEY # non-optional

# Only init pinecone if we have an env value for it.
if PINECONE_API_KEY is not None and PINECONE_API_KEY != "":

    pinecone.init(
        api_key = PINECONE_API_KEY,
        environment = "us-east1-gcp",
    )

    PINECONE_INDEX = pinecone.Index(index_name="alignment-search")

# log something only if the logging url is set
def log(*args, end="\n"):
    message = " ".join([str(arg) for arg in args]) + end
    # print(message)
    if LOGGING_URL is not None and LOGGING_URL != "":
        while len(message) > 2000 - 8:
            m_section, message = message[:2000 - 8], message[2000 - 8:]
            m_section = "```\n" + m_section + "\n```"
            DiscordWebhook(url=LOGGING_URL, content=m_section).execute()
        DiscordWebhook(url=LOGGING_URL, content="```\n" + message + "\n```").execute()
