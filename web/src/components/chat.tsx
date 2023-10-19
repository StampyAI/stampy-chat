import { useState, useEffect } from "react";
import { queryLLM, getStampyContent, runSearch } from "../hooks/useSearch";

import type {
  CurrentSearch,
  Citation,
  Entry,
  AssistantEntry as AssistantEntryType,
  LLMSettings,
  Followup,
} from "../types";
import useCitations from "../hooks/useCitations";
import { SearchBox } from "../components/searchbox";
import { AssistantEntry } from "../components/assistant";
import { Entry as EntryTag } from "../components/entry";

const MAX_FOLLOWUPS = 4;

type State =
  | {
      state: "idle";
    }
  | {
      state: "loading";
      phase: "semantic" | "prompt" | "llm";
      citations: Citation[];
    }
  | {
      state: "streaming";
      response: AssistantEntryType;
    };

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

export const ChatResponse = ({
  current,
  defaultElem,
}: {
  current: CurrentSearch;
  defaultElem?: any;
}) => {
  switch (current?.phase) {
    case "started":
      return <p>Loading: Sending query...</p>;
    case "semantic":
      return <p>Loading: Performing semantic search...</p>;
    case "context":
      return <p>Loading: Creating context...</p>;
    case "prompt":
      return <p>Loading: Creating prompt...</p>;
    case "llm":
      return <p>Loading: Waiting for LLM...</p>;
    case "streaming":
      return <AssistantEntry entry={current} />;
    case "followups":
      return (
        <>
          <AssistantEntry entry={current} />
          <p>Checking for followups...</p>
        </>
      );
    default:
      return defaultElem;
  }
};

type ChatParams = {
  sessionId: string;
  settings: LLMSettings;
  onQuery?: (q: string) => any;
  onNewEntry?: (history: Entry[]) => any;
};

const Chat = ({ sessionId, settings, onQuery, onNewEntry }: ChatParams) => {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [current, setCurrent] = useState<CurrentSearch>();
  const { citations, setEntryCitations } = useCitations();

  const updateCurrent = (current: CurrentSearch) => {
    if (current?.phase === "streaming") {
      setCurrent(setEntryCitations(current));
      scroll30();
    } else {
      setCurrent(current);
    }
  };

  const addEntry = (entry: Entry) => {
    setEntries((prev) => {
      const entries = [...prev, entry];
      if (onNewEntry) {
        onNewEntry(entries);
      }
      return entries;
    });
  };

  const search = async (
    query: string,
    query_source: "search" | "followups",
    enable: (f_set: Followup[] | ((fs: Followup[]) => Followup[])) => void,
    controller: AbortController
  ) => {
    // clear the query box, append to entries
    const userEntry: Entry = {
      role: "user",
      content: query_source === "search" ? query : query.split("\n", 2)[1]!,
    };

    const { result, followups } = await runSearch(
      query,
      query_source,
      settings,
      entries,
      updateCurrent,
      sessionId,
      controller
    );
    if (result.content !== "aborted") {
      addEntry(userEntry);
      addEntry(result);
      enable(followups || []);
      scroll30();
    } else {
      enable([]);
    }
    setCurrent(undefined);
  };

  return (
    <ul className="flex-auto">
      {entries.map(
        (entry, i) =>
          !entry.deleted && (
            <li className="group relative flex" key={i}>
              <EntryTag entry={entry} />
              <span
                className="delete-item absolute right-5 hidden cursor-pointer group-hover:block"
                onClick={() => {
                  const entry = entries[i];
                  if (entry !== undefined) {
                    entry.deleted = true;
                    setEntries([...entries]);
                  }
                }}
              >
                ✕
              </span>
            </li>
          )
      )}
      <SearchBox search={search} onQuery={onQuery} />
      <ChatResponse
        current={current}
        defaultElem={
          <button onClick={() => setEntries([])}>Clear history</button>
        }
      />
    </ul>
  );
};

export default Chat;
