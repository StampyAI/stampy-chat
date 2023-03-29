import { type NextPage } from "next";
import React from "react";
import { useState, useEffect } from "react";
import TextareaAutosize from 'react-textarea-autosize';
import Head from "next/head";
import Header from "../header";

type Entry = {
    role: "user" | "assistant";
    content: string;
};

const ShowEntry: React.FC<{entry: Entry}> = ({entry}) => {
    if (entry.role === "user") {
        return ( <p className="border border-gray-300 px-1"> {entry.content} </p>);
    }

    return (
        <div className="my-3">
            {   // split into paragraphs
                entry.content.split("\n").map((paragraph, i) => ( <p key={i}> {paragraph} </p>))
            }
        </div>
    );
};

const Home: NextPage = () => {

    const [ entries, setEntries ] = useState<Entry[]>([]);
    const [ query, setQuery ] = useState("");
    const [ loading, setLoading ] = useState(false);

    const inputRef = React.useRef<HTMLTextAreaElement>(null);


    const search = async (query: string) => {
        
        // clear the query box, append to entries
        const old_entries = entries;
        const new_entries: Entry[] = [...old_entries, {role: "user", content: query}];
        setEntries(new_entries);
        setQuery("");

        setLoading(true);

        const res = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json", },
            body: JSON.stringify({query: query, history: old_entries}),
        })

        if (!res.ok) {
            setLoading(false);
            return "load failure: " + res.status;
        }

        const response = res.body!.getReader().read().then(({value}) => {
            return new TextDecoder("utf-8").decode(value);
        });

        setEntries([...new_entries, {role: "assistant", content: await response}]);

        setLoading(false);

    };

    useEffect(() => {
        // set focus on the input box
        if (!loading) inputRef.current?.focus();
    }, [loading]);


    return (
        <>
            <Head>
                <title>Alignment Search</title>
            </Head>
            <main>
                <Header page="index" />
                <ul>
                    {entries.map((entry, i) => (
                        <li key={i}>
                            <ShowEntry entry={entry} />
                        </li>
                    ))}
                </ul>
                { loading ? <p>loading...</p> :
                    <form className="flex mb-2" onSubmit={async (e) => { // store in a form so that <enter> submits
                        e.preventDefault();
                        await search(query);
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
                                    if (query.trim() !== "") search(query);
                                }
                            }}
                        />
                        <button className="ml-2" type="submit" disabled={loading}>
                            {loading ? "Loading..." : "Search"}
                        </button>
                    </form>
                }
            </main>
        </>
    );
};

export default Home;
