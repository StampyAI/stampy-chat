import type { NextPage } from "next";
import { useRouter } from "next/router";
import { useState, useEffect } from "react";
import Head from "next/head";

import { queryLLM, getStampyContent, runSearch } from "../hooks/useSearch";
import type { Mode, Entry, LLMSettings } from "../types";
import Header from "../components/header";
import Chat from "../components/chat";
import { Controls } from "../components/controls";
import {
  ChatSettings,
  ChatPrompts,
  updateIn,
  makeSettings,
} from "../components/settings";

const Playground: NextPage = () => {
  const [sessionId, setSessionId] = useState("");
  const [settings, updateSettings] = useState<LLMSettings>(makeSettings({}));

  const [query, setQuery] = useState<string>("");
  const [history, setHistory] = useState<Entry[]>([]);

  const router = useRouter();

  const setMode = (mode: [Mode, boolean]) => {
    if (mode[1]) {
      localStorage.setItem("chat_mode", mode[0]);
      updateSettings((settings) => ({ ...settings, mode: mode[0] }));
    }
  };

  const changeSetting = (path: string[], value: any) => {
    router.replace(
      {
        pathname: router.pathname,
        query: {
          ...router.query,
          [path.join(".")]: value.toString(),
        },
      },
      undefined,
      { scroll: false, shallow: true }
    );
    updateSettings((settings) => ({ ...updateIn(settings, path, value) }));
  };

  // initial load
  useEffect(() => {
    const mode = (localStorage.getItem("chat_mode") as Mode) || "default";
    setMode([mode, true]);
    setSessionId(crypto.randomUUID());
  }, []);

  useEffect(() => {
    updateSettings(makeSettings(router.query));
  }, [updateSettings, router]);

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
            changeSetting={changeSetting}
          />
          <Chat
            sessionId={sessionId}
            settings={settings}
            onQuery={setQuery}
            onNewEntry={setHistory}
          />
          <ChatSettings settings={settings} changeSetting={changeSetting} />
        </div>
      </main>
    </>
  );
};

export default Playground;
