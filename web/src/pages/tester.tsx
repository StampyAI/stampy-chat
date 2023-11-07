import type { NextPage } from "next";
import { useRouter } from "next/router";
import { useState, useEffect, useCallback } from "react";
import Page from "../components/page";

import useCitations from "../hooks/useCitations";
import { queryLLM, getStampyContent } from "../hooks/useSearch";
import useSettings from "../hooks/useSettings";
import { initialQuestions } from "../settings";
import type {
  CurrentSearch,
  SearchResult,
  Mode,
  Entry,
  LLMSettings,
  AssistantEntry,
} from "../types";
import { ChatResponse } from "../components/chat";
import { Controls } from "../components/controls";
import { ChatSettings, ChatPrompts } from "../components/settings";

type QuestionState = {
  question: string;
  selected: boolean;
  index: number;
  sessionId?: string;
  query?: Promise<SearchResult>;
};
const ChatResult = ({ question }: { question: QuestionState }) => {
  const { citations, setEntryCitations } = useCitations();
  const current = setEntryCitations(question as unknown as AssistantEntry);

  // A nasty hack to ignore any stampy followup questions
  if (current && current.phase == "followups") {
    current.phase = "streaming";
  }

  return (
    <details className="chat-result gap-4 border-2 outline-black" open={true}>
      <summary>{question.question}</summary>
      <ChatResponse current={current} />
    </details>
  );
};

const Tester: NextPage = () => {
  const [controller, setController] = useState(new AbortController());
  const [questions, updateQuestions] = useState<QuestionState[]>(
    initialQuestions.map((q, i) => ({ question: q, selected: true, index: i }))
  );

  const { settings, changeSettings, setMode, settingsLoaded } = useSettings();

  /** Run a search for the given `question` and insert the query promise into it
   */
  const search = useCallback(
    (
      { question, sessionId, query, selected, index }: QuestionState,
      controller: AbortController
    ): QuestionState => ({
      question,
      sessionId,
      selected,
      index,
      query: queryLLM(
        settings,
        [{ role: "user", content: question }],
        updater(index),
        sessionId,
        controller
      ),
    }),
    [settings]
  );

  useEffect(() => {
    // Only run the initial search once the settings have been loaded from the URL and localstorage
    if (!settingsLoaded) return;

    updateQuestions((questions) =>
      questions
        .map((q) => ({ ...q, sessionId: q.sessionId || crypto.randomUUID() }))
        .map((q) => (q.selected && !q.query ? search(q, controller) : q))
    );
  }, [settingsLoaded, controller, search]);

  /** Return a function that will update the `index`-th question with the current results of its search
   */
  const updater = (index: number) => (entry: CurrentSearch) =>
    updateQuestions((questions) => {
      const question = questions[index];
      if (!question) return questions;

      questions[index] = { ...question, ...entry };
      return [...questions];
    });

  const toggleQuestion = (i: number) => {
    const question = questions[i];
    if (question === undefined) return;

    question.selected = !question.selected;

    // If the question is to be displayed, but hasn't had a search run, run it now
    if (question.selected && question.query === undefined) {
      questions[i] = search(question, controller);
    }
    updateQuestions([...questions]);
  };

  const selectedQuestions = questions.filter(({ selected }) => selected);
  return (
    <Page page="tester" widescreen={true}>
      <Controls mode={settings.mode || "default"} setMode={setMode} />
      <div className="flex">
        <div>
          <ChatPrompts
            settings={settings}
            query="<this is where the query will go>"
            history={[]}
            changeSettings={changeSettings}
          />
          <div className="chat-settings mx-5 w-[400px] flex-none gap-4 border-2 outline-black">
            {questions.map(({ question, selected }, i) => (
              <div key={i} onClick={() => toggleQuestion(i)}>
                <input
                  type="checkbox"
                  defaultChecked={selected}
                  name={i.toString()}
                  className="m-2"
                />
                <label htmlFor="i">{question}</label>
              </div>
            ))}
            <button
              onClick={() => {
                controller.abort();
                const newController = new AbortController();
                setController(newController);
                updateQuestions(
                  questions.map((q) =>
                    q.selected ? search(q, newController) : q
                  )
                );
              }}
            >
              Rerun search
            </button>
          </div>
        </div>

        <div className="chat-results flex-auto">
          {selectedQuestions.length == 0 ? (
            <div>Please select some questions to test</div>
          ) : (
            selectedQuestions.map((question) => (
              <ChatResult question={question} key={question.index} />
            ))
          )}
        </div>

        <ChatSettings settings={settings} changeSettings={changeSettings} />
      </div>
    </Page>
  );
};

export default Tester;
