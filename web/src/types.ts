export type Citation = {
  title: string;
  authors: string[];
  date: string;
  url: string;
  source: string;
  index: number;
  text: string;
  reference: string;
  id?: string;
};

export type Followup = {
  text: string;
  pageid: string;
  score: number;
};

export type Entry = UserEntry | AssistantEntry | ErrorMessage | StampyMessage;

export type UserEntry = {
  role: "user";
  content: string;
  deleted?: boolean;
};

export type AssistantEntry = {
  role: "assistant";
  content: string;
  citations?: Citation[];
  citationsMap?: Map<string, Citation>;
  deleted?: boolean;
  promptedHistory?: Array<{ role: string; content: string }>;
  timings?: Array<{ time: number; name: string }>;
  hydeResult?: string;
  settings?: LLMSettings;
};

export type ErrorMessage = {
  role: "error";
  content: string;
  deleted?: boolean;
};

export type StampyMessage = {
  role: "stampy";
  content: string;
  url: string;
  deleted?: boolean;
};

export type SearchResult = {
  followups?: Followup[] | ((f: Followup[]) => Followup[]);
  result: Entry;
};
export type CurrentSearch =
  | (AssistantEntry & { phase?: string; thinkingCount?: number })
  | undefined;

export type Mode = "rookie" | "concise" | "default" | "discord";

export type LLMSettings = {
  prompts?: {
    [key: string]: any;
  };
  mode?: Mode;
  completions?: string;
  encoder?: string;
  topKBlocks?: number;
  maxNumTokens?: number;
  tokensBuffer?: number;
  maxHistory?: number;
  historyFraction?: number;
  contextFraction?: number;
  enable_hyde?: boolean;
  thinking_budget?: number;
  [key: string]: any;
};

export type Parseable = string | number | undefined;

export type Distance = "core" | "wider";
export type SearchFilters = {
  miri_confidence?: number;
  miri_distance?: Distance[];
  needs_tech?: boolean | null;
};
