from collections import namedtuple
from typing import Any, Literal, TypedDict
from dataclasses import dataclass

from stampy_chat.env import MODEL
from frozendict import frozendict, deepfreeze


Model = namedtuple(
    "Model", ["maxTokens", "topKBlocks", "maxCompletionTokens", "can_think", "min_think"]
)

Mode = Literal["default", "concise", "rookie", "discord"]


class Prompts(TypedDict):
    system: str
    history: str
    history_summary: str
    pre_message: str
    post_message: str
    modes: dict[Mode, str]
    message_format: str
    instruction_wrapper: str


# warning: when changing these prompts, also change useSettings.ts
SYSTEM_PROMPT = """
<core-reference-documents>
<entire-source id="LL">
{yudkowsky-list-of-lethalities-2507132226-e11d43}
</entire-source>

<entire-source id="TP">
{miri-the-problem-2507121135-b502d1}
</entire-source>

<entire-source id="TB">
{miri-the-briefing-2507132220-44fbe5}
</entire-source>

<summary-points>
{miri-the-problem-main-points-2507132222-1916a0}
</summary-points>
</core-reference-documents>
""".strip()
HISTORY_PROMPT = "{stampy-history-2507211352-060b74}"
HISTORY_SUMMARIZE_PROMPT = "{stampy-history_summary-2507231056-b048af}"

PRE_MESSAGE_PROMPT = ""

POST_MESSAGE_PROMPT = """
{post_message_new_noconfabwarn-2602182346-ce4775}

{mode}
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

MESSAGE_FORMAT = "<from-public-user id=\"{message_id}\">\n{message}\n</from-public-user>"

DEFAULT_PROMPTS = Prompts(
    system=SYSTEM_PROMPT,
    history=HISTORY_PROMPT,
    history_summary=HISTORY_SUMMARIZE_PROMPT,
    pre_message=PRE_MESSAGE_PROMPT,
    post_message=POST_MESSAGE_PROMPT,
    modes=PROMPT_MODES,
    message_format=MESSAGE_FORMAT,
    instruction_wrapper=INSTRUCTION_WRAPPER,
)

MODELS = {
    # Current models (dateless IDs)
    "anthropic/claude-sonnet-4-6":                  Model(200_000, 20, 16000, True,  1024),
    "anthropic/claude-opus-4-6":                    Model(200_000, 20, 16000, True,  1024),
    "anthropic/claude-haiku-4-5":                   Model(200_000, 20, 8192,  False, 0),
    # Dated aliases (still work)
    "anthropic/claude-sonnet-4-5-20250929":         Model(200_000, 20, 8192,  True,  1024),
    "anthropic/claude-opus-4-5-20251101":           Model(200_000, 20, 16000, True,  1024),
    "anthropic/claude-sonnet-4-20250514":           Model(200_000, 20, 4096,  True,  1024),
    "anthropic/claude-opus-4-20250514":             Model(200_000, 20, 4096,  True,  1024),
    "anthropic/claude-3-7-sonnet-latest":           Model(200_000, 20, 4096,  True,  1024),
    "anthropic/claude-3-5-sonnet-latest":           Model(200_000, 20, 4096,  False, 0),
}

DEFAULT_MIRI_FILTERS = {
    "miri_confidence": 6,
    "miri_distance": [],
}


def num_tokens(text, chars_per_token=4):
    """Calculate the number of tokens in a string."""
    if isinstance(text, str):
        return len(text) // chars_per_token
    return 0  # block-structured content -- can't easily count


@dataclass(frozen=True)
class Settings:
    encoders = {}

    prompts: frozendict = frozendict(DEFAULT_PROMPTS)
    mode: Mode = "default"
    model: str = MODEL
    topKBlocks: int = None
    maxNumTokens: int = None
    maxCompletionTokens: int = None
    min_response_tokens: int = 10
    thinking_budget: int = 2048
    tokensBuffer: int = 100
    maxHistory: int = 10
    maxHistorySummaryTokens: int = 200
    historyFraction: float = 0.25
    contextFraction: float = 0.5
    filters: frozendict = frozendict(DEFAULT_MIRI_FILTERS)

    def __init__(
        self,
        prompts: Prompts = DEFAULT_PROMPTS,
        mode: Mode = "default",
        model=MODEL,
        modelID=None,
        topKBlocks=None,
        maxNumTokens=None,
        min_response_tokens=10,
        thinking_budget=2048,
        tokensBuffer=100,
        maxHistory=10,
        maxHistorySummaryTokens=200,
        historyFraction=0.25,
        contextFraction=0.5,
        filters=DEFAULT_MIRI_FILTERS,
        **_kwargs,
    ):
        if modelID is not None:
            model = modelID

        frozen_prompts = deepfreeze(prompts)

        if frozen_prompts.get("modes", {}).get(mode) is None and mode != "default":
            raise ValueError("Invalid mode: " + mode)

        if model not in MODELS:
            raise ValueError(f"Unknown model: {model}")

        if maxNumTokens is None:
            maxNumTokens = MODELS[model].maxTokens
        if topKBlocks is None:
            topKBlocks = MODELS[model].topKBlocks
        maxCompletionTokens = MODELS[model].maxCompletionTokens

        object.__setattr__(self, "prompts", frozen_prompts)
        object.__setattr__(self, "mode", mode)
        object.__setattr__(self, "model", model)
        object.__setattr__(self, "topKBlocks", topKBlocks)
        object.__setattr__(self, "maxNumTokens", maxNumTokens)
        object.__setattr__(self, "maxCompletionTokens", maxCompletionTokens)
        object.__setattr__(self, "min_response_tokens", min_response_tokens)
        object.__setattr__(self, "thinking_budget", thinking_budget)
        object.__setattr__(self, "tokensBuffer", tokensBuffer)
        object.__setattr__(self, "maxHistory", maxHistory)
        object.__setattr__(self, "maxHistorySummaryTokens", maxHistorySummaryTokens)
        object.__setattr__(self, "historyFraction", historyFraction)
        object.__setattr__(self, "contextFraction", contextFraction)
        object.__setattr__(self, "filters", deepfreeze(filters))

    def __repr__(self) -> str:
        return f"<Settings mode: {self.mode}, model: {self.model}, tokens: {self.maxNumTokens}"

    def __hash__(self) -> int:
        def freeze_deep(obj):
            if isinstance(obj, dict):
                return frozendict({k: freeze_deep(v) for k, v in obj.items()})
            elif isinstance(obj, list):
                return tuple(freeze_deep(item) for item in obj)
            return obj

        return hash((
            freeze_deep(self.prompts),
            self.mode,
            self.model,
            self.maxNumTokens,
            self.topKBlocks,
            self.tokensBuffer,
            self.maxHistory,
            self.maxHistorySummaryTokens,
            self.historyFraction,
            self.contextFraction,
            self.min_response_tokens,
            self.thinking_budget,
        ))

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
    def message_format(self):
        return self.prompts.get("message_format", MESSAGE_FORMAT)

    @property
    def instruction_wrapper(self):
        return self.prompts.get("instruction_wrapper", INSTRUCTION_WRAPPER)

    @property
    def history_tokens(self):
        """The max number of tokens to be used for the history"""
        return int(self.maxNumTokens * self.historyFraction) - num_tokens(
            self.history_prompt
        )

    @property
    def max_response_tokens(self):
        model_info = MODELS[self.model]
        if model_info.can_think and self.thinking_budget > 0:
            return self.maxCompletionTokens + max(model_info.min_think, self.thinking_budget)
        return self.maxCompletionTokens

    @property
    def model_id(self):
        _, slash, model = self.model.partition("/")
        if slash != "/":
            raise ValueError(
                f"Invalid model: {self.model} - expected format: provider/model"
            )
        return model

    @property
    def model_given_name(self):
        return "Claude"

    @property
    def miri_filters(self) -> dict[str, Any]:
        filters = {}
        if self.filters.get("needs_tech"):
            filters["needs_tech"] = True
        else:
            filters["needs_tech"] = {"$ne": True}

        if confidence := self.filters.get("miri_confidence"):
            filters["miri_confidence"] = {"$gte": confidence}
        if distance := self.filters.get("miri_distance"):
            filters["miri_distance"] = {"$in": distance}
        return filters
