import { ChangeEvent, useState } from "react";
import TextareaAutosize from "react-textarea-autosize";

import type { Parseable, LLMSettings, Entry, Mode } from "../types";
import { API_URL } from "../settings";
import { MODELS, ENCODERS } from "../hooks/useSettings";
import {
  SectionHeader,
  NumberInput,
  Slider,
  Checkbox,
  Select,
} from "../components/html";

type ChatSettingsUpdate = [path: string[], value: any];
type ChatSettingsParams = {
  settings: LLMSettings;
  changeSettings: (...v: ChatSettingsUpdate[]) => void;
};

type DetailsProps = {
  children: React.ReactNode;
  defaultOpen?: boolean;
} & React.DetailsHTMLAttributes<HTMLDetailsElement>;

function Details({ children, defaultOpen = true, ...props }: DetailsProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <details
      {...props}
      open={isOpen}
      onToggle={(e) => setIsOpen((e.target as HTMLDetailsElement).open)}
    >
      {children}
    </details>
  );
}

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
      <label htmlFor="model" className="col-span-2">
        Model:
      </label>
      <Select
        name="model"
        value={settings.model || ""}
        updater={(event: ChangeEvent) => {
          const value = (event.target as HTMLInputElement).value;
          const { maxNumTokens, topKBlocks } =
            MODELS[value as keyof typeof MODELS] || {};
          const prevNumTokens =
            MODELS[settings.model as keyof typeof MODELS]?.maxNumTokens;
          const prevTopKBlocks =
            MODELS[settings.model as keyof typeof MODELS]?.topKBlocks;

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
          changeVal("model", value);
        }}
        options={Object.keys(MODELS)}
      />

      <label htmlFor="encoder" className="col-span-2">
        Encoder:
      </label>
      <Select
        name="encoder"
        value={settings.encoder || ""}
        updater={update("encoder")}
        options={ENCODERS}
      />

      <SectionHeader text="Token options" />
      <NumberInput
        value={settings.maxNumTokens}
        field="maxNumTokens"
        label="Tokens"
        min="1"
        max={MODELS[settings.model as keyof typeof MODELS]?.maxNumTokens}
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
      <Checkbox
        checked={settings?.enable_hyde || false}
        field="enable_hyde"
        label="Enable Hyde"
        updater={(checked: boolean) =>
          changeSettings([["enable_hyde"], checked])
        }
      />
      <NumberInput
        field="thinking_budget"
        value={settings.thinking_budget}
        label="Max tokens for thinking. 0 or >=1024"
        min="0"
        max={settings.maxNumTokens}
        updater={updateNum("thinking_budget")}
      />
      <Checkbox
        checked={
          (settings?.thinking_budget && settings.thinking_budget >= 1024) ||
          false
        }
        field="enable_thinking"
        label="Enable Thinking"
        updater={(checked: boolean) =>
          changeSettings([["thinking_budget"], checked ? 1024 : 0])
        }
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
      <SectionHeader text="Search filters" />
      <NumberInput
        value={settings.filters?.miri_confidence || 0}
        field="filters.miri_confidence"
        label="MIRI confidence"
        min="0"
        max="10"
        updater={updateNum("filters.miri_confidence")}
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

  const inlineAllTemplates = async () => {
    try {
      const response = await fetch(API_URL + "/inline-prompts", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ settings }),
      });
      if (response.ok) {
        const inlinedPrompts = await response.json();

        // Call changeSettings recursively for each prompt field
        const updates: [string[], any][] = [];

        const addUpdates = (obj: any, path: string[] = ["prompts"]) => {
          Object.entries(obj).forEach(([key, value]) => {
            const currentPath = [...path, key];
            if (
              typeof value === "object" &&
              value !== null &&
              !Array.isArray(value)
            ) {
              addUpdates(value, currentPath);
            } else {
              updates.push([currentPath, value]);
            }
          });
        };

        addUpdates(inlinedPrompts);
        changeSettings(...updates);
      }
    } catch (error) {
      console.error("Failed to inline templates:", error);
    }
  };

  return (
    <div className="chat-prompts mx-5 w-[400px] flex-none border-2 p-5 outline-black">
      <button onClick={inlineAllTemplates} className="mb-4 px-4">
        Inline All Templates
      </button>
      <Details>
        <summary>History summary prompt</summary>
        <TextareaAutosize
          className="border-gray w-full border px-1"
          value={settings?.prompts?.history_summary}
          onChange={updatePrompt("history_summary")}
        />
      </Details>
      <Details>
        <summary>System prompt</summary>
        <TextareaAutosize
          className="border-gray w-full border px-1"
          value={settings?.prompts?.system}
          onChange={updatePrompt("system")}
        />
        <div>(This is where sources will be injected)</div>
      </Details>
      {history.length > 0 && (
        <>
          <Details>
            <summary>History prompt</summary>
            <TextareaAutosize
              className="border-gray w-full border px-1"
              value={settings?.prompts?.history}
              onChange={updatePrompt("history")}
            />
          </Details>
          <Details>
            <summary>History</summary>
            {history
              .slice(Math.max(0, history.length - (settings.maxHistory || 0)))
              .map((entry, i) => (
                <div className="history-entry" key={i}>
                  {entry.content}
                </div>
              ))}
          </Details>
        </>
      )}
      <Details>
        <summary>Pre-message prompt</summary>
        <TextareaAutosize
          className="border-gray w-full border px-1"
          value={settings?.prompts?.pre_message}
          onChange={updatePrompt("pre_message")}
        />
      </Details>
      <Details>
        <summary>Hyde pre-message prompt</summary>
        <TextareaAutosize
          className="border-gray w-full border px-1"
          value={settings?.prompts?.hyde_pre_message}
          onChange={updatePrompt("hyde_pre_message")}
        />
      </Details>
      <Details>
        <summary>Hyde post-message prompt</summary>
        <TextareaAutosize
          className="border-gray w-full border px-1"
          value={settings?.prompts?.hyde_post_message}
          onChange={updatePrompt("hyde_post_message")}
        />
      </Details>
      <Details>
        <summary>Post-message prompt</summary>
        <TextareaAutosize
          className="border-gray w-full border px-1"
          value={settings?.prompts?.post_message}
          onChange={updatePrompt("post_message")}
        />
      </Details>
      <Details>
        User mode prompt:
        <TextareaAutosize
          className="border-gray w-full border px-1"
          value={settings?.prompts?.modes[settings.mode || "default"]}
          onChange={updatePrompt("modes", settings.mode || "default")}
        />
      </Details>
      <Details>
        Message format:
        <TextareaAutosize
          className="border-gray w-full border px-1"
          value={settings?.prompts?.message_format}
          onChange={updatePrompt("message_format")}
        />
        <div>{query}</div>
      </Details>
    </div>
  );
};
