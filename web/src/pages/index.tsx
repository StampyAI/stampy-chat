import { type NextPage } from "next";
import { useState, useEffect } from "react";
import Link from "next/link";

import { queryLLM, getStampyContent, runSearch } from "../hooks/useSearch";
import useSettings from "../hooks/useSettings";
import type { Mode } from "../types";
import Page from "../components/page";
import Chat from "../components/chat";
import { Controls } from "../components/controls";

const MAX_FOLLOWUPS = 4;

const Home: NextPage = () => {
  const [sessionId, setSessionId] = useState("");
  const { settings, setMode } = useSettings();

  // initial load
  useEffect(() => {
    setSessionId(crypto.randomUUID());
  }, []);

  return (
    <Page page="index">
      <Controls mode={settings.mode || "default"} setMode={setMode} />

      <h2 className="bg-red-100 text-red-800">
        <b>WARNING</b>: This is a very <b>early prototype</b>.{" "}
        <Link href="http://bit.ly/stampy-chat-issues" target="_blank">
          Feedback
        </Link>{" "}
        welcomed.
      </h2>

      <Chat sessionId={sessionId} settings={{ mode: settings.mode }} />
    </Page>
  );
};

export default Home;
