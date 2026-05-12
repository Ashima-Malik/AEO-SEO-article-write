"use client";
import { useState } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
import { TopBar } from "@/components/layout/TopBar";
import { PageLoader } from "@/components/ui/LoadingSpinner";
import { api } from "@/lib/api";
import { Hash, Search, FileText } from "lucide-react";

const INTENT_COLORS: Record<string, { bg: string; color: string }> = {
  informational: { bg: "#EFF6FF", color: "#3B82F6" },
  transactional:  { bg: "#F0FDF4", color: "#10B981" },
  navigational:   { bg: "#FFF7ED", color: "#F59E0B" },
  long_tail:      { bg: "#F5F3FF", color: "#7C3AED" },
};

export default function KeywordsPage() {
  const [topic, setTopic] = useState("");
  const [loadingCluster, setLoadingCluster] = useState(false);
  const [loadingBrief, setLoadingBrief]     = useState(false);
  const [clusters, setClusters] = useState<any>(null);
  const [brief, setBrief]       = useState<any>(null);
  const [error, setError]       = useState("");

  const card = { background: "#FFFFFF", border: "1.5px solid #E2E8F0", borderRadius: "16px", boxShadow: "0 1px 3px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.04)" };

  async function handleCluster() {
    if (!topic) return;
    setLoadingCluster(true); setError(""); setClusters(null); setBrief(null);
    try { setClusters(await api.clusterKeywords(topic)); }
    catch (e: any) { setError(e.message || "Failed."); }
    finally { setLoadingCluster(false); }
  }

  async function handleBrief() {
    if (!topic) return;
    setLoadingBrief(true); setError(""); setBrief(null); setClusters(null);
    try { setBrief(await api.generateBrief(topic)); }
    catch (e: any) { setError(e.message || "Failed."); }
    finally { setLoadingBrief(false); }
  }

  if (loadingCluster) return <AppLayout><TopBar title="Keywords" /><PageLoader message="Clustering keywords by intent..." /></AppLayout>;
  if (loadingBrief)   return <AppLayout><TopBar title="Keywords" /><PageLoader message="Generating content brief..." /></AppLayout>;

  return (
    <AppLayout>
      <TopBar title="Keywords" subtitle="Cluster keywords by intent or generate a content brief" />
      <div style={{ padding: "28px 32px", maxWidth: "840px" }}>

        <div style={{ ...card, padding: "24px", marginBottom: "24px" }}>
          <label style={{ display: "block", fontSize: "16px", fontWeight: 600, color: "#334155", marginBottom: "10px" }}>Topic or Keyword</label>
          <div style={{ display: "flex", gap: "10px" }}>
            <div style={{ flex: 1, position: "relative" }}>
              <Hash size={18} style={{ position: "absolute", left: "14px", top: "50%", transform: "translateY(-50%)", color: "#94A3B8" }} />
              <input
                value={topic} onChange={e => setTopic(e.target.value)}
                placeholder="e.g. AI product manager"
                className="rr-input" style={{ paddingLeft: "42px" }}
              />
            </div>
            <button onClick={handleCluster} disabled={!topic} className="btn-primary" style={{ whiteSpace: "nowrap", padding: "11px 20px" }}>
              <Search size={17} /> Cluster
            </button>
            <button onClick={handleBrief} disabled={!topic} className="btn-secondary" style={{ whiteSpace: "nowrap", padding: "11px 20px" }}>
              <FileText size={17} /> Brief
            </button>
          </div>
          {error && <p style={{ marginTop: "10px", fontSize: "15px", color: "#DC2626" }}>{error}</p>}
        </div>

        {clusters && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div style={{ ...card, padding: "20px" }}>
              <p style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 700, fontSize: "17px", marginBottom: "8px" }}>Primary Keyword</p>
              <span style={{ background: "#F5F3FF", color: "#7C3AED", padding: "5px 16px", borderRadius: "100px", fontSize: "16px", fontWeight: 600 }}>
                {clusters.primary_keyword}
              </span>
            </div>
            {clusters.clusters?.map((cluster: any) => {
              const style = INTENT_COLORS[cluster.intent] || { bg: "#F8FAFC", color: "#64748B" };
              return (
                <div key={cluster.intent} style={{ ...card, overflow: "hidden" }}>
                  <div style={{ padding: "14px 20px", borderBottom: "1px solid #E2E8F0", display: "flex", alignItems: "center", gap: "12px" }}>
                    <span style={{ fontSize: "13px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", background: style.bg, color: style.color, padding: "4px 12px", borderRadius: "100px" }}>
                      {cluster.intent}
                    </span>
                    <p style={{ fontSize: "15px", color: "#64748B" }}>{cluster.rationale}</p>
                  </div>
                  <div style={{ padding: "16px 20px", display: "flex", flexWrap: "wrap", gap: "8px" }}>
                    {cluster.keywords?.map((kw: string) => (
                      <span key={kw} style={{ fontSize: "15px", background: "#F8FAFC", border: "1px solid #E2E8F0", borderRadius: "8px", padding: "5px 14px", color: "#334155" }}>{kw}</span>
                    ))}
                  </div>
                </div>
              );
            })}
            {clusters.paa_questions?.length > 0 && (
              <div style={{ ...card, padding: "20px" }}>
                <p style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 700, fontSize: "17px", marginBottom: "14px" }}>People Also Ask</p>
                {clusters.paa_questions.map((q: string, i: number) => (
                  <div key={i} style={{ fontSize: "15px", color: "#475569", padding: "9px 0", borderBottom: "1px solid #F8FAFC" }}>
                    {i + 1}. {q}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {brief && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div style={{ ...card, padding: "22px" }}>
              <p style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 800, fontSize: "20px", color: "#0F172A", marginBottom: "10px" }}>{brief.suggested_title}</p>
              <p style={{ fontSize: "16px", color: "#64748B", marginBottom: "14px" }}>{brief.content_angle}</p>
              <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
                {[
                  { label: "Target Words", value: brief.target_word_count },
                  { label: "Reading Level", value: brief.target_reading_level },
                  { label: "URL Slug", value: brief.suggested_url_slug },
                ].map(item => (
                  <span key={item.label} style={{ fontSize: "14px", background: "#F5F3FF", color: "#7C3AED", padding: "5px 14px", borderRadius: "8px", fontWeight: 500 }}>
                    {item.label}: {item.value}
                  </span>
                ))}
              </div>
            </div>
            {brief.sections?.length > 0 && (
              <div style={{ ...card, overflow: "hidden" }}>
                <div style={{ padding: "16px 20px", borderBottom: "1px solid #E2E8F0" }}>
                  <p style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 700, fontSize: "17px" }}>Outline</p>
                </div>
                {brief.sections.map((s: any, i: number) => (
                  <div key={i} style={{ padding: "16px 20px", borderBottom: "1px solid #F8FAFC" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                      <p style={{ fontSize: "16px", fontWeight: 600, color: "#0F172A" }}>{s.heading}</p>
                      <span style={{ fontSize: "14px", color: "#94A3B8" }}>{s.target_word_count} words</span>
                    </div>
                    {s.key_points?.map((pt: string, j: number) => (
                      <p key={j} style={{ fontSize: "15px", color: "#64748B", marginLeft: "14px", marginBottom: "4px" }}>• {pt}</p>
                    ))}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
