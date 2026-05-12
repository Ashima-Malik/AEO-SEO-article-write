"use client";
import { useState } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
import { TopBar } from "@/components/layout/TopBar";
import { PageLoader } from "@/components/ui/LoadingSpinner";
import { api } from "@/lib/api";
import { Bot, AlertCircle, CheckCircle } from "lucide-react";

const card = { background: "#FFFFFF", border: "1.5px solid #E2E8F0", borderRadius: "16px", boxShadow: "0 1px 3px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.04)" };

function ScoreBadge({ score }: { score: number }) {
  const color = score >= 80 ? "#10B981" : score >= 65 ? "#3B82F6" : score >= 50 ? "#F59E0B" : "#EF4444";
  const label = score >= 80 ? "AI-Ready" : score >= 65 ? "Strong" : score >= 50 ? "Needs Work" : "Not Optimized";
  return (
    <div style={{ textAlign: "center" }}>
      <div style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 800, fontSize: "68px", color, lineHeight: 1 }}>{score}</div>
      <div style={{ fontSize: "15px", fontWeight: 600, color, marginTop: "8px" }}>{label}</div>
    </div>
  );
}

function CriterionRow({ name, data }: { name: string; data: any }) {
  const score = data?.score ?? 0;
  const color = score >= 80 ? "#10B981" : score >= 65 ? "#3B82F6" : score >= 50 ? "#F59E0B" : "#EF4444";
  const label = name.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
  return (
    <div style={{ padding: "14px 20px", borderBottom: "1px solid #F8FAFC" }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "7px" }}>
        <span style={{ fontSize: "15px", fontWeight: 600, color: "#0F172A" }}>{label}</span>
        <span style={{ fontSize: "15px", fontWeight: 700, color }}>{score}</span>
      </div>
      <div style={{ height: "5px", background: "#F1F5F9", borderRadius: "100px", marginBottom: "7px" }}>
        <div style={{ height: "100%", width: `${score}%`, background: color, borderRadius: "100px", transition: "width 0.6s ease" }} />
      </div>
      {data?.rationale && <p style={{ fontSize: "14px", color: "#64748B" }}>{data.rationale}</p>}
      {data?.improvements?.map((imp: string, i: number) => (
        <p key={i} style={{ fontSize: "14px", color: "#7C3AED", marginTop: "4px" }}>→ {imp}</p>
      ))}
    </div>
  );
}

export default function AEOPage() {
  const [tab, setTab]           = useState<"url" | "text">("url");
  const [url, setUrl]           = useState("");
  const [content, setContent]   = useState("");
  const [topic, setTopic]       = useState("");
  const [keywords, setKeywords] = useState("");
  const [loading, setLoading]   = useState(false);
  const [result, setResult]     = useState<any>(null);
  const [error, setError]       = useState("");

  async function handleAudit() {
    const kws = keywords.split(",").map(k => k.trim()).filter(Boolean);
    const text = tab === "text" ? content : "";
    if (!text && !url) { setError("Please enter a URL or paste content."); return; }
    if (!topic) { setError("Please enter a topic."); return; }
    setLoading(true); setError(""); setResult(null);
    try {
      const data = await api.aeoFullAudit(text || `[URL: ${url}]`, topic, kws.length ? kws : undefined, url || undefined);
      setResult(data);
    } catch (e: any) { setError(e.message || "AEO audit failed."); }
    finally { setLoading(false); }
  }

  if (loading) return <AppLayout><TopBar title="AEO Audit" /><PageLoader message="Running 5-agent AEO analysis..." /></AppLayout>;

  return (
    <AppLayout>
      <TopBar title="AEO Full Audit" subtitle="Answer Engine Optimization — score, entities, facts, and citable claims" />
      <div style={{ padding: "28px 32px", maxWidth: "900px" }}>

        {/* Input card */}
        <div style={{ ...card, padding: "26px", marginBottom: "24px" }}>
          <div style={{ display: "flex", gap: "8px", marginBottom: "22px" }}>
            {(["url", "text"] as const).map(t => (
              <button key={t} onClick={() => setTab(t)}
                style={{ padding: "9px 22px", borderRadius: "8px", border: "1.5px solid", fontSize: "15px", fontWeight: 600, cursor: "pointer",
                  background: tab === t ? "#7C3AED" : "white",
                  color: tab === t ? "white" : "#64748B",
                  borderColor: tab === t ? "#7C3AED" : "#E2E8F0" }}>
                {t === "url" ? "URL" : "Paste Text"}
              </button>
            ))}
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {tab === "url" ? (
              <div>
                <label style={{ display: "block", fontSize: "16px", fontWeight: 600, color: "#334155", marginBottom: "8px" }}>Page URL</label>
                <input type="url" value={url} onChange={e => setUrl(e.target.value)} placeholder="https://yoursite.com/article" className="rr-input" />
              </div>
            ) : (
              <div>
                <label style={{ display: "block", fontSize: "16px", fontWeight: 600, color: "#334155", marginBottom: "8px" }}>Paste Content</label>
                <textarea value={content} onChange={e => setContent(e.target.value)} rows={6} placeholder="Paste your article or webpage content here..." className="rr-input" style={{ resize: "vertical" }} />
              </div>
            )}

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" }}>
              <div>
                <label style={{ display: "block", fontSize: "16px", fontWeight: 600, color: "#334155", marginBottom: "8px" }}>Topic / Primary Keyword</label>
                <input value={topic} onChange={e => setTopic(e.target.value)} placeholder="e.g. AI product manager" className="rr-input" />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "16px", fontWeight: 600, color: "#334155", marginBottom: "8px" }}>
                  Target Keywords <span style={{ color: "#94A3B8", fontWeight: 400 }}>(comma-separated, optional)</span>
                </label>
                <input value={keywords} onChange={e => setKeywords(e.target.value)} placeholder="e.g. AI PM, product manager skills" className="rr-input" />
              </div>
            </div>

            {error && <p style={{ fontSize: "15px", color: "#DC2626" }}>{error}</p>}

            <button onClick={handleAudit} disabled={(!url && !content) || !topic} className="btn-primary" style={{ justifyContent: "center", fontSize: "16px", padding: "14px" }}>
              <Bot size={18} /> Run AEO Full Audit
            </button>
          </div>
        </div>

        {result && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>

            {/* AEO Score */}
            {result.aeo_score && (
              <div style={{ ...card, padding: "30px", display: "grid", gridTemplateColumns: "auto 1fr", gap: "36px", alignItems: "start" }}>
                <div>
                  <ScoreBadge score={result.aeo_score.overall ?? 0} />
                  <p style={{ fontSize: "14px", color: "#94A3B8", textAlign: "center", marginTop: "8px" }}>AEO Score</p>
                  {result.aeo_score.ai_citation_likelihood && (
                    <div style={{ marginTop: "14px", textAlign: "center" }}>
                      <span style={{ fontSize: "14px", fontWeight: 700, padding: "5px 14px", borderRadius: "100px",
                        background: result.aeo_score.ai_citation_likelihood === "High" ? "#F0FDF4" : result.aeo_score.ai_citation_likelihood === "Medium" ? "#FFFBEB" : "#FEF2F2",
                        color: result.aeo_score.ai_citation_likelihood === "High" ? "#10B981" : result.aeo_score.ai_citation_likelihood === "Medium" ? "#F59E0B" : "#EF4444" }}>
                        {result.aeo_score.ai_citation_likelihood} Citation Likelihood
                      </span>
                    </div>
                  )}
                </div>
                <div>
                  {result.aeo_score.top_wins?.length > 0 && (
                    <div style={{ marginBottom: "14px" }}>
                      <p style={{ fontSize: "13px", fontWeight: 700, color: "#10B981", marginBottom: "8px", textTransform: "uppercase", letterSpacing: "0.05em" }}>What's Working</p>
                      {result.aeo_score.top_wins.map((w: string, i: number) => (
                        <div key={i} style={{ display: "flex", gap: "9px", marginBottom: "6px" }}>
                          <CheckCircle size={15} color="#10B981" style={{ flexShrink: 0, marginTop: "2px" }} />
                          <p style={{ fontSize: "15px", color: "#475569" }}>{w}</p>
                        </div>
                      ))}
                    </div>
                  )}
                  {result.aeo_score.critical_gaps?.length > 0 && (
                    <div>
                      <p style={{ fontSize: "13px", fontWeight: 700, color: "#EF4444", marginBottom: "8px", textTransform: "uppercase", letterSpacing: "0.05em" }}>Critical Gaps</p>
                      {result.aeo_score.critical_gaps.map((g: string, i: number) => (
                        <div key={i} style={{ display: "flex", gap: "9px", marginBottom: "6px" }}>
                          <AlertCircle size={15} color="#EF4444" style={{ flexShrink: 0, marginTop: "2px" }} />
                          <p style={{ fontSize: "15px", color: "#475569" }}>{g}</p>
                        </div>
                      ))}
                    </div>
                  )}
                  {result.aeo_score.recommended_schema_types?.length > 0 && (
                    <div style={{ marginTop: "14px", display: "flex", gap: "8px", flexWrap: "wrap" }}>
                      {result.aeo_score.recommended_schema_types.map((s: string, i: number) => (
                        <span key={i} style={{ fontSize: "14px", background: "#F5F3FF", color: "#7C3AED", padding: "4px 12px", borderRadius: "100px", fontWeight: 600 }}>
                          {s} Schema
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Criteria breakdown */}
            {result.aeo_score?.criteria && Object.keys(result.aeo_score.criteria).length > 0 && (
              <div style={{ ...card, overflow: "hidden" }}>
                <div style={{ padding: "16px 20px", borderBottom: "1px solid #E2E8F0" }}>
                  <p style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 700, fontSize: "17px" }}>AEO Criteria Breakdown</p>
                </div>
                {Object.entries(result.aeo_score.criteria).map(([k, v]: [string, any]) => (
                  <CriterionRow key={k} name={k} data={v} />
                ))}
              </div>
            )}

            {/* Fact Density */}
            {result.fact_density && (
              <div style={{ ...card, overflow: "hidden" }}>
                <div style={{ padding: "16px 20px", borderBottom: "1px solid #E2E8F0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <p style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 700, fontSize: "17px" }}>Fact Density Audit</p>
                  <span style={{ fontSize: "15px", fontWeight: 700, color: "#7C3AED" }}>{result.fact_density.fact_density_per_500_words} facts / 500 words — {result.fact_density.density_rating}</span>
                </div>
                {result.fact_density.vague_claims_found?.length > 0 && (
                  <div style={{ padding: "16px 20px", borderBottom: "1px solid #F8FAFC" }}>
                    <p style={{ fontSize: "13px", fontWeight: 700, color: "#F59E0B", marginBottom: "10px", textTransform: "uppercase", letterSpacing: "0.05em" }}>Vague Claims to Fix</p>
                    {result.fact_density.vague_claims_found.map((vc: any, i: number) => (
                      <div key={i} style={{ marginBottom: "12px", paddingBottom: "12px", borderBottom: "1px solid #F8FAFC" }}>
                        <p style={{ fontSize: "15px", color: "#EF4444", fontStyle: "italic" }}>"{vc.claim}"</p>
                        <p style={{ fontSize: "14px", color: "#64748B", marginTop: "4px" }}>Issue: {vc.issue}</p>
                        <p style={{ fontSize: "14px", color: "#10B981", marginTop: "4px" }}>Fix: {vc.suggested_fix}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Entity Map */}
            {result.entity_map && (
              <div style={{ ...card, overflow: "hidden" }}>
                <div style={{ padding: "16px 20px", borderBottom: "1px solid #E2E8F0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <p style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 700, fontSize: "17px" }}>Entity Coverage Map</p>
                  <span style={{ fontSize: "15px", fontWeight: 700, color: "#7C3AED" }}>
                    {result.entity_map.entity_coverage_score}/100 — {result.entity_map.coverage_rating}
                  </span>
                </div>
                {result.entity_map.missing_entities?.length > 0 && (
                  <div style={{ padding: "16px 20px" }}>
                    <p style={{ fontSize: "13px", fontWeight: 700, color: "#EF4444", marginBottom: "12px", textTransform: "uppercase", letterSpacing: "0.05em" }}>Missing Entities</p>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "10px" }}>
                      {result.entity_map.missing_entities.map((e: any, i: number) => (
                        <div key={i} style={{ background: "#FEF2F2", border: "1px solid #FECACA", borderRadius: "8px", padding: "8px 14px" }}>
                          <p style={{ fontSize: "14px", fontWeight: 700, color: "#EF4444" }}>{e.name}</p>
                          <p style={{ fontSize: "13px", color: "#94A3B8" }}>{e.type}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Citable Claims */}
            {result.citable_claims?.generated_citable_claims?.length > 0 && (
              <div style={{ ...card, overflow: "hidden" }}>
                <div style={{ padding: "16px 20px", borderBottom: "1px solid #E2E8F0" }}>
                  <p style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 700, fontSize: "17px" }}>Generated Citable Claims</p>
                  <p style={{ fontSize: "15px", color: "#64748B", marginTop: "4px" }}>Drop these directly into your content to boost AI citation likelihood</p>
                </div>
                {result.citable_claims.generated_citable_claims.map((claim: any, i: number) => (
                  <div key={i} style={{ padding: "16px 20px", borderBottom: "1px solid #F8FAFC" }}>
                    <p style={{ fontSize: "15px", color: "#0F172A", fontWeight: 500, marginBottom: "8px" }}>"{claim.claim}"</p>
                    <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                      <span style={{ fontSize: "13px", background: "#F5F3FF", color: "#7C3AED", padding: "3px 10px", borderRadius: "100px", fontWeight: 600 }}>{claim.format}</span>
                      <span style={{ fontSize: "13px", color: "#64748B" }}>Place in: {claim.recommended_placement}</span>
                    </div>
                    <p style={{ fontSize: "14px", color: "#94A3B8", marginTop: "6px" }}>Answers: {claim.question_it_answers}</p>
                  </div>
                ))}
              </div>
            )}

            {/* FAQ Pairs */}
            {result.citable_claims?.faq_pairs?.length > 0 && (
              <div style={{ ...card, overflow: "hidden" }}>
                <div style={{ padding: "16px 20px", borderBottom: "1px solid #E2E8F0" }}>
                  <p style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 700, fontSize: "17px" }}>FAQ Schema Pairs</p>
                  <p style={{ fontSize: "15px", color: "#64748B", marginTop: "4px" }}>Add these to your page with FAQ structured data markup</p>
                </div>
                {result.citable_claims.faq_pairs.map((faq: any, i: number) => (
                  <div key={i} style={{ padding: "16px 20px", borderBottom: "1px solid #F8FAFC" }}>
                    <p style={{ fontSize: "15px", fontWeight: 700, color: "#0F172A", marginBottom: "8px" }}>Q: {faq.question}</p>
                    <p style={{ fontSize: "15px", color: "#475569" }}>{faq.answer}</p>
                  </div>
                ))}
              </div>
            )}

            {/* Total cost */}
            {result.total_usage && (
              <p style={{ fontSize: "14px", color: "#94A3B8", textAlign: "center" }}>
                {result.total_usage.agents_run} agents · {result.total_usage.input_tokens + result.total_usage.output_tokens} tokens · ${result.total_usage.cost_usd} cost
              </p>
            )}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
