import { useState, useEffect } from "react";
import {
  queryLLM,
  getStampyContent,
  EntryRole,
  HistoryEntry,
} from "../hooks/useSearch";
import { initialQuestions } from "../settings";

import type {
  CurrentSearch,
  Citation,
  Entry,
  AssistantEntry as AssistantEntryType,
  LLMSettings,
  Followup,
  SearchResult,
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

// smooth-scroll to the bottom of the window if we're already less than 10% a screen away
// note: finicky interaction with "smooth" - maybe fix later.
function scroll30() {
  if (
    document.documentElement.scrollHeight - window.scrollY <
    window.innerHeight * 1.1
  ) {
    window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
  }
}

const randomQuestion = () =>
  initialQuestions[Math.floor(Math.random() * initialQuestions.length)] || "";

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
    case "history":
      return <p>Loading: Processing history...</p>;
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

const makeHistory = (query: string, entries: Entry[]): HistoryEntry[] => {
  const getRole = (entry: Entry): EntryRole => {
    if (entry.deleted) return "deleted";
    if (entry.role === "stampy") return "assistant";
    return entry.role;
  };

  const history = entries
    .filter((entry) => entry.role !== "error")
    .map((entry) => ({
      role: getRole(entry),
      content: entry.content.trim(),
    }));
  return [...history, { role: "user", content: query }];
};

type ChatParams = {
  sessionId: string;
  settings: LLMSettings;
  initialQuery?: string;
  onQuery?: (q: string) => any;
  onNewEntry?: (history: Entry[]) => any;
};

const Chat = ({
  initialQuery,
  sessionId,
  settings,
  onQuery,
  onNewEntry,
}: ChatParams) => {
  const [entries, setEntries] = useState<Entry[]>([]);

  const [query, setQuery] = useState(() => initialQuery || randomQuestion());
  const [current, setCurrent] = useState<CurrentSearch>();
  const [followups, setFollowups] = useState<Followup[]>([]);
  const [controller, setController] = useState(() => new AbortController());
  const { citations, setEntryCitations } = useCitations();

  const updateCurrent = (current: CurrentSearch) => {
    if (current?.phase === "streaming") {
      setCurrent(setEntryCitations(current));
      scroll30();
    } else {
      setCurrent(current);
    }
  };

  const addResult = (query: string, { result, followups }: SearchResult) => {
    const userEntry = { role: "user", content: query };
    setEntries((prev) => {
      const entries = [...prev, userEntry, result] as Entry[];
      if (onNewEntry) {
        onNewEntry(entries);
      }
      return entries;
    });
    setFollowups(followups || []);
    setQuery("");
    scroll30();
  };

  const abortable =
    (f: any) =>
    (...args: any) => {
      controller.abort();
      const newController = new AbortController();
      setController(newController);
      return f(newController, ...args);
    };

  const search = async (controller: AbortController, query: string) => {
    // clear the query box, append to entries
    setFollowups([]);

    const history = makeHistory(query, entries);

    const result = await queryLLM(
      settings,
      history,
      updateCurrent,
      sessionId,
      controller
    );

    if (result.result.content !== "aborted") {
      addResult(query, result);
    }
    setCurrent(undefined);
  };

  const fetchFollowup = async (
    controller: AbortController,
    followup: Followup
  ) => {
    setCurrent({ role: "assistant", content: "", phase: "started" });
    const result = await getStampyContent(followup.pageid, controller);
    if (!controller.signal.aborted) {
      addResult(followup.text, result);
    }
    setCurrent(undefined);
  };

  const deleteEntry = (i: number) => {
    const entry = entries[i];
    if (entry === undefined) {
      return;
    } else if (
      i === entries.length - 1 &&
      ["assistant", "stampy", "error"].includes(entry.role)
    ) {
      const prev = entries[i - 1];
      if (prev !== undefined) setQuery(prev.content);
      setEntries(entries.slice(0, i - 1));
      setFollowups([]);
    } else {
      entry.deleted = true;
      setEntries([...entries]);
    }
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
                onClick={() => deleteEntry(i)}
              >
                ✕
              </span>
            </li>
          )
      )}

      <Followups followups={followups} onClick={abortable(fetchFollowup)} />
      <SearchBox
        search={abortable(search)}
        query={query}
        onQuery={(v: string) => {
          setQuery(v);
          onQuery && onQuery(v);
        }}
        abortSearch={() => controller.abort()}
      />
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

const Followups = ({
  followups,
  onClick,
}: {
  followups: Followup[];
  onClick: (f: Followup) => void;
}) => (
  <div className="mt-1 flex flex-col items-end">
    {followups.map((followup: Followup, i: number) => (
      <li key={i}>
        <button
          className="my-1 border border-gray-300 px-1"
          onClick={() => onClick(followup)}
        >
          <span> {followup.text} </span>
        </button>
      </li>
    ))}
  </div>
);
