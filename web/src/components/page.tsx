import React, { ReactNode } from "react";
import Head from "next/head";
import type { Page as PageType } from "./header";
import Header from "./header";

const Page: React.FC<{
  children: ReactNode;
  widescreen?: boolean;
  page: PageType;
}> = ({ page, children, widescreen = false }) => {
  return (
    <>
      <Head>
        <title>AI Safety Info</title>
      </Head>
      <main style={widescreen ? { maxWidth: "none" } : {}}>
        <Header page={page} />
        {children}
      </main>
    </>
  );
};
export default Page;
