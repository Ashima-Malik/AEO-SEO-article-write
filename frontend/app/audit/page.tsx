"use client";
import { useState } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
import { TopBar } from "@/components/layout/TopBar";
import { PageLoader } from "@/components/ui/LoadingSpinner";
import { api } from "@/lib/api";
import { Globe, Search, CheckCircle, XCircle, AlertCircle } from "lucide-react";
import { scoreColor } from "@/lib/utils";

export default function AuditPage() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");

  async function handleAudit() {
    if (!url) return;
    setLoading(true); setError(""); setResult(null);
    try {
      const data = await api.runAudit(url);
      setResult(data);
    } catch (err: any) {
      setError(err.message || "Audit failed.");
    } finally { setLoading(false); }
  }

  const card = { background: "#FFFFFF", border: "1.5px solid #E2E8F0", borderRadius: "16px", boxShadow: "0 1px 3px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.04)" };

  if (loading) return <AppLayout><TopBar title="Site Audit" /><PageLoader message="Running 20-point technical audit..." /></AppLayout>;

  return (
    <AppLayout>
      <TopBar title="Site Audit" subtitle="20-point technical SEO check" />
      <div style={{ padding: "28px 32px", maxWidth: "760px" }}>
        <div style={{ ...card, padding: "24px", marginBottom: "24px" }}>
          <label style={{ display: "block", fontSize: "16px", fontWeight: 600, color: "#334155", marginBottom: "10px" }}>Website URL</label>
          <div style={{ display: "flex", gap: "10px" }}>
            <div style={{ flex: 1, position: "relative" }}>
              <Globe size={18} style={{ position: "absolute", left: "14px", top: "50%", transform: "translateY(-50%)", color: "#94A3B8" }} />
              <input
                type="url" value={url} onChange={e => setUrl(e.target.value)}
                onKeyDown={e => e.key === "Enter" && handleAudit()}
                placeholder="https://yoursite.com"
                className="rr-input" style={{ paddingLeft: "42px" }}
              />
            </div>
            <button onClick={handleAudit} disabled={!url} className="btn-primary" style={{ padding: "11px 22px", whiteSpace: "nowrap" }}>
              <Search size={17} /> Run Audit
            </button>
          </div>
          {error && <p style={{ marginTop: "10px", fontSize: "15px", color: "#DC2626" }}>{error}</p>}
        </div>

        {result && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {/* Score */}
            <div style={{ ...card, padding: "28px", textAlign: "center" }}>
              <p style={{ fontSize: "15px", color: "#94A3B8", marginBottom: "8px" }}>Audit Score</p>
              <span style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 800, fontSize: "60px", color: scoreColor(result.overall_score || 0) }}>
                {result.overall_score}
              </span>
              <span style={{ fontSize: "26px", color: "#94A3B8" }}>/100</span>
              {result.recommendations?.length > 0 && (
                <div style={{ marginTop: "20px", textAlign: "left" }}>
                  <p style={{ fontSize: "16px", fontWeight: 600, color: "#334155", marginBottom: "12px" }}>Top Recommendations</p>
                  {result.recommendations.map((r: string, i: number) => (
                    <div key={i} style={{ display: "flex", gap: "10px", marginBottom: "10px", alignItems: "flex-start" }}>
                      <span style={{ fontSize: "15px", fontWeight: 700, color: "#7C3AED", flexShrink: 0 }}>{i + 1}.</span>
                      <span style={{ fontSize: "15px", color: "#475569" }}>{r}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Sections */}
            {result.sections?.map((section: any) => (
              <div key={section.name} style={{ ...card, overflow: "hidden" }}>
                <div style={{ padding: "16px 20px", borderBottom: "1px solid #E2E8F0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <p style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 700, fontSize: "17px", color: "#0F172A" }}>{section.name}</p>
                  <span style={{ fontSize: "15px", fontWeight: 600, color: scoreColor(section.score || 0) }}>{section.score}%</span>
                </div>
                {section.checks?.map((check: any) => (
                  <div key={check.name} style={{ padding: "13px 20px", borderBottom: "1px solid #F8FAFC", display: "flex", alignItems: "flex-start", gap: "12px" }}>
                    {check.passed
                      ? <CheckCircle size={17} color="#10B981" style={{ flexShrink: 0, marginTop: "2px" }} />
                      : check.severity === "critical"
                        ? <XCircle size={17} color="#EF4444" style={{ flexShrink: 0, marginTop: "2px" }} />
                        : <AlertCircle size={17} color="#F59E0B" style={{ flexShrink: 0, marginTop: "2px" }} />}
                    <div style={{ flex: 1 }}>
                      <p style={{ fontSize: "15px", fontWeight: 500, color: "#0F172A" }}>{check.name}</p>
                      {check.value && <p style={{ fontSize: "14px", color: "#94A3B8", marginTop: "3px" }}>{check.value}</p>}
                      {!check.passed && check.recommendation && (
                        <p style={{ fontSize: "14px", color: "#7C3AED", marginTop: "4px" }}>→ {check.recommendation}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
