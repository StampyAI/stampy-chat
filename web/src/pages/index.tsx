import { type NextPage } from "next";
import React from "react";
import { useState } from "react";
import Head from "next/head";

const Home: NextPage = () => {
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
                <p>Python serverless test:</p>
                <ApiButton />
                <ApiButton2 />
            </main>
        </>
    );
};

// round trip test. If this works, our heavier usecase probably will (famous last words)
// The one real difference is we'll want to send back a series of results as we get
// them back from OpenAI - I think we can just do this with a websocket, which
// shouldn't be too different.

const ApiButton: React.FC = () => {
    const [response, setResponse] = useState("");
    const [num, setNum] = useState(12);
    const [loading, setLoading] = useState(false);

    const calculate = async () => {

        setLoading(true);

        const res = await fetch("/api/embeddings", {
            method: "POST",
            headers: { "Content-Type": "application/json", },
            body: JSON.stringify({number: num}),
        })

        const data = await res.json();

        setLoading(false);

        return data.result || "error";

    };

    return (
        <>
            <span>
                <button className="mr-2"
                onClick={async () => setResponse(JSON.stringify(await calculate()))} disabled={loading}>
                    {loading ? "Loading..." : "Calculate"}
                </button>
                the factorial of
                <input 
                    type = "number" 
                    className = "w-10 border border-gray-300 px-1 mx-1" value={num} onChange={(e) => setNum(parseInt(e.target.value))} />
                = {loading ? "..." : response}
            </span>
        </>
    );
};


const ApiButton2: React.FC = () => {
    const [response, setResponse] = useState("");
    const [query, setQuery] = useState("");
    const [loading, setLoading] = useState(false);

    const getEmbeddings = async () => {

        setLoading(true);

        const res = await fetch("/api", {
            method: "POST",
            headers: { "Content-Type": "application/json", },
            body: JSON.stringify({query: query}),
        })

        const data = await res.json();

        setLoading(false);

        return data;

        // return data.result || "error";

    };

    return (
        <>
            <span>
                <button className="mr-2"
                onClick={async () => setResponse(JSON.stringify(await getEmbeddings()))} disabled={loading}> {loading ? "Loading..." : "Calculate"} </button>
                the factorial of
                <input 
                    type = "number" 
                    className = "w-10 border border-gray-300 px-1 mx-1" value={query} onChange={(e) => setQuery(e.target.value)} />
                = {loading ? "..." : response}
            </span>
        </>
    );
};


export default Home;
