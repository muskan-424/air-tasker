"use client";

import React, { useRef, useState } from "react";
import { Loader2, Mic, Square } from "lucide-react";
import { voiceAPI } from "@/lib/api";

/**
 * Records audio, sends to POST /api/voice/transcribe, returns editable transcript.
 */
export default function VoiceInputButton({
  onTranscript,
  languageHint = "auto",
  disabled = false,
  className = "",
}) {
  const [recording, setRecording] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState(null);
  const mediaRef = useRef(null);
  const recorderRef = useRef(null);
  const chunksRef = useRef([]);

  const stopTracks = () => {
    mediaRef.current?.getTracks().forEach((t) => t.stop());
    mediaRef.current = null;
  };

  const startRecording = async () => {
    if (disabled || processing) return;
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRef.current = stream;
      chunksRef.current = [];
      const recorder = new MediaRecorder(stream);
      recorderRef.current = recorder;
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.start();
      setRecording(true);
    } catch (err) {
      setError(err.message || "Microphone access denied");
    }
  };

  const stopRecording = async () => {
    const recorder = recorderRef.current;
    if (!recorder || recorder.state === "inactive") {
      setRecording(false);
      stopTracks();
      return;
    }

    setProcessing(true);
    setRecording(false);

    await new Promise((resolve) => {
      recorder.onstop = resolve;
      recorder.stop();
    });
    stopTracks();

    try {
      const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
      if (!blob.size) throw new Error("No audio captured — try speaking longer.");
      const res = await voiceAPI.transcribe(blob, languageHint);
      const text = (res.text || "").trim();
      if (!text) throw new Error("Empty transcript returned.");
      onTranscript?.(text, res);
    } catch (err) {
      setError(err.message);
    } finally {
      setProcessing(false);
      chunksRef.current = [];
      recorderRef.current = null;
    }
  };

  const handleClick = () => {
    if (recording) stopRecording();
    else startRecording();
  };

  return (
    <div className={`voice-input-wrap ${className}`}>
      <button
        type="button"
        className={`voice-mic-btn ${recording ? "recording" : ""}`}
        onClick={handleClick}
        disabled={disabled || processing}
        title={recording ? "Stop and transcribe" : "Record voice"}
      >
        {processing ? (
          <Loader2 size={16} className="spin-icon" />
        ) : recording ? (
          <Square size={16} />
        ) : (
          <Mic size={16} />
        )}
      </button>
      {error && <span className="voice-error">{error}</span>}
      <style jsx>{`
        .voice-input-wrap { display: flex; align-items: center; gap: 8px; }
        .voice-mic-btn {
          width: 44px; height: 44px; border-radius: 12px; flex-shrink: 0;
          display: flex; align-items: center; justify-content: center;
          background: rgba(20,184,166,0.08); border: 1px solid var(--border-teal);
          color: var(--color-teal); cursor: pointer; font-family: inherit;
        }
        .voice-mic-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .voice-mic-btn.recording {
          background: rgba(245,158,11,0.12); border-color: var(--border-saffron);
          color: var(--color-saffron); animation: pulse 1.2s infinite;
        }
        .voice-error { font-size: 0.72rem; color: #fca5a5; max-width: 140px; }
        :global(.spin-icon) { animation: spin 1s linear infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.65; } }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
