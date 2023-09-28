import os
import openai
import pinecone
from discord_webhook import DiscordWebhook

if os.path.exists('.env'):
    from dotenv import load_dotenv
    load_dotenv()
else:
    print("'api/.env' not found. Rename the 'api/.env.example' file and fill in values.")

FLASK_PORT = int(os.environ.get('FLASK_PORT', '3001'))

LOG_LEVEL           = os.environ.get("LOG_LEVEL", "WARNING").upper()
DISCORD_LOG_LEVEL   = os.environ.get("DISCORD_LOG_LEVEL", "WARNING").upper()
DISCORD_LOGGING_URL = os.environ.get('LOGGING_URL')

### OpenAI ###
OPENAI_API_KEY   = os.environ.get('OPENAI_API_KEY')
openai.api_key = OPENAI_API_KEY # non-optional

### Pinecone ###
PINECONE_API_KEY     = os.environ.get('PINECONE_API_KEY')
PINECONE_ENVIRONMENT = os.environ.get('PINECONE_ENVIRONMENT', "us-east1-gcp")
PINECONE_INDEX_NAME  = os.environ.get("PINECONE_INDEX_NAME", "alignment-search")
PINECONE_INDEX       = None
PINECONE_NAMESPACE   = os.environ.get("PINECONE_NAMESPACE", "alignment-search")  # "normal" or "finetuned" for the new index, "alignment-search" for the old one
# Only init pinecone if we have an env value for it.
if PINECONE_API_KEY:
    pinecone.init(
        api_key = PINECONE_API_KEY,
        environment = PINECONE_ENVIRONMENT,
    )

    PINECONE_INDEX = pinecone.Index(index_name=PINECONE_INDEX_NAME)

# log something only if the logging url is set
def log(*args, end="\n"):
    message = " ".join([str(arg) for arg in args]) + end
    # print(message)
    if DISCORD_LOGGING_URL is not None and DISCORD_LOGGING_URL != "":
        while len(message) > 2000 - 8:
            m_section, message = message[:2000 - 8], message[2000 - 8:]
            m_section = "```\n" + m_section + "\n```"
            DiscordWebhook(url=DISCORD_LOGGING_URL, content=m_section).execute()
        DiscordWebhook(url=DISCORD_LOGGING_URL, content="```\n" + message + "\n```").execute()

### MySQL ###
user = os.environ.get("CHAT_DB_USER", "user")
password = os.environ.get("CHAT_DB_PASSWORD", "we all live in a yellow submarine")
host = os.environ.get("CHAT_DB_HOST", "127.0.0.1")
port = os.environ.get("CHAT_DB_PORT", "3306")
db_name = os.environ.get("CHAT_DB_NAME", "stampy_chat")
DB_CONNECTION_URI = f"mysql+mysqlconnector://{user}:{password}@{host}:{port}/{db_name}"
