import type {
  Entry as EntryType,
  AssistantEntry as AssistantEntryType,
  ErrorMessage,
  StampyMessage,
  UserEntry,
} from '../types'
import {AssistantEntry} from './assistant'
import {GlossarySpan} from './glossary'
import Image from 'next/image'
import logo from '../logo.svg'
import TextareaAutosize from 'react-textarea-autosize'

export const User = ({entry}: {entry: UserEntry}) => {
  return (
    <li className="mt-1 mb-2 flex">
      <TextareaAutosize
        className="flex-1 resize-none border border-gray-300 px-1"
        value={entry.content}
      />
    </li>
  )
}

export const Error = ({entry}: {entry: ErrorMessage}) => {
  return (
    <li>
      <p className="border border-red-500 bg-red-100 px-1 text-red-800"> {entry.content} </p>
    </li>
  )
}

export const Assistant = ({entry}: {entry: AssistantEntryType}) => {
  return (
    <li>
      <AssistantEntry entry={entry} />
    </li>
  )
}

export const Stampy = ({entry}: {entry: StampyMessage}) => {
  return (
    <li>
      <div
        className="my-7 rounded bg-slate-500 px-4 py-0.5 text-slate-50"
        style={{
          marginLeft: 'auto',
          marginRight: 'auto',
          maxWidth: '99.8%',
        }}
      >
        <div>
          <GlossarySpan content={entry.content} />
        </div>
        <div className="mb-3 flex justify-end">
          <a href={entry.url} target="_blank" className="flex items-center space-x-1">
            <span>aisafety.info</span>
            <Image src={logo} alt="aisafety.info logo" width={19} />
          </a>
        </div>
      </div>
    </li>
  )
}

export const Entry = ({entry}: {entry: EntryType}) => {
  switch (entry.role) {
    case 'user':
      return <User entry={entry} />
    case 'error':
      return <Error entry={entry} />
    case 'assistant':
      return <Assistant entry={entry} />
    case 'stampy':
      return <Stampy entry={entry} />
  }
}
