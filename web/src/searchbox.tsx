import React from "react";
import { useState, useEffect } from "react";
import TextareaAutosize from 'react-textarea-autosize';
import dynamic from 'next/dynamic'

export type Followup = {
  text: string;
  pageid: string;
  score: number;
}

// initial questions to fill the search box with.
export const initialQuestions: string[] = [
  "Are there any regulatory efforts aimed at addressing AI safety and alignment concerns?",
  "How can I help with AI safety and alignment?",
  "How could a predictive model - like an LLM - act like an agent?",
  "How could an AI possibly be an x-risk when some populations aren't even connected to the internet?",
  "I'm not convinced, why is this important?",
  "Summarize the differences in opinion between Eliezer Yudkowsky and Paul Christiano.",
  "What are \"RAAPs\"?",
  "What are \"scaling laws\" and how are they relevant to safety?",
  "What are some of the different research approaches?",
  "What are the differences between Inner and Outer alignment?",
  "What does the term \"x-risk\" mean?",
  "What is \"FOOM\"?",
  "What is \"instrumental convergence\"?",
  "What is a hard takeoff?",
  "What is a mesa-optimizer?",
  "What is AI safety and alignment?",
  "What is an AI arms race?",
  "What is an Intelligence Explosion?",
  "What is the \"orthogonality thesis\"?",
  "Why would we expect AI to be \"misaligned by default\"?",
]


const SearchBoxInternal: React.FC<{search: (
    query: string,
    query_source: "search" | "followups",
    disable: () => void,
    enable: (f_set: Followup[] | ((fs: Followup[]) => Followup[])) => void,
  ) => void,
}> = ({search}) => {

  const initial_query = initialQuestions[Math.floor(Math.random() * initialQuestions.length)] || "";

  const [ query, setQuery ] = useState(initial_query);
  const [ loading, setLoading ] = useState(false);
  const [ followups, setFollowups ] = useState<Followup[]>([]);

  const inputRef = React.useRef<HTMLTextAreaElement>(null);

  // because everything is async, I can't just manually set state at the
  // point we do a search. Instead it needs to be passed into the search
  // method, for some reason.
  const enable = (f_set: Followup[] | ((fs: Followup[]) => Followup[])) => {
    setLoading(false);
    setFollowups(f_set);
  };
  const disable = () => {
    setLoading(true);
    setQuery("");
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

  if (loading) return <></>;
  return (<>

    <div className="flex flex-col items-end mt-1"> {
      followups.map((followup, i) => {
        return <li key={i}>
          <button className="border border-gray-300 px-1 my-1" onClick={() => {
              search(followup.pageid + "\n" + followup.text, "followups", disable, enable);
            }}>
            <span> {followup.text} </span>
          </button>
        </li>
      })
    }</div>

    <form className="flex mt-1 mb-2" onSubmit={(e) => {
      e.preventDefault();
      search(query, "search", disable, enable);
    }}>
      <TextareaAutosize
        className="border border-gray-300 px-1 flex-1 resize-none"
        ref={inputRef}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={(e) => {
          // if <esc>, blur the input box
          if (e.key === "Escape") e.currentTarget.blur();
          // if <enter> without <shift>, submit the form (if it's not empty)
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            if (query.trim() !== "") search(query, "search", disable, enable);
          }
        }}
      />
      <button className="ml-2" type="submit" disabled={loading}>
        {loading ? "Loading..." : "Search"}
      </button>
    </form>
  </>);
};

export const SearchBox = dynamic(() => Promise.resolve(SearchBoxInternal), {
  ssr: false,
});

