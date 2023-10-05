import type { NextPage } from "next";
import { useState, useEffect, ChangeEvent } from "react";
import TextareaAutosize from "react-textarea-autosize";
import Head from "next/head";
import Link from "next/link";

import { queryLLM, getStampyContent, runSearch } from "../hooks/useSearch";
import type { Mode, Entry, LLMSettings } from "../types";
import Header from "../components/header";
import Chat from "../components/chat";
import { Controls } from "../components/controls";

const MAX_FOLLOWUPS = 4;
const DEFAULT_PROMPTS = {
  context:
    "You are a helpful assistant knowledgeable about AI Alignment and Safety. " +
    'Please give a clear and coherent answer to the user\'s questions.(written after "Q:") ' +
    "using the following sources. Each source is labeled with a letter. Feel free to " +
    "use the sources in any order, and try to use multiple sources in your answers.\n\n",
  history:
    "\n\n" +
    'Before the question ("Q: "), there will be a history of previous questions and answers. ' +
    "These sources only apply to the last question. Any sources used in previous answers " +
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
const MODELS = {
  "gpt-3.5-turbo": { numTokens: 4095, topKBlocks: 10 },
  "gpt-3.5-turbo-16k": { numTokens: 16385, topKBlocks: 30 },
  "gpt-4": { numTokens: 8192, topKBlocks: 20 },
  /* 'gpt-4-32k': {numTokens: 32768, topKBlocks: 30}, */
};
const DEFAULT_SETTINGS = {
  prompts: DEFAULT_PROMPTS,
  mode: "default" as Mode,
  completions: "gpt-3.5-turbo",
  encoder: "cl100k_base",
  topKBlocks: MODELS["gpt-3.5-turbo"].topKBlocks, //  the number of blocks to use as citations
  numTokens: MODELS["gpt-3.5-turbo"].numTokens,
  tokensBuffer: 50, //  the number of tokens to leave as a buffer when calculating remaining tokens
  maxHistory: 10, //  the max number of previous items to use as history
  historyFraction: 0.25, //  the (approximate) fraction of num_tokens to use for history text before truncating
  contextFraction: 0.5, //  the (approximate) fraction of num_tokens to use for context text before truncating
};
const ENCODERS = ["cl100k_base"];

const updateIn = (
  obj: { [key: string]: any },
  [head, ...rest]: string[],
  val: any
) => {
  if (!head) {
    // No path provided - do nothing
  } else if (!rest || rest.length == 0) {
    obj[head] = val;
  } else {
    updateIn(obj[head], rest, val);
  }
  return obj;
};

type Parseable = string | number | undefined;
type NumberParser = (v: Parseable) => number;
type InputFields = {
  field: string;
  label: string;
  value?: Parseable;
  min?: string | number;
  max?: string | number;
  step?: string | number;
  parser?: NumberParser;
  updater: (v: any) => any;
};

const between =
  (
    min: Parseable,
    max: Parseable,
    parser: NumberParser,
    updater: (v: any) => any
  ) =>
  (event: ChangeEvent) => {
    let num = parser((event.target as HTMLInputElement).value);
    if (isNaN(num)) {
      return;
    } else if (min !== undefined && num < parser(min)) {
      num = parser(min);
    } else if (max !== undefined && num > parser(max)) {
      num = parser(max);
    }
    updater(num);
  };

const SectionHeader = ({ text }: { text: string }) => (
  <h4 className="col-span-4 text-lg font-semibold">{text}</h4>
);

const NumberInput = ({
  field,
  value,
  label,
  min,
  max,
  updater,
  // this cast is just to satisfy typescript - it can handle numbers, strings and undefined just fine
  parser = (v) => parseInt(v as string, 10),
}: InputFields) => (
  <>
    <label htmlFor={field} className="col-span-3 inline-block">
      {label}:{" "}
    </label>
    <input
      name={field}
      value={value}
      className="w-20"
      onChange={between(min, max, parser, updater)}
      type="number"
    />
  </>
);

const Slider = ({
  field,
  value,
  label,
  min = 0,
  max = 1,
  step = 0.01,
  // this cast is just to satisfy typescript - it can handle numbers, strings and undefined just fine
  parser = (v) => parseFloat(v as string),
  updater,
}: InputFields) => (
  <>
    <label htmlFor={field} className="col-span-2">
      {label}:
    </label>
    <input
      name={field}
      className="col-span-2"
      value={value}
      onChange={between(min, max, parser, updater)}
      type="range"
      min={min}
      max={max}
      step={step}
    />
  </>
);

type ChatSettingsParams = {
  settings: LLMSettings;
  updateSettings: (updater: (settings: LLMSettings) => LLMSettings) => void;
};

const ChatSettings = ({ settings, updateSettings }: ChatSettingsParams) => {
  const changeVal = (field: string, value: any) =>
    updateSettings((prev) => ({ ...prev, [field]: value }));
  const update = (setting: string) => (event: ChangeEvent) => {
    changeVal(setting, (event.target as HTMLInputElement).value);
  };
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
          const { numTokens, topKBlocks } =
            MODELS[value as keyof typeof MODELS];
          const prevNumTokens =
            MODELS[settings.completions as keyof typeof MODELS].numTokens;
          const prevTopKBlocks =
            MODELS[settings.completions as keyof typeof MODELS].topKBlocks;

          if (settings.numTokens === prevNumTokens) {
            changeVal("numTokens", numTokens);
          } else {
            changeVal(
              "numTokens",
              Math.min(settings.numTokens || 0, numTokens)
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
        value={settings.numTokens}
        field="numTokens"
        label="Tokens"
        min="1"
        max={MODELS[settings.completions as keyof typeof MODELS].numTokens}
        updater={updateNum("numTokens")}
      />
      <NumberInput
        field="tokensBuffer"
        value={settings.tokensBuffer}
        label="Number of tokens to leave as a buffer when calculating remaining tokens"
        min="0"
        max={settings.numTokens}
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
  updateSettings: (updater: (settings: LLMSettings) => LLMSettings) => void;
};

const ChatPrompts = ({
  settings,
  query,
  history,
  updateSettings,
}: ChatPromptParams) => {
  const updatePrompt =
    (...path: string[]) =>
    (event: ChangeEvent) => {
      const newPrompts = {
        ...updateIn(
          settings.prompts || {},
          path,
          (event.target as HTMLInputElement).value
        ),
      };
      updateSettings((settings) => ({ ...settings, prompts: newPrompts }));
    };

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

const Playground: NextPage = () => {
  const [sessionId, setSessionId] = useState("");
  const [settings, updateSettings] = useState<LLMSettings>(DEFAULT_SETTINGS);

  const [query, setQuery] = useState<string>("");
  const [history, setHistory] = useState<Entry[]>([]);

  const setMode = (mode: [Mode, boolean]) => {
    if (mode[1]) {
      localStorage.setItem("chat_mode", mode[0]);
      updateSettings((settings) => ({ ...settings, mode: mode[0] }));
    }
  };

  // initial load
  useEffect(() => {
    const mode = (localStorage.getItem("chat_mode") as Mode) || "default";
    setMode([mode, true]);
    setSessionId(crypto.randomUUID());
  }, []);

  return (
    <>
      <Head>
        <title>AI Safety Info</title>
      </Head>
      <main style={{ maxWidth: "none" }}>
        <Header page="playground" />
        <Controls mode={[settings.mode || "default", true]} setMode={setMode} />
        <div className="flex">
          <ChatPrompts
            settings={settings}
            query={query}
            history={history}
            updateSettings={updateSettings}
          />
          <Chat
            sessionId={sessionId}
            settings={settings}
            onQuery={setQuery}
            onNewEntry={setHistory}
          />
          <ChatSettings settings={settings} updateSettings={updateSettings} />
        </div>
      </main>
    </>
  );
};

export default Playground;
