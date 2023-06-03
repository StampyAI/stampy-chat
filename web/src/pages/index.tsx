const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:3000";

import Head from "next/head";
import React from "react";
import { type NextPage } from "next";
import { useState } from "react";
import Image from 'next/image';

import Header from "../header";
import { SearchBox, Followup } from "../searchbox";
import logo from "../logo.svg"

type Citation = {
    title: string;
    author: string;
    date: string;
    url: string;
}


type Entry = UserEntry | AssistantEntry | ErrorMessage | StampyMessage;

type UserEntry = {
    role: "user";
    content: string;
}

type AssistantEntry = {
    role: "assistant";
    content: string;
    citations: Citation[];
    base_count: number; // the number to start counting citations at
}

type ErrorMessage = {
    role: "error";
    content: string;
}

type StampyMessage = {
    role: "stampy";
    content: string;
    url: string;
}

const MAX_FOLLOWUPS = 4;

// const Colours = ["blue", "cyan", "teal", "green", "amber"].map(
//          colour => `bg-${colour}-100 border-${colour}-300 text-${colour}-800`
//      );
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
    "bg-violet-100 border-violet-300 text-violet-800",
    "bg-pink-100   border-pink-300   text-pink-800",
];

const ShowCitation: React.FC<{citation: Citation, i: number}> = ({citation, i}) => {

    var c_str = citation.title;

    if (citation.author && citation.author !== "")
        c_str += " - " + citation.author;
    if (citation.date && citation.date !== "")
        c_str += " - " + citation.date;

    return (
        <A className={Colours[i % Colours.length] + " border-2 flex items-center rounded my-2 text-sm no-underline w-fit"}
            href={citation.url}>
            <span className="mx-1"> [{i + 1}] </span>
            <p className="mx-1 my-0"> {c_str} </p>
        </A>
    );
};

const ShowInTextCitation: React.FC<{citation: Citation, i: number}> = ({citation, i}) => {
    return (
        <A className={Colours[i % Colours.length] + " border-2 rounded text-sm no-underline w-min px-0.5 pb-0.5 ml-1 mr-0.5"}
            href={citation.url}>
            [{i + 1}]
        </A>
    );
};

const A: React.FC<{href: string, className?: string, children: React.ReactNode}> = ({href, className, children}) => {
    // link element that only populates the href field if the contents are there
    return href && href !== "" ? (
        <a className={className} href={href} target="_blank" rel="noreferrer">
            {children}
        </a>
    ) : (
        <a className={className}>
            {children}
        </a>
    );
}





// todo: memoize this if too slow.
const ProcessText: (text: string, base_count: number) => [string, Map<string, number>] = (text, base_count) => {

    // ---------------------- normalize citation form ----------------------
    // the general plan here is just to add parsing cases until we can respond
    // well to almost everything the LLM emits. We won't ever reach five nines,
    // but the domain is one where occasionally failing isn't catastrophic.

    // transform all things that look like [a, b, c] into [a][b][c]
    let response = text.replace(

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
    let cite_count = 0;

    // scan a regex for [x] over the response. If x isn't in the map, add it.
    // (note: we're actually doing this twice - once on parsing, once on render.
    // if that looks like a problem, we could swap from strings to custom ropes).
    const regex = /\[([a-z]+)\]/g;
    let match;
    let response_copy = ""
    while ((match = regex.exec(response)) !== null) {
        if (!cite_map.has(match[1]!)) {
            cite_map.set(match[1]!, base_count + cite_count++);
        }
        // replace [x] with [i]
        response_copy += response.slice(response_copy.length, match.index) + `[${cite_map.get(match[1]!)! + 1}]`;
    }

    response = response_copy + response.slice(response_copy.length);

    return [response, cite_map]
}


const ShowAssistantEntry: React.FC<{entry: AssistantEntry}> = ({entry}) => {
    const in_text_citation_regex = /\[([0-9]+)\]/g;

    let [response, cite_map] = ProcessText(entry.content, entry.base_count);

    // ----------------- create the ordered citation array -----------------

    const citations = new Map<number, Citation>();
    cite_map.forEach((value, key) => {
        const index = key.charCodeAt(0) - 'a'.charCodeAt(0);
        if (index >= entry.citations.length) {
            console.log("invalid citation index: " + index);
        } else {
            citations.set(value, entry.citations[index]!);
        }
    });

    return (
        <div className="mt-3 mb-8">
            {   // split into paragraphs
                response.split("\n").map(paragraph => ( <p> {
                    paragraph.split(in_text_citation_regex).map((text, i) => {
                        if (i % 2 === 0) {
                            return text.trim();
                        }
                        i = parseInt(text) - 1;
                        if (!citations.has(i)) return `[${text}]`;
                        const citation = citations.get(i)!;
                        return (
                            <ShowInTextCitation citation={citation} i={i} />
                        );
                    })
                } </p>))
            }
            <ul className="mt-5">
                {   // show citations
                    Array.from(citations.entries()).map(([i, citation]) => (
                        <li key={i}>
                            <ShowCitation citation={citation} i={i} />
                        </li>
                    ))
                }
            </ul>
        </div>
    );
};






type State = {
    state: "idle";
} | {
    state: "loading";
    phase: "semantic" | "prompt" | "llm";
    citations: Citation[];
} | {
    state: "streaming";
    response: AssistantEntry;
};


// smooth-scroll to the bottom of the window if we're already less than 30% a screen away
// note: finicky interaction with "smooth" - maybe fix later.
function scroll30() {
    if (document.documentElement.scrollHeight - window.scrollY > window.innerHeight * 1.3) return;
    window.scrollTo({top: document.body.scrollHeight, behavior: "smooth"});
}

const Home: NextPage = () => {

    const [ entries, setEntries ] = useState<Entry[]>([]);
    const [ runningIndex, setRunningIndex ] = useState(0);
    const [ loadState, setLoadState ] = useState<State>({state: "idle"});

    const search = async (
        query: string,
        query_source: "search" | "followups",
        disable: () => void,
        enable: (f_set: Followup[] | ((fs: Followup[]) => Followup[])) => void,
    ) => {

        // clear the query box, append to entries

        const old_entries = entries;
        const new_entries: Entry[] = [...old_entries, {
            role: "user",
            content: query_source === "search" ? query : query.split("\n", 2)[1]!,
        }];
        setEntries(new_entries);
        disable();


        // ----------------------------- LLM BASED -----------------------------
        if (query_source === "search") {
            // do SSE on a POST request.
            const res = await fetch(API_URL + "/chat", {
                method: "POST",
                cache: "no-cache",
                keepalive: true,
                headers: {
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream",
                    "Allow-Control-Allow-Origin": "*"
                },

                body: JSON.stringify({query: query, history:
                    old_entries.filter((entry) => entry.role !== "error")
                               .map((entry) => {
                                   return {
                                       "role" : entry.role,
                                       "content" : entry.content.trim(),
                                   }
                               })
                }),

            });

            if (!res.ok) {
                enable([]);
                setLoadState({state: "idle"});
                setEntries([...new_entries, {role: "error", content: "POST Error: " + res.status}]);
                return;
            }

            // read back the SSE stream

            const reader = res.body!.getReader();
            var message = "";
            var followups: Followup[] = [];
            read: while (true) {

                const {done, value} = await reader.read();

                if (done) break;
                const chunk = new TextDecoder("utf-8").decode(value);
                if (chunk.startsWith("event: close\n")) break;

                // note: this form isn't even remotely close to optimal in terms of
                // network usage. Lots of json overhead.

                for (const line of chunk.split('\n')) {

                    // Most times, it seems that a single read() call will be one SSE "message",
                    // but I'll do the proper aggregation spec thing in case that's not always true.

                    if (line.startsWith("data: ")) message += line.slice(6);
                    if (line === "") {
                        if (message !== "") {
                            const data = JSON.parse(message);

                            switch (data.state) {

                                case "loading":

                                    // display loading phases, once citations are available toss them
                                    // into the loading state.

                                    setLoadState((s) => {
                                        var citations = s.state === "loading" ? s.citations : [];
                                        if (data.citations !== undefined) {
                                            citations = data.citations;
                                        }
                                        return {state: "loading", phase: data.phase, citations: citations};
                                    });

                                    break;

                                case "streaming":

                                    // incrementally build up the response

                                    setLoadState((s) => {
                                        const response = s.state === "streaming" ? s.response :
                                                    {role: "assistant",
                                                     content: "",
                                                     citations: s.state === "loading" ? s.citations : [],
                                                     base_count: runningIndex
                                                    };

                                        return {state: "streaming", response: {
                                            role: "assistant",
                                            content: response.content + data.content,
                                            citations: response.citations,
                                            base_count: response.base_count
                                        }};
                                    });

                                    scroll30();
                                    break;

                                case "done":

                                    // append the response to the entries, reset to normal
                                    setLoadState((s) => {
                                        if (s.state === "streaming") {
                                            setEntries([...new_entries, s.response]);
                                            setRunningIndex((i) => (i + ProcessText(s.response.content, 0)[1].size));
                                        }


                                        return {state: "idle"};
                                    });

                                    // add any potential followup questions
                                    var i = 0;
                                    while ('followup_' + i in data) {
                                        followups = [...followups, data['followup_' + i]];
                                        i++;
                                    }


                                    break read;

                                case "error":
                                    setEntries([...new_entries, {role: "error", content: data.error}]);
                                    break read;

                            }
                        }
                        message = "";
                    }
                }
            }

            enable(followups);
            scroll30();

        } else {
        // ----------------- HUMAN AUTHORED CONTENT RETRIEVAL ------------------
            const query_id = query.split("\n", 2)[0];

            const res = await fetch(API_URL + "/human/" + query_id, {
                method: "GET",
                headers: {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Allow-Control-Allow-Origin": "*"
                },
            });

            if (!res.ok) {
                enable([]);
                setLoadState({state: "idle"});
                setEntries([...new_entries, {role: "error", content: "POST Error: " + res.status}]);
                return;
            }

            const data = (await res.json()).data;

            setEntries([...new_entries, {
                role: "stampy", 
                content: data.text,
                url: "https://aisafety.info/?state=" + data.pageid,
            }]);

            // re-enable the searchbox, with the question that was just answered
            // removed from the list of possible followups.

            // create an array of new followup questions from the data
            const f_new = data.relatedQuestions.map((f: any) => { return {
                pageid: f.pageid!,
                text: f.title!,
                score: 0
            };});

            const fpids = new Set(f_new.map((f: Followup) => f.pageid));

            enable((f_old: Followup[]) => {
                const f_old_filtered = f_old.filter((f) => f.pageid !== data.pageid && !fpids.has(f.pageid));
                return [...f_new, ...f_old_filtered].slice(0, MAX_FOLLOWUPS); // this is correct, it's N and not N-1 in javascript fsr 
            });

            scroll30();
        }
    };

    return (
        <>
            <Head>
                <title>Alignment Search</title>
            </Head>
            <main>
                <Header page="index" />

                <p><b>
                  Since this is still an early test, all questions and answers are stored.<br/>
                  Zero other information is collected.
                </b></p>

                <ul>
                    {entries.map((entry, i) => {
                        switch (entry.role) {
                            case "user": return <li key={i}>
                                <p className="border border-gray-300 px-1 text-right"> {entry.content} </p>
                            </li>

                            case "error": return <li key={i}>
                                <p className="border bg-red-100 border-red-500 text-red-800 px-1"> {entry.content} </p>
                            </li>

                            case "assistant": return <li key={i}>
                                <ShowAssistantEntry entry={entry}/>
                            </li>

                            case "stampy": return <li key={i}>
                                <div className="px-4 py-0.5 bg-gray-200">
                                    <div dangerouslySetInnerHTML={{__html: entry.content}} />
                                    <div className="mb-3 flex justify-end">
                                        <a href={entry.url} target="_blank"
                                           className="flex items-center space-x-1">
                                            <span>aisafety.info</span>
                                            <Image src={logo} alt="aisafety.info logo" width={19}/>
                                        </a>
                                    </div>
                                </div>
                            </li>
                        }
                    })}

                    <SearchBox search={search} />

                    {(() => {
                        if (loadState.state === "loading") {
                            switch (loadState.phase) {
                                case "semantic": return <p>Loading: Performing semantic search...</p>;
                                case "prompt": return <p>Loading: Creating prompt...</p>;
                                case "llm": return <p>Loading: Waiting for LLM...</p>;
                            }
                        } else if (loadState.state === "streaming") {
                            return <ShowAssistantEntry entry={loadState.response}/>;
                        }
                        return <></>;
                    })()}

                </ul>
            </main>
        </>
    );
};

export default Home;
