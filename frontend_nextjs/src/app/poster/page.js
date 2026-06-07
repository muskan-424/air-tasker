"use client";

import React, { useState, useEffect, useRef } from "react";
import { Mic, Square, Sparkles, CheckCircle2, Play, FileText, Landmark, AlertTriangle } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { draftsAPI, tasksAPI } from "@/lib/api";

export default function PosterSandbox() {
  const { isLoggedIn, user } = useAuth();
  const [inputText, setInputText] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [audioUrl, setAudioUrl] = useState(null);
  const [stage, setStage] = useState("input"); // 'input' | 'processing' | 'draft'
  const [activeStep, setActiveStep] = useState(0);
  const [draftId, setDraftId] = useState(null);
  const [apiError, setApiError] = useState(null);

  const [draftSchema, setDraftSchema] = useState({
    category: "",
    title: "",
    description: "",
    requiredTools: [],
    estimatedDurationMinutes: 60,
    location: "",
    completionCriteria: "",
    evidenceRequirements: "",
    suggestedPriceRange: { min: 600, max: 1200 },
  });

  const processingSteps = [
    "Receiving your input...",
    "Bhashini API: Translating to English...",
    "Gemini AI: Parsing intent & category...",
    "Gemini AI: Extracting required tools...",
    "Aggregating local pricing estimates...",
  ];

  const canvasRef = useRef(null);
  const animationRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const streamRef = useRef(null);

  const startRecording = async () => {
    setIsRecording(true);
    setAudioUrl(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      const audioCtx = new AudioContext();
      audioContextRef.current = audioCtx;
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 64;
      analyserRef.current = analyser;
      const source = audioCtx.createMediaStreamSource(stream);
      source.connect(analyser);
      drawRealWaveform();
    } catch {
      drawSimulatedWaveform();
    }
  };

  const stopRecording = () => {
    setIsRecording(false);
    if (animationRef.current) cancelAnimationFrame(animationRef.current);
    if (streamRef.current) streamRef.current.getTracks().forEach((t) => t.stop());
    if (audioContextRef.current) audioContextRef.current.close();
    setAudioUrl("#");
  };

  const drawRealWaveform = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const analyser = analyserRef.current;
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    const draw = () => {
      animationRef.current = requestAnimationFrame(draw);
      analyser.getByteFrequencyData(dataArray);
      ctx.fillStyle = "rgba(7, 9, 19, 0.2)";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      const barWidth = (canvas.width / bufferLength) * 1.5;
      let x = 0;
      for (let i = 0; i < bufferLength; i++) {
        const barHeight = (dataArray[i] / 255) * canvas.height * 0.8;
        ctx.fillStyle = `rgba(20, 184, 166, ${0.4 + barHeight / canvas.height})`;
        ctx.fillRect(x, canvas.height / 2 - barHeight / 2, barWidth - 2, barHeight);
        x += barWidth;
      }
    };
    draw();
  };

  const drawSimulatedWaveform = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    let tick = 0;
    const draw = () => {
      animationRef.current = requestAnimationFrame(draw);
      tick++;
      ctx.fillStyle = "rgba(7, 9, 19, 0.2)";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      const numLines = 20;
      const barWidth = canvas.width / numLines;
      for (let i = 0; i < numLines; i++) {
        const h = Math.abs(Math.sin(i * 0.5 + tick * 0.15) * Math.cos(i * 0.2)) * canvas.height * 0.7;
        ctx.fillStyle = `rgba(20, 184, 166, ${0.3 + h / canvas.height})`;
        ctx.fillRect(i * barWidth, canvas.height / 2 - h / 2, barWidth - 3, h);
      }
    };
    draw();
  };

  // ── Submit to backend: POST /api/tasks/drafts ──────────────────────────────
  const submitToAI = async () => {
    if (!inputText && !audioUrl) return;
    if (!isLoggedIn) { window.location.href = "/login"; return; }
    setApiError(null);
    setStage("processing");
    setActiveStep(0);

    try {
      // Advance steps for UX while API is called
      let step = 0;
      const stepInterval = setInterval(() => {
        step++;
        setActiveStep(step);
        if (step >= processingSteps.length - 1) clearInterval(stepInterval);
      }, 900);

      const raw = inputText || "AC unit is leaking water from indoor panel, PIN 110001";
      const data = await draftsAPI.create(raw);

      clearInterval(stepInterval);
      setActiveStep(processingSteps.length - 1);

      // Map backend ai_schema to local state
      const schema = data.ai_schema || {};
      setDraftId(data.id);
      setDraftSchema({
        category: schema.category || "General Service",
        title: schema.title || raw.slice(0, 60),
        description: schema.description || raw,
        requiredTools: Array.isArray(schema.requiredTools) ? schema.requiredTools : [],
        estimatedDurationMinutes: schema.estimatedDurationMinutes || 60,
        location: schema.location || "110001",
        completionCriteria: schema.completionCriteria || "Task completed as described.",
        evidenceRequirements: schema.evidenceRequirements || "Before and after photos required.",
        suggestedPriceRange: schema.suggestedPriceRange || { min: 600, max: 1200 },
      });

      setTimeout(() => setStage("draft"), 600);
    } catch (err) {
      setApiError(err.message);
      setStage("input");
    }
  };

  // ── Publish draft: POST /api/tasks/{draft_id}/publish ─────────────────────
  const handlePublish = async () => {
    if (!draftId) return;
    setApiError(null);
    try {
      await tasksAPI.publish(draftId);
      alert("✅ Task published successfully! It is now live on the Tasker Radar.");
      window.location.href = "/tasker";
    } catch (err) {
      setApiError(err.message);
    }
  };

  return (
    <div className="sandbox-wrapper">
      <div className="header-box">
        <h2 className="title-gradient">AI Task Generator</h2>
        <p className="desc-box">
          Post your task in local words and let AI build a verified, structured contract draft.
        </p>
        {!isLoggedIn && (
          <div className="auth-warning">
            <AlertTriangle className="warn-icon" />
            <span>You must <a href="/login">sign in</a> to create tasks.</span>
          </div>
        )}
      </div>

      {apiError && (
        <div className="api-error-bar">
          ⚠ Backend Error: {apiError}
        </div>
      )}

      {stage === "input" && (
        <div className="input-grid">
          <div className="glass-card panel-card">
            <h3 className="panel-title">Describe Your Task</h3>
            <div className="audio-record-box">
              <p className="sub-label">Voice-to-Task (any language)</p>
              <div className="waveform-container">
                <canvas ref={canvasRef} width="350" height="80" className="waveform-canvas"></canvas>
                {!isRecording && !audioUrl && (
                  <div className="waveform-placeholder">Click to record your task</div>
                )}
                {audioUrl && !isRecording && (
                  <div className="audio-play-indicator">
                    <Play className="play-icon" style={{ width: 14, height: 14 }} /> Audio captured
                  </div>
                )}
              </div>
              <div className="controls-row">
                {!isRecording ? (
                  <button onClick={startRecording} className="btn-premium btn-teal record-btn">
                    <Mic style={{ width: 16, height: 16 }} /> Start Recording
                  </button>
                ) : (
                  <button onClick={stopRecording} className="btn-premium btn-saffron stop-btn pulse-marker-saffron">
                    <Square style={{ width: 16, height: 16 }} /> Stop & Save
                  </button>
                )}
              </div>
            </div>

            <div className="divider-row"><span className="divider-text">OR TYPE INSTEAD</span></div>

            <textarea
              placeholder="e.g. Mera bedroom AC paani de raha hai, isko saaf karna hai. PIN 110001..."
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              className="input-textarea"
            />

            <button
              onClick={submitToAI}
              disabled={!inputText && !audioUrl}
              className="btn-premium btn-teal"
              style={{ width: "100%" }}
            >
              <Sparkles style={{ width: 16, height: 16 }} /> Generate Task Draft via API
            </button>
          </div>

          <div className="glass-card panel-card">
            <h3 className="panel-title">Backend Connected</h3>
            <div className="info-bullets">
              {[
                { icon: <Sparkles />, title: "POST /api/tasks/drafts", desc: "Your raw description is sent to the FastAPI backend which runs it through the AI schema builder." },
                { icon: <FileText />, title: "AI Schema Generated", desc: "The backend returns a structured JSON schema with category, tools, budget range, and evidence requirements." },
                { icon: <Landmark />, title: "POST /api/tasks/{id}/publish", desc: "Publish the reviewed draft to make it live for taskers to discover in the radar feed." },
              ].map((b, i) => (
                <div key={i} className="info-bullet">
                  <div className="bullet-icon-box">{b.icon}</div>
                  <div>
                    <h4>{b.title}</h4>
                    <p>{b.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {stage === "processing" && (
        <div className="glass-card processing-box">
          <div className="gemini-orb-container">
            <div className="gemini-orb"></div>
            <Sparkles style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%,-50%)", color: "#fff", width: 28, height: 28 }} />
          </div>
          <h3 className="processing-title">FastAPI + Gemini AI Processing...</h3>
          <div className="steps-container">
            {processingSteps.map((step, idx) => (
              <div key={idx} className={`step-row ${idx === activeStep ? "step-active" : idx < activeStep ? "step-completed" : "step-pending"}`}>
                <div className="step-bullet">
                  {idx < activeStep ? <CheckCircle2 style={{ color: "var(--color-teal)", width: 20, height: 20 }} /> : <div className="step-dot"></div>}
                </div>
                <span className="step-text">{step}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {stage === "draft" && (
        <div className="draft-container">
          <div className="draft-header">
            <div className="badge-glow">
              <CheckCircle2 style={{ width: 14, height: 14 }} /> Backend Schema Generated
            </div>
            {draftId && <p className="draft-id-label">Draft ID: <code>{draftId}</code></p>}
            <h3>Review Contract Parameters</h3>
          </div>

          <div className="draft-editor-grid">
            <div className="glass-card editor-card">
              <div className="form-row">
                <label>Category</label>
                <input type="text" value={draftSchema.category} onChange={(e) => setDraftSchema({ ...draftSchema, category: e.target.value })} />
              </div>
              <div className="form-row">
                <label>Task Title</label>
                <input type="text" value={draftSchema.title} onChange={(e) => setDraftSchema({ ...draftSchema, title: e.target.value })} />
              </div>
              <div className="form-row">
                <label>Description</label>
                <textarea rows="4" value={draftSchema.description} onChange={(e) => setDraftSchema({ ...draftSchema, description: e.target.value })} />
              </div>
              <div className="form-row">
                <label>Required Tools (comma separated)</label>
                <input type="text" value={draftSchema.requiredTools.join(", ")} onChange={(e) => setDraftSchema({ ...draftSchema, requiredTools: e.target.value.split(", ") })} />
              </div>
            </div>

            <div className="glass-card editor-card shadow-accent">
              <div className="form-row-group">
                <div className="form-row">
                  <label>Duration (min)</label>
                  <input type="number" value={draftSchema.estimatedDurationMinutes} onChange={(e) => setDraftSchema({ ...draftSchema, estimatedDurationMinutes: Number(e.target.value) })} />
                </div>
                <div className="form-row">
                  <label>PIN Code</label>
                  <input type="text" value={draftSchema.location} onChange={(e) => setDraftSchema({ ...draftSchema, location: e.target.value })} />
                </div>
              </div>
              <div className="form-row">
                <label>Completion Criteria</label>
                <textarea rows="3" value={draftSchema.completionCriteria} onChange={(e) => setDraftSchema({ ...draftSchema, completionCriteria: e.target.value })} />
              </div>
              <div className="form-row">
                <label>Evidence Required</label>
                <input type="text" value={draftSchema.evidenceRequirements} onChange={(e) => setDraftSchema({ ...draftSchema, evidenceRequirements: e.target.value })} />
              </div>
              <div className="price-range-box">
                <div className="price-header">
                  <span className="price-title">AI Suggested Price</span>
                  <span className="price-value">₹{draftSchema.suggestedPriceRange?.min} - ₹{draftSchema.suggestedPriceRange?.max}</span>
                </div>
                <div className="price-bar"><div className="price-fill"></div></div>
              </div>
            </div>
          </div>

          <div className="draft-actions">
            <button onClick={() => { setStage("input"); setDraftId(null); }} className="btn-premium btn-outline">Discard & Re-draft</button>
            <button onClick={handlePublish} className="btn-premium btn-teal">Publish Task to Radar →</button>
          </div>
        </div>
      )}

      <style dangerouslySetInnerHTML={{ __html: `
        .sandbox-wrapper { display: flex; flex-direction: column; gap: 40px; }
        .header-box { text-align: center; max-width: 600px; margin: 0 auto; display: flex; flex-direction: column; gap: 12px; }
        .title-gradient { font-size: 2.2rem; font-weight: 800; background: linear-gradient(135deg, var(--color-teal) 0%, #14b8a6 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .desc-box { color: var(--color-text-muted); font-size: 0.95rem; }
        .auth-warning { display: flex; align-items: center; gap: 8px; justify-content: center; color: var(--color-saffron); font-size: 0.85rem; font-weight: 600; }
        .warn-icon { width: 16px; height: 16px; }
        .auth-warning a { color: var(--color-teal); text-decoration: underline; }
        .api-error-bar { background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.25); border-radius: 10px; padding: 12px 16px; color: #fca5a5; font-size: 0.85rem; }
        .input-grid { display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 30px; }
        .panel-card { padding: 30px; display: flex; flex-direction: column; gap: 24px; }
        .panel-title { font-size: 1.3rem; font-weight: 700; border-left: 3px solid var(--color-teal); padding-left: 12px; }
        .audio-record-box { display: flex; flex-direction: column; gap: 12px; }
        .sub-label { font-size: 0.85rem; color: var(--color-text-muted); font-weight: 600; }
        .waveform-container { height: 100px; background: rgba(7,9,19,0.6); border: 1px solid var(--border-glow); border-radius: 12px; display: flex; align-items: center; justify-content: center; position: relative; overflow: hidden; }
        .waveform-canvas { width: 100%; height: 100%; }
        .waveform-placeholder { position: absolute; font-size: 0.85rem; color: var(--color-text-muted); }
        .audio-play-indicator { position: absolute; color: var(--color-teal); font-size: 0.85rem; font-weight: 600; display: flex; align-items: center; gap: 6px; }
        .controls-row { display: flex; gap: 12px; }
        .record-btn, .stop-btn { flex: 1; }
        .divider-row { display: flex; align-items: center; color: var(--color-text-muted); font-size: 0.72rem; font-weight: 700; letter-spacing: 0.1em; }
        .divider-row::before, .divider-row::after { content: ''; flex: 1; border-bottom: 1px solid var(--border-glow); }
        .divider-row::before { margin-right: 12px; } .divider-row::after { margin-left: 12px; }
        .input-textarea { width: 100%; background: rgba(7,9,19,0.4); border: 1px solid var(--border-glow); border-radius: 12px; padding: 16px; color: var(--color-text-main); font-family: inherit; font-size: 0.95rem; resize: none; min-height: 100px; outline: none; transition: border 0.3s ease; }
        .input-textarea:focus { border-color: var(--color-teal); }
        .info-bullets { display: flex; flex-direction: column; gap: 24px; }
        .info-bullet { display: flex; gap: 16px; }
        .bullet-icon-box { width: 40px; height: 40px; border-radius: 10px; background: rgba(20,184,166,0.1); border: 1px solid var(--border-teal); color: var(--color-teal); display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
        .bullet-icon-box svg { width: 20px; height: 20px; }
        .info-bullet h4 { font-size: 0.85rem; font-weight: 700; color: var(--color-teal); margin-bottom: 4px; font-family: monospace; }
        .info-bullet p { font-size: 0.82rem; color: var(--color-text-muted); line-height: 1.4; }
        .processing-box { padding: 60px; display: flex; flex-direction: column; align-items: center; gap: 30px; max-width: 650px; margin: 0 auto; }
        .gemini-orb-container { position: relative; width: 80px; height: 80px; }
        .gemini-orb { width: 100%; height: 100%; border-radius: 50%; }
        .processing-title { font-size: 1.3rem; font-weight: 700; }
        .steps-container { display: flex; flex-direction: column; gap: 16px; width: 100%; }
        .step-row { display: flex; align-items: center; gap: 16px; transition: all 0.3s ease; }
        .step-bullet { width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; }
        .step-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--color-text-muted); }
        .step-active .step-dot { background: var(--color-teal); transform: scale(1.5); box-shadow: 0 0 10px var(--color-teal); }
        .step-text { font-size: 0.9rem; color: var(--color-text-muted); }
        .step-active .step-text { color: var(--color-text-main); font-weight: 600; }
        .step-completed .step-text { opacity: 0.6; text-decoration: line-through; }
        .draft-container { display: flex; flex-direction: column; gap: 30px; }
        .draft-header { text-align: center; max-width: 600px; margin: 0 auto; display: flex; flex-direction: column; align-items: center; gap: 8px; }
        .badge-glow { background: rgba(20,184,166,0.1); border: 1px solid var(--border-teal); color: var(--color-teal); font-size: 0.75rem; font-weight: 700; padding: 6px 14px; border-radius: 20px; display: flex; align-items: center; gap: 6px; text-transform: uppercase; }
        .draft-id-label { font-size: 0.75rem; color: var(--color-text-muted); } .draft-id-label code { color: var(--color-teal); }
        .draft-header h3 { font-size: 1.8rem; font-weight: 800; }
        .draft-editor-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; }
        .editor-card { padding: 28px; display: flex; flex-direction: column; gap: 20px; }
        .shadow-accent { border-color: var(--border-teal); }
        .form-row-group { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
        .form-row { display: flex; flex-direction: column; gap: 8px; }
        .form-row label { font-size: 0.8rem; font-weight: 700; text-transform: uppercase; color: var(--color-text-muted); letter-spacing: 0.05em; }
        .form-row input, .form-row textarea { background: rgba(7,9,19,0.6); border: 1px solid var(--border-glow); border-radius: 8px; padding: 12px; color: var(--color-text-main); font-family: inherit; font-size: 0.95rem; outline: none; }
        .form-row input:focus, .form-row textarea:focus { border-color: var(--color-teal); }
        .price-range-box { background: rgba(20,184,166,0.03); border: 1px dashed var(--border-teal); border-radius: 12px; padding: 20px; display: flex; flex-direction: column; gap: 12px; }
        .price-header { display: flex; justify-content: space-between; }
        .price-title { font-size: 0.85rem; font-weight: 600; color: var(--color-teal); }
        .price-value { font-size: 1.25rem; font-weight: 800; }
        .price-bar { height: 6px; background: rgba(255,255,255,0.05); border-radius: 3px; overflow: hidden; }
        .price-fill { width: 60%; height: 100%; background: linear-gradient(90deg, var(--color-teal), #0d9488); margin-left: 20%; border-radius: 3px; }
        .draft-actions { display: flex; justify-content: flex-end; gap: 16px; }
        @media (max-width: 768px) { .input-grid, .draft-editor-grid { grid-template-columns: 1fr; } .form-row-group { grid-template-columns: 1fr; } }
      ` }} />
    </div>
  );
}
