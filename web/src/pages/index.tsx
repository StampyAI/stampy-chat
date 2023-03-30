const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:3000";

import Head from "next/head";
import React from "react";
import { type NextPage } from "next";
import { useState } from "react";

import Header from "../header";
import SearchBox from "../searchbox";

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


    const search = async (
        query: string,
        setQuery: (query: string) => void,
        setLoading: (loading: boolean) => void
    ) => {
        
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
            console.log("load failure: " + res.status);
            return;
        }

        const response = res.body!.getReader().read().then(({value}) => {
            return new TextDecoder("utf-8").decode(value);
        });

        setEntries([...new_entries, {role: "assistant", content: await response}]);

        setLoading(false);

    };

    return (
        <>
            <Head>
                <title>Alignment Search</title>
            </Head>
            <main>
                <p>1: {API_URL}</p>
                <Header page="index" />
                <ul>
                    {entries.map((entry, i) => (
                        <li key={i}>
                            <ShowEntry entry={entry} />
                        </li>
                    ))}
                </ul>
                <SearchBox search={search} />
            </main>
        </>
    );
};

export default Home;
