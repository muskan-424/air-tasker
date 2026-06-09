"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { betaAPI } from "@/lib/api";

const DEFAULT_CONFIG = {
  beta_enabled: false,
  city_label: "",
  categories: [],
  pin_codes: [],
  languages: [],
  feature_flags: {
    ai_chat: true,
    voice_input: true,
    kyc_payout: true,
    razorpay_checkout: true,
    disputes: true,
  },
  feedback_path: "/feedback",
};

const BetaContext = createContext({ config: DEFAULT_CONFIG, loading: true });

export function BetaProvider({ children }) {
  const [config, setConfig] = useState(DEFAULT_CONFIG);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    betaAPI
      .getConfig()
      .then(setConfig)
      .catch(() => setConfig(DEFAULT_CONFIG))
      .finally(() => setLoading(false));
  }, []);

  return (
    <BetaContext.Provider value={{ config, loading }}>
      {children}
    </BetaContext.Provider>
  );
}

export function useBeta() {
  return useContext(BetaContext);
}

export function isNavEnabled(href, featureFlags) {
  const flags = featureFlags || DEFAULT_CONFIG.feature_flags;
  if (href === "/chat") return flags.ai_chat !== false;
  if (href === "/kyc") return flags.kyc_payout !== false;
  if (href === "/payments") return flags.razorpay_checkout !== false;
  if (href === "/disputes") return flags.disputes !== false;
  return true;
}
