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
  context:
    "You are a helpful assistant knowledgeable about AI Alignment and Safety. " +
    'Please give a clear and coherent answer to the user\'s questions.(written after "Q:") ' +
    "using the following sources. Each source is labeled with a letter. Feel free to " +
    "use the sources in any order, and try to use multiple sources in your answers.\n\n",
  history:
    "\n\n" +
    'Before the question ("Q: "), there will be a history of previous questions and answers. ' +
    "These sources only apply to the last question. any sources used in previous answers " +
    "are invalid.",
  history_summary:
    "You are a helpful assistant knowledgeable about AI Alignment and Safety. " +
    'Please summarize the following chat history (written after "H:") in one ' +
    'sentence so as to put the current questions (written after "Q:") in context. ' +
    "Please keep things as terse as possible." +
    "\nH:",
  question:
    "In your answer, please cite any claims you make back to each source " +
    "using the format: [a], [b], etc. If you use multiple sources to make a claim " +
    'cite all of them. For example: "AGI is concerning [c, d, e]."\n\n',
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
  "gpt-3.5-turbo": { maxNumTokens: 4095, topKBlocks: 10 },
  "gpt-3.5-turbo-16k": { maxNumTokens: 16385, topKBlocks: 30 },
  "gpt-4": { maxNumTokens: 8192, topKBlocks: 20 },
  "gpt-4-1106-preview": { maxNumTokens: 128000, topKBlocks: 50 },
  /* 'gpt-4-32k': {maxNumTokens: 32768, topKBlocks: 30}, */
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
  completions: withDefault("gpt-3.5-turbo"),
  encoder: withDefault("cl100k_base"),
  topKBlocks: withDefault(MODELS["gpt-3.5-turbo"]?.topKBlocks), //  the number of blocks to use as citations
  maxNumTokens: withDefault(MODELS["gpt-3.5-turbo"]?.maxNumTokens),
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

  const updateInUrl = (vals: { [key: string]: any }) =>
    router.replace({
      pathname: router.pathname,
      query: { ...router.query, ...vals },
    });

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
