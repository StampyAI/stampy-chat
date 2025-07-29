import { useRouter } from "next/router";
import { useState, useEffect, useCallback } from "react";

import type { Mode, LLMSettings, SearchFilters } from "../types";

type LLMSettingsParsers = {
  [key: string]:
  | ((v: number | undefined) => any)
  | ((v: string | undefined) => any)
  | ((v: object | undefined) => any);
};

// warning: when changing these prompts, also change settings.py
const DEFAULT_PROMPTS = {
  system: `
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
`,
  history: "{stampy-history-2507211352-060b74}",
  history_summary: "{stampy-history_summary-2507231056-b048af}",
  pre_message: '',
  post_message: `
{detailed-cautious-epistem-safetyinfo-v5-2507220231-d00b79}

{post-message-2507220220-cff788}

{socratic-avoid-bad-questions-harder-2507220153-a11064}

{mode}`,
  message_format: "<from-public-user>\n{message}\n</from-public-user>",
  modes: {
    "default": "",
    "concise": "{mode-concise-2507231147-db01d9}",
    "rookie": "{mode-rookie-2507231143-f32d39}",
    "discord": "{mode-discord-2507231144-ffe1d1}",
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
  "google/gemini-2.5-flash": { maxNumTokens: 250_000, topKBlocks: 50 },
  "google/gemini-2.5-pro": { maxNumTokens: 250_000, topKBlocks: 50 },
};
export const ENCODERS = ["cl100k_base"];
export const DEFAULT_FILTERS: SearchFilters = {
  miri_confidence: 4,
  miri_distance: [],
  needs_tech: false,
};

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
  } else if (typeof defaultVal === "boolean") {
    return (v: string | undefined): boolean =>
      v !== undefined ? v === "true" : defaultVal;
  } else if (Array.isArray(defaultVal)) {
    return (v: any[] | undefined): any[] => {
      if (v === undefined) {
        return defaultVal
      } else if (Array.isArray(v)) {
        return v
      } else if (typeof v === "string") {
        return (v as string).split(",").map((x) => x.trim())
      } else {
        return v
      }
    }
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
  filters: withDefault(DEFAULT_FILTERS),
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
