import React from "react";
import Link from "next/link";

const Header: React.FC<{page: "index" | "semantic"}> = ({page}) => {
    const sidebar = page === "index" ? (
        <span className="flex flex-col font-semibold flex-1 justify-start text-right">
            <p className="my-0">Conversational Agent</p>
            <Link href="/semantic">Semantic Search</Link>
        </span>
    ) : (
        <span className="flex flex-col font-semibold flex-1 justify-start text-right">
            <Link href="/">Conversational Agent</Link>
            <p className="my-0">Semantic Search</p>
        </span>
    );
        
    return (<>
                <div className="flex my-4">
                    <h1 className="flex-1 my-0">AlignmentSearch</h1>
                    {sidebar}
                </div>
                <p>
                    This site has been created by McGill students Henri Lemoine, Fraser Lee, and Thomas Lemoine
                    as an attempt to create a "conversational FAQ" that can answer questions about AI alignment.
                    When asked a question, we
                </p>
                <ol>
                    <li>Embed the question into a low dimensional semantic space</li>
                    <li>Pull the semantically closest passages out of a massive alignment dataset</li>
                    <li>Instruct an LLM to construct a response while citing these passages</li>
                    <li>Display this response in conversational flow with inline citations</li>
                </ol>
                <p>
                    We've created this as an attempt on the <a href="https://www.lesswrong.com/posts/SLRLuiuDykfTdmesK/speed-running-everyone-through-the-bad-alignement-bingo"> $5k bounty for a LW conversational agent</a>.
                </p>
                <p>
                    We hope that it can be a useful tool for the community, and we're eager to hear feedback and suggestions.
                    For a technical report on our implemention, see our <u>LessWrong post</u> <i>(coming soon)</i>.
                </p>
            </>);
};

export default Header;
