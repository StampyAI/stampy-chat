import { useState } from "react";

import type { CurrentSearch, Citation } from "../types";

const updateCitations = (
  allCitations: Citation[],
  setCitations: (citations: Citation[]) => any,
  entry?: CurrentSearch
) => {
  if (!entry || !entry.citationsMap) return entry;

  const entryCitations = Array.from(entry.citationsMap.values());
  if (!entryCitations.some((c) => !c.index)) {
    // All of the entries citations have indexes, so there weren't any changes since the last check
    return entry;
  }

  // Get a mapping of all known citations, so as to reuse them if they appear again
  const citationsMapping = Object.fromEntries(
    allCitations.map((c) => [c.title + c.url, c.index])
  );

  entryCitations.forEach((c) => {
    const hash = c.title + c.url;
    const index = citationsMapping[hash];
    if (!index) {
      c.index = allCitations.length + 1;
      allCitations.push(c);
    } else {
      c.index = index;
    }
  });
  setCitations(allCitations);
  return entry;
};

export default function useCitations() {
  const [citations, setCitations] = useState<Citation[]>([]);

  const setEntryCitations = (entry: CurrentSearch) =>
    updateCitations(citations, setCitations, entry);

  return {
    citations,
    setEntryCitations,
  };
}
