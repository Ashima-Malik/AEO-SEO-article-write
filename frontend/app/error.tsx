"use client";
import { useEffect } from "react";

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => { console.error(error); }, [error]);
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100vh", gap: "16px", fontFamily: "system-ui, sans-serif" }}>
      <p style={{ fontSize: "16px", color: "#334155", fontWeight: 600 }}>Something went wrong</p>
      <p style={{ fontSize: "13px", color: "#94A3B8" }}>{error.message}</p>
      <button onClick={reset} style={{ padding: "8px 20px", background: "#7C3AED", color: "white", border: "none", borderRadius: "8px", cursor: "pointer", fontSize: "14px" }}>
        Try again
      </button>
    </div>
  );
}
