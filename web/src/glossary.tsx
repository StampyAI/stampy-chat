import { createContext, useContext } from "react";

type GlossaryItem = {
  term: string;
  pageid: string;
  contents: string;
};

export type Glossary = Map<string, GlossaryItem>;

export const GlossaryContext = createContext<{g: Glossary, r: RegExp} | null>(null);

// A component which wraps arbitrary html in a span, and injects glossary terms
// into it as hoverable pop-up links. The text is immediately rendered normally,
// but after the glossary is loaded (which happens once per page, asynchronously),
// the glossary terms are replaced with elements.

export const GlossarySpan: React.FC<{content: string}> = ({content}) => {

  const g = useContext(GlossaryContext);

  // If the glossary hasn't loaded yet, just render the text normally.
  if (g == null) {
    return <span dangerouslySetInnerHTML={{__html: content}} />;
  }

  const glossary = g.g;
  const glossaryRegex = g.r;

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

        if (pageid == undefined || pageid.trim() == "") {
            return `
                <div class="glossary-hover" nowrap>${hover_content}</div>
                <span class="glossary-link">${match}</span>
            `;
        } else {
            return `
                <div class="glossary-hover" nowrap>${hover_content}</div>
                <a href="https://aisafety.info/?state=${pageid}"
                   target="_blank"
                   class="glossary-link">
                     ${match}
                </a>
            `;
        }

  })}} />;
}
