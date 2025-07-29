import type { Citation } from "../types";
import { Colours, A } from "./html";

export const formatCitations: (text: string) => string = (text) => {
  // ---------------------- normalize citation form ----------------------
  // the general plan here is just to add parsing cases until we can respond
  // well to almost everything the LLM emits. We won't ever reach five nines,
  // but the domain is one where occasionally failing isn't catastrophic.

  // transform all things that look like [1, 2, 3] into [1][2][3]
  let response = text.replace(
    /\[((?:\d+,\s*)*\d+)\]/g, // identify groups of this form

    (block: string) =>
      block
        .split(",")
        .map((x) => x.trim())
        .join("][")
  );

  // transform all things that look like [(1), (2), (3)] into [(1)][(2)][(3)]
  response = response.replace(
    /\[((?:\(\d+\),\s*)*\(\d+\))\]/g, // identify groups of this form

    (block: string) =>
      block
        .split(",")
        .map((x) => x.trim())
        .join("][")
  );

  // transform all things that look like [(3)] into [3]
  response = response.replace(
    /\[\((\d+)\)\]/g,
    (_match: string, x: string) => `[${x}]`
  );

  // transform all things that look like [ 12 ] into [12]
  response = response.replace(
    /\[\s*(\d+)\s*\]/g,
    (_match: string, x: string) => `[${x}]`
  );
  return response;
};

export const findCitations: (
  text: string,
  citations: Citation[]
) => Map<string, Citation> = (text, citations) => {
  // figure out what citations are in the response, and map them appropriately
  const cite_map = new Map<string, Citation>();
  const byRef = citations.reduce(
    (acc, c) => ({ ...acc, [c.reference]: c }),
    {}
  ) as {
    [k: string]: Citation;
  };
  let index = 1;
  const refs = [...text.matchAll(/\[(\d+)\]/g)];
  refs.forEach(([_, num]) => {
    if (!num || cite_map.has(num)) return;
    const citation = byRef[num as keyof typeof byRef];
    if (!citation) return;

    cite_map.set(num, { ...citation, index: index++ });
  });

  return cite_map;
};

export const ShowCitation: React.FC<{ citation: Citation }> = ({
  citation,
}) => {
  var c_str = citation.title;

  if (citation.authors && citation.authors.length > 0)
    c_str += " - " + citation.authors.join(", ");
  if (citation.date && citation.date !== "") c_str += " - " + citation.date;

  // if we don't have a url, link to a duckduckgo search for the title instead
  const url =
    citation.url && citation.url !== ""
      ? citation.url
      : `https://duckduckgo.com/?q=${encodeURIComponent(citation.title)}`;

  return (
    <A
      className={
        Colours[(citation.index - 1) % Colours.length] +
        " my-2 flex w-fit items-center rounded border-2 text-sm no-underline"
      }
      href={url}
    >
      <span className="mx-1"> [{citation.index}] </span>
      <p className="mx-1 my-0"> {c_str} </p>
    </A>
  );
};

const Popup = ({
  children,
  content,
}: {
  content: string;
  children: React.ReactElement;
}) => {
  return (
    <div className="popup-container">
      {children}
      <div className="popup">
        {content.split("\n").map((v, i) => (
          <div className="text-section" key={i}>
            {v}
          </div>
        ))}
      </div>
    </div>
  );
};

export const CitationRef: React.FC<{ citation?: Citation }> = ({
  citation,
}) => {
  if (!citation) return null;

  const split = citation.text.split('"""');
  const text = split.length === 1 ? citation.text : split[1];
  const url =
    citation.url && citation.url !== ""
      ? citation.url
      : `https://duckduckgo.com/?q=${encodeURIComponent(citation.title)}`;
  return (
    <Popup content={text || ""}>
      <A
        className={
          Colours[(citation.index - 1) % Colours.length] +
          " ml-1 mr-0.5 w-min rounded border-2 px-0.5 pb-0.5 text-sm no-underline"
        }
        href={url}
      >
        [{citation.index}]
      </A>
    </Popup>
  );
};

export const CitationsBlock: React.FC<{
  text: string;
  citations: Map<string, Citation>;
  textRenderer: (t: string) => any;
}> = ({ text, citations, textRenderer }) => {
  const regex = /\[([a-z]+)\]/g;
  return (
    <div className="text-section">
      {text.split(regex).map((part, i) => {
        // When splitting, the even parts are basic text sections, while the odd ones are
        // citations
        if (i % 2 == 0) {
          return textRenderer(part);
        } else {
          return <CitationRef citation={citations.get(part)} key={i} />;
        }
      })}
    </div>
  );
};
