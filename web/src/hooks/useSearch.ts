import { API_URL, STAMPY_URL, STAMPY_CONTENT_URL } from "../settings";
import type {
  AssistantEntry,
  ContentBlock,
  StampyMessage,
  Followup,
  Citation,
  CurrentSearch,
  SearchResult,
  LLMSettings,
} from "../types";
import { formatCitations, findCitations } from "../components/citations";

const MAX_FOLLOWUPS = 4;
const DATA_HEADER = "data: ";
const EVENT_END_HEADER = "event: close";

export type EntryRole = "error" | "stampy" | "assistant" | "user" | "deleted";
export type HistoryEntry = {
  role: EntryRole;
  content: string | ContentBlock[];
};

const ignoreAbort = (error: Error) => {
  if (error.name !== "AbortError") {
    throw error;
  }
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

const makeEntry = () =>
  ({
    role: "assistant",
    blocks: [],
    content: "",
    citations: [],
    citationsMap: new Map(),
    timings: [],
  } as AssistantEntry);

/** Extract citations from tool result ui_output (search results). */
const extractCitationsFromBlocks = (blocks: ContentBlock[]): Citation[] => {
  const citations: Citation[] = [];
  for (const block of blocks) {
    if (block.type !== "tool_result") continue;
    if (!Array.isArray(block.ui_output)) continue;
    for (const item of block.ui_output) {
      if (item.title && item.url) {
        citations.push(item as Citation);
      }
    }
  }
  return citations;
};

export const extractAnswer = async (
  res: Response,
  setCurrent: (e: CurrentSearch) => void,
  settings?: LLMSettings,
  priorCitations?: Citation[],
): Promise<SearchResult> => {
  var result: AssistantEntry = makeEntry();
  var followups: Followup[] = [];
  const startTime = Date.now();
  const prior = priorCitations || [];

  const addTiming = (name: string) => {
    if (!result.timings) result.timings = [];
    result.timings.push({ time: Date.now() - startTime, name });
  };

  /** Append to or create the last block of a given type. */
  const appendToBlock = (type: "thinking" | "text", key: "thinking" | "text", delta: string) => {
    const last = result.blocks[result.blocks.length - 1];
    if (last && last.type === type) {
      (last as any)[key] += delta;
    } else {
      result.blocks = [...result.blocks, { type, [key]: delta } as ContentBlock];
    }
  };

  if (settings) {
    result.settings = settings;
  }
  for await (var data of iterateData(res)) {
    switch (data.state) {
      case "thinking":
        addTiming("thinking");
        appendToBlock("thinking", "thinking", data.content || "");
        result = { ...result, blocks: [...result.blocks] };
        setCurrent({ phase: "thinking", ...result });
        break;

      case "streaming": {
        addTiming("content");
        appendToBlock("text", "text", data.content || "");
        const content = formatCitations(result.content + (data.content || ""));
        const citations = [...prior, ...extractCitationsFromBlocks(result.blocks)];
        result = {
          ...result,
          blocks: [...result.blocks],
          content,
          citations,
          citationsMap: findCitations(content, citations),
        };
        setCurrent({ phase: "streaming", ...result });
        break;
      }

      case "turn":
        addTiming("turn");
        if (data.role === "assistant") {
          if (Array.isArray(data.content)) {
            for (const block of data.content) {
              if (block.type === "tool_use") {
                result.blocks.push(block);
              }
            }
          }
        } else if (data.role === "tool") {
          // Tool result turn
          result.blocks.push({
            type: "tool_result",
            tool: data.tool,
            tool_use_id: data.tool_use_id,
            model_output: data.model_output || "",
            ui_output: data.ui_output,
          });
          // Update citations from tool results
          const citations = [...prior, ...extractCitationsFromBlocks(result.blocks)];
          result = { ...result, citations };
        }
        setCurrent({ phase: "turn", ...result });
        break;

      case "followups":
        addTiming("followups");
        followups = data.followups.map((value: any) => value as Followup);
        break;

      case "done":
        addTiming("done");
        break;

      case "error":
        throw data.error;

      case "loading":
        setCurrent({ phase: data.phase, ...result });
        break;
    }
  }
  return { result, followups };
};

const fetchLLM = async (
  sessionId: string | undefined,
  settings: LLMSettings,
  history: HistoryEntry[],
  controller: AbortController
): Promise<Response | void> =>
  fetch(API_URL + "/chat", {
    signal: controller.signal,
    method: "POST",
    cache: "no-cache",
    //keepalive: true, // claude says not to do this, it caused an error. but, TODO: why was it here? will removal cause problems? delete this comment if there have been no site-breaking issues caused by commenting this line by jan 2026.
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },

    body: JSON.stringify({ sessionId, history, settings }),
  }).catch(ignoreAbort);

export const queryLLM = async (
  settings: LLMSettings,
  history: HistoryEntry[],
  setCurrent: (e?: CurrentSearch) => void,
  sessionId: string | undefined,
  controller: AbortController,
  priorCitations?: Citation[],
): Promise<SearchResult> => {
  setCurrent({ ...makeEntry(), phase: "started" });
  // do SSE on a POST request.
  const res = await fetchLLM(sessionId, settings, history, controller);

  if (!res) {
    return { result: { role: "error", content: "No response from server" } };
  } else if (!res.ok) {
    return { result: { role: "error", content: "POST Error: " + res.status } };
  }

  try {
    return await extractAnswer(res, setCurrent, settings, priorCitations);
  } catch (e) {
    if ((e as Error)?.name === "AbortError") {
      return { result: { role: "error", content: "aborted" } };
    }
    return {
      result: { role: "error", content: e ? e.toString() : "unknown error" },
    };
  }
};

const cleanStampyContent = (contents: string) =>
  contents.replace(
    /<a(.*?)href="\/\?state=([a-zA-Z0-9]+.*?)"(.*?)<\/a>/g,
    (_, pre, linkParts, post) =>
      `<a${pre}href="${STAMPY_URL}/?state=${linkParts}"${post}</a>`
  );

export const getStampyContent = async (
  questionId: string,
  controller: AbortController
): Promise<SearchResult> => {
  const res = await fetch(`${STAMPY_CONTENT_URL}/${questionId}`, {
    method: "GET",
    signal: controller.signal,
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
  }).catch(ignoreAbort);

  if (!res) {
    return { result: { role: "error", content: "No response from server" } };
  } else if (!res.ok) {
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
