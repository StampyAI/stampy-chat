import {useState, useEffect} from 'react'
import {queryLLM, getStampyContent, runSearch} from '../hooks/useSearch'

import type {
  CurrentSearch,
  Citation,
  Entry,
  AssistantEntry as AssistantEntryType,
  LLMSettings,
  Followup,
} from '../types'
import {SearchBox} from '../components/searchbox'
import {AssistantEntry} from '../components/assistant'
import {Entry as EntryTag} from '../components/entry'

const MAX_FOLLOWUPS = 4

type State =
  | {
      state: 'idle'
    }
  | {
      state: 'loading'
      phase: 'semantic' | 'prompt' | 'llm'
      citations: Citation[]
    }
  | {
      state: 'streaming'
      response: AssistantEntryType
    }

// smooth-scroll to the bottom of the window if we're already less than 30% a screen away
// note: finicky interaction with "smooth" - maybe fix later.
function scroll30() {
  if (document.documentElement.scrollHeight - window.scrollY > window.innerHeight * 1.3) return
  window.scrollTo({top: document.body.scrollHeight, behavior: 'smooth'})
}

type ChatParams = {
  sessionId: string
  settings: LLMSettings
  onQuery?: (q: string) => any
  onNewEntry?: (history: Entry[]) => any
}

const Chat = ({sessionId, settings, onQuery, onNewEntry}: ChatParams) => {
  const [entries, setEntries] = useState<Entry[]>([])
  const [current, setCurrent] = useState<CurrentSearch>()
  const [citations, setCitations] = useState<Citation[]>([])

  const updateCurrent = (current: CurrentSearch) => {
    setCurrent(current)
    if (current?.phase === 'streaming') {
      scroll30()
    }
  }

  const updateCitations = (allCitations: Citation[], current?: CurrentSearch) => {
    if (!current) return

    const entryCitations = Array.from(current.citationsMap.values())
    if (!entryCitations.some((c) => !c.index)) {
      // All of the entries citations have indexes, so there weren't any changes since the last check
      return
    }

    // Get a mapping of all known citations, so as to reuse them if they appear again
    const citationsMapping = Object.fromEntries(allCitations.map((c) => [c.title + c.url, c.index]))

    entryCitations.forEach((c) => {
      const hash = c.title + c.url
      const index = citationsMapping[hash]
      if (!index) {
        c.index = allCitations.length + 1
        allCitations.push(c)
      } else {
        c.index = index
      }
    })
    setCitations(allCitations)
    setCurrent(current)
  }

  const addEntry = (entry: Entry) => {
    setEntries((prev) => {
      const entries = [...prev, entry]
      if (onNewEntry) {
        onNewEntry(entries)
      }
      return entries
    })
  }

  const search = async (
    query: string,
    query_source: 'search' | 'followups',
    disable: () => void,
    enable: (f_set: Followup[] | ((fs: Followup[]) => Followup[])) => void
  ) => {
    // clear the query box, append to entries
    const userEntry: Entry = {
      role: 'user',
      content: query_source === 'search' ? query : query.split('\n', 2)[1]!,
    }
    addEntry(userEntry)
    disable()

    const {result, followups} = await runSearch(
      query,
      query_source,
      settings,
      entries,
      updateCurrent,
      sessionId
    )
    setCurrent(undefined)

    addEntry(result)
    enable(followups || [])
    scroll30()
  }

  var last_entry = <></>
  switch (current?.phase) {
    case 'semantic':
      last_entry = <p>Loading: Performing semantic search...</p>
      break
    case 'prompt':
      last_entry = <p>Loading: Creating prompt...</p>
      break
    case 'llm':
      last_entry = <p>Loading: Waiting for LLM...</p>
      break
    case 'streaming':
      updateCitations(citations, current)
      last_entry = <AssistantEntry entry={current} />
      break
    case 'followups':
      last_entry = (
        <>
          <AssistantEntry entry={current} />
          <p>Checking for followups...</p>
        </>
      )
      break
    default:
      last_entry = <button onClick={() => setEntries([])}>Clear history</button>
      break
  }

  return (
    <ul className="flex-auto">
      {entries.map((entry, i) => (
        <EntryTag entry={entry} key={i} />
      ))}
      <SearchBox search={search} onQuery={onQuery} />

      {last_entry}
    </ul>
  )
}

export default Chat
