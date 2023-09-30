import json
from logging import *
from discord_webhook import DiscordWebhook
from stampy_chat.env import LOG_LEVEL, DISCORD_LOG_LEVEL, DISCORD_LOGGING_URL
from stampy_chat.db.session import ItemAdder
from stampy_chat.db.models import Interaction


MAX_MESSAGE_LEN = 2000 - 8

class DiscordHandler(StreamHandler):
    def emit(self, record):
        # Ignore messages that come from non chat modules
        if record.name.startswith('stampy_chat'):
            return

        # Ignore messages that have lower levels
        if record.levelno < getLevelName(DISCORD_LOG_LEVEL):
            return

        self.to_discord(self.format(record))

    def to_discord(self, message):
        if not DISCORD_LOGGING_URL:
            return

        while len(message) > MAX_MESSAGE_LEN:
            m_section, message = message[:MAX_MESSAGE_LEN], message[MAX_MESSAGE_LEN:]
            m_section = "```\n" + m_section + "\n```"
            DiscordWebhook(url=DISCORD_LOGGING_URL, content=m_section).execute()
        DiscordWebhook(url=DISCORD_LOGGING_URL, content="```\n" + message + "\n```").execute()


class ChatLogger(Logger):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.addHandler(DiscordHandler())
        self.item_adder = ItemAdder()

    def is_debug(self):
        return self.isEnabledFor(DEBUG)

    def interaction(self, session_id: str, query: str, response: str, history, prompt, blocks):
        prompt = [i for i in prompt if i.get('role') == 'system']
        prompt = prompt[0].get('content') if prompt else None

        self.item_adder.add(
            Interaction(
                session_id=session_id,
                interaction_no=len([i for i in history if i.get('role') == 'user']),
                query=query,
                prompt=prompt,
                response=response,
                chunks=",".join(b.id for b in blocks),
            )
        )
        self.info('query: %s', query)
        self.info('response: %s', response)

    def moderation_issue(self, query, prompt_string, mod_res):
        # this is a biiig ask of a discord webhook - put most important
        # info at start such that it's more likely to not be cut off
        messages = [
            '-' * 80,
            "MODERATION REJECTED",
            "MODERATION RESPONSE:\n\n" + json.dumps(mod_res["results"], indent=2),
            "REJECTED QUERY: " + query,
            "REJECTED PROMPT:\n\n " + prompt_string,
            '-' * 80,
        ]
        for message in messages:
            self.warn(message)


setLoggerClass(ChatLogger)
basicConfig(level=getLevelName(LOG_LEVEL))
