import { ChangeEvent } from "react";
import TextareaAutosize from "react-textarea-autosize";

import type { Parseable, LLMSettings, Entry, Mode } from "../types";
import { MODELS, ENCODERS } from "../hooks/useSettings";
import { SectionHeader, NumberInput, Slider } from "../components/html";

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
