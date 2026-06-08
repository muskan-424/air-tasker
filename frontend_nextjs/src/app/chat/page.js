"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";
import {
  Send,
  Languages,
  Wifi,
  WifiOff,
  Sparkles,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Wand2,
} from "lucide-react";
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

const TONES = [
  { value: "friendly", label: "Friendly" },
  { value: "professional", label: "Professional" },
  { value: "concise", label: "Concise" },
];

const QUICK_PROMPTS = [
  { label: "Last 5 orders", text: "mera last 5 order dikhao" },
  { label: "What is this app?", text: "what this app does" },
  { label: "Nearby tech jobs", text: "near high earning tech tasks" },
  { label: "Create AC repair task", text: "create a task for AC repair at home tomorrow" },
];

const REFINE_ACTIONS = [
  { label: "Shorter", instruction: "Make this shorter and clearer." },
  { label: "Professional", instruction: "Rewrite in a professional tone." },
  { label: "Hindi", instruction: "Answer in Hindi." },
  { label: "Steps", instruction: "Explain with numbered steps." },
];

const GREETING = {
  id: "greeting",
  role: "assistant",
  text: "Namaste! I'm your VayuTask AI assistant. Ask about your orders, post a task, find nearby gigs, or get help with payments and verification.",
  translated: null,
  lang: "en",
  intent: "greeting",
};

const SESSION_KEY = "vayutask_chat_session";

function nextId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function mapAssistantPayload(data) {
  return {
    id: nextId(),
    role: "assistant",
    text: data.reply || data.message || "",
    translated: null,
    lang: "en",
    intent: data.intent,
    toolTraces: data.tool_traces || [],
    suggestedActions: data.suggested_actions || [],
    confidence: data.confidence,
    needsVerification: data.needs_verification,
    llmProvider: data.llm_provider,
    followUpRequired: data.follow_up_required,
  };
}

export default function TranslatedChat() {
  const { token, isLoggedIn } = useAuth();
  const [messages, setMessages] = useState([GREETING]);
  const [input, setInput] = useState("");
  const [targetLang, setTargetLang] = useState("hi");
  const [chatLang, setChatLang] = useState("en");
  const [tone, setTone] = useState("friendly");
  const [wsStatus, setWsStatus] = useState("disconnected");
  const [translating, setTranslating] = useState(false);
  const [sending, setSending] = useState(false);
  const [refining, setRefining] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [apiError, setApiError] = useState(null);
  const [showTraces, setShowTraces] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);

  const wsRef = useRef(null);
  const bottomRef = useRef(null);

  const persistSession = useCallback((sid) => {
    if (!sid) return;
    setSessionId(sid);
    try {
      localStorage.setItem(SESSION_KEY, sid);
    } catch (_) {}
  }, []);

  const loadHistory = useCallback(async (sid) => {
    if (!isLoggedIn || !sid) return;
    setHistoryLoading(true);
    setApiError(null);
    try {
      const data = await chatAPI.history(sid);
      if (data.messages?.length) {
        setMessages([
          GREETING,
          ...data.messages.map((m) => ({
            id: nextId(),
            role: m.role,
            text: m.text,
            translated: null,
            lang: chatLang,
            intent: m.intent,
          })),
        ]);
      }
      persistSession(data.session_id || sid);
    } catch (err) {
      setApiError(err.message);
    } finally {
      setHistoryLoading(false);
    }
  }, [isLoggedIn, chatLang, persistSession]);

  useEffect(() => {
    if (!isLoggedIn) return;
    try {
      const stored = localStorage.getItem(SESSION_KEY);
      if (stored) loadHistory(stored);
    } catch (_) {}
  }, [isLoggedIn, loadHistory]);

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
            setSending(false);
            return;
          }
          if (data.type === "reply") {
            if (data.session_id) persistSession(data.session_id);
            setMessages((prev) => [...prev, mapAssistantPayload(data)]);
            setSending(false);
          }
        } catch (_) {
          setSending(false);
        }
      };

      ws.onclose = (e) => {
        setWsStatus("disconnected");
        if (e.code !== 1000 && e.code !== 1008) setTimeout(connect, 3000);
      };

      ws.onerror = () => setWsStatus("error");
    };

    connect();
    return () => {
      if (wsRef.current) wsRef.current.close(1000, "component unmount");
    };
  }, [isLoggedIn, token, persistSession]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  const sendText = async (text) => {
    const trimmed = text.trim();
    if (!trimmed || sending) return;

    setApiError(null);
    setSending(true);

    const userMsg = {
      id: nextId(),
      role: "user",
      text: trimmed,
      translated: null,
      lang: chatLang,
    };
    setMessages((prev) => [...prev, userMsg]);

    if (targetLang !== "en") {
      setTranslating(true);
      try {
        const tRes = await chatAPI.translate(trimmed, targetLang);
        setMessages((prev) =>
          prev.map((m) => (m.id === userMsg.id ? { ...m, translated: tRes.translated_text } : m))
        );
      } catch (_) {}
      setTranslating(false);
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: "message",
          text: trimmed,
          language: chatLang,
          tone,
          session_id: sessionId,
        })
      );
      return;
    }

    try {
      const res = await chatAPI.agent(trimmed, sessionId, chatLang, tone);
      if (res.session_id) persistSession(res.session_id);
      setMessages((prev) => [...prev, mapAssistantPayload(res)]);
    } catch (err) {
      setApiError(err.message);
    } finally {
      setSending(false);
    }
  };

  const sendMessage = () => {
    const text = input;
    setInput("");
    sendText(text);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const translateMessage = async (msgId, text) => {
    setTranslating(true);
    setApiError(null);
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

  const refineLastAssistant = async (instruction) => {
    const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant" && m.id !== "greeting");
    if (!lastAssistant) return;

    setRefining(true);
    setApiError(null);
    try {
      const res = await chatAPI.refine(lastAssistant.text, instruction, chatLang);
      setMessages((prev) => [
        ...prev,
        {
          id: nextId(),
          role: "assistant",
          text: res.refined_answer,
          translated: null,
          lang: chatLang,
          intent: "refined",
        },
      ]);
    } catch (err) {
      setApiError(err.message);
    } finally {
      setRefining(false);
    }
  };

  const startNewSession = () => {
    try {
      localStorage.removeItem(SESSION_KEY);
    } catch (_) {}
    setSessionId(null);
    setMessages([GREETING]);
    setApiError(null);
  };

  const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant" && m.id !== "greeting");

  const statusColors = {
    connected: "#10b981",
    connecting: "#f59e0b",
    disconnected: "#64748b",
    error: "#ef4444",
  };
  const statusLabels = {
    connected: "WS Connected",
    connecting: "Connecting...",
    disconnected: isLoggedIn ? "REST fallback ready" : "Sign in to connect",
    error: "WS Error — REST fallback",
  };

  return (
    <div className="chat-wrapper">
      <div className="chat-header-bar glass-card">
        <div className="chat-header-left">
          <Sparkles style={{ color: "var(--color-teal)", width: 22, height: 22 }} />
          <div>
            <h2 className="chat-title">
              VayuTask AI Chat <span className="chat-title-badge">Agent</span>
            </h2>
            <p className="chat-subtitle">
              Orders · task help · nearby jobs · create tasks · refine answers
            </p>
          </div>
        </div>

        <div className="chat-header-right">
          <div className="lang-pill">
            <span className="pill-label">Reply</span>
            <select value={chatLang} onChange={(e) => setChatLang(e.target.value)} className="lang-select">
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>{l.label}</option>
              ))}
            </select>
          </div>
          <div className="lang-pill">
            <span className="pill-label">Tone</span>
            <select value={tone} onChange={(e) => setTone(e.target.value)} className="lang-select">
              {TONES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>
          <div className="lang-pill">
            <Languages style={{ width: 16, height: 16, color: "var(--color-teal)" }} />
            <select value={targetLang} onChange={(e) => setTargetLang(e.target.value)} className="lang-select">
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>{l.label}</option>
              ))}
            </select>
          </div>
          <div
            className="ws-status-pill"
            style={{ borderColor: statusColors[wsStatus], color: statusColors[wsStatus] }}
          >
            {wsStatus === "connected" ? <Wifi size={14} /> : <WifiOff size={14} />}
            <span>{statusLabels[wsStatus]}</span>
          </div>
        </div>
      </div>

      {!isLoggedIn && (
        <div className="chat-auth-banner">
          Sign in for persistent chat history. <Link href="/login">Login</Link>
        </div>
      )}

      {apiError && <div className="api-error-bar">⚠ {apiError}</div>}

      <div className="toolbar glass-card">
        <div className="quick-prompts">
          {QUICK_PROMPTS.map((p) => (
            <button key={p.label} type="button" className="prompt-chip" onClick={() => sendText(p.text)} disabled={sending}>
              {p.label}
            </button>
          ))}
        </div>
        <div className="toolbar-actions">
          {sessionId && (
            <button type="button" className="tool-btn" onClick={() => loadHistory(sessionId)} disabled={historyLoading}>
              <RefreshCw size={14} style={{ animation: historyLoading ? "spin 1s linear infinite" : "none" }} />
              Reload history
            </button>
          )}
          <button type="button" className="tool-btn" onClick={startNewSession}>
            New session
          </button>
          <button type="button" className="tool-btn" onClick={() => setShowTraces((v) => !v)}>
            {showTraces ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            Tool traces
          </button>
        </div>
      </div>

      {sessionId && (
        <div className="session-bar">
          Session: <code>{sessionId}</code>
        </div>
      )}

      {lastAssistant && (
        <div className="refine-bar glass-card">
          <Wand2 size={16} style={{ color: "var(--color-saffron)" }} />
          <span className="refine-label">Refine last answer:</span>
          {REFINE_ACTIONS.map((a) => (
            <button
              key={a.label}
              type="button"
              className="refine-chip"
              disabled={refining}
              onClick={() => refineLastAssistant(a.instruction)}
            >
              {a.label}
            </button>
          ))}
        </div>
      )}

      <div className="chat-messages-box glass-card">
        <div className="messages-list">
          {messages.map((msg) => (
            <div key={msg.id} className={`msg-row ${msg.role === "user" ? "msg-user-row" : "msg-assistant-row"}`}>
              <div className={`msg-avatar ${msg.role === "user" ? "avatar-user" : "avatar-ai"}`}>
                {msg.role === "user" ? "U" : <Sparkles size={14} />}
              </div>

              <div className="msg-content-group">
                <div className={`msg-bubble ${msg.role === "user" ? "bubble-user" : "bubble-ai"}`}>
                  <p className="bubble-text">{msg.text}</p>
                  {msg.intent && <span className="intent-badge">{msg.intent}</span>}
                  {msg.role === "assistant" && msg.confidence != null && (
                    <span className="meta-badge">
                      confidence {(msg.confidence * 100).toFixed(0)}%
                      {msg.llmProvider ? ` · ${msg.llmProvider}` : ""}
                    </span>
                  )}
                </div>

                {msg.translated && (
                  <div className="msg-bubble bubble-translated">
                    <p className="bubble-text">{msg.translated}</p>
                    <span className="translated-label">
                      <Languages size={11} />
                      Translated · {LANGUAGES.find((l) => l.code === targetLang)?.label}
                    </span>
                  </div>
                )}

                {msg.role === "assistant" && msg.suggestedActions?.length > 0 && (
                  <div className="suggested-actions">
                    {msg.suggestedActions.map((action) => (
                      <button key={action} type="button" className="prompt-chip small" onClick={() => sendText(action)}>
                        {action}
                      </button>
                    ))}
                  </div>
                )}

                {showTraces && msg.toolTraces?.length > 0 && (
                  <div className="trace-box">
                    {msg.toolTraces.map((t) => (
                      <div key={`${t.name}-${t.details}`} className="trace-line">
                        <strong>{t.name}</strong> {t.used ? "✓" : "—"} {t.details || ""}
                      </div>
                    ))}
                  </div>
                )}

                {!msg.translated && msg.role === "assistant" && (
                  <button
                    type="button"
                    onClick={() => translateMessage(msg.id, msg.text)}
                    disabled={translating}
                    className="translate-btn"
                  >
                    <Languages size={12} />
                    Translate
                  </button>
                )}
              </div>
            </div>
          ))}

          {(sending || translating || refining) && (
            <div className="translating-indicator">
              <div className="typing-dot" />
              <div className="typing-dot" />
              <div className="typing-dot" />
              <span className="typing-label">
                {refining ? "Refining..." : sending ? "Agent thinking..." : "Translating..."}
              </span>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      <div className="chat-input-row glass-card">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask: mera last 5 order dikhao, nearby tech tasks, create plumbing task..."
          className="chat-textarea"
          rows={2}
        />
        <button
          type="button"
          onClick={sendMessage}
          disabled={!input.trim() || sending}
          className="btn-premium btn-teal send-btn"
        >
          <Send size={16} />
        </button>
      </div>

      <style jsx>{`
        .chat-wrapper { display: flex; flex-direction: column; gap: 16px; max-width: 920px; margin: 0 auto; }
        .chat-header-bar { padding: 20px 24px; display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
        .chat-header-left { display: flex; align-items: center; gap: 16px; }
        .chat-title { font-size: 1.4rem; font-weight: 800; display: flex; align-items: center; gap: 10px; }
        .chat-title-badge { font-size: 0.65rem; padding: 3px 8px; border-radius: 20px; background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.3); color: #10b981; font-weight: 700; }
        .chat-subtitle { font-size: 0.8rem; color: var(--color-text-muted); margin-top: 2px; }
        .chat-header-right { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
        .lang-pill { display: flex; align-items: center; gap: 6px; background: rgba(20,184,166,0.05); border: 1px solid var(--border-teal); border-radius: 20px; padding: 6px 12px; }
        .pill-label { font-size: 0.68rem; color: var(--color-text-muted); font-weight: 700; text-transform: uppercase; }
        .lang-select { background: transparent; border: none; color: var(--color-text-main); font-family: inherit; font-size: 0.82rem; outline: none; cursor: pointer; max-width: 120px; }
        .ws-status-pill { display: flex; align-items: center; gap: 6px; border: 1px solid; border-radius: 20px; padding: 6px 12px; font-size: 0.72rem; font-weight: 600; }
        .chat-auth-banner { background: rgba(245,158,11,0.07); border: 1px solid rgba(245,158,11,0.2); border-radius: 10px; padding: 12px 16px; font-size: 0.85rem; color: var(--color-saffron); text-align: center; }
        .chat-auth-banner a { color: var(--color-teal); text-decoration: underline; }
        .api-error-bar { background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.25); border-radius: 10px; padding: 12px 16px; color: #fca5a5; font-size: 0.85rem; }
        .toolbar { padding: 14px 16px; display: flex; flex-direction: column; gap: 12px; }
        .quick-prompts, .toolbar-actions, .suggested-actions { display: flex; flex-wrap: wrap; gap: 8px; }
        .toolbar-actions { justify-content: flex-end; }
        .prompt-chip, .refine-chip, .tool-btn { border-radius: 999px; padding: 6px 12px; font-size: 0.78rem; font-weight: 600; font-family: inherit; cursor: pointer; transition: all 0.15s ease; }
        .prompt-chip, .refine-chip { background: rgba(20,184,166,0.08); border: 1px solid var(--border-teal); color: var(--color-teal); }
        .prompt-chip.small { font-size: 0.72rem; padding: 4px 10px; }
        .prompt-chip:hover, .refine-chip:hover { background: rgba(20,184,166,0.15); }
        .tool-btn { display: inline-flex; align-items: center; gap: 6px; background: rgba(255,255,255,0.04); border: 1px solid var(--border-glow); color: var(--color-text-muted); }
        .refine-bar { padding: 12px 16px; display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
        .refine-label { font-size: 0.8rem; color: var(--color-text-muted); margin-right: 4px; }
        .session-bar { font-size: 0.75rem; color: var(--color-text-muted); text-align: center; }
        .session-bar code { color: var(--color-teal); }
        .chat-messages-box { padding: 24px; min-height: 380px; max-height: 520px; overflow: hidden; }
        .messages-list { display: flex; flex-direction: column; gap: 18px; max-height: 470px; overflow-y: auto; padding-right: 8px; }
        .msg-row { display: flex; gap: 12px; }
        .msg-user-row { flex-direction: row-reverse; }
        .msg-avatar { width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.85rem; font-weight: 700; flex-shrink: 0; }
        .avatar-user { background: rgba(245,158,11,0.1); border: 1px solid var(--border-saffron); color: var(--color-saffron); }
        .avatar-ai { background: rgba(20,184,166,0.1); border: 1px solid var(--border-teal); color: var(--color-teal); }
        .msg-content-group { display: flex; flex-direction: column; gap: 6px; max-width: 78%; }
        .msg-user-row .msg-content-group { align-items: flex-end; }
        .msg-bubble { padding: 14px 18px; border-radius: 16px; display: flex; flex-direction: column; gap: 6px; }
        .bubble-user { background: rgba(245,158,11,0.08); border: 1px solid var(--border-saffron); border-top-right-radius: 4px; }
        .bubble-ai { background: rgba(20,184,166,0.05); border: 1px solid var(--border-teal); border-top-left-radius: 4px; }
        .bubble-translated { background: rgba(20,184,166,0.03); border: 1px dashed var(--border-teal); }
        .bubble-text { font-size: 0.92rem; line-height: 1.55; white-space: pre-wrap; }
        .intent-badge, .meta-badge { font-size: 0.65rem; padding: 2px 8px; border-radius: 10px; background: rgba(20,184,166,0.1); color: var(--color-teal); font-weight: 600; align-self: flex-start; }
        .trace-box { font-size: 0.72rem; color: var(--color-text-muted); background: rgba(0,0,0,0.2); border: 1px solid var(--border-glow); border-radius: 8px; padding: 8px 10px; }
        .trace-line { margin-bottom: 4px; }
        .translate-btn { display: flex; align-items: center; gap: 5px; padding: 5px 12px; border-radius: 16px; background: rgba(20,184,166,0.05); border: 1px solid var(--border-teal); color: var(--color-teal); font-size: 0.75rem; font-weight: 600; cursor: pointer; font-family: inherit; }
        .translating-indicator { display: flex; align-items: center; padding: 10px 14px; }
        .typing-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--color-teal); margin: 0 3px; animation: typingBounce 0.9s infinite; }
        .typing-dot:nth-child(2) { animation-delay: 0.15s; }
        .typing-dot:nth-child(3) { animation-delay: 0.3s; }
        .typing-label { font-size: 0.8rem; color: var(--color-text-muted); margin-left: 8px; }
        .chat-input-row { padding: 16px 20px; display: flex; gap: 12px; align-items: flex-end; }
        .chat-textarea { flex: 1; background: transparent; border: none; resize: none; color: var(--color-text-main); font-family: inherit; font-size: 0.95rem; outline: none; line-height: 1.5; }
        .send-btn { width: 48px; height: 48px; border-radius: 12px; flex-shrink: 0; }
        @keyframes typingBounce { 0%, 60%, 100% { transform: translateY(0); } 30% { transform: translateY(-6px); } }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
