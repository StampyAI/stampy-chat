const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:3000";

import Head from "next/head";
import React from "react";
import { type NextPage } from "next";
import { useState } from "react";

import Header from "../header";
import SearchBox from "../searchbox";

type Citation = {
    title: string;
    author: string;
    date: string;
    url: string;
}

type UserEntry = {
    role: "user";
    content: string;
}

type AssistantEntry = {
    role: "assistant";
    content: string;
    display_content: string;
    citations: Map<number, Citation>;
}

type Entry = UserEntry | AssistantEntry;

// const Colours = ["blue", "cyan", "teal", "green", "amber"].map(colour => `bg-${colour}-100 border-${colour}-300 text-${colour}-800`);
// this would be nice, but Tailwind needs te actual string of the class to be in
// the source file for it to be included in the build

const Colours = [
    "bg-red-100    border-red-300    text-red-800",
    "bg-amber-100  border-amber-300  text-amber-800",
    "bg-orange-100 border-orange-300 text-orange-800",
    "bg-lime-100   border-lime-300   text-lime-800",
    "bg-green-100  border-green-300  text-green-800",
    "bg-cyan-100   border-cyan-300   text-cyan-800",
    "bg-blue-100   border-blue-300   text-blue-800",
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

const ShowInTextCitation: React.FC<{citation: Citation, i: number}> = ({citation, i}) => {
    return (
        <a className={Colours[i % Colours.length] + " border-2 rounded text-sm no-underline w-min px-0.5 pb-0.5 ml-1 mr-0.5"}
            href={citation.url} target="_blank" rel="noreferrer">
            [{i + 1}]
        </a>
    );
};

const ShowEntry: React.FC<{entry: Entry}> = ({entry}) => {

    // user message
    if (entry.role === "user") {
        return ( <p className="border border-gray-300 px-1"> {entry.content} </p>);
    }

    const in_text_citation_regex = /\[([0-9]+)\]/g;

    // system reply
    return (
        <div className="my-3">
            {   // split into paragraphs
                entry.display_content.split("\n").map(paragraph => ( <p> {
                    paragraph.split(in_text_citation_regex).map((text, i) => {
                        if (i % 2 === 0) {
                            return text.trim();
                        }
                        i = parseInt(text) - 1;
                        if (!entry.citations.has(i)) return `[${text}]`;
                        const citation = entry.citations.get(i)!;
                        return (
                            <ShowInTextCitation citation={citation} i={i} />
                        );
                    })
                } </p>))
            }
            <ul>
                {   // show citations
                    Array.from(entry.citations.entries()).map(([i, citation]) => (
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
    const [ runningIndex, setRunningIndex ] = useState(0);

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
            body: JSON.stringify({query: query, history: old_entries.map((entry) => {
                return {
                    "role" : entry.role,
                    "content" : entry.content
                }
            })})
        })

        if (!res.ok) {
            setLoading(false);
            console.log("load failure: " + res.status);
            return;
        }

        const data = await res.json();

        // ---------------------- normalize citation form ----------------------

        // transform all things that look like [a, b, c] into [a][b][c]
        let response = data.response.replace(

                    /\[((?:[a-z]+,\s*)*[a-z]+)\]/g, // identify groups of this form

                    (block: string) => block.split(',')
                                            .map((x) => x.trim())
                                            .join("][")
        )

        // transform all things that look like [(a), (b), (c)] into [(a)][(b)][(c)]
        response = response.replace(
            
                /\[((?:\([a-z]+\),\s*)*\([a-z]+\))\]/g, // identify groups of this form

                (block: string) => block.split(',')
                                        .map((x) => x.trim())
                                        .join("][")
        )

        // transform all things that look like [(a)] into [a]
        response = response.replace(
            /\[\(([a-z]+)\)\]/g,
            (_match: string, x: string) => `[${x}]`
        )

        // transform all things that look like [ a ] into [a]
        response = response.replace(
            /\[\s*([a-z]+)\s*\]/g,
            (_match: string, x: string) => `[${x}]`
        )

        // -------------- map citations from strings into numbers --------------

        // figure out what citations are in the response, and map them appropriately
        const cite_map = new Map<string, number>();
        let cite_count = runningIndex;

        // scan a regex for [x] over the response. If x isn't in the map, add it.
        const regex = /\[([a-z]+)\]/g;
        let match;
        let response_copy = ""
        while ((match = regex.exec(response)) !== null) {
            if (!cite_map.has(match[1]!)) {
                cite_map.set(match[1]!, cite_count++);
            }
            // replace [x] with [i]
            response_copy += response.slice(response_copy.length, match.index) + `[${cite_map.get(match[1]!)! + 1}]`;
        }

        setRunningIndex(cite_count);

        response = response_copy + response.slice(response_copy.length);

        // ----------------- create the ordered citation array -----------------

        const citations = new Map<number, Citation>();
        cite_map.forEach((value, key) => {
            citations.set(value, data.citations[key.charCodeAt(0) - 'a'.charCodeAt(0)]);
        });

        setEntries([...new_entries, {role: "assistant", 
                                     content: await data.response, 
                                     display_content: response,
                                     citations: citations}]);

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
