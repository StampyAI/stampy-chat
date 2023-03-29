import { type NextPage } from "next";
import React from "react";
import { useState } from "react";
import Head from "next/head";

const Semantic: NextPage = () => {
    return (
        <>
            <Head>
                <title>Alignment Search</title>
            </Head>
            <main>
                <h2>Get the most semantic similar results to a query:</h2>
                <SearchBox />
            </main>
        </>
    );
};

// Round trip test. If this works, our heavier usecase probably will (famous last words)
// The one real difference is we'll want to send back a series of results as we get
// them back from OpenAI - I think we can just do this with a websocket, which
// shouldn't be too much harder.

type SemanticEntry = {
    title: string;
    author: string;
    date: string;
    url: string;
    tags: string;
    text: string;
};

const ShowSemanticEntry: React.FC<{entry: SemanticEntry}> = ({entry}) => {
    return (
        <div className="my-3">

            {/* horizontally split first row, title on left, author on right */}
            <div className="flex">
                <h3 className="text-xl flex-1">{entry.title}</h3>
                <p className="flex-1 text-right my-0">{entry.author} - {entry.date}</p>
            </div>

            <p className="text-sm">{entry.text}</p>

            <a href={entry.url}>Read more</a>
        </div>
    );
};

const SearchBox: React.FC = () => {

    const [query,   setQuery]   = useState("");
    const [results, setResults] = useState<SemanticEntry[] | string>([]);
    const [loading, setLoading] = useState(false);

    const semantic_search = async (query: String) => {
        
        setLoading(true);

        const res = await fetch("/api/semantic_search", {
            method: "POST",
            headers: { "Content-Type": "application/json", },
            body: JSON.stringify({query: query}),
        })

        if (!res.ok) {
            setLoading(false);
            return "load failure: " + res.status;
        }

        const data = await res.json();
        setLoading(false);
        return data;
    };

        

    return (
        <>
            <form className="flex mb-2" onSubmit={async (e) => { // store in a form so that <enter> submits
                e.preventDefault();
                setResults(await semantic_search(query));
            }}>

                <input
                    type="text"
                    className="border border-gray-300 px-1 flex-1"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                />
                <button className="ml-2" type="submit" disabled={loading}>
                    {loading ? "Loading..." : "Search"}
                </button>
            </form>

            {
                loading ? <p>loading...</p> :
                typeof results === "string" ? <p className="text-red-500">{results}</p> :
                <ul>
                    {results.map((result, i) => (
                        <li key={i}>
                            <ShowSemanticEntry entry={result} />
                        </li>
                    ))}
                </ul>
            }
        </>
    );
};


export default Semantic;
