import type { NextPage } from "next";
import { useState, useEffect } from "react";
import Page from "../components/page";

import useSettings from "../hooks/useSettings";
import type { Entry } from "../types";
import Chat from "../components/chat";
import { Controls } from "../components/controls";
import { ChatSettings, ChatPrompts } from "../components/settings";

const Playground: NextPage = () => {
  const [sessionId, setSessionId] = useState("");

  const [query, setQuery] = useState<string>("");
  const [history, setHistory] = useState<Entry[]>([]);
  const { settings, changeSetting, setMode } = useSettings();

  // initial load
  useEffect(() => {
    setSessionId(crypto.randomUUID());
  }, []);

  return (
    <Page page="playground" widescreen={true}>
      <Controls mode={settings.mode || "default"} setMode={setMode} />
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
    </Page>
  );
};

export default Playground;
