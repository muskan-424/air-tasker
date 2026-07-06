"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { authAPI, accountAPI } from "@/lib/api";

const AuthContext = createContext(null);

/**
 * AuthProvider — wraps the entire app and provides auth state.
 * Usage: const { user, token, login, register, logout } = useAuth();
 */
export function AuthProvider({ children }) {
  const [token, setToken] = useState(null);
  const [user, setUser] = useState(null);   // { email, role, id }
  const [loading, setLoading] = useState(true);

  // Rehydrate from localStorage on mount
  useEffect(() => {
    try {
      const storedToken = localStorage.getItem("vayutask_token");
      const storedUser = localStorage.getItem("vayutask_user");
      if (storedToken) {
        setToken(storedToken);
        setUser(storedUser ? JSON.parse(storedUser) : null);
      }
    } catch (_) {}
    setLoading(false);
  }, []);

  /**
   * Login with email + password.
   * Calls POST /api/auth/login, stores token, decodes minimal user info.
   */
  const login = async (email, password) => {
    const data = await authAPI.login(email, password);
    await _storeAuth(data.access_token, { email });
    return data;
  };

  /**
   * Register a new account.
   * Calls POST /api/auth/register, then auto-logs in.
   */
  const register = async (email, password, role = "POSTER") => {
    const data = await authAPI.register(email, password, role);
    await _storeAuth(data.access_token, { email, role });
    return data;
  };

  const logout = () => {
    localStorage.removeItem("vayutask_token");
    localStorage.removeItem("vayutask_user");
    setToken(null);
    setUser(null);
    window.location.href = "/login";
  };

  const setUserVerified = (verified = true) => {
    setUser((prev) => {
      if (!prev) return prev;
      const next = {
        ...prev,
        email_verified: verified,
        email_verified_at: verified ? new Date().toISOString() : null,
      };
      localStorage.setItem("vayutask_user", JSON.stringify(next));
      return next;
    });
  };

  const _storeAuth = async (accessToken, userInfo) => {
    let decoded = userInfo;
    try {
      const payload = JSON.parse(atob(accessToken.split(".")[1]));
      decoded = { ...userInfo, id: payload.sub };
    } catch (_) {}

    localStorage.setItem("vayutask_token", accessToken);
    setToken(accessToken);

    try {
      const me = await accountAPI.me();
      decoded = {
        ...decoded,
        id: me.id,
        email: me.email,
        role: me.role,
        email_verified_at: me.email_verified_at,
        email_verified: Boolean(me.email_verified_at),
      };
    } catch (_) {}

    localStorage.setItem("vayutask_user", JSON.stringify(decoded));
    setUser(decoded);
  };

  const isLoggedIn = Boolean(token);

  return (
    <AuthContext.Provider value={{ user, token, loading, isLoggedIn, login, register, logout, setUserVerified }}>
      {children}
    </AuthContext.Provider>
  );
}

/** Hook to consume auth context */
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
