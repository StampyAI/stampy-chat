import type { Citation } from "../types";
import { Colours, A } from "./html";


// todo: memoize this if too slow.
export const ProcessText: (text: string, base_count: number) => [string, Map<string, number>] = (text, base_count) => {

  // ---------------------- normalize citation form ----------------------
  // the general plan here is just to add parsing cases until we can respond
  // well to almost everything the LLM emits. We won't ever reach five nines,
  // but the domain is one where occasionally failing isn't catastrophic.

  // transform all things that look like [a, b, c] into [a][b][c]
  let response = text.replace(

      /\[((?:[a-z]+,\s*)*[a-z]+)\]/g, // identify groups of this form

      (block: string) => block.split(',')
                              .map((x) => x.trim())
                              .join("][")
  )

  // transform all things that look like [(a), (b), (c)] into [(a)][(b)][(c)]
  response = response.replace(

    /\[((?:\([a-z]+\),\s*)*\([a-z]+\))\]/g, // identify groups of this form

    (block: string) => block.split(',')
                            .map((x) => x.trim())
                            .join("][")
  )

  // transform all things that look like [(a)] into [a]
  response = response.replace(
    /\[\(([a-z]+)\)\]/g,
    (_match: string, x: string) => `[${x}]`
  )

  // transform all things that look like [ a ] into [a]
  response = response.replace(
    /\[\s*([a-z]+)\s*\]/g,
    (_match: string, x: string) => `[${x}]`
  )

  // -------------- map citations from strings into numbers --------------

  // figure out what citations are in the response, and map them appropriately
  const cite_map = new Map<string, number>();
  let cite_count = 0;

  // scan a regex for [x] over the response. If x isn't in the map, add it.
  // (note: we're actually doing this twice - once on parsing, once on render.
  // if that looks like a problem, we could swap from strings to custom ropes).
  const regex = /\[([a-z]+)\]/g;
  let match;
  let response_copy = ""
  while ((match = regex.exec(response)) !== null) {
    if (!cite_map.has(match[1]!)) {
      cite_map.set(match[1]!, base_count + cite_count++);
    }
    // replace [x] with [i]
    response_copy += response.slice(response_copy.length, match.index) + `[${cite_map.get(match[1]!)! + 1}]`;
  }

  response = response_copy + response.slice(response_copy.length);

  return [response, cite_map]
}

export const ShowCitation: React.FC<{citation: Citation, i: number}> = ({citation, i}) => {

  var c_str = citation.title;

  if (citation.authors && citation.authors.length > 0)
    c_str += " - " + citation.authors.join(', ');
  if (citation.date && citation.date !== "")
    c_str += " - " + citation.date;

  // if we don't have a url, link to a duckduckgo search for the title instead
  const url = citation.url && citation.url !== ""
        ? citation.url
        : `https://duckduckgo.com/?q=${encodeURIComponent(citation.title)}`;

  return (
    <A className={Colours[i % Colours.length] + " border-2 flex items-center rounded my-2 text-sm no-underline w-fit"}
      href={url}>
      <span className="mx-1"> [{i + 1}] </span>
      <p className="mx-1 my-0"> {c_str} </p>
    </A>
  );
};

export const ShowInTextCitation: React.FC<{citation: Citation, i: number}> = ({citation, i}) => {
  const url = citation.url && citation.url !== ""
        ? citation.url
        : `https://duckduckgo.com/?q=${encodeURIComponent(citation.title)}`;
  return (
    <A className={Colours[i % Colours.length] + " border-2 rounded text-sm no-underline w-min px-0.5 pb-0.5 ml-1 mr-0.5"}
      href={url}>
      [{i + 1}]
    </A>
  );
};
