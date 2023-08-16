import { type AppType } from "next/dist/shared/lib/utils";
import { useEffect, useState } from "react";

import "~/styles/globals.css";

import { Glossary, GlossaryContext } from "../glossary";

const MyApp: AppType = ({ Component, pageProps }) => {
  const [glossary, setGlossary] = useState<{ g: Glossary, r: RegExp } | null>(null);

  // fetch glossary and compile regex once on load
  useEffect(() => {
    if (glossary === null)
      fetch("/questions/glossary")
        .then((res) => res.json())
        .then((data) => {
          const glossary: Glossary = new Map(Object.entries(data));
          const keys = Array.from(glossary.keys())
                            .sort((a, b) => b.length - a.length) // sort by length descending
                            .map((k) => k.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&')) // escape regex chars
                            .map((k) => `\\b${k}\\b`); // add word boundaries

          const regex = new RegExp(keys.join("|"), "gim");
          setGlossary({ g: glossary, r: regex });
        });
  }, []);

  return (
    <GlossaryContext.Provider value={glossary}>
      <Component {...pageProps} />
    </GlossaryContext.Provider>
  );
};

export default MyApp;
