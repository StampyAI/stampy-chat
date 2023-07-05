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
            </>);
};

export default Header;
