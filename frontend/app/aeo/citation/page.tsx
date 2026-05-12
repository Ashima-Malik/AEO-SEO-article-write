"use client";
import { useState } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
import { TopBar } from "@/components/layout/TopBar";
import { PageLoader } from "@/components/ui/LoadingSpinner";
import { api } from "@/lib/api";
import { Target, CheckCircle, XCircle, ExternalLink } from "lucide-react";

const card = { background: "#FFFFFF", border: "1.5px solid #E2E8F0", borderRadius: "16px", boxShadow: "0 1px 3px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.04)" };

export default function CitationTrackerPage() {
  const [url, setUrl]           = useState("");
  const [keywords, setKeywords] = useState("");
  const [loading, setLoading]   = useState(false);
  const [result, setResult]     = useState<any>(null);
  const [error, setError]       = useState("");

  async function handleAudit() {
    const kws = keywords.split(",").map(k => k.trim()).filter(Boolean);
    if (!url || kws.length === 0) { setError("Enter your URL and at least one keyword."); return; }
    setLoading(true); setError(""); setResult(null);
    try { setResult(await api.aeoCitationAudit(url, kws)); }
    catch (e: any) { setError(e.message || "Citation audit failed."); }
    finally { setLoading(false); }
  }

  const rate = result ? Math.round((result.citation_rate ?? 0) * 100) : 0;
  const rateColor = rate >= 60 ? "#10B981" : rate >= 40 ? "#F59E0B" : "#EF4444";

  if (loading) return <AppLayout><TopBar title="Citation Tracker" /><PageLoader message="Querying ChatGPT for each keyword via live web search..." /></AppLayout>;

  return (
    <AppLayout>
      <TopBar title="AI Citation Tracker" subtitle="See if ChatGPT cites your domain when users search your target keywords" />
      <div style={{ padding: "28px 32px", maxWidth: "800px" }}>

        <div style={{ ...card, padding: "26px", marginBottom: "24px" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
            <div>
              <label style={{ display: "block", fontSize: "16px", fontWeight: 600, color: "#334155", marginBottom: "8px" }}>Your Domain / URL</label>
              <input type="url" value={url} onChange={e => setUrl(e.target.value)} placeholder="https://yoursite.com" className="rr-input" />
            </div>
            <div>
              <label style={{ display: "block", fontSize: "16px", fontWeight: 600, color: "#334155", marginBottom: "8px" }}>
                Target Keywords <span style={{ color: "#94A3B8", fontWeight: 400 }}>(comma-separated, up to 5)</span>
              </label>
              <input value={keywords} onChange={e => setKeywords(e.target.value)} placeholder="e.g. AI product manager, PM skills 2025, AI PM salary" className="rr-input" />
            </div>
            {error && <p style={{ fontSize: "15px", color: "#DC2626" }}>{error}</p>}
            <button onClick={handleAudit} disabled={!url || !keywords} className="btn-primary" style={{ justifyContent: "center", fontSize: "16px", padding: "14px" }}>
              <Target size={18} /> Check ChatGPT Citations
            </button>
          </div>
        </div>

        {result && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>

            {/* Citation rate header */}
            <div style={{ ...card, padding: "32px", textAlign: "center" }}>
              <p style={{ fontSize: "15px", color: "#94A3B8", marginBottom: "10px" }}>ChatGPT Citation Rate</p>
              <div style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 800, fontSize: "72px", color: rateColor, lineHeight: 1 }}>{rate}%</div>
              <p style={{ fontSize: "16px", color: "#64748B", marginTop: "12px" }}>{result.summary}</p>
              <div style={{ display: "flex", justifyContent: "center", gap: "24px", marginTop: "20px" }}>
                <div style={{ textAlign: "center" }}>
                  <p style={{ fontSize: "24px", fontWeight: 800, color: "#10B981" }}>{result.keywords_cited}</p>
                  <p style={{ fontSize: "14px", color: "#94A3B8" }}>Keywords cited</p>
                </div>
                <div style={{ width: "1px", background: "#E2E8F0" }} />
                <div style={{ textAlign: "center" }}>
                  <p style={{ fontSize: "24px", fontWeight: 800, color: "#64748B" }}>{result.keywords_checked}</p>
                  <p style={{ fontSize: "14px", color: "#94A3B8" }}>Total checked</p>
                </div>
              </div>
            </div>

            {/* Per-keyword results */}
            <div style={{ ...card, overflow: "hidden" }}>
              <div style={{ padding: "16px 20px", borderBottom: "1px solid #E2E8F0" }}>
                <p style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 700, fontSize: "17px" }}>Per-Keyword Results</p>
              </div>
              {result.per_keyword?.map((kw: any, i: number) => (
                <div key={i} style={{ padding: "16px 20px", borderBottom: "1px solid #F8FAFC" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "10px" }}>
                    {kw.cited
                      ? <CheckCircle size={18} color="#10B981" />
                      : <XCircle size={18} color="#EF4444" />}
                    <p style={{ fontSize: "16px", fontWeight: 600, color: "#0F172A", flex: 1 }}>{kw.keyword}</p>
                    <span style={{ fontSize: "13px", fontWeight: 700, padding: "4px 12px", borderRadius: "100px",
                      background: kw.cited ? "#F0FDF4" : "#FEF2F2",
                      color: kw.cited ? "#10B981" : "#EF4444" }}>
                      {kw.cited ? "Cited ✓" : "Not cited"}
                    </span>
                  </div>

                  {kw.cited_sources?.length > 0 && (
                    <div style={{ marginLeft: "30px" }}>
                      <p style={{ fontSize: "12px", fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "8px" }}>
                        {kw.cited ? "Top cited sources" : "Who ChatGPT cites instead"}
                      </p>
                      <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                        {kw.cited_sources.slice(0, 4).map((src: any, j: number) => (
                          <a key={j} href={src.url} target="_blank" rel="noopener noreferrer"
                            style={{ display: "flex", alignItems: "center", gap: "7px", fontSize: "14px", color: "#7C3AED", textDecoration: "none" }}>
                            <ExternalLink size={12} />
                            <span style={{ fontWeight: 600 }}>{src.domain}</span>
                            {src.title && <span style={{ color: "#94A3B8" }}>— {src.title.slice(0, 50)}</span>}
                          </a>
                        ))}
                      </div>
                    </div>
                  )}

                  {kw.answer_snippet && (
                    <div style={{ marginTop: "10px", marginLeft: "30px", padding: "10px 14px", background: "#F8FAFC", borderRadius: "8px", borderLeft: "3px solid #E2E8F0" }}>
                      <p style={{ fontSize: "14px", color: "#64748B", fontStyle: "italic" }}>{kw.answer_snippet.slice(0, 300)}…</p>
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Top competing domains */}
            {result.top_competing_domains?.length > 0 && (
              <div style={{ ...card, padding: "22px" }}>
                <p style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 700, fontSize: "17px", marginBottom: "14px" }}>Top Competing Domains</p>
                {result.top_competing_domains.map((d: any, i: number) => (
                  <div key={i} style={{ display: "flex", alignItems: "center", gap: "12px", padding: "10px 0", borderBottom: "1px solid #F8FAFC" }}>
                    <span style={{ fontSize: "13px", fontWeight: 700, color: "#94A3B8", width: "22px" }}>#{i + 1}</span>
                    <span style={{ fontSize: "15px", fontWeight: 600, color: "#0F172A", flex: 1 }}>{d.domain}</span>
                    <span style={{ fontSize: "14px", color: "#64748B" }}>cited {d.cited_count}×</span>
                  </div>
                ))}
              </div>
            )}

            {result.usage && (
              <p style={{ fontSize: "13px", color: "#94A3B8", textAlign: "center" }}>
                {result.usage.input_tokens + result.usage.output_tokens} tokens · ${result.usage.cost_usd} cost
              </p>
            )}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
