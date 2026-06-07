"use client";

import { useEffect } from "react";
import { validatePublicEnv } from "@/lib/env";

/** Runs one-time public env checks in development. */
export default function EnvGuard() {
  useEffect(() => {
    validatePublicEnv();
  }, []);
  return null;
}
