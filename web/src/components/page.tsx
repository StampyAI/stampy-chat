import React, { ReactNode } from "react";
import Head from "next/head";
import Header from "./header";

const Page: React.FC<{ children: ReactNode; page: "index" | "semantic" }> = ({
  page,
  children,
}) => {
  return (
    <>
      <Head>
        <title>AI Safety Info</title>
      </Head>
      <main>
        <Header page={page} />
        {children}
      </main>
    </>
  );
};
export default Page;
