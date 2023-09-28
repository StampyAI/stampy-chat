import { type AppType } from "next/dist/shared/lib/utils";
import { useEffect, useState } from "react";

import "~/styles/globals.css";

import { Glossary, GlossaryContext } from "../components/glossary";

const MyApp: AppType = ({ Component, pageProps }) => {
  const [glossary, setGlossary] = useState<{ g: Glossary, r: RegExp } | null>(null);

  // fetch glossary and compile regex once on load
  useEffect(() => {
    if (glossary === null)
      tempHackFetch("/questions/glossary")
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

// ------------------- hack until server endpoint is working -------------------

const GLOSSARY_JSON = {"chain of thought prompting":{"term":"chain of thought prompting","pageid":"8EL7","contents":"<p>Chain-of-thought prompting is a technique which makes a language model generate intermediate reasoning steps in its output.</p>\n"},"chain-of-thought":{"term":"chain-of-thought","pageid":"8EL7","contents":"<p>Chain-of-thought prompting is a technique which makes a language model generate intermediate reasoning steps in its output.</p>\n"},"goodhart's law":{"term":"goodhart's law","pageid":"8185","contents":"<p>Goodhart’s law states that when a measure becomes a target, it ceases to be a good measure.</p>\n"},"the big g,":{"term":"the big g,","pageid":"8185","contents":"<p>Goodhart’s law states that when a measure becomes a target, it ceases to be a good measure.</p>\n"},"terminal goals":{"term":"terminal goals","pageid":"","contents":"<p>Goals which are valued as ends in themselves, rather than as instrumental to something else.</p>\n"},"terminal goal":{"term":"terminal goal","pageid":"","contents":"<p>Goals which are valued as ends in themselves, rather than as instrumental to something else.</p>\n"},"orthogonality thesis":{"term":"orthogonality thesis","pageid":"6568","contents":"<p>The thesis that any level of intelligence is compatible with any terminal goals. This implies that intelligence alone is not enough to make a system moral.</p>\n"},"instrumental convergence":{"term":"instrumental convergence","pageid":"897I","contents":"<p>Instrumental convergence is the idea that different AI agents, each with distinct terminal goals, will end up adopting many of the same instrumental goals.</p>\n"},"instrumentally convergent goals":{"term":"instrumentally convergent goals","pageid":"897I","contents":"<p>Instrumental convergence is the idea that different AI agents, each with distinct terminal goals, will end up adopting many of the same instrumental goals.</p>\n"},"llm":{"term":"llm","pageid":"","contents":"<p>A large language model is an AI  model which has been trained on a large body of text, in order to produce texts in a human-like way.</p>\n"},"large language model":{"term":"large language model","pageid":"","contents":"<p>A large language model is an AI  model which has been trained on a large body of text, in order to produce texts in a human-like way.</p>\n"},"goal misgeneralization":{"term":"goal misgeneralization","pageid":"","contents":"<p>pursuing a different goal during deployment from the one that was pursued during training due to distribution shift</p>\n"},"interpretability":{"term":"interpretability","pageid":"8241","contents":"<p>Interpretability is an area of alignment research that aims to make machine learning systems easier for humans to understand.</p>\n"},"existential risk":{"term":"existential risk","pageid":"89LL","contents":"<p>risks that threaten the destruction of humanity's long-term potential, including human extinction</p>\n"}}

const tempHackFetch = (_url: string) => {
  return new Promise<Response>((resolve, _reject) => {
    setTimeout(() => {
      resolve({
        ok: true,
        json: () => Promise.resolve(GLOSSARY_JSON),
      } as unknown as Response);
    }, 1000);
  });
}
