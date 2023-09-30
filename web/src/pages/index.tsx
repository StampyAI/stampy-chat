import { type NextPage } from "next";
import { useState, useEffect } from "react";
import Link from "next/link";
import Image from 'next/image';

import Page from "../components/page"
import { API_URL } from "../settings"
import { queryLLM, getStampyContent, runSearch } from "../hooks/useSearch";
import type {
    CurrentSearch,
    Citation,
    Entry,
    UserEntry,
    AssistantEntry as AssistantEntryType,
    ErrorMessage,
    StampyMessage
} from "../types";
import { SearchBox, Followup } from "../components/searchbox";
import { GlossarySpan } from "../components/glossary";
import { Controls, Mode } from "../components/controls";
import { AssistantEntry } from "../components/assistant";
import { Entry as EntryTag } from "../components/entry";

const MAX_FOLLOWUPS = 4;

type State = {
  state: "idle";
} | {
  state: "loading";
  phase: "semantic" | "prompt" | "llm";
  citations: Citation[];
} | {
  state: "streaming";
  response: AssistantEntryType;
};

type Mode = "rookie" | "concise" | "default";


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
  const [current, setCurrent] = useState<CurrentSearch>();
  const [sessionId, setSessionId] = useState()

  // [state, ready to save to localstorage]
  const [mode, setMode] = useState<[Mode, boolean]>(["default", false]);

  // store mode in localstorage
  useEffect(() => {
    if (mode[1]) localStorage.setItem("chat_mode", mode[0]);

  }, [mode]);

  // initial load
  useEffect(() => {
    const mode = localStorage.getItem("chat_mode") as Mode || "default";
    setMode([mode, true]);
    setSessionId(crypto.randomUUID());
  }, []);

  const updateCurrent = (current: CurrentSearch) => {
      setCurrent(current);
      if (current?.phase === "streaming") {
          scroll30();
      }
  };

  const updateCitations = (current: CurrentSearch) => {
       const citations = Array.from(current.citationsMap.values());
       if (citations.some(c => !c.index)) {
           let index = 1;
           citations.forEach((c) => {c.index = index++});
           setCurrent(current)
       }
    }

  const search = async (
    query: string,
    query_source: "search" | "followups",
    disable: () => void,
    enable: (f_set: Followup[] | ((fs: Followup[]) => Followup[])) => void,
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
          entries,
          updateCurrent,
          sessionId,
      );
      setCurrent(undefined);

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
      updateCitations(current)
      last_entry = <AssistantEntry entry={current} />;
      break;
    case "followups":
      last_entry = <>
        <AssistantEntry entry={current} />
        <p>Checking for followups...</p>
      </>;
      break;
  }

  return (
    <Page page="index">
      <Controls mode={mode} setMode={setMode} />

      <h2 className="bg-red-100 text-red-800"><b>WARNING</b>: This is a very <b>early prototype</b>. <Link href="http://bit.ly/stampy-chat-issues" target="_blank">Feedback</Link> welcomed.</h2>


      <ul>
        {entries.map((entry, i) => (
          <EntryTag entry={entry} key={i} />
        ))}
        <SearchBox search={search} />

        { last_entry }

      </ul>
    </Page>
  );
};

export default Home;
