import { type NextPage } from "next";
import React from "react";
import Head from "next/head";
import Header from "../components/header";
import { SearchBox, Followup } from "../components/searchbox";
import { useState } from "react";
import { API_URL } from "../settings"

const Semantic: NextPage = () => {

  const [results, setResults] = useState<SemanticEntry[]>([]);

  const semantic_search = async (
    query: string,
    _query_source: "search" | "followups",
    disable: () => void,
    enable: (f_set: Followup[]) => void,
  ) => {

    disable();

    const res = await fetch(API_URL + "/semantic", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*", },
      body: JSON.stringify({query: query}),
    })

    if (!res.ok) {
      enable([]);
      console.log("load failure: " + res.status);
    }

    const data = await res.json();

    setResults(data);
    enable([]);

  };

  return (
    <>
      <Head>
        <title>AI Safety Info</title>
      </Head>
      <main>
        <Header page="semantic" />
        <h2>Retrieve relevant data sources from alignment research</h2>
        <SearchBox search={semantic_search} />
        <ul>
          {results.map((entry, i) => (
            <li key={"entry" + i}>
              <ShowSemanticEntry entry={entry} />
            </li>
          ))}
        </ul>
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
  authors: string[];
  date: string;
  url: string;
  tags: string;
  text: string;
};

const ShowSemanticEntry: React.FC<{entry: SemanticEntry}> = ({entry}) => {

  return (
    <div className="my-3">

      {/* horizontally split first row, title on left, authors on right */}
      <div className="flex">
        <h3 className="text-xl flex-1">{entry.title}</h3>
        <p className="flex-1 text-right my-0">{entry.authors.join(', ')} - {entry.date}</p>
      </div>
      { entry.text.split("\n").map((paragraph, i) => {
        const p = paragraph.trim();
        if (p === "") return <></>;
        if (p === ".....") return <hr key={"b" + i} />;
        return <p className="text-sm" key={"p" + i}> {paragraph} </p>
        })
      }

      <a href={entry.url}>Read more</a>
    </div>
  );
};


export default Semantic;
