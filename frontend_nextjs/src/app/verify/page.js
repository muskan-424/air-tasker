"use client";

import React, { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Upload, ShieldCheck, AlertTriangle, Loader, Link2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import EvidenceFilePicker from "@/components/EvidenceFilePicker";
import { tasksAPI, uploadsAPI, resolveMediaUrl } from "@/lib/api";

const CONFIDENCE_COLORS = {
  PASS: { ring: "#10b981", glow: "rgba(16,185,129,0.2)", label: "VERIFIED", textColor: "#10b981" },
  LOW_CONFIDENCE: { ring: "#f59e0b", glow: "rgba(245,158,11,0.2)", label: "LOW CONFIDENCE", textColor: "#f59e0b" },
  FAIL: { ring: "#ef4444", glow: "rgba(239,68,68,0.2)", label: "FAILED", textColor: "#ef4444" },
};

function VerifyInner() {
  const { isLoggedIn, user } = useAuth();
  const searchParams = useSearchParams();
  const urlTaskId = searchParams?.get("task_id") || "";

  const [taskId, setTaskId] = useState(urlTaskId);
  const [useUrls, setUseUrls] = useState(false);
  const [beforeUrl, setBeforeUrl] = useState("");
  const [afterUrl, setAfterUrl] = useState("");
  const [videoUrl, setVideoUrl] = useState("");
  const [beforeFile, setBeforeFile] = useState(null);
  const [afterFile, setAfterFile] = useState(null);
  const [videoFile, setVideoFile] = useState(null);
  const [beforePreview, setBeforePreview] = useState("");
  const [afterPreview, setAfterPreview] = useState("");
  const [stage, setStage] = useState("input");
  const [result, setResult] = useState(null);
  const [apiError, setApiError] = useState(null);
  const [sliderVal, setSliderVal] = useState(50);
  const [evidenceId, setEvidenceId] = useState(null);
  const [existingEvidence, setExistingEvidence] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [verifying, setVerifying] = useState(false);

  const isTasker = user?.role === "TASKER";
  const isPoster = user?.role === "POSTER";

  useEffect(() => {
    if (urlTaskId) setTaskId(urlTaskId);
  }, [urlTaskId]);

  useEffect(() => {
    if (!taskId.trim() || !isLoggedIn) {
      setExistingEvidence(null);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const data = await tasksAPI.getEvidence(taskId.trim());
        if (!cancelled && data) {
          setExistingEvidence(data);
          setBeforeUrl(data.before_image_url || "");
          setAfterUrl(data.after_image_url || "");
          setVideoUrl(data.evidence_video_url || "");
          setEvidenceId(data.evidence_id);
        }
      } catch (_) {
        if (!cancelled) setExistingEvidence(null);
      }
    })();
    return () => { cancelled = true; };
  }, [taskId, isLoggedIn]);

  const setFileWithPreview = (setter, previewSetter) => (file) => {
    setter(file);
    previewSetter(file ? URL.createObjectURL(file) : "");
  };

  const resolveBefore = () => (useUrls ? beforeUrl : beforePreview || resolveMediaUrl(existingEvidence?.before_image_url));
  const resolveAfter = () => (useUrls ? afterUrl : afterPreview || resolveMediaUrl(existingEvidence?.after_image_url));

  const uploadFileIfNeeded = async (file, fallbackUrl) => {
    if (file) {
      const res = await uploadsAPI.uploadEvidenceFile(file);
      return res.url;
    }
    return fallbackUrl || null;
  };

  const handleUploadEvidence = async () => {
    if (!isLoggedIn) { window.location.href = "/login"; return; }
    if (!taskId.trim()) { setApiError("Please enter a Task ID first."); return; }
    if (!isTasker) { setApiError("Only the assigned tasker can upload evidence."); return; }

    setApiError(null);
    setUploading(true);
    setStage("uploading");

    try {
      const before = await uploadFileIfNeeded(beforeFile, useUrls ? beforeUrl : existingEvidence?.before_image_url);
      const after = await uploadFileIfNeeded(afterFile, useUrls ? afterUrl : existingEvidence?.after_image_url);
      const video = await uploadFileIfNeeded(videoFile, useUrls ? videoUrl : existingEvidence?.evidence_video_url);

      if (!before && !after && !video) {
        throw new Error("Add at least one before photo, after photo, or video.");
      }

      const evData = await tasksAPI.uploadEvidence(taskId.trim(), before, after, video);
      setEvidenceId(evData.evidence_id);
      setExistingEvidence({
        evidence_id: evData.evidence_id,
        before_image_url: before,
        after_image_url: after,
        evidence_video_url: video,
      });
      if (before) setBeforeUrl(before);
      if (after) setAfterUrl(after);
      if (video) setVideoUrl(video);
      setStage("input");
    } catch (err) {
      setApiError(err.message);
      setStage("input");
    } finally {
      setUploading(false);
    }
  };

  const handleVerify = async () => {
    if (!isLoggedIn) { window.location.href = "/login"; return; }
    if (!taskId.trim()) { setApiError("Please enter a Task ID first."); return; }
    if (!isPoster && user?.role !== "ADMIN") {
      setApiError("Only the poster (or admin) can trigger AI verification.");
      return;
    }

    setApiError(null);
    setVerifying(true);
    setStage("verifying");

    try {
      const verData = await tasksAPI.verify(taskId.trim());
      setResult({
        verificationId: verData.verification_id,
        status: verData.status.toUpperCase(),
        confidence: Math.round(verData.confidence * 100),
        explanation: verData.explanation,
      });
      setStage("result");
    } catch (err) {
      setApiError(err.message);
      setStage("input");
    } finally {
      setVerifying(false);
    }
  };

  const reset = () => {
    setStage("input");
    setResult(null);
    setApiError(null);
  };

  const colors = result ? (CONFIDENCE_COLORS[result.status] || CONFIDENCE_COLORS.FAIL) : null;
  const circumference = 2 * Math.PI * 54;
  const sliderBefore = resolveBefore();
  const sliderAfter = resolveAfter();

  return (
    <div className="verify-wrapper">
      <div className="verify-header-box">
        <h2 className="title-gradient-purple">Vision Proof Verification</h2>
        <p>Taskers upload before/after photos from their device. Posters run AI verification to release escrow.</p>
      </div>

      {!isLoggedIn && (
        <div className="verify-auth-warning">
          <AlertTriangle style={{ width: 16, height: 16 }} />
          <span>You must <a href="/login">sign in</a> to submit verification.</span>
        </div>
      )}

      {apiError && <div className="api-error-bar">⚠ {apiError}</div>}

      {(stage === "uploading" || stage === "verifying") && (
        <div className="processing-card glass-card">
          <Loader style={{ width: 36, height: 36, color: "var(--color-teal)", animation: "spin 1s linear infinite" }} />
          <h3>{stage === "uploading" ? "Uploading Evidence..." : "AI Verification in Progress..."}</h3>
          <p style={{ color: "var(--color-text-muted)", fontSize: "0.9rem" }}>
            {stage === "uploading"
              ? "Uploading your before/after photos..."
              : "Analyzing evidence quality..."}
          </p>
        </div>
      )}

      {stage === "input" && (
        <div className="verify-grid">
          <div className="glass-card verify-form-card">
            <h3 className="panel-title" style={{ borderColor: "#a78bfa" }}>Task & Evidence</h3>

            <div className="form-row">
              <label>Task ID</label>
              <input
                type="text"
                placeholder="UUID from accepted task"
                value={taskId}
                onChange={(e) => setTaskId(e.target.value)}
                className="form-input"
              />
              {existingEvidence && (
                <p className="helper-text success">Evidence on file · ID <code>{existingEvidence.evidence_id?.slice(0, 8)}…</code></p>
              )}
            </div>

            <label className="url-toggle">
              <input type="checkbox" checked={useUrls} onChange={(e) => setUseUrls(e.target.checked)} />
              <Link2 size={14} /> Use external URLs instead of file upload
            </label>

            {useUrls ? (
              <>
                <div className="form-row">
                  <label>Before Image URL</label>
                  <input type="url" value={beforeUrl} onChange={(e) => setBeforeUrl(e.target.value)} className="form-input" />
                </div>
                <div className="form-row">
                  <label>After Image URL</label>
                  <input type="url" value={afterUrl} onChange={(e) => setAfterUrl(e.target.value)} className="form-input" />
                </div>
                <div className="form-row">
                  <label>Video URL (optional)</label>
                  <input type="url" value={videoUrl} onChange={(e) => setVideoUrl(e.target.value)} className="form-input" />
                </div>
              </>
            ) : (
              <>
                <EvidenceFilePicker
                  label="Before photo"
                  file={beforeFile}
                  previewUrl={beforePreview || resolveMediaUrl(existingEvidence?.before_image_url)}
                  onFileSelect={setFileWithPreview(setBeforeFile, setBeforePreview)}
                  onClear={() => { setBeforeFile(null); setBeforePreview(""); }}
                  disabled={!isTasker || uploading}
                />
                <EvidenceFilePicker
                  label="After photo"
                  file={afterFile}
                  previewUrl={afterPreview || resolveMediaUrl(existingEvidence?.after_image_url)}
                  onFileSelect={setFileWithPreview(setAfterFile, setAfterPreview)}
                  onClear={() => { setAfterFile(null); setAfterPreview(""); }}
                  disabled={!isTasker || uploading}
                />
                <EvidenceFilePicker
                  label="Video (optional)"
                  accept="video/mp4,video/webm,video/quicktime"
                  file={videoFile}
                  previewUrl=""
                  onFileSelect={setVideoFile}
                  onClear={() => setVideoFile(null)}
                  disabled={!isTasker || uploading}
                />
                {videoFile && <p className="helper-text">Selected: {videoFile.name}</p>}
                {!videoFile && existingEvidence?.evidence_video_url && (
                  <p className="helper-text success">Video on file</p>
                )}
              </>
            )}

            <div className="action-row">
              {isTasker && (
                <button onClick={handleUploadEvidence} className="btn-premium btn-teal" disabled={uploading}>
                  <Upload style={{ width: 16, height: 16 }} />
                  {uploading ? "Uploading..." : "Upload Evidence"}
                </button>
              )}
              {(isPoster || user?.role === "ADMIN") && (
                <button onClick={handleVerify} className="btn-premium btn-saffron" disabled={verifying || (!existingEvidence && !evidenceId)}>
                  <ShieldCheck style={{ width: 16, height: 16 }} />
                  {verifying ? "Verifying..." : "Run AI Verification"}
                </button>
              )}
              {!isTasker && !isPoster && isLoggedIn && (
                <p className="helper-text">Sign in as tasker to upload or poster to verify.</p>
              )}
            </div>
          </div>

          <div className="glass-card slider-preview-card">
            <h3 className="panel-title" style={{ borderColor: "#a78bfa" }}>Before / After Preview</h3>
            <div className="slider-outer">
              <div className="slider-before" style={{ backgroundImage: sliderBefore ? `url(${sliderBefore})` : undefined }} />
              <div
                className="slider-after"
                style={{
                  backgroundImage: sliderAfter ? `url(${sliderAfter})` : undefined,
                  clipPath: `inset(0 ${100 - sliderVal}% 0 0)`,
                }}
              />
              <input type="range" min="0" max="100" value={sliderVal} onChange={(e) => setSliderVal(Number(e.target.value))} className="slider-handle" />
              <div className="slider-labels">
                <span className="label-before">BEFORE</span>
                <span className="label-after">AFTER</span>
              </div>
            </div>

            <div className="backend-info-box">
              <h4>How it works</h4>
              <ul>
                <li><b>Tasker</b> — pick photos from device (or paste URLs in advanced mode).</li>
                <li><b>Poster</b> — run verification after evidence is uploaded.</li>
                <li><b>PASS</b> — both before &amp; after → escrow release eligible.</li>
                <li><b>LOW / FAIL</b> — dispute may open; check Payments.</li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {stage === "result" && result && colors && (
        <div className="result-container">
          <div className="result-ring-box glass-card">
            <svg width="160" height="160" viewBox="0 0 120 120">
              <circle cx="60" cy="60" r="54" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="8" />
              <circle
                cx="60" cy="60" r="54"
                fill="none"
                stroke={colors.ring}
                strokeWidth="8"
                strokeLinecap="round"
                strokeDasharray={circumference}
                strokeDashoffset={circumference - (result.confidence / 100) * circumference}
                transform="rotate(-90 60 60)"
                style={{ filter: `drop-shadow(0 0 8px ${colors.ring})`, transition: "stroke-dashoffset 1s ease" }}
              />
              <text x="60" y="55" textAnchor="middle" fill="white" fontSize="22" fontWeight="800" fontFamily="'Outfit', sans-serif">
                {result.confidence}%
              </text>
              <text x="60" y="70" textAnchor="middle" fill={colors.textColor} fontSize="8" fontWeight="700" fontFamily="sans-serif" letterSpacing="1">
                CONFIDENCE
              </text>
            </svg>

            <div className="result-status-badge" style={{ color: colors.textColor, borderColor: colors.ring, background: colors.glow }}>
              <ShieldCheck style={{ width: 16, height: 16 }} /> {colors.label}
            </div>
            <p className="result-explanation">{result.explanation}</p>
            {result.verificationId && (
              <p className="verify-id-label">Verification ID: <code>{result.verificationId}</code></p>
            )}
            {evidenceId && (
              <p className="verify-id-label">Evidence ID: <code>{evidenceId}</code></p>
            )}

            <button onClick={reset} className="btn-premium btn-outline" style={{ marginTop: 8 }}>
              Verify Another Task
            </button>
          </div>

          <div className="glass-card comparison-result-card">
            <h3 className="panel-title" style={{ borderColor: colors.ring }}>Evidence Comparison</h3>
            <div className="comparison-pair">
              <div className="compare-img-box">
                <span className="compare-label">BEFORE</span>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={sliderBefore} alt="Before" className="compare-img" />
              </div>
              <div className="compare-arrow">→</div>
              <div className="compare-img-box">
                <span className="compare-label" style={{ color: colors.textColor }}>AFTER</span>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={sliderAfter} alt="After" className="compare-img" />
              </div>
            </div>

            <div className="next-step-box">
              <h4>Next Step:</h4>
              {result.status === "PASS" ? (
                <p>Escrow is now <b>Release Eligible</b>. Go to <a href={`/payments?task_id=${taskId}`}>Payments</a> to release funds.</p>
              ) : (
                <p>Low confidence or failed — dispute may have opened. Check <a href={`/payments?task_id=${taskId}`}>Payments</a>.</p>
              )}
            </div>
          </div>
        </div>
      )}

      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .verify-wrapper { display: flex; flex-direction: column; gap: 40px; }
        .verify-header-box { text-align: center; max-width: 640px; margin: 0 auto; display: flex; flex-direction: column; gap: 8px; }
        .title-gradient-purple { font-size: 2.2rem; font-weight: 800; background: linear-gradient(135deg, #a78bfa 0%, #7c3aed 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .verify-auth-warning { display: flex; align-items: center; gap: 8px; justify-content: center; background: rgba(245,158,11,0.07); border: 1px solid rgba(245,158,11,0.2); border-radius: 10px; padding: 12px 20px; color: var(--color-saffron); font-size: 0.85rem; font-weight: 600; }
        .verify-auth-warning a { color: var(--color-teal); text-decoration: underline; }
        .api-error-bar { background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.25); border-radius: 10px; padding: 12px 16px; color: #fca5a5; font-size: 0.85rem; }
        .processing-card { max-width: 500px; margin: 0 auto; padding: 60px; display: flex; flex-direction: column; align-items: center; gap: 20px; text-align: center; }
        .verify-grid { display: grid; grid-template-columns: 1.1fr 0.9fr; gap: 30px; }
        .verify-form-card { padding: 30px; display: flex; flex-direction: column; gap: 20px; }
        .panel-title { font-size: 1.2rem; font-weight: 700; border-left: 3px solid; padding-left: 12px; }
        .form-row { display: flex; flex-direction: column; gap: 8px; }
        .form-row label { font-size: 0.8rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--color-text-muted); }
        .form-input { background: rgba(7,9,19,0.6); border: 1px solid var(--border-glow); border-radius: 8px; padding: 12px; color: var(--color-text-main); font-family: inherit; font-size: 0.9rem; outline: none; transition: border 0.2s ease; }
        .form-input:focus { border-color: #a78bfa; }
        .helper-text { font-size: 0.75rem; color: var(--color-text-muted); }
        .helper-text.success { color: var(--color-teal); }
        .helper-text code { color: var(--color-teal); }
        .url-toggle { display: flex; align-items: center; gap: 8px; font-size: 0.82rem; color: var(--color-text-muted); cursor: pointer; }
        .action-row { display: flex; flex-wrap: wrap; gap: 10px; padding-top: 8px; }
        .slider-preview-card { padding: 30px; display: flex; flex-direction: column; gap: 20px; }
        .slider-outer { position: relative; height: 220px; border-radius: 12px; overflow: hidden; border: 1px solid var(--border-glow); background: #111; }
        .slider-before, .slider-after { position: absolute; inset: 0; background-size: cover; background-position: center; }
        .slider-after { transition: clip-path 0.05s ease; }
        .slider-handle { position: absolute; inset: 0; opacity: 0; cursor: ew-resize; width: 100%; z-index: 10; }
        .slider-labels { position: absolute; bottom: 10px; left: 0; right: 0; display: flex; justify-content: space-between; padding: 0 12px; pointer-events: none; }
        .label-before, .label-after { font-size: 0.7rem; font-weight: 700; padding: 3px 8px; border-radius: 4px; background: rgba(0,0,0,0.5); }
        .label-before { color: #94a3b8; } .label-after { color: var(--color-teal); }
        .backend-info-box { background: rgba(167,139,250,0.05); border: 1px solid rgba(167,139,250,0.2); border-radius: 12px; padding: 16px; }
        .backend-info-box h4 { font-size: 0.85rem; font-weight: 700; color: #a78bfa; margin-bottom: 8px; }
        .backend-info-box ul { display: flex; flex-direction: column; gap: 6px; padding-left: 16px; }
        .backend-info-box li { font-size: 0.8rem; color: var(--color-text-muted); }
        .result-container { display: grid; grid-template-columns: 0.8fr 1.2fr; gap: 30px; }
        .result-ring-box { padding: 36px; display: flex; flex-direction: column; align-items: center; gap: 20px; }
        .result-status-badge { display: flex; align-items: center; gap: 8px; padding: 8px 20px; border-radius: 20px; border-width: 1px; border-style: solid; font-size: 0.8rem; font-weight: 700; letter-spacing: 0.05em; }
        .result-explanation { font-size: 0.85rem; color: var(--color-text-muted); text-align: center; line-height: 1.4; }
        .verify-id-label { font-size: 0.72rem; color: var(--color-text-muted); } .verify-id-label code { color: var(--color-teal); font-size: 0.7rem; }
        .comparison-result-card { padding: 30px; display: flex; flex-direction: column; gap: 20px; }
        .comparison-pair { display: flex; align-items: center; gap: 16px; }
        .compare-img-box { flex: 1; display: flex; flex-direction: column; gap: 8px; }
        .compare-label { font-size: 0.7rem; font-weight: 700; letter-spacing: 0.1em; color: var(--color-text-muted); }
        .compare-img { width: 100%; height: 130px; object-fit: cover; border-radius: 10px; border: 1px solid var(--border-glow); }
        .compare-arrow { color: var(--color-teal); font-size: 1.4rem; flex-shrink: 0; }
        .next-step-box { background: rgba(20,184,166,0.04); border: 1px dashed var(--border-teal); border-radius: 12px; padding: 16px; }
        .next-step-box h4 { font-size: 0.85rem; font-weight: 700; color: var(--color-teal); margin-bottom: 6px; }
        .next-step-box p { font-size: 0.85rem; color: var(--color-text-muted); line-height: 1.5; }
        .next-step-box a { color: var(--color-teal); text-decoration: underline; }
        @media (max-width: 768px) { .verify-grid, .result-container { grid-template-columns: 1fr; } .comparison-pair { flex-direction: column; } .compare-arrow { transform: rotate(90deg); } }
      ` }} />
    </div>
  );
}

export default function VerifyPage() {
  return (
    <Suspense fallback={<div className="verify-wrapper"><div className="processing-card glass-card">Loading...</div></div>}>
      <VerifyInner />
    </Suspense>
  );
}
