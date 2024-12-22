import { ChangeEvent } from "react";
import TextareaAutosize from "react-textarea-autosize";

import type { Parseable, LLMSettings, Entry, Mode } from "../types";
import { MODELS, ENCODERS } from "../hooks/useSettings";
import { SectionHeader, NumberInput, Slider } from "../components/html";

type ChatSettingsUpdate = [path: string[], value: any];
type ChatSettingsParams = {
  settings: LLMSettings;
  changeSettings: (...v: ChatSettingsUpdate[]) => void;
};

export const ChatSettings = ({
  settings,
  changeSettings,
}: ChatSettingsParams) => {
  const changeVal = (field: string, value: any) =>
    changeSettings([[field], value]);
  const update = (field: string) => (event: ChangeEvent) =>
    changeVal(field, (event.target as HTMLInputElement).value);
  const updateNum = (field: string) => (num: Parseable) =>
    changeVal(field, num);

  const updateTokenFraction = (field: string) => (num: Parseable) => {
    // Calculate the fraction of the tokens taken by the buffer
    const bufferFraction =
      settings.tokensBuffer && settings.maxNumTokens
        ? settings.tokensBuffer / settings.maxNumTokens
        : 0;
    const val = Math.min(parseFloat((num || 0).toString()), 1 - bufferFraction);

    let context = settings.contextFraction || 0;
    let history = settings.historyFraction || 0;

    if (field == "contextFraction") {
      history = Math.min(history, Math.max(0, 1 - val - bufferFraction));
      context = val;
    } else {
      context = Math.min(context, Math.max(0, 1 - val - bufferFraction));
      history = val;
    }
    changeSettings(
      [["contextFraction"], context],
      [["historyFraction"], history]
    );
  };

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
            MODELS[value as keyof typeof MODELS] || {};
          const prevNumTokens =
            MODELS[settings.completions as keyof typeof MODELS]?.maxNumTokens;
          const prevTopKBlocks =
            MODELS[settings.completions as keyof typeof MODELS]?.topKBlocks;

          if (settings.maxNumTokens === prevNumTokens) {
            changeVal("maxNumTokens", maxNumTokens);
          } else {
            changeVal(
              "maxNumTokens",
              Math.min(settings.maxNumTokens || 0, maxNumTokens || 0)
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
        max={MODELS[settings.completions as keyof typeof MODELS]?.maxNumTokens}
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
      <NumberInput
        field="maxHistorySummaryTokens"
        value={settings.maxHistorySummaryTokens}
        label="The max number of tokens to use for the history summary"
        min="0"
        max={settings.maxNumTokens}
        updater={updateNum("maxHistorySummaryTokens")}
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
        updater={updateTokenFraction("contextFraction")}
      />
      <Slider
        value={settings.historyFraction}
        field="historyFraction"
        label="Approximate fraction of num_tokens to use for history text before truncating"
        updater={updateTokenFraction("historyFraction")}
      />
    </div>
  );
};

type ChatPromptParams = {
  settings: LLMSettings;
  query: string;
  history: Entry[];
  changeSettings: (...vals: ChatSettingsUpdate[]) => void;
};

export const ChatPrompts = ({
  settings,
  query,
  history,
  changeSettings,
}: ChatPromptParams) => {
  const updatePrompt =
    (...path: string[]) =>
    (event: ChangeEvent) =>
      changeSettings([
        ["prompts", ...path],
        (event.target as HTMLInputElement).value,
      ]);

  return (
    <div className="chat-prompts mx-5 w-[400px] flex-none border-2 p-5 outline-black">
      <details>
        <summary>History summary prompt</summary>
        <TextareaAutosize
          className="border-gray w-full border px-1"
          value={settings?.prompts?.history_summary}
          onChange={updatePrompt("history_summary")}
        />
      </details>
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
        User mode prompt:
        <TextareaAutosize
          className="border-gray w-full border px-1"
          value={settings?.prompts?.modes[settings.mode || "default"]}
          onChange={updatePrompt("modes", settings.mode || "default")}
        />
      </details>
      <div>
        <input
          type="text"
          value={settings?.prompts?.question_marker}
          onChange={updatePrompt("question_marker")}
          style={{ border: '1px solid #ccc', width: 'auto' }}
        />
        <span>asd {query}</span>
      </div>
    </div>
  );
};
