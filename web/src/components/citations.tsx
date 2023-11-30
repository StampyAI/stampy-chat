import type { Citation } from "../types";
import { Colours, A } from "./html";

export const formatCitations: (text: string) => string = (text) => {
  // ---------------------- normalize citation form ----------------------
  // the general plan here is just to add parsing cases until we can respond
  // well to almost everything the LLM emits. We won't ever reach five nines,
  // but the domain is one where occasionally failing isn't catastrophic.

  // transform all things that look like [a, b, c] into [a][b][c]
  let response = text.replace(
    /\[((?:[a-z]+,\s*)*[a-z]+)\]/g, // identify groups of this form

    (block: string) =>
      block
        .split(",")
        .map((x) => x.trim())
        .join("][")
  );

  // transform all things that look like [(a), (b), (c)] into [(a)][(b)][(c)]
  response = response.replace(
    /\[((?:\([a-z]+\),\s*)*\([a-z]+\))\]/g, // identify groups of this form

    (block: string) =>
      block
        .split(",")
        .map((x) => x.trim())
        .join("][")
  );

  // transform all things that look like [(a)] into [a]
  response = response.replace(
    /\[\(([a-z]+)\)\]/g,
    (_match: string, x: string) => `[${x}]`
  );

  // transform all things that look like [ a ] into [a]
  response = response.replace(
    /\[\s*([a-z]+)\s*\]/g,
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

  // scan a regex for [x] over the response. If x isn't in the map, add it.
  // (note: we're actually doing this twice - once on parsing, once on render.
  // if that looks like a problem, we could swap from strings to custom ropes).
  const regex = /\[([a-z]+)\]/g;
  let match;
  while ((match = regex.exec(text)) !== null) {
    const letter = match[1];
    if (!letter || cite_map.has(letter!)) continue;

    const citation = citations[letter.charCodeAt(0) - "a".charCodeAt(0)];
    if (!citation) continue;

    cite_map.set(letter!, citation);
  }
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
