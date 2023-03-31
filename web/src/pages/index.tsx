const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:3000";

import Head from "next/head";
import React from "react";
import { type NextPage } from "next";
import { useState } from "react";

import Header from "../header";
import SearchBox from "../searchbox";


type UserEntry = {
    role: "user";
    content: string;
}

type AssistantEntry = {
    role: "assistant";
    content: string;
    citations: Citation[];
}

type Entry = UserEntry | AssistantEntry;

type Citation = {
    title: string;
    author: string;
    date: string;
    url: string;
}

// const Colours = ["blue", "cyan", "teal", "green", "amber"].map(colour => `bg-${colour}-100 border-${colour}-300 text-${colour}-800`);
// this would be nice, but Tailwind needs te actual string of the class to be in
// the source file for it to be included in the build

const Colours = [
    // "bg-teal-100   border-teal-300   text-teal-800",
    "bg-red-100    border-red-300    text-red-800",
    "bg-amber-100  border-amber-300  text-amber-800",
    "bg-orange-100 border-orange-300 text-orange-800",
    "bg-lime-100   border-lime-300   text-lime-800",
    "bg-green-100  border-green-300  text-green-800",
    "bg-cyan-100  border-cyan-300  text-cyan-800",
    "bg-blue-100  border-blue-300  text-blue-800",
];

const ShowCitation: React.FC<{citation: Citation, i: number}> = ({citation, i}) => {
    return (
        <a className={Colours[i % Colours.length] + " border-2 flex items-center rounded my-2 text-sm no-underline w-fit"}
            href={citation.url} target="_blank" rel="noreferrer">
            <span className="mx-1"> [{i + 1}] </span>
            <p className="mx-1 my-0">
                {citation.title + " - " + citation.author + " - " + citation.date}
            </p>
        </a>
    );
};

const ShowEntry: React.FC<{entry: Entry}> = ({entry}) => {

    // user message
    if (entry.role === "user") {
        return ( <p className="border border-gray-300 px-1"> {entry.content} </p>);
    }

    // system reply
    return (
        <div className="my-3">
            {   // split into paragraphs
                entry.content.split("\n").map(paragraph => ( <p> {paragraph} </p>))
            }
            <ul>
                {   // show citations
                    entry.citations.map((citation, i) => (
                        <li key={i}>
                            <ShowCitation citation={citation} i={i} />
                        </li>
                    ))
                }
            </ul>
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

        const res = await fetch(API_URL + "/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json", "Allow-Control-Allow-Origin": "*" },
            body: JSON.stringify({query: query, history: old_entries}),
        })

        if (!res.ok) {
            setLoading(false);
            console.log("load failure: " + res.status);
            return;
        }

        const data = await res.json();

        setEntries([...new_entries, {role: "assistant", content: await data.response, citations: await data.citations}]);

        setLoading(false);

    };

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
                <SearchBox search={search} />
            </main>
        </>
    );
};

export default Home;
