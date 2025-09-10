import { useRouter } from "next/router";
import { useState, useEffect, useCallback, useRef } from "react";

import type { Mode, LLMSettings, SearchFilters } from "../types";

type LLMSettingsParsers = {
  [key: string]:
  | ((v: number | undefined) => any)
  | ((v: string | undefined) => any)
  | ((v: object | undefined) => any)
  | ((v: any[] | undefined) => any);
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
  pre_message: "",
  post_message: `
{detailed-cautious-epistem-safetyinfo-v7-2508241916-cdc305}

{post-message-2507220220-cff788}

{socratic-avoid-bad-questions-harder-2507220153-a11064}

{mode}`,
  hyde_pre_message: "",
  hyde_post_message:
    "{detailed-cautious-epistem-safetyinfo-v7-hyde-2508241917-fba3ad}\n\n{hyde_post_message-2507222109-597ed2}",
  message_format: "<from-public-user>\n{message}\n</from-public-user>",
  modes: {
    default: "",
    concise: "{mode-concise-2507231147-db01d9}",
    rookie: "{mode-rookie-2507231143-f32d39}",
    discord: "{mode-discord-2507231144-ffe1d1}",
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
  "openai/gpt-5-chat-latest": { maxNumTokens: 128000, topKBlocks: 50 },
  "openai/gpt-5-2025-08-07": { maxNumTokens: 128000, topKBlocks: 50 },
  "openai/gpt-5": { maxNumTokens: 128000, topKBlocks: 50 },
  "anthropic/claude-3-opus-20240229": { maxNumTokens: 200000, topKBlocks: 50 },
  "anthropic/claude-3-5-sonnet-20240620": {
    maxNumTokens: 200_000,
    topKBlocks: 50,
  },
  "anthropic/claude-3-5-sonnet-20241022": {
    maxNumTokens: 200_000,
    topKBlocks: 50,
  },
  "anthropic/claude-3-5-sonnet-latest": {
    maxNumTokens: 200_000,
    topKBlocks: 50,
  },
  "anthropic/claude-opus-4-20250514": { maxNumTokens: 200_000, topKBlocks: 50 },
  "anthropic/claude-opus-4-1-20250805": { maxNumTokens: 200_000, topKBlocks: 50 },
  "anthropic/claude-sonnet-4-20250514": {
    maxNumTokens: 200_000,
    topKBlocks: 50,
  },
  "anthropic/claude-3-7-sonnet-latest": {
    maxNumTokens: 200_000,
    topKBlocks: 50,
  },
  "google/gemini-2.5-flash": { maxNumTokens: 250_000, topKBlocks: 50 },
  "google/gemini-2.5-pro": { maxNumTokens: 250_000, topKBlocks: 50 },
  // OpenRouter models
  "openrouter/openai/gpt-5": { maxNumTokens: 128000, topKBlocks: 50 },
  "openrouter/openai/gpt-oss-20b": { maxNumTokens: 128000, topKBlocks: 50 },
  "openrouter/moonshotai/kimi-k2": { maxNumTokens: 128000, topKBlocks: 50 },
};
export const ENCODERS = ["cl100k_base"];
export const DEFAULT_FILTERS: SearchFilters = {
  miri_confidence: 6,
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
    if (
      obj[head] === undefined ||
      typeof obj[head] !== "object" ||
      obj[head] === null
    ) {
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
        return defaultVal;
      } else if (Array.isArray(v)) {
        return v;
      } else if (typeof v === "string") {
        return (v as string).split(",").map((x) => x.trim());
      } else {
        return v;
      }
    };
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
  modelID: withDefault("anthropic/claude-sonnet-4-20250514"),
  encoder: withDefault("cl100k_base"),
  topKBlocks: withDefault(
    MODELS["anthropic/claude-sonnet-4-20250514"]?.topKBlocks
  ), //  the number of blocks to use as citations
  maxNumTokens: withDefault(
    MODELS["anthropic/claude-sonnet-4-20250514"]?.maxNumTokens
  ),
  tokensBuffer: withDefault(50), //  the number of tokens to leave as a buffer when calculating remaining tokens
  maxHistory: withDefault(10), //  the max number of previous items to use as history
  maxHistorySummaryTokens: withDefault(200), //  the max number of tokens to use in the history summary
  historyFraction: withDefault(0.25), //  the (approximate) fraction of num_tokens to use for history text before truncating
  contextFraction: withDefault(0.5), //  the (approximate) fraction of num_tokens to use for context text before truncating
  enable_hyde: withDefault(false), //  whether to enable hyde functionality
  thinking_budget: withDefault(0), // 0 or >=1024
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
  const modelID = randomElement(Object.keys(MODELS));
  const model = MODELS[modelID] as Model;
  const maxNumTokens = randomInt(
    Math.floor(model.maxNumTokens * 0.3),
    model.maxNumTokens
  );
  const historyFraction = randomFloat(0.2, 0.8);
  const contextFraction = randomFloat(0.2, 0.9 - historyFraction);
  return makeSettings({
    modelID,
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

// Parse hash string into object
const parseHash = (hash: string): { [key: string]: any } => {
  if (!hash || hash === "#") return {};
  const cleanHash = hash.startsWith("#") ? hash.slice(1) : hash;
  const params = new URLSearchParams(cleanHash);
  const result: { [key: string]: any } = {};
  params.forEach((value, key) => {
    result[key] = value;
  });
  return result;
};

// Serialize object to hash string
const serializeToHash = (obj: { [key: string]: any }): string => {
  const params = new URLSearchParams();
  Object.entries(obj).forEach(([key, val]) => {
    if (val !== undefined && val !== null && val !== "") {
      params.set(key, String(val));
    }
  });
  const str = params.toString();
  return str ? "#" + str : "";
};

function useUrlSettings(onLoad: (data: any) => void, deps: any[]) {
  const [urlLoaded, setUrlLoaded] = useState(false);
  const router = useRouter();
  const debouncingEnabled = useRef(false);
  const debounceTimeout = useRef<NodeJS.Timeout | null>(null);
  const pendingUpdates = useRef<{ [key: string]: any }>({});
  const lastChangeTime = useRef<number>(Date.now());

  useEffect(() => {
    if (!router.isReady) return;
    if (urlLoaded) return;

    // Parse both query and hash
    const hashData = parseHash(router.asPath.split("#")[1] || "");
    const queryData = router.query;

    // Merge query into hash (query takes precedence for migration)
    const mergedData = { ...hashData, ...queryData };

    // If there was data in query, migrate it to hash and clear query
    if (Object.keys(queryData).length > 0) {
      const newHash = serializeToHash(mergedData);
      // Clear query params and set hash
      router.replace(
        router.pathname + newHash,
        undefined,
        { scroll: false }
      );
    }

    onLoad(mergedData);
    debouncingEnabled.current = true;
    setUrlLoaded(true);
    // eslint-disable-next-line
  }, [router, debouncingEnabled].concat(deps));

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (debounceTimeout.current) {
        clearTimeout(debounceTimeout.current);
      }
      pendingUpdates.current = {};
    };
  }, []);

  const updateInUrl = useCallback((vals: { [key: string]: any }) => {
    if (!router.isReady) {
      return;
    }

    // Read current hash data
    const currentHashData = parseHash(router.asPath.split("#")[1] || "");

    if (!debouncingEnabled.current) {
      // Before onLoad, apply immediately
      const newHashData = { ...currentHashData, ...vals };
      const newHash = serializeToHash(newHashData);
      return router.replace(
        router.pathname + newHash,
        undefined,
        { scroll: false }
      );
    }

    // Accumulate pending updates
    pendingUpdates.current = { ...pendingUpdates.current, ...vals };
    const now = Date.now();
    const timeSinceLastChange = now - lastChangeTime.current;

    // Clear any existing timeout
    if (debounceTimeout.current) {
      clearTimeout(debounceTimeout.current);
      debounceTimeout.current = null;
    }

    // If it's been more than 2.5 seconds since last change, apply immediately
    if (timeSinceLastChange > 2500) {
      lastChangeTime.current = now;
      const updatesToApply = { ...pendingUpdates.current };
      pendingUpdates.current = {};

      const newHashData = { ...currentHashData, ...updatesToApply };
      const newHash = serializeToHash(newHashData);

      console.log(
        "updating settings to hash",
        router.isReady,
        router.pathname,
        updatesToApply,
        newHashData,
        newHash
      );

      return router.replace(
        router.pathname + newHash,
        undefined,
        { scroll: false }
      );
    } else {
      // Update last change time and set timeout for final update
      lastChangeTime.current = now;

      debounceTimeout.current = setTimeout(() => {
        const updatesToApply = { ...pendingUpdates.current };
        pendingUpdates.current = {};
        debounceTimeout.current = null;
        lastChangeTime.current = 0;

        const currentHashData = parseHash(router.asPath.split("#")[1] || "");
        const newHashData = { ...currentHashData, ...updatesToApply };
        const newHash = serializeToHash(newHashData);

        router.replace(
          router.pathname + newHash,
          undefined,
          { scroll: false }
        );
      }, 5000);
    }
  }, [router]);

  return updateInUrl;
}

export default function useSettings() {
  const [settings, updateSettings] = useState<LLMSettings>(makeSettings({}));
  const [settingsLoaded, setSettingsLoaded] = useState(false);

  const updateInUrl = useUrlSettings(
    ({completions: undefined, ...data}) => {
      const mode = (data?.mode ||
        localStorage.getItem("chat_mode") ||
        "default") as Mode;
      let modelID = data?.modelID;
      if (data?.completions !== null && data?.completions !== undefined) {
        modelID = data.completions;
      }
      const newSettings = makeSettings({ ...data, mode, modelID });
      updateSettings(newSettings);
      setSettingsLoaded(true);
    },
    [updateSettings, setSettingsLoaded]
  );

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
