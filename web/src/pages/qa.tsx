import { type NextPage } from "next";
import { useState, useEffect, useCallback } from "react";
import Link from "next/link";

import { API_URL, STAMPY_URL, STAMPY_CONTENT_URL } from "../settings";
import useSettings from "../hooks/useSettings";
import Page from "../components/page";
import Chat from "../components/chat";
import { Controls } from "../components/controls";
import type {
  CurrentSearch,
  Citation,
  Entry,
  AssistantEntry as AssistantEntryType,
  LLMSettings,
  Followup,
  SearchResult,
} from "../types";

const MAX_FOLLOWUPS = 4;

export const saveRatings = async (
  sessionId: string,
  score: number,
  comment: string | null,
  settings: LLMSettings
): Promise<any> =>
  fetch(API_URL + "/ratings", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ sessionId, settings, score, comment }),
  }).then((r) => r.json());

const Rater = ({
  settings,
  sessionId,
  reset,
}: {
  settings: LLMSettings;
  sessionId: string;
  reset: () => void;
}) => {
  const [comment, setComment] = useState<string | null>(null);

  const onRate = async (rate: number) => {
    const res = await saveRatings(sessionId, rate, comment, settings);
    if (!res.error) reset();
  };

  return (
    <div className="rate-container">
      <div>Rate this session (will reset once rated):</div>
      <div>
        <span>Bad</span>
        {[1, 2, 3, 4, 5].map((i) => (
          <button key={i} className="rate-button" onClick={() => onRate(i)}>
            {i}
          </button>
        ))}
        <span>Good</span>
      </div>
      <textarea
        placeholder="Add any comments here"
        onChange={(e) => setComment(e.target.value)}
      ></textarea>
    </div>
  );
};

const QA: NextPage = () => {
  const [sessionId, setSessionId] = useState("");
  const [entries, setEntries] = useState<Entry[]>([]);
  const { settings, setMode, randomize } = useSettings();

  const reset = useCallback(() => {
    randomize();
    setSessionId(crypto.randomUUID());
    setEntries([]);
  }, [randomize]);

  // initial load
  useEffect(() => {
    reset();
  }, [reset]);

  return (
    <Page page="index">
      <Controls mode={settings.mode || "default"} setMode={setMode} />

      <h2 className="bg-red-100 text-red-800">
        <Link href="http://bit.ly/stampy-chat-issues" target="_blank">
          Feedback
        </Link>{" "}
        welcomed.
      </h2>

      <Chat
        key={sessionId}
        sessionId={sessionId}
        settings={settings}
        onNewEntry={(e) => setEntries((entries) => [...entries, ...e])}
      />
      {entries.length > 0 && (
        <Rater settings={settings} sessionId={sessionId} reset={reset} />
      )}
    </Page>
  );
};

export default QA;
