import React from "react";
import Link from "next/link";
import Image from "next/image";
import logo from "../logo.svg";

export type Page = "index" | "semantic" | "playground" | "tester";

const Header: React.FC<{ page: Page }> = ({ page }) => {
  const sidebar =
    page === "index" ? (
      <span className="flex flex-1 flex-col justify-start text-right font-semibold">
        <Link href="/semantic">Show Sources</Link>
      </span>
    ) : (
      <span className="flex flex-col justify-start text-right font-semibold">
        <Link href="/">Go Chat</Link>
      </span>
    );

  return (
    <div className="my-4 flex">
      <Image src={logo} alt="aisafety.info logo" width={36} />
      <h1 className="my-0 flex-1">AI Safety Chatbot</h1>
      {sidebar}
    </div>
  );
};

export default Header;
