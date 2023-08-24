import Head from "next/head";
import React from "react";
import { type NextPage } from "next";
import { useState, useEffect } from "react";
import Link from "next/link";
import Image from "next/image";

import Header from "../components/header";
import { SearchBox } from "../components/searchbox";
import logo from "../logo.svg";
import { GlossarySpan } from "../components/glossary";
import { API_URL } from "../settings";
import { queryLLM, getStampyContent, runSearch } from "../hooks/useSearch";
import type {
  Citation,
  Entry,
  AssistantEntry,
  ErrorMessage,
  StampyMessage,
  CurrentSearch,
  Followup,
  SearchResult,
} from "../types";
import { Entry as EntryTag } from "../components/entry";
import { ProcessText } from "../components/citations";
import { ShowAssistantEntry } from "../components/assistant";
import { Controls, Mode } from "../components/controls";

// smooth-scroll to the bottom of the window if we're already less than 30% a screen away
// note: finicky interaction with "smooth" - maybe fix later.
function scroll30() {
  if (
    document.documentElement.scrollHeight - window.scrollY >
    window.innerHeight * 1.3
  )
    return;
  window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
}

const Home: NextPage = () => {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [runningIndex, setRunningIndex] = useState(0);

  const [current, setCurrent] = useState<CurrentSearch>();

  // [state, ready to save to localstorage]
  const [mode, setMode] = useState<[Mode, boolean]>(["default", false]);

  // store mode in localstorage
  useEffect(() => {
    if (mode[1]) localStorage.setItem("chat_mode", mode[0]);
  }, [mode]);

  // initial load
  useEffect(() => {
    const mode = (localStorage.getItem("chat_mode") as Mode) || "default";
    setMode([mode, true]);
  }, []);

  const updateCurrent = (current: CurrentSearch) => {
    setCurrent(current);
    if (current?.phase === "streaming") {
      scroll30();
    }
  };

  const search = async (
    query: string,
    query_source: "search" | "followups",
    disable: () => void,
    enable: (f_set: Followup[] | ((fs: Followup[]) => Followup[])) => void
  ) => {
    // clear the query box, append to entries

    const userEntry: Entry = {
      role: "user",
      content: query_source === "search" ? query : query.split("\n", 2)[1]!,
    };
    setEntries((prev) => [...prev, userEntry]);
    disable();

    const { result, followups } = await runSearch(
      query,
      query_source,
      mode[0],
      runningIndex,
      entries,
      updateCurrent
    );

    if (query_source === "search") {
      setRunningIndex(runningIndex + ProcessText(result.content, 0)[1].size);
    }
    setEntries((prev) => [...prev, result]);
    enable(followups || []);
    scroll30();
  };

  var last_entry = <></>;
  switch (current?.phase) {
    case "semantic":
      last_entry = <p>Loading: Performing semantic search...</p>;
      break;
    case "prompt":
      last_entry = <p>Loading: Creating prompt...</p>;
      break;
    case "llm":
      last_entry = <p>Loading: Waiting for LLM...</p>;
      break;
    case "streaming":
      last_entry = <ShowAssistantEntry entry={current} />;
      break;
  }

  return (
    <>
      <Head>
        <title>AI Safety Info</title>
      </Head>
      <main>
        <Header page="index" />
        <Controls mode={mode} setMode={setMode} />

        <h2 className="bg-red-100 text-red-800">
          <b>WARNING</b>: This is a very <b>early prototype</b> using data
          through June 2022.{" "}
          <Link href="http://bit.ly/stampy-chat-issues" target="_blank">
            Feedback
          </Link>{" "}
          welcomed.
        </h2>

        <ul>
          {entries.map((entry, i) => (
            <EntryTag entry={entry} key={i} />
          ))}

          <SearchBox search={search} />

          {last_entry}
        </ul>
      </main>
    </>
  );
};

export default Home;
