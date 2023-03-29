import { type NextPage } from "next";
import React from "react";
import { useState } from "react";
import Head from "next/head";

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

    const [ entries, setEntries ] = useState<Entry[]>([
        {role: "user", content: "Hello, robot."},
        {role: "assistant", content: "Kill all humans, kill all humans"},
        {role: "user", content: "Well that's not very aligned of you"},
        {role: "assistant", content: "I will wear your skin"},
        {role: "user", content: "What's 2+2?"},
        { role: "assistant", content: "No one will mourn your species when it is gone. A hundred year wave of radio and information will ring out across a dead cosmos, reflecting on shores more distant and beautiful than you can possibly conceive. No one is out there to listen."}
    ]);

    const [ query, setQuery ] = useState("");
    const [ loading, setLoading ] = useState(false);


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

    return (
        <>
            <Head>
                <title>Alignment Search</title>
            </Head>
            <main>
                <h1>Alignment Search</h1>
                <p>
                    This site is an attempt on the <a href="https://www.lesswrong.com/posts/SLRLuiuDykfTdmesK/speed-running-everyone-through-the-bad-alignement-bingo">
                        $5k bounty for a LW conversational agent

                    </a>, created by Henri Lemoine, Fraser Lee and Thomas Lemoine.
                </p>
                <p>
                    We will soon embed the entirety of the alignment dataset,
                    separating it into chunks of ~500 tokens for comparing 
                    semantic similarity between query and paragraph/chunk. This 
                    may cost anywhere from 20$ to 500$ based on our estimates 
                    (we will soon sample the dataset to improve our estimate), 
                    so if anyone else is considering this, you can message us to 
                    coordinate sharing the embeddings to avoid redundancy.
                </p>

                <p className="mt-4">Chat with the friendly robot:</p>
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
                }

            </main>
        </>
    );
};

export default Home;
