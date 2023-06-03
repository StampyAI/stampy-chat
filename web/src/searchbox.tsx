import React from "react";
import { useState, useEffect } from "react";
import TextareaAutosize from 'react-textarea-autosize';

export type Followup = { 
    text: string;
    pageid: string;
    score: number;
}

export const SearchBox: React.FC<{search: (
        query: string,
        disable: () => void,
        enable: (followups: Followup[]) => void,
    ) => void,
}> = ({search}) => {

    const [ query, setQuery ] = useState("");
    const [ loading, setLoading ] = useState(false);
    const [ followups, setFollowups ] = useState<Followup[]>([]);

    const inputRef = React.useRef<HTMLTextAreaElement>(null);

    // because everything is async, I can't just manually set state at the
    // point we do a search. Instead it needs to be passed into the search
    // method, for some reason.
    const enable = (followups: Followup[]) => {
        setLoading(false); 
        setFollowups(followups);
    };
    const disable = () => {
        setLoading(true);
        setQuery("");
    };


    useEffect(() => {
        // set focus on the input box
        if (!loading) inputRef.current?.focus();
    }, [loading]);

    if (loading) return <></>;
    return (<>

        <div className="flex flex-col items-end"> {
          followups.map((followup, i) => {
            return <li key={i}>
              <button className="border border-gray-300 px-1 my-1" onClick={() => {
                  // temporary solution: open https://stampy.ai/?state={pageid} in a new tab
                  window.open("https://stampy.ai/?state=" + followup.pageid, "_blank");
              }}>
                <span> {followup.text} </span>
              </button>
            </li>
          })
        }</div>

        <form className="flex mt-1 mb-2" onSubmit={(e) => {
            e.preventDefault();
            search(query, disable, enable);
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
                        if (query.trim() !== "") search(query, disable, enable);
                    }
                }}
            />
            <button className="ml-2" type="submit" disabled={loading}>
                {loading ? "Loading..." : "Search"}
            </button>
        </form>
    </>);
};
