import json
from logging import *
from stampy_chat.env import LOG_LEVEL


class ChatLogger(Logger):

    def is_debug(self):
        return self.isEnabledFor(DEBUG)

    def query(self, query):
        self.info('query: %s', query)

    def response(self, response):
        self.info('response: %s', response)

    def moderation_issue(self, query, prompt_string, mod_res):
        # this is a biiig ask of a discord webhook - put most important
        # info at start such that it's more likely to not be cut off
        self.warn('-' * 80)
        self.warn("MODERATION REJECTED")
        self.warn("MODERATION RESPONSE:\n\n%s", json.dumps(mod_res["results"], indent=2))
        self.warn("REJECTED QUERY: %s", query)
        self.warn("REJECTED PROMPT:\n\n %s", prompt_string)
        self.warn('-' * 80)


setLoggerClass(ChatLogger)
basicConfig(level=getLevelName(LOG_LEVEL))
