import { ChangeEvent } from "react";
import TextareaAutosize from "react-textarea-autosize";

import type { Parseable, LLMSettings, Entry, Mode } from "../types";
import { SectionHeader, NumberInput, Slider } from "../components/html";

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
  question:
    "In your answer, please cite any claims you make back to each source " +
    "using the format: [a], [b], etc. If you use multiple sources to make a claim " +
    'cite all of them. For example: "AGI is concerning [c, d, e]."\n\n',
  modes: {
    default: "",
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
export const MODELS = {
  "gpt-3.5-turbo": { maxNumTokens: 4095, topKBlocks: 10 },
  "gpt-3.5-turbo-16k": { maxNumTokens: 16385, topKBlocks: 30 },
  "gpt-4": { maxNumTokens: 8192, topKBlocks: 20 },
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
  topKBlocks: withDefault(MODELS["gpt-3.5-turbo"].topKBlocks), //  the number of blocks to use as citations
  maxNumTokens: withDefault(MODELS["gpt-3.5-turbo"].maxNumTokens),
  tokensBuffer: withDefault(50), //  the number of tokens to leave as a buffer when calculating remaining tokens
  maxHistory: withDefault(10), //  the max number of previous items to use as history
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

type ChatSettingsParams = {
  settings: LLMSettings;
  changeSetting: (path: string[], value: any) => void;
};

export const ChatSettings = ({
  settings,
  changeSetting,
}: ChatSettingsParams) => {
  const changeVal = (field: string, value: any) =>
    changeSetting([field], value);
  const update = (field: string) => (event: ChangeEvent) =>
    changeVal(field, (event.target as HTMLInputElement).value);
  const updateNum = (field: string) => (num: Parseable) =>
    changeVal(field, num);

  return (
    <div
      className="chat-settings mx-5 grid w-[400px] flex-none grid-cols-4 gap-4 border-2 outline-black"
      style={{ height: "fit-content" }}
    >
      <SectionHeader text="Models" />
      <label htmlFor="completions-model" className="col-span-2">
        Completions model:
      </label>
      <select
        name="completions-model"
        className="col-span-2"
        value={settings.completions}
        onChange={(event: ChangeEvent) => {
          const value = (event.target as HTMLInputElement).value;
          const { maxNumTokens, topKBlocks } =
            MODELS[value as keyof typeof MODELS];
          const prevNumTokens =
            MODELS[settings.completions as keyof typeof MODELS].maxNumTokens;
          const prevTopKBlocks =
            MODELS[settings.completions as keyof typeof MODELS].topKBlocks;

          if (settings.maxNumTokens === prevNumTokens) {
            changeVal("maxNumTokens", maxNumTokens);
          } else {
            changeVal(
              "maxNumTokens",
              Math.min(settings.maxNumTokens || 0, maxNumTokens)
            );
          }
          if (settings.topKBlocks === prevTopKBlocks) {
            changeVal("topKBlocks", topKBlocks);
          }
          changeVal("completions", value);
        }}
      >
        {Object.keys(MODELS).map((name) => (
          <option value={name} key={name}>
            {name}
          </option>
        ))}
      </select>

      <label htmlFor="encoder" className="col-span-2">
        Encoder:
      </label>
      <select
        name="encoder"
        className="col-span-2"
        value={settings.encoder}
        onChange={update("encoder")}
      >
        {ENCODERS.map((name) => (
          <option value={name} key={name}>
            {name}
          </option>
        ))}
      </select>

      <SectionHeader text="Token options" />
      <NumberInput
        value={settings.maxNumTokens}
        field="maxNumTokens"
        label="Tokens"
        min="1"
        max={MODELS[settings.completions as keyof typeof MODELS].maxNumTokens}
        updater={updateNum("maxNumTokens")}
      />
      <NumberInput
        field="tokensBuffer"
        value={settings.tokensBuffer}
        label="Number of tokens to leave as a buffer when calculating remaining tokens"
        min="0"
        max={settings.maxNumTokens}
        updater={updateNum("tokensBuffer")}
      />

      <SectionHeader text="Prompt options" />
      <NumberInput
        value={settings.topKBlocks}
        field="topKBlocks"
        label="Number of blocks to use as citations"
        min="1"
        updater={updateNum("topKBlocks")}
      />
      <NumberInput
        value={settings.maxHistory}
        field="maxHistory"
        label="The max number of previous interactions to use"
        min="0"
        updater={updateNum("maxHistory")}
      />

      <Slider
        value={settings.contextFraction}
        field="contextFraction"
        label="Approximate fraction of num_tokens to use for citations text before truncating"
        updater={updateNum("contextFraction")}
      />
      <Slider
        value={settings.historyFraction}
        field="historyFraction"
        label="Approximate fraction of num_tokens to use for history text before truncating"
        updater={updateNum("historyFraction")}
      />
    </div>
  );
};

type ChatPromptParams = {
  settings: LLMSettings;
  query: string;
  history: Entry[];
  changeSetting: (path: string[], value: any) => void;
};

export const ChatPrompts = ({
  settings,
  query,
  history,
  changeSetting,
}: ChatPromptParams) => {
  const updatePrompt =
    (...path: string[]) =>
    (event: ChangeEvent) =>
      changeSetting(
        ["prompts", ...path],
        (event.target as HTMLInputElement).value
      );

  return (
    <div className="chat-prompts mx-5 w-[400px] flex-none border-2 p-5 outline-black">
      <details open>
        <summary>Source prompt</summary>
        <TextareaAutosize
          className="border-gray w-full border px-1"
          value={settings?.prompts?.context}
          onChange={updatePrompt("context")}
        />
        <div>(This is where sources will be injected)</div>
      </details>
      {history.length > 0 && (
        <details open>
          <summary>History prompt</summary>
          <TextareaAutosize
            className="border-gray w-full border px-1"
            value={settings?.prompts?.history}
            onChange={updatePrompt("history")}
          />
          <details>
            <summary>History</summary>
            {history
              .slice(Math.max(0, history.length - (settings.maxHistory || 0)))
              .map((entry, i) => (
                <div className="history-entry" key={i}>
                  {entry.content}
                </div>
              ))}
          </details>
        </details>
      )}
      <details open>
        <summary>Question prompt</summary>
        <TextareaAutosize
          className="border-gray w-full border px-1"
          value={settings?.prompts?.question}
          onChange={updatePrompt("question")}
        />
        <TextareaAutosize
          className="border-gray w-full border px-1"
          value={settings?.prompts?.modes[settings.mode || "default"]}
          onChange={updatePrompt("modes", settings.mode || "default")}
        />
      </details>
      <div>Q: {query}</div>
    </div>
  );
};
