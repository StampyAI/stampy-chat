import React from "react";
import { useState, useEffect } from "react";
import { initialQuestions } from "../settings";
import type { Followup } from "../types";
import TextareaAutosize from "react-textarea-autosize";
import dynamic from "next/dynamic";

const SearchBoxInternal: React.FC<{
  search: (
    query: string,
    query_source: "search" | "followups",
    enable: (f_set: Followup[] | ((fs: Followup[]) => Followup[])) => void,
    controller: AbortController
  ) => void;
  onQuery?: (q: string) => any;
}> = ({ search, onQuery }) => {
  const initial_query =
    initialQuestions[Math.floor(Math.random() * initialQuestions.length)] || "";

  const [query, setQuery] = useState(initial_query);
  const [loading, setLoading] = useState(false);
  const [followups, setFollowups] = useState<Followup[]>([]);
  const [controller, setController] = useState(new AbortController());

  const inputRef = React.useRef<HTMLTextAreaElement>(null);

  // because everything is async, I can't just manually set state at the
  // point we do a search. Instead it needs to be passed into the search
  // method, for some reason.
  const enable =
    (controller: AbortController) =>
    (f_set: Followup[] | ((fs: Followup[]) => Followup[])) => {
      if (!controller.signal.aborted) setQuery("");

      setLoading(false);
      setFollowups(f_set);
    };

  useEffect(() => {
    // set focus on the input box
    if (!loading) inputRef.current?.focus();
  }, [loading]);

  // on first mount focus and set cursor to end of input
  useEffect(() => {
    if (!inputRef.current) return;
    inputRef.current.focus();
    inputRef.current.selectionStart = inputRef.current.textLength;
    inputRef.current.selectionEnd = inputRef.current.textLength;
  }, []);

  const runSearch =
    (query: string, searchtype: "search" | "followups") => () => {
      if (loading || query.trim() === "") return;

      setLoading(true);
      const controller = new AbortController();
      setController(controller);
      search(query, searchtype, enable(controller), controller);
    };
  const cancelSearch = () => controller.abort();

  return (
    <>
      <div className="mt-1 flex flex-col items-end">
        {" "}
        {followups.map((followup, i) => {
          return (
            <li key={i}>
              <button
                className="my-1 border border-gray-300 px-1"
                onClick={runSearch(
                  followup.pageid + "\n" + followup.text,
                  "followups"
                )}
              >
                <span> {followup.text} </span>
              </button>
            </li>
          );
        })}
      </div>

      <div className="mt-1 mb-2 flex">
        <TextareaAutosize
          className="flex-1 resize-none border border-gray-300 px-1"
          ref={inputRef}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            onQuery && onQuery(e.target.value);
          }}
          onKeyDown={(e) => {
            // if <esc>, blur the input box
            if (e.key === "Escape") e.currentTarget.blur();
            // if <enter> without <shift>, submit the form (if it's not empty)
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              runSearch(query, "search")();
            }
          }}
        />
        <button
          className="ml-2"
          type="button"
          onClick={loading ? cancelSearch : runSearch(query, "search")}
        >
          {loading ? "Cancel" : "Search"}
        </button>
      </div>
    </>
  );
};

export const SearchBox = dynamic(() => Promise.resolve(SearchBoxInternal), {
  ssr: false,
});
