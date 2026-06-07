"use client";

import React, { useState, useEffect, useRef } from "react";
import { Send, Languages, Wifi, WifiOff, Sparkles } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { chatAPI } from "@/lib/api";

const LANGUAGES = [
  { code: "hi", label: "हिंदी (Hindi)" },
  { code: "en", label: "English" },
  { code: "ta", label: "தமிழ் (Tamil)" },
  { code: "te", label: "తెలుగు (Telugu)" },
  { code: "mr", label: "मराठी (Marathi)" },
  { code: "bn", label: "বাংলা (Bengali)" },
];

export default function TranslatedChat() {
  const { token, isLoggedIn } = useAuth();
  const [messages, setMessages] = useState([
    {
      id: Date.now(),
      role: "assistant",
      text: "Namaste! I'm your VayuTask AI assistant. I can help you post a task, find taskers, check payment status, or answer any questions about your service. How can I help you today?",
      translated: null,
      lang: "en",
      intent: "greeting",
    },
  ]);
  const [input, setInput] = useState("");
  const [targetLang, setTargetLang] = useState("hi");
  const [wsStatus, setWsStatus] = useState("disconnected"); // 'disconnected' | 'connecting' | 'connected' | 'error'
  const [translating, setTranslating] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [apiError, setApiError] = useState(null);

  const wsRef = useRef(null);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  // ── Connect WebSocket with real JWT ───────────────────────────────────────
  useEffect(() => {
    if (!isLoggedIn || !token) return;

    const connect = () => {
      setWsStatus("connecting");
      const url = chatAPI.buildWsUrl(token);
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => setWsStatus("connected");

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "pong") return;
          if (data.type === "error") {
            setApiError(data.detail || "WebSocket error");
            return;
          }
          if (data.type === "reply") {
            if (data.session_id) setSessionId(data.session_id);
            const newMsg = {
              id: Date.now() + Math.random(),
              role: "assistant",
              text: data.reply || data.message || "",
              translated: null,
              lang: "en",
              intent: data.intent,
            };
            setMessages((prev) => [...prev, newMsg]);
          }
        } catch {}
      };

      ws.onclose = (e) => {
        setWsStatus("disconnected");
        // Auto-reconnect after 3s unless deliberately closed
        if (e.code !== 1000 && e.code !== 1008) {
          setTimeout(connect, 3000);
        }
      };

      ws.onerror = () => setWsStatus("error");
    };

    connect();
    return () => {
      if (wsRef.current) wsRef.current.close(1000, "component unmount");
    };
  }, [isLoggedIn, token]);

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ── Send message over WebSocket or REST fallback ──────────────────────────
  const sendMessage = async () => {
    const text = input.trim();
    if (!text) return;

    setInput("");
    setApiError(null);

    const userMsg = {
      id: Date.now(),
      role: "user",
      text,
      translated: null,
      lang: "en",
    };
    setMessages((prev) => [...prev, userMsg]);

    // Translate user message to target language for display
    let translatedUserText = null;
    if (targetLang !== "en") {
      setTranslating(true);
      try {
        const tRes = await chatAPI.translate(text, targetLang);
        translatedUserText = tRes.translated_text;
        setMessages((prev) =>
          prev.map((m) => (m.id === userMsg.id ? { ...m, translated: translatedUserText } : m))
        );
      } catch {}
      setTranslating(false);
    }

    // Send over WebSocket if connected
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: "message",
          text,
          language: "en",
          tone: "friendly",
          session_id: sessionId,
        })
      );
    } else {
      // Fallback to REST /api/chat/agent
      try {
        const res = await chatAPI.agent(text, sessionId);
        if (res.session_id) setSessionId(res.session_id);
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now() + 1,
            role: "assistant",
            text: res.reply,
            translated: null,
            lang: "en",
            intent: res.intent,
          },
        ]);
      } catch (err) {
        setApiError(err.message);
      }
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  };

  // Translate a message on demand
  const translateMessage = async (msgId, text) => {
    setTranslating(true);
    try {
      const res = await chatAPI.translate(text, targetLang);
      setMessages((prev) =>
        prev.map((m) => (m.id === msgId ? { ...m, translated: res.translated_text } : m))
      );
    } catch (err) {
      setApiError(err.message);
    }
    setTranslating(false);
  };

  const statusColors = {
    connected: "#10b981",
    connecting: "#f59e0b",
    disconnected: "#64748b",
    error: "#ef4444",
  };
  const statusLabels = {
    connected: "WS Connected",
    connecting: "Connecting...",
    disconnected: isLoggedIn ? "WS Disconnected — using REST fallback" : "Sign in to connect",
    error: "WS Error — using REST fallback",
  };

  return (
    <div className="chat-wrapper">
      {/* Header */}
      <div className="chat-header-bar glass-card">
        <div className="chat-header-left">
          <Sparkles style={{ color: "var(--color-teal)", width: 22, height: 22 }} />
          <div>
            <h2 className="chat-title">AI Task Chat <span className="chat-title-badge">Live</span></h2>
            <p className="chat-subtitle">
              Real-time agent via WebSocket · REST fallback · Bhashini Translation
            </p>
          </div>
        </div>

        <div className="chat-header-right">
          {/* Lang selector */}
          <div className="lang-pill">
            <Languages style={{ width: 16, height: 16, color: "var(--color-teal)" }} />
            <select
              value={targetLang}
              onChange={(e) => setTargetLang(e.target.value)}
              className="lang-select"
            >
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>{l.label}</option>
              ))}
            </select>
          </div>

          {/* WS status */}
          <div className="ws-status-pill" style={{ borderColor: statusColors[wsStatus], color: statusColors[wsStatus] }}>
            {wsStatus === "connected" ? (
              <Wifi style={{ width: 14, height: 14 }} />
            ) : (
              <WifiOff style={{ width: 14, height: 14 }} />
            )}
            <span>{statusLabels[wsStatus]}</span>
          </div>
        </div>
      </div>

      {!isLoggedIn && (
        <div className="chat-auth-banner">
          WebSocket chat requires authentication. <a href="/login">Sign in</a> to connect, or messages will use REST fallback.
        </div>
      )}

      {apiError && (
        <div className="api-error-bar">⚠ {apiError}</div>
      )}

      {sessionId && (
        <div className="session-bar">
          Session: <code>{sessionId}</code>
        </div>
      )}

      {/* Messages */}
      <div className="chat-messages-box glass-card">
        <div className="messages-list">
          {messages.map((msg) => (
            <div key={msg.id} className={`msg-row ${msg.role === "user" ? "msg-user-row" : "msg-assistant-row"}`}>
              {/* Avatar */}
              <div className={`msg-avatar ${msg.role === "user" ? "avatar-user" : "avatar-ai"}`}>
                {msg.role === "user" ? "U" : <Sparkles style={{ width: 14, height: 14 }} />}
              </div>

              <div className="msg-content-group">
                {/* Original bubble */}
                <div className={`msg-bubble ${msg.role === "user" ? "bubble-user" : "bubble-ai"}`}>
                  <p className="bubble-text">{msg.text}</p>
                  {msg.intent && (
                    <span className="intent-badge">Intent: {msg.intent}</span>
                  )}
                </div>

                {/* Translated bubble */}
                {msg.translated && (
                  <div className="msg-bubble bubble-translated">
                    <p className="bubble-text">{msg.translated}</p>
                    <span className="translated-label">
                      <Languages style={{ width: 11, height: 11 }} />
                      Translated · {LANGUAGES.find((l) => l.code === targetLang)?.label}
                    </span>
                  </div>
                )}

                {/* Translate button */}
                {!msg.translated && msg.role === "assistant" && (
                  <button
                    onClick={() => translateMessage(msg.id, msg.text)}
                    disabled={translating}
                    className="translate-btn"
                  >
                    <Languages style={{ width: 12, height: 12 }} />
                    Translate to {LANGUAGES.find((l) => l.code === targetLang)?.label}
                  </button>
                )}
              </div>
            </div>
          ))}
          {translating && (
            <div className="translating-indicator">
              <div className="typing-dot"></div><div className="typing-dot"></div><div className="typing-dot"></div>
              <span style={{ fontSize: "0.8rem", color: "var(--color-text-muted)", marginLeft: 8 }}>Translating...</span>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input */}
      <div className="chat-input-row glass-card">
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about tasks, payments, or write in any language..."
          className="chat-textarea"
          rows={2}
        />
        <button
          onClick={sendMessage}
          disabled={!input.trim()}
          className="btn-premium btn-teal send-btn"
        >
          <Send style={{ width: 16, height: 16 }} />
        </button>
      </div>

      <style dangerouslySetInnerHTML={{ __html: `
        .chat-wrapper { display: flex; flex-direction: column; gap: 20px; max-width: 900px; margin: 0 auto; }
        .chat-header-bar { padding: 20px 24px; display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
        .chat-header-left { display: flex; align-items: center; gap: 16px; }
        .chat-title { font-size: 1.4rem; font-weight: 800; display: flex; align-items: center; gap: 10px; }
        .chat-title-badge { font-size: 0.65rem; padding: 3px 8px; border-radius: 20px; background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.3); color: #10b981; font-weight: 700; vertical-align: middle; }
        .chat-subtitle { font-size: 0.8rem; color: var(--color-text-muted); margin-top: 2px; }
        .chat-header-right { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
        .lang-pill { display: flex; align-items: center; gap: 6px; background: rgba(20,184,166,0.05); border: 1px solid var(--border-teal); border-radius: 20px; padding: 6px 12px; }
        .lang-select { background: transparent; border: none; color: var(--color-text-main); font-family: inherit; font-size: 0.85rem; outline: none; cursor: pointer; }
        .ws-status-pill { display: flex; align-items: center; gap: 6px; border-width: 1px; border-style: solid; border-radius: 20px; padding: 6px 12px; font-size: 0.75rem; font-weight: 600; }
        .chat-auth-banner { background: rgba(245,158,11,0.07); border: 1px solid rgba(245,158,11,0.2); border-radius: 10px; padding: 12px 16px; font-size: 0.85rem; color: var(--color-saffron); text-align: center; }
        .chat-auth-banner a { color: var(--color-teal); text-decoration: underline; }
        .api-error-bar { background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.25); border-radius: 10px; padding: 12px 16px; color: #fca5a5; font-size: 0.85rem; }
        .session-bar { font-size: 0.75rem; color: var(--color-text-muted); text-align: center; } .session-bar code { color: var(--color-teal); }
        .chat-messages-box { padding: 24px; min-height: 400px; max-height: 500px; overflow: hidden; }
        .messages-list { display: flex; flex-direction: column; gap: 20px; height: 100%; max-height: 450px; overflow-y: auto; padding-right: 8px; }
        .messages-list::-webkit-scrollbar { width: 4px; }
        .messages-list::-webkit-scrollbar-thumb { background: var(--border-glow); border-radius: 2px; }
        .msg-row { display: flex; gap: 12px; }
        .msg-user-row { flex-direction: row-reverse; }
        .msg-assistant-row { flex-direction: row; }
        .msg-avatar { width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.85rem; font-weight: 700; flex-shrink: 0; }
        .avatar-user { background: rgba(245,158,11,0.1); border: 1px solid var(--border-saffron); color: var(--color-saffron); }
        .avatar-ai { background: rgba(20,184,166,0.1); border: 1px solid var(--border-teal); color: var(--color-teal); }
        .msg-content-group { display: flex; flex-direction: column; gap: 6px; max-width: 75%; }
        .msg-user-row .msg-content-group { align-items: flex-end; }
        .msg-assistant-row .msg-content-group { align-items: flex-start; }
        .msg-bubble { padding: 14px 18px; border-radius: 16px; display: flex; flex-direction: column; gap: 6px; }
        .bubble-user { background: rgba(245,158,11,0.08); border: 1px solid var(--border-saffron); border-top-right-radius: 4px; }
        .bubble-ai { background: rgba(20,184,166,0.05); border: 1px solid var(--border-teal); border-top-left-radius: 4px; }
        .bubble-translated { background: rgba(20,184,166,0.03); border: 1px dashed var(--border-teal); }
        .bubble-text { font-size: 0.92rem; line-height: 1.55; color: var(--color-text-main); }
        .intent-badge { font-size: 0.65rem; padding: 2px 8px; border-radius: 10px; background: rgba(20,184,166,0.1); color: var(--color-teal); font-weight: 600; align-self: flex-start; }
        .translated-label { display: flex; align-items: center; gap: 4px; font-size: 0.7rem; color: var(--color-text-muted); font-style: italic; }
        .translate-btn { display: flex; align-items: center; gap: 5px; padding: 5px 12px; border-radius: 16px; background: rgba(20,184,166,0.05); border: 1px solid var(--border-teal); color: var(--color-teal); font-size: 0.75rem; font-weight: 600; cursor: pointer; font-family: inherit; transition: all 0.2s ease; }
        .translate-btn:hover { background: rgba(20,184,166,0.1); }
        .translating-indicator { display: flex; align-items: center; padding: 10px 14px; }
        .typing-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--color-teal); margin: 0 3px; animation: typingBounce 0.9s infinite; }
        .typing-dot:nth-child(2) { animation-delay: 0.15s; } .typing-dot:nth-child(3) { animation-delay: 0.3s; }
        @keyframes typingBounce { 0%, 60%, 100% { transform: translateY(0); } 30% { transform: translateY(-6px); } }
        .chat-input-row { padding: 16px 20px; display: flex; gap: 12px; align-items: flex-end; }
        .chat-textarea { flex: 1; background: transparent; border: none; resize: none; color: var(--color-text-main); font-family: inherit; font-size: 0.95rem; outline: none; line-height: 1.5; }
        .send-btn { width: 48px; height: 48px; border-radius: 12px; flex-shrink: 0; }
      ` }} />
    </div>
  );
}
