import React from "react";
import { useState, useEffect } from "react";
import TextareaAutosize from 'react-textarea-autosize';

const SearchBox: React.FC<{search: (
    query: string,
    setQuery: (query: string) => void,
    setLoading: (loading: boolean) => void
) => void}> = ({search}) => {

    const [ query, setQuery ] = useState("");

    const [ loading, setLoading ] = useState(false);

    const inputRef = React.useRef<HTMLTextAreaElement>(null);


    useEffect(() => {
        // set focus on the input box
        if (!loading) inputRef.current?.focus();
    }, [loading]);

    if (loading) return <></>;
    return (<>
        <form className="flex mb-2 mt-1" onSubmit={async (e) => {
            e.preventDefault();
            search(query, setQuery, setLoading);
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
                        if (query.trim() !== "") search(query, setQuery, setLoading);
                    }
                }}
            />
            <button className="ml-2" type="submit" disabled={loading}>
                {loading ? "Loading..." : "Search"}
            </button>
        </form>
    </>);
};

export default SearchBox;
