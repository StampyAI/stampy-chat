export type Citation = {
  title: string
  authors: string[]
  date: string
  url: string
  index: number
}

export type Followup = {
  text: string
  pageid: string
  score: number
}

export type Entry = UserEntry | AssistantEntry | ErrorMessage | StampyMessage

export type UserEntry = {
  role: 'user'
  content: string
}

export type AssistantEntry = {
  role: 'assistant'
  content: string
  citations: Citation[]
  citationsMap: Map<string, Citation>
}

export type ErrorMessage = {
  role: 'error'
  content: string
}

export type StampyMessage = {
  role: 'stampy'
  content: string
  url: string
}

export type SearchResult = {
  followups?: Followup[] | ((f: Followup[]) => Followup[])
  result: Entry
}
export type CurrentSearch = (AssistantEntry & {phase?: string}) | undefined

export type Mode = 'rookie' | 'concise' | 'default'

export type LLMSettings = {
  prompts?: {
    [key: string]: any
  }
  mode?: Mode
  completions?: string
  encoder?: string
  topKBlocks?: number
  numTokens?: number
  tokensBuffer?: number
  maxHistory?: number
  historyFraction?: number
  contextFraction?: number
  [key: string]: any
}
