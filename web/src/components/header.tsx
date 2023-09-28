import React from "react";
import Link from "next/link";
import Image from 'next/image';
import logo from "../logo.svg"

const Header: React.FC<{page: "index" | "semantic"}> = ({page}) => {
  const sidebar = page === "index" ? (
    <span className="flex flex-col font-semibold flex-1 justify-start text-right">
      <Link href="/semantic">Show Sources</Link>
    </span>
  ) : (
    <span className="flex flex-col font-semibold flex-1 justify-start text-right">
      <Link href="/">Go Chat</Link>
    </span>
  );

  return (<div className="flex my-4">
              <Image src={logo} alt="aisafety.info logo" width={36}/>
              <h1 className="flex-1 my-0">AI Safety Chatbot</h1>
              {sidebar}
          </div>);
};

export default Header;
