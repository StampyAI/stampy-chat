import {type NextPage} from 'next'
import {useState, useEffect} from 'react'
import Link from 'next/link'

import {queryLLM, getStampyContent, runSearch} from '../hooks/useSearch'
import type {Mode} from '../types'
import Page from '../components/page'
import Chat from '../components/chat'
import {Controls} from '../components/controls'

const MAX_FOLLOWUPS = 4

const Home: NextPage = () => {
  const [sessionId, setSessionId] = useState('')
  const [mode, setMode] = useState<[Mode, boolean]>(['default', false])

  // store mode in localstorage
  useEffect(() => {
    if (mode[1]) localStorage.setItem('chat_mode', mode[0])
  }, [mode])

  // initial load
  useEffect(() => {
    const mode = (localStorage.getItem('chat_mode') as Mode) || 'default'
    setMode([mode, true])
    setSessionId(crypto.randomUUID())
  }, [])

  return (
    <Page page="index">
      <Controls mode={mode} setMode={setMode} />

      <h2 className="bg-red-100 text-red-800">
        <b>WARNING</b>: This is a very <b>early prototype</b>.{' '}
        <Link href="http://bit.ly/stampy-chat-issues" target="_blank">
          Feedback
        </Link>{' '}
        welcomed.
      </h2>

      <Chat sessionId={sessionId} settings={{mode: mode[0]}} />
    </Page>
  )
}

export default Home
