"use client";

import React, { useEffect, useState } from "react";
import { Save, User, MapPin, Wrench, Languages } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { profileAPI } from "@/lib/api";

const LANGUAGE_OPTIONS = [
  { code: "en", label: "English" },
  { code: "hi", label: "Hindi" },
  { code: "ta", label: "Tamil" },
  { code: "te", label: "Telugu" },
  { code: "mr", label: "Marathi" },
  { code: "bn", label: "Bengali" },
];

export default function ProfilePage() {
  const { isLoggedIn, user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [form, setForm] = useState({
    display_name: "",
    bio: "",
    default_location_pin: "",
    skills: "",
    service_pin_codes: "",
    preferred_languages: ["en"],
  });

  useEffect(() => {
    if (!isLoggedIn) return;
    setLoading(true);
    profileAPI
      .get()
      .then((data) => {
        setForm({
          display_name: data.display_name || "",
          bio: data.bio || "",
          default_location_pin: data.default_location_pin || "",
          skills: (data.skills || []).join(", "),
          service_pin_codes: (data.service_pin_codes || []).join(", "),
          preferred_languages: data.preferred_languages?.length ? data.preferred_languages : ["en"],
        });
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [isLoggedIn]);

  const toggleLanguage = (code) => {
    setForm((prev) => {
      const langs = prev.preferred_languages.includes(code)
        ? prev.preferred_languages.filter((l) => l !== code)
        : [...prev.preferred_languages, code];
      return { ...prev, preferred_languages: langs.length ? langs : ["en"] };
    });
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      await profileAPI.update({
        display_name: form.display_name || null,
        bio: form.bio || null,
        default_location_pin: form.default_location_pin || null,
        skills: form.skills.split(",").map((s) => s.trim()).filter(Boolean),
        service_pin_codes: form.service_pin_codes.split(",").map((s) => s.trim()).filter(Boolean),
        preferred_languages: form.preferred_languages,
      });
      setSuccess("Profile saved.");
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  if (!isLoggedIn) {
    return (
      <div className="profile-wrapper">
        <p>Please <a href="/login">sign in</a> to manage your profile.</p>
      </div>
    );
  }

  const isTasker = user?.role === "TASKER";

  return (
    <div className="profile-wrapper">
      <div className="profile-header">
        <User style={{ color: "var(--color-teal)", width: 28, height: 28 }} />
        <div>
          <h1>My Profile</h1>
          <p>{isTasker ? "Set skills and service PINs for better task matches." : "Set your default location PIN for posting tasks."}</p>
        </div>
      </div>

      {error && <div className="api-error-bar">⚠ {error}</div>}
      {success && <div className="success-bar">{success}</div>}

      {loading ? (
        <p className="muted">Loading profile…</p>
      ) : (
        <form onSubmit={handleSave} className="profile-form glass-card">
          <label>
            Display name
            <input value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} />
          </label>

          <label>
            Bio
            <textarea rows={3} value={form.bio} onChange={(e) => setForm({ ...form, bio: e.target.value })} />
          </label>

          <label>
            <MapPin size={14} /> Default location PIN
            <input
              value={form.default_location_pin}
              onChange={(e) => setForm({ ...form, default_location_pin: e.target.value.replace(/\D/g, "").slice(0, 6) })}
              placeholder="110001"
              maxLength={6}
            />
          </label>

          {isTasker && (
            <>
              <label>
                <Wrench size={14} /> Skills (comma separated)
                <input
                  value={form.skills}
                  onChange={(e) => setForm({ ...form, skills: e.target.value })}
                  placeholder="plumbing, electrical, AC repair"
                />
              </label>
              <label>
                Service PIN codes (comma separated, 6 digits)
                <input
                  value={form.service_pin_codes}
                  onChange={(e) => setForm({ ...form, service_pin_codes: e.target.value })}
                  placeholder="110001, 560001"
                />
              </label>
            </>
          )}

          <div className="lang-section">
            <span className="lang-title"><Languages size={14} /> Preferred languages</span>
            <div className="lang-chips">
              {LANGUAGE_OPTIONS.map((l) => (
                <button
                  key={l.code}
                  type="button"
                  className={`lang-chip ${form.preferred_languages.includes(l.code) ? "active" : ""}`}
                  onClick={() => toggleLanguage(l.code)}
                >
                  {l.label}
                </button>
              ))}
            </div>
          </div>

          <button type="submit" className="btn-premium btn-teal" disabled={saving}>
            <Save size={16} /> {saving ? "Saving…" : "Save profile"}
          </button>
        </form>
      )}

      <style jsx>{`
        .profile-wrapper { max-width: 640px; margin: 0 auto; display: flex; flex-direction: column; gap: 20px; }
        .profile-header { display: flex; gap: 16px; align-items: flex-start; }
        .profile-header h1 { font-size: 1.6rem; font-weight: 800; }
        .profile-header p { color: var(--color-text-muted); font-size: 0.9rem; margin-top: 4px; }
        .profile-header a { color: var(--color-teal); }
        .profile-form { padding: 24px; display: flex; flex-direction: column; gap: 16px; }
        .profile-form label { display: flex; flex-direction: column; gap: 6px; font-size: 0.78rem; font-weight: 700; text-transform: uppercase; color: var(--color-text-muted); }
        .profile-form input, .profile-form textarea {
          background: rgba(7,9,19,0.5); border: 1px solid var(--border-glow); border-radius: 8px;
          padding: 10px 12px; color: var(--color-text-main); font-family: inherit; font-size: 0.92rem;
        }
        .lang-section { display: flex; flex-direction: column; gap: 8px; }
        .lang-title { display: flex; align-items: center; gap: 6px; font-size: 0.78rem; font-weight: 700; color: var(--color-text-muted); text-transform: uppercase; }
        .lang-chips { display: flex; flex-wrap: wrap; gap: 8px; }
        .lang-chip { padding: 6px 12px; border-radius: 999px; border: 1px solid var(--border-glow); background: transparent; color: var(--color-text-muted); font-size: 0.78rem; cursor: pointer; font-family: inherit; }
        .lang-chip.active { border-color: var(--border-teal); color: var(--color-teal); background: rgba(20,184,166,0.08); }
        .success-bar { background: rgba(16,185,129,0.08); border: 1px solid rgba(16,185,129,0.25); border-radius: 10px; padding: 10px 14px; color: #10b981; font-size: 0.85rem; }
        .muted { color: var(--color-text-muted); }
      `}</style>
    </div>
  );
}
