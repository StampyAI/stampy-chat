import { API_URL, STAMPY_URL, STAMPY_CONTENT_URL } from "../settings";
import type {
  Citation,
  Entry,
  AssistantEntry,
  ErrorMessage,
  StampyMessage,
  CurrentSearch,
  Followup,
  SearchResult,
} from "../types";

const MAX_FOLLOWUPS = 4;
const DATA_HEADER = "data: "
const EVENT_END_HEADER = "event: close"

type HistoryEntry = {
  role: "error" | "stampy" | "assistant" | "user";
  content: string;
};

export async function* iterateData(res: Response) {
  const reader = res.body!.getReader();
  var message = "";

  while (true) {
    const { done, value } = await reader.read();

    if (done) return;

    const chunk = new TextDecoder("utf-8").decode(value);
    for (const line of chunk.split("\n")) {
      // Most times, it seems that a single read() call will be one SSE "message",
      // but I'll do the proper aggregation spec thing in case that's not always true.

      if (line.startsWith(EVENT_END_HEADER)) {
        return;
      } else if (line.startsWith(DATA_HEADER)) {
        message += line.slice(DATA_HEADER.length);
        // Fixes #43
      } else if (line !== "") {
        message += line;
      } else if (message !== "") {
        yield JSON.parse(message);
        message = "";
      }
    }
  }
}

export const extractAnswer = async (
  res: Response,
  baseReferencesIndex: number,
  setCurrent: (e: CurrentSearch) => void
): Promise<SearchResult> => {
  var result: AssistantEntry = {
    role: "assistant",
    content: "",
    citations: [],
    base_count: baseReferencesIndex,
  };
  var followups: Followup[] = [];
  for await (var data of iterateData(res)) {
    switch (data.state) {
      case "loading":
        // display loading phases, once citations are available toss them
        // into the current item.
        result = {
          ...result,
          citations: data?.citations || result?.citations || [],
        };
        setCurrent({ phase: data.phase, ...result });
        break;

      case "streaming":
        // incrementally build up the response
        result = {
          role: "assistant",
          content: (result?.content || "") + data.content,
          citations: result?.citations || [],
          base_count: result?.base_count || baseReferencesIndex,
        };
        setCurrent({ phase: "streaming", ...result });
        break;

      case "followups":
         // add any potential followup questions
         followups = data.followups.map((value) => value as Followup);
         break;
      case "done":
        break;
      case "error":
        throw data.error;
    }
  }
  return { result, followups };
};

const fetchLLM = async (
  sessionId: string,
  query: string,
  mode: string,
  history: HistoryEntry[]
): Promise<Response> =>
  fetch(API_URL + "/chat", {
    method: "POST",
    cache: "no-cache",
    keepalive: true,
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },

    body: JSON.stringify({ sessionId, query, mode, history }),
  });

export const queryLLM = async (
  query: string,
  mode: string,
  history: HistoryEntry[],
  baseReferencesIndex: number,
  setCurrent: (e?: CurrentSearch) => void,
  sessionId: string
): Promise<SearchResult> => {
  // do SSE on a POST request.
  const res = await fetchLLM(sessionId, query, mode, history);

  if (!res.ok) {
    return { result: { role: "error", content: "POST Error: " + res.status } };
  }

  try {
    return await extractAnswer(res, baseReferencesIndex, setCurrent);
  } catch (e) {
    return {
      result: { role: "error", content: e ? e.toString() : "unknown error" },
    };
  }
};

const cleanStampyContent = (contents: string) => contents.replace(
    /<a(.*?)href="\/\?state=([a-zA-Z0-9]+.*?)"(.*?)<\/a>/g,
    (_, pre, linkParts, post) => `<a${pre}href="${STAMPY_URL}/?state=${linkParts}"${post}</a>`
);

export const getStampyContent = async (
  questionId: string
): Promise<SearchResult> => {
  const res = await fetch(`${STAMPY_CONTENT_URL}/${questionId}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
  });

  if (!res.ok) {
    return { result: { role: "error", content: "POST Error: " + res.status } };
  }

  const data = (await res.json()).data;

  let result = {
    role: "stampy",
    content: cleanStampyContent(data.text),
    url: `${STAMPY_URL}/?state=${data.pageid}`,
  } as StampyMessage;

  // re-enable the searchbox, with the question that was just answered
  // removed from the list of possible followups.

  // create an array of new followup questions from the data
  const f_new = data.relatedQuestions.map((f: any) => ({
    pageid: f.pageid!,
    text: f.title!,
    score: 0,
  }));

  const fpids = new Set(f_new.map((f: Followup) => f.pageid));
  const followups = (f_old: Followup[]): Followup[] => {
    const f_old_filtered = f_old.filter(
      (f) => f.pageid !== data.pageid && !fpids.has(f.pageid)
    );
    return [...f_new, ...f_old_filtered].slice(0, MAX_FOLLOWUPS);
  };

  return { followups, result };
};

export const runSearch = async (
  query: string,
  query_source: "search" | "followups",
  mode: string,
  baseReferencesIndex: number,
  entries: Entry[],
  setCurrent: (c: CurrentSearch) => void,
  sessionId: string
): SearchResult => {
  if (query_source === "search") {
    const history = entries
      .filter((entry) => entry.role !== "error")
      .map((entry) => ({
        role: entry.role,
        content: entry.content.trim(),
      }));

    return await queryLLM(
      query,
      mode,
      history,
      baseReferencesIndex,
      setCurrent,
      sessionId
    );
  } else {
    // ----------------- HUMAN AUTHORED CONTENT RETRIEVAL ------------------
    const [questionId] = query.split("\n", 2);
    if (questionId) {
      return await getStampyContent(questionId);
    }
    const result = {
      role: "error",
      content: "Could not extract Stampy id from " + query,
    };
    return { result } as SearchResult;
  }
};
