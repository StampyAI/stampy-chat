import { useState, useEffect } from "react";

// temporary hack to get glossary working
const GLOSSARY_JSON = {"chain of thought prompting":{"term":"chain of thought prompting","pageid":"8EL7","contents":"<p>Chain-of-thought prompting is a technique which makes a language model generate intermediate reasoning steps in its output.</p>\n"},"chain-of-thought":{"term":"chain-of-thought","pageid":"8EL7","contents":"<p>Chain-of-thought prompting is a technique which makes a language model generate intermediate reasoning steps in its output.</p>\n"},"goodhart's law":{"term":"goodhart's law","pageid":"8185","contents":"<p>Goodhart’s law states that when a measure becomes a target, it ceases to be a good measure.</p>\n"},"the big g,":{"term":"the big g,","pageid":"8185","contents":"<p>Goodhart’s law states that when a measure becomes a target, it ceases to be a good measure.</p>\n"},"terminal goals":{"term":"terminal goals","pageid":"","contents":"<p>Goals which are valued as ends in themselves, rather than as instrumental to something else.</p>\n"},"terminal goal":{"term":"terminal goal","pageid":"","contents":"<p>Goals which are valued as ends in themselves, rather than as instrumental to something else.</p>\n"},"orthogonality thesis":{"term":"orthogonality thesis","pageid":"6568","contents":"<p>The thesis that any level of intelligence is compatible with any terminal goals. This implies that intelligence alone is not enough to make a system moral.</p>\n"},"instrumental convergence":{"term":"instrumental convergence","pageid":"897I","contents":"<p>Instrumental convergence is the idea that different AI agents, each with distinct terminal goals, will end up adopting many of the same instrumental goals.</p>\n"},"instrumentally convergent goals":{"term":"instrumentally convergent goals","pageid":"897I","contents":"<p>Instrumental convergence is the idea that different AI agents, each with distinct terminal goals, will end up adopting many of the same instrumental goals.</p>\n"},"llm":{"term":"llm","pageid":"","contents":"<p>A large language model is an AI  model which has been trained on a large body of text, in order to produce texts in a human-like way.</p>\n"},"large language model":{"term":"large language model","pageid":"","contents":"<p>A large language model is an AI  model which has been trained on a large body of text, in order to produce texts in a human-like way.</p>\n"},"goal misgeneralization":{"term":"goal misgeneralization","pageid":"","contents":"<p>pursuing a different goal during deployment from the one that was pursued during training due to distribution shift</p>\n"},"interpretability":{"term":"interpretability","pageid":"8241","contents":"<p>Interpretability is an area of alignment research that aims to make machine learning systems easier for humans to understand.</p>\n"},"existential risk":{"term":"existential risk","pageid":"89LL","contents":"<p>risks that threaten the destruction of humanity's long-term potential, including human extinction</p>\n"}}

type GlossaryItem = {
    term: string;
    pageid: string;
    contents: string;
};

// A component which wraps a paragraph and injects glossary terms into it as
// hoverable pop-up links. The text is immediately rendered normally, but after
// the glossary is loaded (which happens once per page, asynchronously), the
// glossary terms are replaced with elements.
export const GlossaryP: React.FC<{content: string}> = ({content}) => {
    const [glossary, setGlossary] = useState<Map<string, GlossaryItem> | null>(null);
    const [glossaryRegex, setGlossaryRegex] = useState<RegExp | null>(null);

    useEffect(() => {
        if (glossary === null) {
            const glossary = new Map(Object.entries(GLOSSARY_JSON));
            setGlossary(glossary);
            setGlossaryRegex(new RegExp(Array.from(glossary.keys()).join("|"), "gim"));
        }
    }, [glossary]);

    // If the glossary hasn't loaded yet, just render the text normally.
    if (glossary == null || glossaryRegex == null) {
        return <span dangerouslySetInnerHTML={{__html: content}} />;
    }

    // Otherwise, replace glossary terms with links. We can do this in
    // O(n * sum of term lengths) by finding String.prototype.indexOf of
    // each term in the glossary (since that'd probably be backed by KMP)
    // but I think it should be faster to compile a regex state machine
    // once and use that instead.

    return <span dangerouslySetInnerHTML={{__html: content.replace(glossaryRegex!, (match) => {

        const item = glossary.get(match.toLowerCase());
        if (item == undefined) return match;

        const hover_content = item.contents;
        const pageid = item.pageid;

        return `
            <a href="https://aisafety.info/?state=${pageid}"
               target="_blank"
               class="glossary-link">
                 ${match}
            </a>
            <div class="glossary-hover">${hover_content}</div>
        `;

    })}} />;
}




