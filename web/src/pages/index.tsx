import { useState, useEffect } from "react";
import { type NextPage } from "next";
import { useRouter } from "next/router";
import Link from "next/link";

import useSettings from "../hooks/useSettings";
import Page from "../components/page";
import Chat from "../components/chat";
import { Controls } from "../components/controls";

const MAX_FOLLOWUPS = 4;

const Home: NextPage = () => {
  const [sessionId, setSessionId] = useState("");
  const { settings, setMode } = useSettings();
  const router = useRouter();

  // initial load
  useEffect(() => {
    setSessionId(crypto.randomUUID());
  }, []);
  const initialQuery = Array.isArray(router?.query?.question)
    ? router?.query?.question[0]
    : router?.query?.question;

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

      {router.isReady && (
        <Chat
          sessionId={sessionId}
          settings={{ mode: settings.mode }}
          initialQuery={initialQuery}
        />
      )}
    </Page>
  );
};

export default Home;
