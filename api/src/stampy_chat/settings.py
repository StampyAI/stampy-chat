import tiktoken

from stampy_chat.env import COMPLETIONS_MODEL


SOURCE_PROMPT = (
    "You are a helpful assistant knowledgeable about AI Alignment and Safety. "
    "Please give a clear and coherent answer to the user's questions.(written after \"Q:\") "
    "using the following sources. Each source is labeled with a letter. Feel free to "
    "use the sources in any order, and try to use multiple sources in your answers.\n\n"
)
SOURCE_PROMPT_SUFFIX = (
    "\n\n"
    "Before the question (\"Q: \"), there will be a history of previous questions and answers. "
    "These sources only apply to the last question. Any sources used in previous answers "
    "are invalid."
)

QUESTION_PROMPT = (
    "In your answer, please cite any claims you make back to each source "
    "using the format: [a], [b], etc. If you use multiple sources to make a claim "
    "cite all of them. For example: \"AGI is concerning [c, d, e].\"\n\n"
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
}
DEFAULT_PROMPTS = {
    'source': {
        'prefix': SOURCE_PROMPT,
        'suffix': SOURCE_PROMPT_SUFFIX,
    },
    'question': QUESTION_PROMPT,
    'modes': PROMPT_MODES,
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
            numTokens=None,
            tokensBuffer=50,
            maxHistory=10,
            historyFraction=0.25,
            contextFraction=0.5,
            **_kwargs,
    ) -> None:
        self.prompts = prompts
        self.mode = mode
        if self.mode_prompt is None:
            raise ValueError("Invalid mode: " + mode)

        self.encoder = encoder

        self.set_completions(completions, numTokens, topKBlocks)

        self.tokensBuffer = tokensBuffer
        """the number of tokens to leave as a buffer when calculating remaining tokens"""

        self.maxHistory = maxHistory
        """the max number of previous interactions to use as the history"""

        self.historyFraction = historyFraction
        """the (approximate) fraction of num_tokens to use for history text before truncating"""

        self.contextFraction = contextFraction
        """the (approximate) fraction of num_tokens to use for context text before truncating"""

    def __repr__(self) -> str:
        return f'<Settings mode: {self.mode}, encoder: {self.encoder}, completions: {self.completions}, tokens: {self.numTokens}'

    @property
    def encoder(self):
        return self.encoders.get(self.encoder_name)

    @encoder.setter
    def encoder(self, value):
        self.encoder_name = value
        if value not in self.encoders:
            self.encoders[value] = tiktoken.get_encoding(value)

    def set_completions(self, completions, numTokens=None, topKBlocks=None):
        self.completions = completions

        # Set the max number of tokens sent in the prompt
        if numTokens is not None:
            self.numTokens = numTokens
        elif completions == 'gtp-4':
            self.numTokens = 8191
        else:
            self.numTokens = 4095

        # Set the max number of blocks used as citations
        if topKBlocks is not None:
            self.topKBlocks = topKBlocks
        elif completions == 'gtp-4':
            self.topKBlocks = 20
        else:
            self.topKBlocks = 10

    @property
    def prompt_modes(self):
        return self.prompts['modes']

    @property
    def source_prompt_prefix(self):
        return self.prompts['source']['prefix']

    @property
    def source_prompt_suffix(self):
        return self.prompts['source']['suffix']

    @property
    def mode_prompt(self):
        return self.prompts['modes'].get(self.mode)

    def question_prompt(self, query: str):
        return self.prompts['question'] + self.mode_prompt + 'Q: ' + query

    @property
    def context_tokens(self):
        """The max number of tokens to be used for the context"""
        return int(self.numTokens * self.contextFraction)

    @property
    def history_tokens(self):
        """The max number of tokens to be used for the history"""
        return int(self.numTokens * self.historyFraction)
