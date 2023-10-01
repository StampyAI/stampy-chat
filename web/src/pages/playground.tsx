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
  source: {
    prefix:
      "You are a helpful assistant knowledgeable about AI Alignment and Safety. " +
      'Please give a clear and coherent answer to the user\'s questions.(written after "Q:") ' +
      "using the following sources. Each source is labeled with a letter. Feel free to " +
      "use the sources in any order, and try to use multiple sources in your answers.\n\n",
    suffix:
      "\n\n" +
      'Before the question ("Q: "), there will be a history of previous questions and answers. ' +
      "These sources only apply to the last question. Any sources used in previous answers " +
      "are invalid.",
  },
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
const DEFAULT_SETTINGS = {
  prompts: DEFAULT_PROMPTS,
  mode: "default" as Mode,
  completions: "gpt-3.5-turbo",
  encoder: "cl100k_base",
  topKBlocks: 10, //  the number of blocks to use as citations
  numTokens: 4095,
  tokensBuffer: 50, //  the number of tokens to leave as a buffer when calculating remaining tokens
  historyFraction: 0.25, //  the (approximate) fraction of num_tokens to use for history text before truncating
  contextFraction: 0.5, //  the (approximate) fraction of num_tokens to use for context text before truncating
};
const COMPLETION_MODELS = ["gpt-3.5-turbo", "gpt-4"];
const ENCODERS = ["cl100k_base"];

const updateIn = (obj, [head, ...rest]: string[], val: any) => {
  if (!head) {
    // No path provided - do nothing
  } else if (!rest || rest.length == 0) {
    obj[head] = val;
  } else {
    updateIn(obj[head], rest, val);
  }
  return obj;
};

type ChatSettingsParams = {
  settings: LLMSettings;
  updateSettings: (updater: (settings: LLMSettings) => LLMSettings) => void;
};

const ChatSettings = ({ settings, updateSettings }: ChatSettingsParams) => {
  const update = (setting: string) => (event: ChangeEvent) => {
    updateSettings((prev) => ({
      ...prev,
      [setting]: (event.target as HTMLInputElement).value,
    }));
  };
  const between =
    (setting: string, min?: number, max?: number, parser?) =>
    (event: ChangeEvent) => {
      let num = parser((event.target as HTMLInputElement).value);
      if (isNaN(num)) {
        return;
      } else if (min !== undefined && num < min) {
        num = min;
      } else if (max !== undefined && num > max) {
        num = max;
      }
      updateSettings((prev) => ({ ...prev, [setting]: num }));
    };
  const intBetween = (setting: string, min?: number, max?: number) =>
    between(setting, min, max, (v: any) => parseInt(v, 10));
  const floatBetween = (setting: string, min?: number, max?: number) =>
    between(setting, min, max, parseFloat);
  return (
    <div className="chat-settings mx-5 w-[400px] flex-none border-2 outline-black">
      <h4>Models</h4>
      <div className="LLM-option">
        <label htmlFor="completions-model">Completions model:</label>
        <select
          name="completions-model"
          value={settings.completions}
          onChange={update("completions")}
        >
          {COMPLETION_MODELS.map((name) => (
            <option value={name}>{name}</option>
          ))}
        </select>
      </div>

      <div className="LLM-option">
        <label htmlFor="encoder">Encoder:</label>
        <select
          name="encoder"
          value={settings.encoder}
          onChange={update("encoder")}
        >
          {ENCODERS.map((name) => (
            <option value={name}>{name}</option>
          ))}
        </select>
      </div>

      <h4>Token options</h4>
      <div className="LLM-option">
        <label htmlFor="tokens">Tokens:</label>
        <input
          name="tokens"
          value={settings.numTokens}
          onChange={intBetween("numTokens", 1)}
          type="number"
        />
      </div>

      <div className="LLM-option">
        <label htmlFor="tokens-buffer">
          Number of tokens to leave as a buffer when calculating remaining
          tokens:
        </label>
        <input
          name="tokens-buffer"
          value={settings.tokensBuffer}
          onChange={intBetween("tokensBuffer", 0, settings.numTokens)}
          type="number"
        />
      </div>

      <h4>Prompt options</h4>
      <div className="LLM-option">
        <label htmlFor="top-k-blocks">
          Number of blocks to use as citations:
        </label>
        <input
          name="top-k-blocks"
          value={settings.topKBlocks}
          onChange={intBetween("topKBlocks", 0)}
          type="number"
        />
      </div>

      <div className="LLM-option">
        <label htmlFor="context-fraction">
          Approximate fraction of num_tokens to use for citations text before
          truncating:
        </label>
        <input
          name="context-fraction"
          value={settings.contextFraction}
          onChange={floatBetween("contextFraction", 0, 1)}
          type="number"
        />
      </div>

      <div className="LLM-option">
        <label htmlFor="history-fraction">
          Approximate fraction of num_tokens to use for history text before
          truncating:
        </label>
        <input
          name="history-fraction"
          value={settings.historyFraction}
          onChange={floatBetween("historyFraction", 0, 1)}
          type="number"
        />
      </div>
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
          settings.prompts,
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
          value={settings.prompts.source.prefix}
          onChange={updatePrompt("source", "prefix")}
        />
        <div>(This is where sources will be injected)</div>
        {history.length > 0 && (
          <TextareaAutosize
            className="border-gray w-full border px-1"
            value={settings.prompts.source.suffix}
            onChange={updatePrompt("source", "suffix")}
          />
        )}
      </details>
      {history.length > 0 && (
        <details>
          <summary>History</summary>
          {history.map((entry) => (
            <div className="history-entry">{entry.content}</div>
          ))}
        </details>
      )}
      <details open>
        <summary>Question prompt</summary>
        <TextareaAutosize
          className="border-gray w-full border px-1"
          value={settings.prompts.question}
          onChange={updatePrompt("question")}
        />
        <TextareaAutosize
          className="border-gray w-full border px-1"
          value={settings.prompts.modes[settings.mode || "default"]}
          onChange={updatePrompt(
            "modes",
            (settings.mode || "default") as string
          )}
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
        <Controls mode={[settings.mode, true]} setMode={setMode} />
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
