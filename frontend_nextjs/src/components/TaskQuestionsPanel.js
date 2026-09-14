"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Loader2, MessageCircleQuestion } from "lucide-react";
import { tasksAPI } from "@/lib/api";

/** Public Q&A on an open task — anyone can ask, only the poster can answer. */
export default function TaskQuestionsPanel({ task, isPoster }) {
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [newQuestion, setNewQuestion] = useState("");
  const [answerDrafts, setAnswerDrafts] = useState({});
  const [busyId, setBusyId] = useState(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const data = await tasksAPI.listQuestions(task.id);
      setQuestions(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [task.id]);

  useEffect(() => { load(); }, [load]);

  const submitQuestion = async () => {
    const text = newQuestion.trim();
    if (text.length < 3) { setError("Enter a question first"); return; }
    setBusyId("ask");
    setError(null);
    try {
      await tasksAPI.askQuestion(task.id, text);
      setNewQuestion("");
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  };

  const submitAnswer = async (questionId) => {
    const text = (answerDrafts[questionId] || "").trim();
    if (!text) return;
    setBusyId(questionId);
    setError(null);
    try {
      await tasksAPI.answerQuestion(task.id, questionId, text);
      setAnswerDrafts((prev) => ({ ...prev, [questionId]: "" }));
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  };

  if (loading) {
    return <section className="qa"><Loader2 className="spin-icon" size={18} /> Loading questions…</section>;
  }

  return (
    <section className="qa">
      <h3><MessageCircleQuestion size={16} /> Questions {questions.length > 0 && <span className="count">{questions.length}</span>}</h3>

      {questions.length === 0 ? (
        <p className="muted">No questions yet.</p>
      ) : (
        <ul className="qa-list">
          {questions.map((q) => (
            <li key={q.id} className="qa-item">
              <p className="q-text"><strong>{q.asker_display_name || "A tasker"} asked:</strong> {q.question}</p>
              {q.answer ? (
                <p className="a-text"><strong>Poster:</strong> {q.answer}</p>
              ) : isPoster ? (
                <div className="answer-form">
                  <input
                    type="text"
                    placeholder="Write an answer…"
                    value={answerDrafts[q.id] || ""}
                    onChange={(e) => setAnswerDrafts((prev) => ({ ...prev, [q.id]: e.target.value }))}
                    maxLength={2000}
                  />
                  <button
                    type="button"
                    className="btn-premium btn-teal"
                    onClick={() => submitAnswer(q.id)}
                    disabled={busyId !== null}
                  >
                    {busyId === q.id ? "Sending…" : "Answer"}
                  </button>
                </div>
              ) : (
                <p className="muted small">Waiting for the poster to answer.</p>
              )}
            </li>
          ))}
        </ul>
      )}

      {!isPoster && (
        <div className="ask-form">
          <textarea
            rows={2}
            maxLength={1000}
            placeholder="Ask the poster a question about this task…"
            value={newQuestion}
            onChange={(e) => setNewQuestion(e.target.value)}
          />
          <button type="button" className="btn-premium btn-saffron" onClick={submitQuestion} disabled={busyId !== null}>
            {busyId === "ask" ? "Sending…" : "Ask"}
          </button>
        </div>
      )}

      {error && <p className="err">{error}</p>}

      <style jsx>{`
        .qa { display: flex; flex-direction: column; gap: 12px; }
        h3 { font-size: 0.95rem; display: flex; align-items: center; gap: 8px; }
        .count { font-size: 0.72rem; padding: 2px 8px; border-radius: 999px; border: 1px solid var(--border-teal); color: var(--color-teal); }
        .qa-list { list-style: none; display: flex; flex-direction: column; gap: 10px; padding: 0; margin: 0; }
        .qa-item { padding: 12px 14px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.08); background: rgba(0,0,0,0.15); display: flex; flex-direction: column; gap: 6px; }
        .q-text, .a-text { font-size: 0.86rem; line-height: 1.5; color: var(--color-text-main); margin: 0; overflow-wrap: anywhere; }
        .a-text { color: var(--color-text-muted); }
        .answer-form { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 4px; }
        .answer-form input { flex: 1 1 200px; padding: 8px 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); background: rgba(0,0,0,0.2); color: var(--color-text-main); font: inherit; }
        .ask-form { display: flex; flex-direction: column; gap: 8px; max-width: 460px; }
        .ask-form textarea { padding: 8px 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); background: rgba(0,0,0,0.2); color: var(--color-text-main); font: inherit; resize: vertical; }
        .muted { color: var(--color-text-muted); font-size: 0.88rem; }
        .small { font-size: 0.78rem; }
        .err { color: #fca5a5; font-size: 0.85rem; }
      `}</style>
    </section>
  );
}
