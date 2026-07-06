"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { Loader2, Send } from "lucide-react";
import { tasksAPI } from "@/lib/api";

export default function TaskThreadChat({ taskId, userId, enabled }) {
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const bottomRef = useRef(null);

  const loadMessages = useCallback(async () => {
    if (!taskId || !enabled) return;
    setLoading(true);
    setError(null);
    try {
      const data = await tasksAPI.listMessages(taskId);
      setMessages(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [taskId, enabled]);

  useEffect(() => {
    loadMessages();
    const interval = setInterval(loadMessages, 8000);
    return () => clearInterval(interval);
  }, [loadMessages]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (e) => {
    e.preventDefault();
    const body = text.trim();
    if (!body || sending) return;
    setSending(true);
    setError(null);
    try {
      const msg = await tasksAPI.postMessage(taskId, body);
      setMessages((prev) => [...prev, msg]);
      setText("");
    } catch (err) {
      setError(err.message);
    } finally {
      setSending(false);
    }
  };

  if (!enabled) {
    return (
      <div className="thread-chat disabled">
        <p>Chat opens after a tasker accepts this job.</p>
      </div>
    );
  }

  return (
    <div className="thread-chat">
      <h3>Task chat</h3>
      <p className="hint">Messages are auto-translated for the other person.</p>

      <div className="messages">
        {loading && messages.length === 0 && (
          <div className="empty"><Loader2 className="spin" size={18} /> Loading...</div>
        )}
        {!loading && messages.length === 0 && (
          <div className="empty">No messages yet — coordinate timing, address, or extras here.</div>
        )}
        {messages.map((msg) => {
          const mine = msg.sender_id === userId;
          return (
            <div key={msg.id} className={`bubble-row ${mine ? "mine" : "theirs"}`}>
              <div className={`bubble ${mine ? "mine" : "theirs"}`}>
                <p>{msg.original_text}</p>
                {msg.translated_text && msg.translated_text !== msg.original_text && (
                  <p className="translated">{msg.translated_text}</p>
                )}
              </div>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>

      {error && <p className="error">{error}</p>}

      <form className="composer" onSubmit={handleSend}>
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Type a message..."
          maxLength={4000}
        />
        <button type="submit" className="btn-premium btn-teal" disabled={sending || !text.trim()}>
          <Send size={16} />
        </button>
      </form>

      <style jsx>{`
        .thread-chat {
          display: flex;
          flex-direction: column;
          gap: 12px;
          padding: 20px;
          border-radius: 16px;
          border: 1px solid rgba(20, 184, 166, 0.2);
          background: rgba(20, 184, 166, 0.04);
        }
        .thread-chat.disabled p { color: var(--color-text-muted); font-size: 0.9rem; }
        h3 { font-size: 1rem; font-weight: 700; }
        .hint { font-size: 0.8rem; color: var(--color-text-muted); margin-top: -6px; }
        .messages {
          max-height: 320px;
          overflow-y: auto;
          display: flex;
          flex-direction: column;
          gap: 10px;
          padding: 8px 4px;
        }
        .empty { color: var(--color-text-muted); font-size: 0.85rem; text-align: center; padding: 24px 12px; }
        .bubble-row { display: flex; }
        .bubble-row.mine { justify-content: flex-end; }
        .bubble {
          max-width: 85%;
          padding: 10px 14px;
          border-radius: 14px;
          font-size: 0.9rem;
          line-height: 1.45;
        }
        .bubble.mine {
          background: rgba(20, 184, 166, 0.2);
          border: 1px solid var(--border-teal);
        }
        .bubble.theirs {
          background: rgba(255, 255, 255, 0.04);
          border: 1px solid rgba(255, 255, 255, 0.08);
        }
        .translated {
          margin-top: 6px;
          font-size: 0.8rem;
          color: var(--color-text-muted);
          font-style: italic;
        }
        .composer { display: flex; gap: 8px; }
        .composer input {
          flex: 1;
          padding: 10px 14px;
          border-radius: 10px;
          border: 1px solid rgba(255, 255, 255, 0.1);
          background: rgba(0, 0, 0, 0.2);
          color: var(--color-text-main);
        }
        .composer button {
          padding: 10px 14px;
          display: flex;
          align-items: center;
        }
        .error { color: #f87171; font-size: 0.82rem; }
        :global(.spin) { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
