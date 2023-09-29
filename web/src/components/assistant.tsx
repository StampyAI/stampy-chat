import { ProcessText, ShowCitation, ShowInTextCitation } from "./citations";
import { GlossarySpan } from "./glossary";
import type { Citation, AssistantEntry } from "../types";

export const ShowAssistantEntry: React.FC<{entry: AssistantEntry}> = ({entry}) => {
  const in_text_citation_regex = /\[([0-9]+)\]/g;

  let [response, cite_map] = ProcessText(entry.content, entry.base_count);

  // ----------------- create the ordered citation array -----------------

  const citations = new Map<number, Citation>();
  cite_map.forEach((value, key) => {
    const index = key.charCodeAt(0) - 'a'.charCodeAt(0);
    if (index >= entry.citations.length) {
      console.log("invalid citation index: " + index);
    } else {
      citations.set(value, entry.citations[index]!);
    }
  });

  return (
    <div className="mt-3 mb-8">
      {  // split into paragraphs
        response.split("\n").map(paragraph => ( <p> {
          paragraph.split(in_text_citation_regex).map((text, i) => {
            if (i % 2 === 0) {
              return <GlossarySpan content={text.trim()} />;
            }
            i = parseInt(text) - 1;
            if (!citations.has(i)) return `[${text}]`;
            const citation = citations.get(i)!;
            return (
              <ShowInTextCitation citation={citation} i={i} />
            );
          })
        } </p>))
      }
      <ul className="mt-5">
        {  // show citations
          Array.from(citations.entries()).map(([i, citation]) => (
            <li key={i}>
              <ShowCitation citation={citation} i={i} />
            </li>
          ))
        }
      </ul>
    </div>
  );
};
