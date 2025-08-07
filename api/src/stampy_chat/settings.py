from collections import namedtuple
from typing import Any, Literal, TypedDict

from stampy_chat.env import COMPLETIONS_MODEL


Model = namedtuple(
    "Model", ["maxTokens", "topKBlocks", "maxCompletionTokens", "publisher"]
)

Mode = Literal["default", "concise", "rookie", "discord"]


class Prompts(TypedDict):
    system: str
    history: str
    history_summary: str
    pre_message: str
    post_message: str
    hyde_pre_message: str
    hyde_post_message: str
    modes: dict[Mode, str]
    message_format: str
    instruction_wrapper: str


# warning: when changing these prompts, also change useSettings.ts
SYSTEM_PROMPT = """
<miri-core-points>
<entire-source id="LL">
{yudkowsky-list-of-lethalities-2507132226-e11d43}
</entire-source>

<entire-source id="TP">
{miri-the-problem-2507121135-b502d1}
</entire-source>

<entire-source id="TB">
{miri-the-briefing-2507132220-44fbe5}
</entire-source>

<main-points>
{miri-the-problem-main-points-2507132222-1916a0}
</main-points>
</miri-core-points>
""".strip()
HISTORY_PROMPT = "{stampy-history-2507211352-060b74}"
HISTORY_SUMMARIZE_PROMPT = "{stampy-history_summary-2507231056-b048af}"

PRE_MESSAGE_PROMPT = ""

POST_MESSAGE_PROMPT = """
{detailed-cautious-epistem-safetyinfo-v6-2508050537-3644ff}

{post-message-2507220220-cff788}

{socratic-avoid-bad-questions-harder-2507220153-a11064}

{mode}
""".strip()

HYDE_POST_MESSAGE_PROMPT = """
{detailed-cautious-epistem-safetyinfo-v6-2508050537-3644ff}

{hyde_post_message-2507222109-597ed2}
""".strip()

INSTRUCTION_WRAPPER = """
<instructions>
{content}
</instructions>
""".strip()

PROMPT_MODES: dict[Mode, str] = {
    "default": "",
    "concise": "{mode-concise-2507231147-db01d9}",
    "rookie": "{mode-rookie-2507231143-f32d39}",
    "discord": "{mode-discord-2507231144-ffe1d1}",
}

MESSAGE_FORMAT = "<from-public-user>\n{message}\n</from-public-user>"

MESSAGE_FORMAT = "<from-public-user>\n{message}\n</from-public-user>"

DEFAULT_PROMPTS = Prompts(
    system=SYSTEM_PROMPT,
    history=HISTORY_PROMPT,
    history_summary=HISTORY_SUMMARIZE_PROMPT,
    pre_message=PRE_MESSAGE_PROMPT,
    post_message=POST_MESSAGE_PROMPT,
    hyde_pre_message="",
    hyde_post_message=HYDE_POST_MESSAGE_PROMPT,
    modes=PROMPT_MODES,
    message_format=MESSAGE_FORMAT,
    instruction_wrapper=INSTRUCTION_WRAPPER,
)

OPENAI = "openai"
ANTHROPIC = "anthropic"
GOOGLE = "google"
MODELS = {
    "openai/gpt-3.5-turbo": Model(4097, 10, 4096, OPENAI),
    "openai/gpt-3.5-turbo-16k": Model(16385, 30, 4096, OPENAI),
    "openai/o1": Model(128000, 50, 4096, OPENAI),
    "openai/o1-mini": Model(128000, 50, 4096, OPENAI),
    "openai/gpt-4": Model(8192, 20, 4096, OPENAI),
    "openai/gpt-4-turbo-preview": Model(128000, 50, 4096, OPENAI),
    "openai/gpt-4o": Model(128000, 50, 4096, OPENAI),
    "openai/gpt-4o-mini": Model(128000, 50, 4096, OPENAI),
    "openai/o4-mini": Model(128000, 50, 4096, OPENAI),
    "openai/o3": Model(128000, 50, 4096, OPENAI),
    "openai/gpt-4.1-nano": Model(128000, 50, 4096, OPENAI),
    "openai/gpt-4.1-mini": Model(128000, 50, 4096, OPENAI),
    "openai/gpt-4.1": Model(128000, 50, 4096, OPENAI),
    "anthropic/claude-3-opus-20240229": Model(200_000, 50, 4096, ANTHROPIC),
    "anthropic/claude-3-5-sonnet-20240620": Model(200_000, 50, 4096, ANTHROPIC),
    "anthropic/claude-3-5-sonnet-20241022": Model(200_000, 50, 4096, ANTHROPIC),
    "anthropic/claude-3-5-sonnet-latest": Model(200_000, 50, 4096, ANTHROPIC),
    "anthropic/claude-opus-4-20250514": Model(200_000, 50, 4096, ANTHROPIC),
    "anthropic/claude-sonnet-4-20250514": Model(200_000, 50, 4096, ANTHROPIC),
    #    "anthropic/claude-sonnet-4-20250514": Model(8000, 50, 8192, ANTHROPIC),
    #    "anthropic/claude-opus-4-20250514": Model(8000, 50, 8192, ANTHROPIC),
    "anthropic/claude-3-7-sonnet-latest": Model(200_000, 50, 4096, ANTHROPIC),
    "google/gemini-2.5-flash": Model(250_000, 50, 4096, GOOGLE),
    "google/gemini-2.5-pro": Model(250_000, 50, 4096, GOOGLE),
}

DEFAULT_MIRI_FILTERS = {
    "miri_confidence": 4,
    "miri_distance": [],
    "needs_tech": None,
}


def num_tokens(text, chars_per_token=4):
    """Calculate the number of tokens in a string."""
    return len(text) // chars_per_token


class Settings:
    encoders = {}

    def __init__(
        self,
        prompts: Prompts = DEFAULT_PROMPTS,
        mode: Mode = "default",
        completions=COMPLETIONS_MODEL,
        topKBlocks=None,
        maxNumTokens=None,
        enable_hyde=False,
        min_response_tokens=10,
        thinking_budget=2048,
        tokensBuffer=100,
        maxHistory=10,
        maxHistorySummaryTokens=200,
        hyde_max_tokens=100,
        historyFraction=0.25,
        contextFraction=0.5,
        filters=DEFAULT_MIRI_FILTERS,
        **_kwargs,
    ) -> None:
        self.prompts: Prompts = prompts
        self.mode: Mode = mode
        assert not any("hyde" in x for x in _kwargs.keys()), f"derp: {str(_kwargs)}"
        if self.mode_prompt is None:
            raise ValueError("Invalid mode: " + mode)

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

        self.thinking_budget = thinking_budget
        """the number of tokens to leave as a buffer for thinking"""

        self.enable_hyde = enable_hyde
        """the number of tokens to leave as a buffer for thinking"""

        self.hyde_max_tokens = hyde_max_tokens

        self.filters = filters

        if (
            self.context_tokens + self.history_tokens
            > self.maxNumTokens - self.min_response_tokens
        ):
            raise ValueError(
                "The context and history fractions are too large, please lower them: "
                f"max context tokens: {self.context_tokens}, max history tokens: {self.history_tokens}, "
                f"max total tokens: {self.maxNumTokens}, minimum reponse tokens {self.min_response_tokens}"
            )

    def __repr__(self) -> str:
        return f"<Settings mode: {self.mode}, completions: {self.completions}, tokens: {self.maxNumTokens}"

    def set_completions(self, completions, maxNumTokens=None, topKBlocks=None):
        if completions not in MODELS:
            raise ValueError(f"Unknown model: {completions}")
        self.completions = completions

        # Set the max number of tokens sent in the prompt - see https://platform.openai.com/docs/models/gpt-4
        if maxNumTokens is not None:
            self.maxNumTokens = int(maxNumTokens)
        else:
            self.maxNumTokens = MODELS[completions].maxTokens

        # Set the max number of blocks used as citations
        if topKBlocks is not None:
            self.topKBlocks = topKBlocks
        else:
            self.topKBlocks = MODELS[completions].topKBlocks

        self.maxCompletionTokens = MODELS[completions].maxCompletionTokens

    @property
    def completions_provider(self):
        if self.completions.startswith("google"):
            return "Gemini"
        elif self.completions.startswith("anthropic"):
            return "Claude"
        elif self.completions.startswith("openai"):
            return "GPT"
        raise ValueError(f"Unknown provider for completions model: {self.completions}")

    @property
    def prompt_modes(self) -> dict[Mode, str]:
        return self.prompts["modes"]

    @property
    def system_prompt(self):
        return self.prompts.get("system", self.prompts.get("context"))

    @property
    def history_prompt(self):
        return self.prompts["history"]

    @property
    def history_summary_prompt(self):
        return self.prompts["history_summary"]

    @property
    def mode_prompt(self) -> str:
        return self.prompt_modes.get(self.mode, "")

    @property
    def pre_message_prompt(self):
        return self.prompts["pre_message"]

    @property
    def post_message_prompt(self):
        return self.prompts["post_message"]

    @property
    def hyde_system_prompt(self):
        return self.prompts.get("hyde_pre_message", self.system_prompt)

    @property
    def hyde_pre_message_prompt(self):
        return self.prompts["hyde_pre_message"]

    @property
    def hyde_post_message_prompt(self):
        return self.prompts["hyde_post_message"]

    @property
    def message_format(self):
        return self.prompts.get("message_format", MESSAGE_FORMAT)

    @property
    def instruction_wrapper(self):
        return self.prompts.get("instruction_wrapper", INSTRUCTION_WRAPPER)

    @property
    def context_tokens(self):
        """The max number of tokens to be used for the context"""
        return int(self.maxNumTokens * self.contextFraction) - num_tokens(
            self.system_prompt
        )

    @property
    def history_tokens(self):
        """The max number of tokens to be used for the history"""
        return int(self.maxNumTokens * self.historyFraction) - num_tokens(
            self.history_prompt
        )

    @property
    def max_response_tokens(self):
        available_tokens = (
            self.maxNumTokens
            - self.maxHistorySummaryTokens
            - self.context_tokens
            - num_tokens(self.system_prompt)
            - self.history_tokens
            - num_tokens(self.history_prompt)
            - num_tokens(self.pre_message_prompt)
            - num_tokens(self.post_message_prompt)
            + self.thinking_budget
        )
        return min(available_tokens, self.maxCompletionTokens)

    @property
    def completions_model_provider(self):
        parts = self.completions.split("/")
        if len(parts) == 2:
            return parts[0]
        raise ValueError(
            f"Invalid completions model: {self.completions} - expected format: provider/model"
        )

    @property
    def completions_model_name(self):
        parts = self.completions.split("/")
        if len(parts) == 2:
            return parts[1]
        raise ValueError(
            f"Invalid completions model: {self.completions} - expected format: provider/model"
        )

    @property
    def miri_filters(self) -> dict[str, Any]:
        filters = {}
        if confidence := self.filters.get("miri_confidence"):
            filters["miri_confidence"] = {"$gte": confidence}
        if distance := self.filters.get("miri_distance"):
            filters["miri_distance"] = {"$in": distance}
        if needs_tech := self.filters.get("needs_tech"):
            filters["needs_tech"] = needs_tech
        return filters
