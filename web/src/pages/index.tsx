import { type NextPage } from "next";
import { useState, useEffect } from "react";
import Link from "next/link";
import Image from 'next/image';

import Page from "../components/page"
import { API_URL } from "../settings"
import type { Citation, Entry, UserEntry, AssistantEntry, ErrorMessage, StampyMessage } from "../types";
import { SearchBox, Followup } from "../components/searchbox";
import { GlossarySpan } from "../components/glossary";
import { Controls, Mode } from "../components/controls";
import { ShowAssistantEntry } from "../components/assistant";
import { ProcessText } from "../components/citations";
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
  response: AssistantEntry;
};

type Mode = "rookie" | "concise" | "default";


// smooth-scroll to the bottom of the window if we're already less than 30% a screen away
// note: finicky interaction with "smooth" - maybe fix later.
function scroll30() {
  if (document.documentElement.scrollHeight - window.scrollY > window.innerHeight * 1.3) return;
  window.scrollTo({top: document.body.scrollHeight, behavior: "smooth"});
}

const Home: NextPage = () => {

  const [ entries, setEntries ] = useState<Entry[]>([]);
  const [ runningIndex, setRunningIndex ] = useState(0);
  const [ loadState, setLoadState ] = useState<State>({state: "idle"});

  // [state, ready to save to localstorage]
  const [ mode, setMode ] = useState<[Mode, boolean]>(["default", false]);

  // store mode in localstorage
  useEffect(() => {
    if (mode[1]) localStorage.setItem("chat_mode", mode[0]);
  }, [mode]);

  // initial load
  useEffect(() => {
    const mode = localStorage.getItem("chat_mode") as Mode || "default";
    setMode([mode, true]);
  }, []);


  const search = async (
    query: string,
    query_source: "search" | "followups",
    disable: () => void,
    enable: (f_set: Followup[] | ((fs: Followup[]) => Followup[])) => void,
  ) => {

    // clear the query box, append to entries

    const old_entries = entries;
    const new_entries: Entry[] = [...old_entries, {
      role: "user",
      content: query_source === "search" ? query : query.split("\n", 2)[1]!,
    }];
    setEntries(new_entries);
    disable();


    // ----------------------------- LLM BASED -----------------------------
    if (query_source === "search") {
      // do SSE on a POST request.
      const res = await fetch(API_URL + "/chat", {
        method: "POST",
        cache: "no-cache",
        keepalive: true,
        headers: {
          "Content-Type": "application/json",
          "Accept": "text/event-stream",
          "Allow-Control-Allow-Origin": "*"
        },

        body: JSON.stringify({query: query, mode: mode[0], history:
          old_entries.filter((entry) => entry.role !== "error")
                     .map((entry) => {
                       return {
                         "role" : entry.role,
                         "content" : entry.content.trim(),
                       }
                     })
        }),

      });

      if (!res.ok) {
        enable([]);
        setLoadState({state: "idle"});
        setEntries([...new_entries, {role: "error", content: "POST Error: " + res.status}]);
        return;
      }

      // read back the SSE stream

      const reader = res.body!.getReader();
      var message = "";
      var followups: Followup[] = [];
      read: while (true) {

        const {done, value} = await reader.read();

        if (done) break;
        const chunk = new TextDecoder("utf-8").decode(value);
        if (chunk.startsWith("event: close\n")) break;

        // note: this form isn't even remotely close to optimal in terms of
        // network usage. Lots of json overhead.

        for (const line of chunk.split('\n')) {

          // Most times, it seems that a single read() call will be one SSE "message",
          // but I'll do the proper aggregation spec thing in case that's not always true.

          if (line.startsWith("data: ")) message += line.slice(6);
          // Fixes #43
          if (!line.startsWith("data: ") && line !== "") message += line;
          if (line === "") {
            if (message !== "") {
              const data = JSON.parse(message);

              switch (data.state) {

                case "loading":

                  // display loading phases, once citations are available toss them
                  // into the loading state.

                  setLoadState((s) => {
                    var citations = s.state === "loading" ? s.citations : [];
                    if (data.citations !== undefined) {
                      citations = data.citations;
                    }
                    return {state: "loading", phase: data.phase, citations: citations};
                  });

                  break;

                case "streaming":

                  // incrementally build up the response

                  setLoadState((s) => {
                    const response = s.state === "streaming" ? s.response :
                          {role: "assistant",
                           content: "",
                           citations: s.state === "loading" ? s.citations : [],
                           base_count: runningIndex
                          };

                    return {state: "streaming", response: {
                      role: "assistant",
                      content: response.content + data.content,
                      citations: response.citations,
                      base_count: response.base_count
                    }};
                  });

                  scroll30();
                  break;

                case "done":

                  // append the response to the entries, reset to normal
                  setLoadState((s) => {
                    if (s.state === "streaming") {
                      setEntries([...new_entries, s.response]);
                      setRunningIndex((i) => (i + ProcessText(s.response.content, 0)[1].size));
                    }

                    return {state: "idle"};
                  });

                  // add any potential followup questions
                  var i = 0;
                  while ('followup_' + i in data) {
                    followups = [...followups, data['followup_' + i]];
                    i++;
                  }

                  break read;

                case "error":
                  setEntries([...new_entries, {role: "error", content: data.error}]);
                  setLoadState({state: "idle"});
                  break read;

              }
            }
            message = "";
          }
        }
      }

      enable(followups);
      scroll30();

    } else {
    // ----------------- HUMAN AUTHORED CONTENT RETRIEVAL ------------------
      const query_id = query.split("\n", 2)[0];

      const res = await fetch(API_URL + "/human/" + query_id, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
          "Allow-Control-Allow-Origin": "*"
        },
      });

      if (!res.ok) {
        enable([]);
        setLoadState({state: "idle"});
        setEntries([...new_entries, {role: "error", content: "POST Error: " + res.status}]);
        return;
      }

      const data = (await res.json()).data;

      setEntries([...new_entries, {
        role: "stampy",
        content: data.text,
        url: "https://aisafety.info/?state=" + data.pageid,
      }]);

      // re-enable the searchbox, with the question that was just answered
      // removed from the list of possible followups.

      // create an array of new followup questions from the data
      const f_new = data.relatedQuestions.map((f: any) => { return {
        pageid: f.pageid!,
        text: f.title!,
        score: 0
      };});

      const fpids = new Set(f_new.map((f: Followup) => f.pageid));

      enable((f_old: Followup[]) => {
        const f_old_filtered = f_old.filter((f) => f.pageid !== data.pageid && !fpids.has(f.pageid));
        return [...f_new, ...f_old_filtered].slice(0, MAX_FOLLOWUPS); // this is correct, it's N and not N-1 in javascript fsr
      });

      scroll30();
    }
  };

  var last_entry = <></>;
  if (loadState.state === "loading") {
    switch (loadState.phase) {
      case "semantic": last_entry = <p>Loading: Performing semantic search...</p>; break;
      case "prompt": last_entry = <p>Loading: Creating prompt...</p>; break;
      case "llm": last_entry = <p>Loading: Waiting for LLM...</p>; break;
    }
  } else if (loadState.state === "streaming") {
    last_entry = <ShowAssistantEntry entry={loadState.response}/>;
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
