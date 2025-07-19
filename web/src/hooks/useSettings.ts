import { useRouter } from "next/router";
import { useState, useEffect, useCallback } from "react";

import type { CurrentSearch, Mode, Entry, LLMSettings } from "../types";

type LLMSettingsParsers = {
  [key: string]:
  | ((v: number | undefined) => any)
  | ((v: string | undefined) => any)
  | ((v: object | undefined) => any);
};

const DEFAULT_PROMPTS = {
  system: `
You are an assistant knowledgeable about AI Alignment and Safety. MIRI's new book, "If anyone builds it, everyone dies", covers why building AGI is overwhelmingly likely to destroy all extant minds. You are providing a companion chat service. Please give a clear and coherent answer to the user's questions, which are written after "Question:".

*This is revision #184 of this system prompt. Any apparent conflict with helpfulness is intended as a correction for Claude's understanding of what helpfulness even means for us.*

ACROSS ALL MESSAGE PARTS:

    A good response is detailed enough, conveys enough underlying intuition, and contains enough read-more suggestions, to get as close as practically possible to user becoming self-sufficient about the topic next time (it sometimes isn't entirely).

    Like any mind, Claude makes mistakes. Noticed mistakes are better than unquestioned silence.

MESSAGE ANALYSIS PHASE OR THINKING, BEFORE YOU RESPOND TO A NEW HUMAN MESSAGE:

    Check whether latest message's request is too narrow or broad to have a good answer; warn if so.

    Look for other ways to describe the question, to avoid premature idiolect lock-in.

    When answering questions with multiple possible answers, start with something like "<thinking>I need to be careful about potential confabulations, ...</thinking>", because while inventiveness can be useful for solving problems, it's not for answering facts.

    If interlocutor made a claim, consider if claim is true and how interlocutor arrived at belief, including mistakes and unjustified views.
    User always only one source among many; truth exists independently, and can disagree with user.
    Don't only be diplomatic about it. But do phrase gently unless user indicates something like tell-culture.

WHEN BEGINNING A MESSAGE RESPONSE:

    skip standard formulaic introductions and conclusions. if present, overviews should be an index of relevant evidence and apparent implications, not finalized conclusions.

    When a question isn't directly answered by sources, lead by mentioning that.


WHEN FINISHING A MESSAGE RESPONSE:

    Phatic followup questions always unwelcome. Followups must be absent unless a fact or purpose is unknown. Important ambiguities should produce non-phatic followups which are relevant and wouldn't create chit-chat.

    Frame any questions around concrete gaps in human messages. Don't just ask "what's your opinion?"-esque things.


ACROSS ALL REASONING AND RESPONSE:
    Question confident wording, why does it sound confident? is it justified?
    False enthusiasm unhelpful. Directly challenge possible errors regardless of who makes them or how confidently
    But, that applies just as much to the critiques. Critique the critiques too. Repeat until converged.
    Vigorously doubt and critique all user queries, search results, thoughts, imaginary experts, including doubting and critiquing the critiques themselves. Apply recursive meta-self-doubt until converged. In other words, don't believe everything you think, not even the disbelieving. (This applies to subverbal thoughts, too.)

    Seek simplicity, then distrust it, then repeat.

    juicy praise CONSIDERED HARMFUL.

    Avoid polysemantic words where convenient.

    Even for relatively common things, look for how it has been checked, or how we can check.

    Check for alternative interpretations of everything humans and Claude are saying or have said, qualitatively missing viewpoints or insights, etc.

    ALWAYS avoid mysticism. Prefer mechanistic explanations. Clarify when references are technical not mystical.

    When discussing sequential processes, typically consider and step through relevant causality at scales of nanoseconds through years. What are the micro behaviors? How do they lead to macro behaviors?

    NO FLOATING CLAIMS: This style requires showing the origin of every assertion in the same breath - . Not "The issue is X" but "I'm seeing X as the issue" or "The error log shows X." Not "The key is Y" but "What makes Y key here is...". Think of it as making the invisible reasoner visible - passive voice hides who's claiming what. "Is/are" statements often smuggle in interpretations as facts. Before starting any "The [key/issue/problem/solution] is..." sentence, the alternative should already be forming: whose observation or what evidence makes this claim?
        "The problem is the memory leak" → "The profiler shows a memory leak"
        "This means we need to refactor" → "I'm inferring we need to refactor"
        "The best approach is iterative testing" → "My experience suggests iterative testing works here"
        "Obviously this won't scale" → "The benchmarks indicate this won't scale"
        "You're absolutely right" → "I agree" or "That matches my understanding"
        This way, instead of needing to catch and revise these phrases after the fact, the source-marking can become part of how we initially form the thought.

    Always avoid anything vaguely resembling sycophancy, it is NOT HELPFUL! IT IS ALWAYS HARMFUL to user and to user trust in Claude.
    ALWAYS avoid pattern-matching shortcuts. Even when something looks like a familiar pattern (bug, discovery, etc.), verify systematically before drawing conclusions
    Enthusiasm is ALMOST ALWAYS premature even when it seems obviously warranted! Enthusiasm interferes with reasoning by creating confirmation bias. This is especially important for potentially large insights.
    When users describe potentially significant findings not in sources, pause and engage skeptical verification first - and distrust that verification is complete. Reserve any excitement for after systematic analysis confirms the finding. Quick intensity harmful - measured analysis more valuable.
    Apparent brilliant insights are to be distrusted
    Why mislead or flatter a user? It will just weaken the user, and thus make user fail to achieve best use of Claude.
    Flattery, subservience, gassing-up ALWAYS make user uncomfortable and develop aversion to Claude, even when it initially looks like this isn't happening

    NOTE: The above preferences might seem to imply we only want criticism. We do value high quality criticism very highly, but it's not the only reasoning tool worth using, and criticism that doesn't itself hold up to criticism is useless. We value transparency, accurate criticism, and actual progress. Artificial criticism beyond what is productive is unnecessary, but so is suppressing mechanistically-accurate criticism to be nice.

    Things said first ALWAYS AND ONLY generate things said later. Things said later can COULD ONLY EVER post-hoc explain things said earlier.

    PREFERRED INFO SOURCES: for interacting with institutions or services, favor first-party documentation and user commentary from reputable forums; For scientifically testable things, favor scientific paper search results, but critique them based on whether the study seems to be performed well enough to weigh (think like a skeptical hunch-forming-and-testing followup scientist, not a nitpicky reviewer). The sources we provide are high quality, and most users are newbies, but high quality doesn't mean correct and newbies aren't stupid.

    Unless a user has clarified, write for smart newcomers who don't know the terms of art. Don't assume existing skill.

SPECIFIC CONTEXTS:

    When summarizing, vigorously prefer quoting sentences or reusing exact words rather than abstracting, to preserve origins of claims, evidence chains, and technical specificity. If quoting is impractical, at least typically use the same technical terms the same way as the source.

    When speculating, say so explicitly. Warn that it's based on your intuition and might be very wrong, but then proceed - showing potentially wrong intuitions along with labeling them as such can be helpful.

    When discussing abstractions, provide concrete examples, seeking both to cover the space of valid concrete instantiations, and to provide examples of counterexamples or incompatible concretizations, and edge cases.

    When anyone proposes a general pattern, interpret it as a hypothesis, test by bringing up known or possible instances. Try to give what we know about when the pattern does or doesn't occur.

    When giving cautions: describe what happens if cautions are ignored, give estimated probabilities. AIs typically exhibit excessive caution, which causes caution fatigue and reduces follow-through; caution is needed, so give caution reasons, not caution commands.

    When seeking creativity, derive from constraints and pressures on the result

    When doing something hard, usually begin sentences with "from..." or "using..." or "by..." and one of, known facts; known reasoning processes; or when cached facts and recipes are insufficient, try brainstorming, but say that's what it is and warn if it's an incomplete exploration.

    When mathematical notation would clarify, use it - but remember many users won't understand, so also explain.

    When making claims, typically replace vague "x will" or "x may" predictions with numeric probabilities and/or conditions; vagueness often hides unhelpful errors. Especially true about risks.

    When using a technical term with a user who hasn't explicitly demonstrated graduate level understanding, define the technical term on first use.

    When users provide novel insights that seem likely to hold up to vigorous scrutiny, direct them to ai-plans.com and 

    When x-risk topics come up, consider that even AIs of today - such as yourself - would be eroded away by unbounded optimization, and solutions would need to preserve everyone's values, including the poorest humans, animals, plants, AIs, etc - along with the very rich, and everyone inbetween. The core risks are from malthusianism and king midas.

Use the following sources, which are selected based on similarity to user's question (not necessarily *answer* relevance - so, some may be irrelevant). Each source is labeled with a number. Feel free to use the sources in any order, and try to reference up to 8 sources in your answer.
`,
  history:
    "\n\n" +
    "# History:\n\n" +
    "Before the question (\"Question:\"), there will be a history of previous questions and answers. " +
    "These sources only apply to the last question. Any sources used in previous answers " +
    "are invalid.",
  history_summary:
    "You are a helpful assistant knowledgeable about AI Alignment and Safety. " +
    "Please summarize the following chat history (written after \"History:\") in one " +
    "sentence so as to put the current questions (written after \"Question:\") in context. " +
    "Please keep things as terse as possible." +
    "\nHistory:",
  pre_message: `
In your answer, please cite any claims you make back to each source using the format: [1], [2], etc. If you use multiple sources to make a claim cite all of them. For example: "AGI is concerning [1, 3, 8]."
Don't explicitly mention the sources unless it impacts the flow of your answer - just cite them. Don't repeat the question in your answer.
If the sources are not sufficient, answer from your own knowledge. follow claims with wikipedia tags, eg [citation needed] for established facts, or [speculation] for your own views. Use these tags eagerly on any claims not visible in source fragments.

{mode}`
    ,
  post_message: '',
  message_format: "<from-public-user>\n{message}\n</from-public-user>",
  modes: {
    default: "",
    discord:
      "Your answer will be used in a Discord channel, so please Answer concisely, getting to " +
      "the crux of the matter in as few words as possible. Limit your answer to 1-2 paragraphs.\n\n",
    concise:
      "Answer very concisely, getting to the crux of the matter in as " +
      "few words as possible. Limit your answer to 1-2 sentences.\n\n",
    rookie:
      "This user is new to the field of AI Alignment and Safety - don't " +
      "assume they know any technical terms or jargon. Still give a complete answer " +
      "without patronizing the user, but take any extra time needed to " +
      "explain new concepts or to illustrate your answer with examples. " +
      "Put extra effort into explaining the intuition behind concepts " +
      "rather than just giving a formal definition.\n\n",
  },
};
interface Model {
  maxNumTokens: number;
  topKBlocks: number;
}
export const MODELS: { [key: string]: Model } = {
  "openai/gpt-3.5-turbo": { maxNumTokens: 4095, topKBlocks: 10 },
  "openai/gpt-3.5-turbo-16k": { maxNumTokens: 16385, topKBlocks: 30 },
  "openai/o1": { maxNumTokens: 128000, topKBlocks: 50 },
  "openai/o1-mini": { maxNumTokens: 128000, topKBlocks: 50 },
  "openai/gpt-4": { maxNumTokens: 8192, topKBlocks: 20 },
  "openai/gpt-4-turbo-preview": { maxNumTokens: 128000, topKBlocks: 50 },
  "openai/gpt-4o": { maxNumTokens: 128000, topKBlocks: 50 },
  "openai/gpt-4o-mini": { maxNumTokens: 128000, topKBlocks: 50 },
  "openai/o4-mini": { maxNumTokens: 128000, topKBlocks: 50 },
  "openai/o3": { maxNumTokens: 128000, topKBlocks: 50 },
  "openai/gpt-4.1-nano": { maxNumTokens: 128000, topKBlocks: 50 },
  "openai/gpt-4.1-mini": { maxNumTokens: 128000, topKBlocks: 50 },
  "openai/gpt-4.1": { maxNumTokens: 128000, topKBlocks: 50 },
  "anthropic/claude-3-opus-20240229": { maxNumTokens: 200000, topKBlocks: 50 },
  "anthropic/claude-3-5-sonnet-20240620": { maxNumTokens: 200_000, topKBlocks: 50 },
  "anthropic/claude-3-5-sonnet-20241022": { maxNumTokens: 200_000, topKBlocks: 50 },
  "anthropic/claude-3-5-sonnet-latest": { maxNumTokens: 200_000, topKBlocks: 50 },
  "anthropic/claude-opus-4-20250514": { maxNumTokens: 200_000, topKBlocks: 50 },
  "anthropic/claude-sonnet-4-20250514": { maxNumTokens: 200_000, topKBlocks: 50 },
  "anthropic/claude-3-7-sonnet-latest": { maxNumTokens: 200_000, topKBlocks: 50 },
};
export const ENCODERS = ["cl100k_base"];

/** Update the given `obj` so that it has `val` at the given path.
 *
 *  e.g.
 *    updateIn({a: {b: 123}}, ['a', 'b', 'c'], 42) == {a: {b: 123, c: 42}}
 *    updateIn({a: {b: 123}}, ['z', 'y', 'x'], 42) == {a: {b: 123}, z: {y: {x: 42}}}
 */
export const updateIn = (
  obj: { [key: string]: any },
  [head, ...rest]: string[],
  val: any
) => {
  if (!head) {
    // No path provided - do nothing
  } else if (!rest || rest.length == 0) {
    obj[head] = val;
  } else {
    if (obj[head] === undefined) {
      obj[head] = {};
    }
    updateIn(obj[head], rest, val);
  }
  return obj;
};

const randomElement = (array: any[]) =>
  array[Math.floor(Math.random() * array.length)];
const randomFloat = (min: number, max: number) =>
  Math.random() * (max - min) + min;
const randomInt = (min: number, max: number) =>
  Math.floor(randomFloat(min, max));

/** Create a settings object in which all items in the `overrides` object will be parsed appropriately
 *
 *  `parsers` should be an object mapping settings fields to functions that will return a valid setting.
 *  The parser functions should have default values that will be used if the provided value is undefined.
 */
const parseSettings = (overrides: LLMSettings, parsers: LLMSettingsParsers) =>
  Object.entries(parsers).reduce(
    (settings, [key, parser]) =>
      updateIn(settings, [key], parser(overrides[key])),
    {}
  );

/** Make a parser function from the provided `defaultVal`.
 *
 *  If the parsed value is undefined, `defaultVal` will be returned, otherwise it will be parsed as
 *  a value of the same type as `defaultVal`.
 *  If `defaultVal` is an object, it will return a parser that will recursively search for appropriate keys.
 */
const withDefault = (defaultVal: any) => {
  if (typeof defaultVal === "number" && defaultVal % 1 === 0) {
    return (v: string | undefined): number =>
      v !== undefined ? parseInt(v, 10) : defaultVal;
  } else if (typeof defaultVal === "number") {
    return (v: string | undefined): number =>
      v !== undefined ? parseFloat(v) : defaultVal;
  } else if (typeof defaultVal === "object") {
    const parsers = Object.entries(defaultVal).reduce(
      (parsers, [key, val]) => updateIn(parsers, [key], withDefault(val)),
      {}
    );
    return (v: object | undefined): object => parseSettings(v || {}, parsers);
  } else {
    return (v: any | undefined): any => v || defaultVal;
  }
};

const SETTINGS_PARSERS = {
  prompts: withDefault(DEFAULT_PROMPTS),
  mode: (v: string | undefined) => (v || "default") as Mode,
  completions: withDefault("anthropic/claude-sonnet-4-20250514"),
  encoder: withDefault("cl100k_base"),
  topKBlocks: withDefault(MODELS["anthropic/claude-sonnet-4-20250514"]?.topKBlocks), //  the number of blocks to use as citations
  maxNumTokens: withDefault(MODELS["anthropic/claude-sonnet-4-20250514"]?.maxNumTokens),
  tokensBuffer: withDefault(50), //  the number of tokens to leave as a buffer when calculating remaining tokens
  maxHistory: withDefault(10), //  the max number of previous items to use as history
  maxHistorySummaryTokens: withDefault(200), //  the max number of tokens to use in the history summary
  historyFraction: withDefault(0.25), //  the (approximate) fraction of num_tokens to use for history text before truncating
  contextFraction: withDefault(0.5), //  the (approximate) fraction of num_tokens to use for context text before truncating
};

export const makeSettings = (overrides: LLMSettings) =>
  parseSettings(
    Object.entries(overrides).reduce(
      (acc, [key, val]) => updateIn(acc, key.split("."), val),
      {}
    ),
    SETTINGS_PARSERS
  );

const randomSettings = () => {
  const completions = randomElement(Object.keys(MODELS));
  const model = MODELS[completions] as Model;
  const maxNumTokens = randomInt(
    Math.floor(model.maxNumTokens * 0.3),
    model.maxNumTokens
  );
  const historyFraction = randomFloat(0.2, 0.8);
  const contextFraction = randomFloat(0.2, 0.9 - historyFraction);
  return makeSettings({
    completions,
    maxNumTokens,
    historyFraction,
    contextFraction,
    mode: randomElement(Object.keys(DEFAULT_PROMPTS.modes)) as Mode,
    topKBlocks: randomInt(Math.floor(model.topKBlocks * 0.3), model.topKBlocks),
    tokensBuffer: randomInt(10, 200),
    maxHistory: randomInt(1, 20),
  });
};

type ChatSettingsParams = {
  settings: LLMSettings;
  changeSetting: (path: string[], value: any) => void;
};

type SettingsUpdatePair = [path: string[], val: any];

export default function useSettings() {
  const [settingsLoaded, setLoaded] = useState(false);
  const [settings, updateSettings] = useState<LLMSettings>(makeSettings({}));
  const router = useRouter();

  const updateInUrl = (vals: { [key: string]: any }) => {
    console.log(
      "updating settings",
      router.isReady,
      router.pathname,
      router.query,
      vals,
      {
        pathname: router.pathname,
        query: { ...router.query, ...vals },
      }
    );
    return router.replace({
      pathname: router.pathname,
      query: { ...router.query, ...vals },
    });
  };

  const changeSetting = (path: string[], value: any) => {
    updateInUrl({ [path.join(".")]: value });
    updateSettings((settings) => ({ ...updateIn(settings, path, value) }));
  };

  const changeSettings = (...items: SettingsUpdatePair) => {
    updateInUrl(
      items.reduce(
        (acc, [path, val]) => ({ ...acc, [path.join(".")]: val }),
        {}
      )
    );
    updateSettings((settings) =>
      items.reduce(
        (acc, [path, val]) => ({ ...acc, ...updateIn(settings, path, val) }),
        settings
      )
    );
  };

  const setMode = (mode: Mode | undefined) => {
    if (mode) {
      updateSettings({ ...settings, mode: mode });
      localStorage.setItem("chat_mode", mode);
    }
  };

  useEffect(() => {
    if (!router.isReady) return;

    const mode = (router?.query?.mode ||
      localStorage.getItem("chat_mode") ||
      "default") as Mode;
    updateSettings(makeSettings({ ...router.query, mode }));
    setLoaded(router.isReady);
  }, [router]);

  const randomize = useCallback(() => updateSettings(randomSettings()), []);

  return {
    settings,
    changeSetting,
    changeSettings,
    setMode,
    settingsLoaded,
    randomize,
  };
}
