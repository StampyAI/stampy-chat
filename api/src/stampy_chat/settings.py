from collections import namedtuple
import tiktoken

from stampy_chat.env import COMPLETIONS_MODEL


Model = namedtuple('Model', ['maxTokens', 'topKBlocks', 'maxCompletionTokens', 'publisher'])


SOURCE_PROMPT = (
    "You are a helpful assistant knowledgeable about AI Alignment and Safety. "
    "Please give a clear and coherent answer to the user's questions. (written after \"Q:\") "
    "using the following sources. Each source is labeled with a number. Feel free to "
    "use the sources in any order, and try to reference up to 8 sources in your answers.\n\n"
)
HISTORY_PROMPT = (
    "\n\n"
    "Before the question (\"Q: \"), there will be a history of previous questions and answers. "
    "These sources only apply to the last question. Any sources used in previous answers "
    "are invalid."
)
HISTORY_SUMMARIZE_PROMPT = (
    "You are a helpful assistant knowledgeable about AI Alignment and Safety. "
    "Please summarize the following chat history (written after \"H:\") in one "
    "sentence so as to put the current questions (written after \"Q:\") in context. "
    "Please keep things as terse as possible."
    "\nH:"
)

QUESTION_PROMPT = (
    "In your answer, please cite any claims you make back to each source "
    "using the format: [1], [2], etc. If you use multiple sources to make a claim "
    "cite all of them. For example: \"AGI is concerning [1, 3, 8].\"\n\n"
)
PROMPT_MODES = {
    'default': "",
    "concise": (
        "Answer very concisely, getting to the crux of the matter in as "
        "few words as possible. Limit your answer to 1-2 sentences.\n\n"
    ),
    "rookie": (
        "This user is new to the field of AI Alignment and Safety - don't "
        "assume they know any technical terms or jargon. Still give a complete answer "
        "without patronizing the user, but take any extra time needed to "
        "explain new concepts or to illustrate your answer with examples. "
        "Put extra effort into explaining the intuition behind concepts "
        "rather than just giving a formal definition.\n\n"
    ),
    "discord": (
        "Your answer will be used in a Discord channel, so please Answer concisely, getting to "
        "the crux of the matter in as few words as possible. Limit your answer to 1-2 paragraphs.\n\n"
    ),
}
DEFAULT_PROMPTS = {
    'context': SOURCE_PROMPT,
    'history': HISTORY_PROMPT,
    'history_summary': HISTORY_SUMMARIZE_PROMPT,
    'question': QUESTION_PROMPT,
    'modes': PROMPT_MODES,
}
OPENAI = 'openai'
ANTRHROPIC = 'anthropic'
MODELS = {
    'gpt-3.5-turbo': Model(4097, 10, 4096, OPENAI),
    'gpt-3.5-turbo-16k': Model(16385, 30, 4096, OPENAI),
    'gpt-4': Model(8192, 20, 4096, OPENAI),
    "gpt-4-turbo-preview": Model(128000, 50, 4096, OPENAI),
    "gpt-4o": Model(128000, 50, 4096, OPENAI),
    "claude-3-opus-20240229": Model(200_000, 50, 4096, ANTRHROPIC),
    "claude-3-sonnet-20240229": Model(200_000, 50, 4096, ANTRHROPIC),
    "claude-3-haiku-20240307": Model(200_000, 50, 4096, ANTRHROPIC),
    "claude-2.1": Model(200_000, 50, 4096, ANTRHROPIC),
    "claude-2.0": Model(100_000, 50, 4096, ANTRHROPIC),
    "claude-instant-1.2": Model(100_000, 50, 4096, ANTRHROPIC),
}


class Settings:

    encoders = {}

    def __init__(
            self,
            prompts=DEFAULT_PROMPTS,
            mode='default',
            completions=COMPLETIONS_MODEL,
            encoder='cl100k_base',
            topKBlocks=None,
            maxNumTokens=None,
            min_response_tokens=10,
            tokensBuffer=100,
            maxHistory=10,
            maxHistorySummaryTokens=200,
            historyFraction=0.25,
            contextFraction=0.5,
            **_kwargs,
    ) -> None:
        self.prompts = prompts
        self.mode = mode
        if self.mode_prompt is None:
            raise ValueError("Invalid mode: " + mode)

        self.encoder = encoder

        self.set_completions(completions, maxNumTokens, topKBlocks)

        self.tokensBuffer = tokensBuffer
        """the number of tokens to leave as a buffer when calculating remaining tokens"""

        self.maxHistory = maxHistory
        """the max number of previous interactions to use as the history"""

        self.maxHistorySummaryTokens = maxHistorySummaryTokens
        """the max number of tokens to be used on the history summary"""

        self.historyFraction = historyFraction
        """the (approximate) fraction of num_tokens to use for history text before truncating"""

        self.contextFraction = contextFraction
        """the (approximate) fraction of num_tokens to use for context text before truncating"""

        self.min_response_tokens = min_response_tokens
        """the minimum of tokens that must be left for the response"""

        if self.context_tokens + self.history_tokens > self.maxNumTokens - self.min_response_tokens:
            raise ValueError(
                'The context and history fractions are too large, please lower them: '
                f'max context tokens: {self.context_tokens}, max history tokens: {self.history_tokens}, '
                f'max total tokens: {self.maxNumTokens}, minimum reponse tokens {self.min_response_tokens}'
            )

    def __repr__(self) -> str:
        return f'<Settings mode: {self.mode}, encoder: {self.encoder}, completions: {self.completions}, tokens: {self.maxNumTokens}'

    @property
    def encoder(self):
        return self.encoders.get(self.encoder_name)

    @encoder.setter
    def encoder(self, value):
        self.encoder_name = value
        if value not in self.encoders:
            self.encoders[value] = tiktoken.get_encoding(value)

    def set_completions(self, completions, maxNumTokens=None, topKBlocks=None):
        if completions not in MODELS:
            raise ValueError(f'Unknown model: {completions}')
        self.completions = completions

        # Set the max number of tokens sent in the prompt - see https://platform.openai.com/docs/models/gpt-4
        if maxNumTokens is not None:
            self.maxNumTokens = maxNumTokens
        else:
            self.maxNumTokens = MODELS[completions].maxTokens

        # Set the max number of blocks used as citations
        if topKBlocks is not None:
            self.topKBlocks = topKBlocks
        else:
            self.topKBlocks = MODELS[completions].topKBlocks

        self.maxCompletionTokens = MODELS[completions].maxCompletionTokens

    @property
    def prompt_modes(self):
        return self.prompts['modes']

    @property
    def context_prompt(self):
        return self.prompts['context']

    @property
    def history_prompt(self):
        return self.prompts['history']

    @property
    def history_summary_prompt(self):
        return self.prompts['history_summary']

    @property
    def mode_prompt(self):
        return self.prompts['modes'].get(self.mode, '')

    @property
    def question_prompt(self):
        return self.prompts['question'] + self.mode_prompt

    @property
    def context_tokens(self):
        """The max number of tokens to be used for the context"""
        return int(self.maxNumTokens * self.contextFraction) - len(self.encoder.encode(self.context_prompt))

    @property
    def history_tokens(self):
        """The max number of tokens to be used for the history"""
        return int(self.maxNumTokens * self.historyFraction) - len(self.encoder.encode(self.history_prompt))

    @property
    def max_response_tokens(self):
        available_tokens = (
            self.maxNumTokens - self.maxHistorySummaryTokens -
            self.context_tokens - len(self.encoder.encode(self.context_prompt)) -
            self.history_tokens - len(self.encoder.encode(self.history_prompt)) -
            len(self.encoder.encode(self.question_prompt))
        )
        return min(available_tokens, self.maxCompletionTokens)
