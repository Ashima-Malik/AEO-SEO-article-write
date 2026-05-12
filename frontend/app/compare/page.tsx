"use client";
import { useState } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
import { TopBar } from "@/components/layout/TopBar";
import { PageLoader } from "@/components/ui/LoadingSpinner";
import { ScoreRing } from "@/components/ui/ScoreRing";
import { api } from "@/lib/api";
import { BarChart2, ArrowRight, TrendingUp, TrendingDown } from "lucide-react";

export default function ComparePage() {
  const [yourUrl, setYourUrl]   = useState("");
  const [compUrl, setCompUrl]   = useState("");
  const [loading, setLoading]   = useState(false);
  const [result, setResult]     = useState<any>(null);
  const [error, setError]       = useState("");

  const card = { background: "#FFFFFF", border: "1.5px solid #E2E8F0", borderRadius: "16px", boxShadow: "0 1px 3px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.04)" };

  async function handleCompare() {
    if (!yourUrl || !compUrl) return;
    setLoading(true); setError(""); setResult(null);
    try { setResult(await api.compareUrls(yourUrl, compUrl)); }
    catch (e: any) { setError(e.message || "Compare failed."); }
    finally { setLoading(false); }
  }

  if (loading) return <AppLayout><TopBar title="Compare" /><PageLoader message="Analyzing both pages with 5-agent pipeline..." /></AppLayout>;

  return (
    <AppLayout>
      <TopBar title="Competitor Compare" subtitle="Head-to-head SEO analysis with prioritized next steps" />
      <div style={{ padding: "28px 32px", maxWidth: "860px" }}>

        <div style={{ ...card, padding: "24px", marginBottom: "24px" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr auto 1fr", gap: "14px", alignItems: "center", marginBottom: "18px" }}>
            <div>
              <label style={{ display: "block", fontSize: "16px", fontWeight: 600, color: "#334155", marginBottom: "8px" }}>Your URL</label>
              <input type="url" value={yourUrl} onChange={e => setYourUrl(e.target.value)} placeholder="https://yoursite.com/page" className="rr-input" />
            </div>
            <div style={{ display: "flex", alignItems: "center", paddingTop: "26px" }}>
              <ArrowRight size={22} color="#94A3B8" />
            </div>
            <div>
              <label style={{ display: "block", fontSize: "16px", fontWeight: 600, color: "#334155", marginBottom: "8px" }}>Competitor URL</label>
              <input type="url" value={compUrl} onChange={e => setCompUrl(e.target.value)} placeholder="https://competitor.com/page" className="rr-input" />
            </div>
          </div>
          {error && <p style={{ fontSize: "15px", color: "#DC2626", marginBottom: "12px" }}>{error}</p>}
          <button onClick={handleCompare} disabled={!yourUrl || !compUrl} className="btn-primary" style={{ width: "100%", justifyContent: "center", fontSize: "16px", padding: "14px" }}>
            <BarChart2 size={18} /> Compare Pages
          </button>
        </div>

        {result && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {/* Score row */}
            {result.your_score && result.competitor_score && (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                {[
                  { label: "Your Score", data: result.your_score },
                  { label: "Competitor Score", data: result.competitor_score },
                ].map(s => (
                  <div key={s.label} style={{ ...card, padding: "28px", textAlign: "center" }}>
                    <p style={{ fontSize: "15px", color: "#94A3B8", marginBottom: "14px" }}>{s.label}</p>
                    <ScoreRing score={s.data.overall} size={96} />
                    <p style={{ fontSize: "16px", fontWeight: 600, color: "#0F172A", marginTop: "12px" }}>{s.data.rating}</p>
                  </div>
                ))}
              </div>
            )}

            {/* Executive summary */}
            {result.insights?.executive_summary && (
              <div style={{ ...card, padding: "22px", background: "#F5F3FF", borderColor: "#DDD6FE" }}>
                <p style={{ fontSize: "16px", color: "#5B21B6", lineHeight: 1.7 }}>{result.insights.executive_summary}</p>
              </div>
            )}

            {/* Your strengths / weaknesses */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
              {[
                { title: "Your Strengths", items: result.insights?.your_strengths, icon: TrendingUp, iconColor: "#10B981", bg: "#F0FDF4", border: "#BBF7D0" },
                { title: "Your Weaknesses", items: result.insights?.your_weaknesses, icon: TrendingDown, iconColor: "#EF4444", bg: "#FEF2F2", border: "#FECACA" },
              ].map(col => (
                <div key={col.title} style={{ ...card, padding: "20px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "9px", marginBottom: "14px" }}>
                    <col.icon size={18} color={col.iconColor} />
                    <p style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 700, fontSize: "16px" }}>{col.title}</p>
                  </div>
                  {col.items?.map((item: string, i: number) => (
                    <p key={i} style={{ fontSize: "15px", color: "#475569", padding: "7px 0", borderBottom: "1px solid #F8FAFC" }}>• {item}</p>
                  ))}
                </div>
              ))}
            </div>

            {/* Next steps */}
            {result.insights?.next_steps?.length > 0 && (
              <div style={{ ...card, overflow: "hidden" }}>
                <div style={{ padding: "16px 20px", borderBottom: "1px solid #E2E8F0" }}>
                  <p style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 700, fontSize: "17px" }}>Prioritized Next Steps</p>
                </div>
                {result.insights.next_steps.map((step: any, i: number) => {
                  const priorityColor = step.priority === "critical" ? "#EF4444" : step.priority === "high" ? "#F59E0B" : "#3B82F6";
                  const priorityBg   = step.priority === "critical" ? "#FEF2F2" : step.priority === "high" ? "#FFFBEB" : "#EFF6FF";
                  return (
                    <div key={i} style={{ padding: "16px 20px", borderBottom: "1px solid #F8FAFC", display: "flex", gap: "14px", alignItems: "flex-start" }}>
                      <span style={{ fontSize: "13px", fontWeight: 700, textTransform: "uppercase", background: priorityBg, color: priorityColor, padding: "4px 12px", borderRadius: "100px", flexShrink: 0, marginTop: "2px" }}>
                        {step.priority}
                      </span>
                      <div>
                        <p style={{ fontSize: "16px", fontWeight: 600, color: "#0F172A", marginBottom: "4px" }}>{step.action}</p>
                        <p style={{ fontSize: "15px", color: "#64748B" }}>{step.reason}</p>
                        {step.estimated_impact && (
                          <span style={{ fontSize: "14px", color: "#7C3AED", fontWeight: 600 }}>{step.estimated_impact}</span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
