"use client";

import React, { useRef } from "react";
import { ImagePlus, X } from "lucide-react";

/**
 * Pick a photo/video from device with preview. Returns the File to parent via onFileSelect.
 */
export default function EvidenceFilePicker({
  label,
  accept = "image/jpeg,image/png,image/webp",
  file,
  previewUrl,
  onFileSelect,
  onClear,
  disabled = false,
}) {
  const inputRef = useRef(null);

  const handleChange = (e) => {
    const picked = e.target.files?.[0];
    if (!picked) return;
    onFileSelect?.(picked);
    e.target.value = "";
  };

  return (
    <div className="evidence-picker">
      <label>{label}</label>
      {previewUrl ? (
        <div className="picker-preview">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={previewUrl} alt={label} />
          {!disabled && (
            <button type="button" className="picker-clear" onClick={onClear} aria-label="Remove">
              <X size={14} />
            </button>
          )}
        </div>
      ) : (
        <button
          type="button"
          className="picker-drop"
          onClick={() => inputRef.current?.click()}
          disabled={disabled}
        >
          <ImagePlus size={20} />
          <span>Choose file</span>
          {file && <span className="picker-name">{file.name}</span>}
        </button>
      )}
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        onChange={handleChange}
        hidden
        disabled={disabled}
      />
      <style jsx>{`
        .evidence-picker { display: flex; flex-direction: column; gap: 8px; }
        label { font-size: 0.8rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--color-text-muted); }
        .picker-drop {
          display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px;
          min-height: 120px; border: 1px dashed var(--border-glow); border-radius: 10px;
          background: rgba(7,9,19,0.4); color: var(--color-text-muted); cursor: pointer;
          transition: border-color 0.2s, color 0.2s;
        }
        .picker-drop:hover:not(:disabled) { border-color: #a78bfa; color: #c4b5fd; }
        .picker-drop:disabled { opacity: 0.5; cursor: not-allowed; }
        .picker-name { font-size: 0.72rem; max-width: 90%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .picker-preview { position: relative; border-radius: 10px; overflow: hidden; border: 1px solid var(--border-glow); max-height: 160px; }
        .picker-preview img { width: 100%; height: 160px; object-fit: cover; display: block; }
        .picker-clear {
          position: absolute; top: 8px; right: 8px; width: 28px; height: 28px; border-radius: 50%;
          border: none; background: rgba(0,0,0,0.65); color: white; cursor: pointer;
          display: flex; align-items: center; justify-content: center;
        }
      `}</style>
    </div>
  );
}
