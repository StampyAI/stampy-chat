import React from "react";
import { useState, useEffect } from "react";
import { initialQuestions } from "../settings";
import type { Followup } from "../types";
import TextareaAutosize from "react-textarea-autosize";
import dynamic from "next/dynamic";

const SearchBoxInternal: React.FC<{
  query: string;
  search: (query: string) => void;
  abortSearch: () => void;
  onQuery: (q: string) => any;
  loading?: boolean;
}> = ({ query, search, onQuery, abortSearch, loading = false }) => {
  const inputRef = React.useRef<HTMLTextAreaElement>(null);

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

  const runSearch = (query: string) => () => {
    if (loading || query.trim() === "") return;
    search(query);
  };

  const cancelSearch = () => {
    abortSearch();
  };

  return (
    <>
      <div className="mt-1 mb-2 flex">
        <TextareaAutosize
          className="flex-1 resize-none border border-gray-300 px-1"
          ref={inputRef}
          value={query}
          onChange={(e) => onQuery(e.target.value)}
          onKeyDown={(e) => {
            // if <esc>, blur the input box
            if (e.key === "Escape") e.currentTarget.blur();
            // if <enter> without <shift>, submit the form (if it's not empty)
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              runSearch(query)();
            }
          }}
        />
        <button
          className="ml-2"
          type="button"
          onClick={loading ? cancelSearch : runSearch(query)}
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
