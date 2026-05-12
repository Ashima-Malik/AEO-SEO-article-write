"use client";
import { useState } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
import { TopBar } from "@/components/layout/TopBar";
import { PageLoader } from "@/components/ui/LoadingSpinner";
import { api } from "@/lib/api";
import { FileSearch, TrendingUp, TrendingDown, Minus, Calendar, Info } from "lucide-react";

const card = { background: "#FFFFFF", border: "1.5px solid #E2E8F0", borderRadius: "16px", boxShadow: "0 1px 3px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.04)" };

const INTENT_COLORS: Record<string, { bg: string; color: string }> = {
  informational: { bg: "#EFF6FF", color: "#3B82F6" },
  transactional:  { bg: "#F0FDF4", color: "#10B981" },
  navigational:   { bg: "#FFF7ED", color: "#F59E0B" },
  commercial:     { bg: "#F5F3FF", color: "#7C3AED" },
};

const AI_LIKELIHOOD_COLORS: Record<string, { bg: string; color: string }> = {
  High:   { bg: "#F0FDF4", color: "#10B981" },
  Medium: { bg: "#FFFBEB", color: "#F59E0B" },
  Low:    { bg: "#FEF2F2", color: "#EF4444" },
};

function TrendIcon({ direction }: { direction: string }) {
  if (direction === "Rising")   return <TrendingUp size={15} color="#10B981" />;
  if (direction === "Declining") return <TrendingDown size={15} color="#EF4444" />;
  return <Minus size={15} color="#94A3B8" />;
}

export default function QueryPlannerPage() {
  const [topic, setTopic]       = useState("");
  const [keywords, setKeywords] = useState("");
  const [loading, setLoading]   = useState(false);
  const [result, setResult]     = useState<any>(null);
  const [error, setError]       = useState("");

  async function handlePlan() {
    if (!topic.trim()) { setError("Please enter a topic."); return; }
    const kws = keywords.split(",").map(k => k.trim()).filter(Boolean);
    setLoading(true); setError(""); setResult(null);
    try { setResult(await api.aeoQueryPlan(topic, kws.length ? kws : undefined)); }
    catch (e: any) { setError(e.message || "Query plan failed."); }
    finally { setLoading(false); }
  }

  if (loading) return <AppLayout><TopBar title="Query Planner" /><PageLoader message="Fetching trend data + generating AEO query plan..." /></AppLayout>;

  return (
    <AppLayout>
      <TopBar title="AEO Query Planner" subtitle="Identify high-impact queries and build an AI-visibility content calendar" />
      <div style={{ padding: "28px 32px", maxWidth: "960px" }}>

        <div style={{ ...card, padding: "26px", marginBottom: "24px" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
            <div>
              <label style={{ display: "block", fontSize: "16px", fontWeight: 600, color: "#334155", marginBottom: "8px" }}>Topic</label>
              <input value={topic} onChange={e => setTopic(e.target.value)} placeholder="e.g. AI product manager" className="rr-input" />
            </div>
            <div>
              <label style={{ display: "block", fontSize: "16px", fontWeight: 600, color: "#334155", marginBottom: "8px" }}>
                Seed Keywords <span style={{ color: "#94A3B8", fontWeight: 400 }}>(optional, comma-separated)</span>
              </label>
              <input value={keywords} onChange={e => setKeywords(e.target.value)} placeholder="e.g. AI PM skills, product manager AI tools" className="rr-input" />
            </div>
          </div>

          <div style={{ marginTop: "16px", display: "flex", gap: "10px", alignItems: "flex-start", padding: "12px 16px", background: "#FFF7ED", borderRadius: "10px", border: "1px solid #FED7AA" }}>
            <Info size={16} color="#F59E0B" style={{ flexShrink: 0, marginTop: "2px" }} />
            <p style={{ fontSize: "14px", color: "#92400E" }}>
              <strong>Connect Google Search Console</strong> for real search volume data. Trend directions below are sourced from Google Trends via pytrends.
            </p>
          </div>

          {error && <p style={{ marginTop: "12px", fontSize: "15px", color: "#DC2626" }}>{error}</p>}
          <button onClick={handlePlan} disabled={!topic.trim()} className="btn-primary" style={{ marginTop: "18px", justifyContent: "center", fontSize: "16px", padding: "14px", width: "100%" }}>
            <FileSearch size={18} /> Generate Query Plan
          </button>
        </div>

        {result && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>

            {/* Strategy summary */}
            {result.aeo_strategy && (
              <div style={{ ...card, padding: "22px", background: "#F5F3FF", borderColor: "#DDD6FE" }}>
                <p style={{ fontSize: "13px", fontWeight: 700, color: "#5B21B6", marginBottom: "8px", textTransform: "uppercase", letterSpacing: "0.05em" }}>AEO Strategy</p>
                <p style={{ fontSize: "16px", color: "#4C1D95", lineHeight: 1.7 }}>{result.aeo_strategy}</p>
              </div>
            )}

            {/* Primary queries */}
            {result.primary_queries?.length > 0 && (
              <div style={{ ...card, overflow: "hidden" }}>
                <div style={{ padding: "16px 20px", borderBottom: "1px solid #E2E8F0" }}>
                  <p style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 700, fontSize: "17px" }}>Primary Queries</p>
                </div>
                {result.primary_queries.map((q: any, i: number) => {
                  const intentStyle = INTENT_COLORS[q.intent] || { bg: "#F8FAFC", color: "#64748B" };
                  const aiStyle     = AI_LIKELIHOOD_COLORS[q.ai_answer_likelihood] || { bg: "#F8FAFC", color: "#64748B" };
                  return (
                    <div key={i} style={{ padding: "16px 20px", borderBottom: "1px solid #F8FAFC" }}>
                      <div style={{ display: "flex", alignItems: "flex-start", gap: "12px" }}>
                        <span style={{ fontSize: "22px", fontWeight: 800, color: "#E2E8F0", lineHeight: 1 }}>#{i + 1}</span>
                        <div style={{ flex: 1 }}>
                          <p style={{ fontSize: "16px", fontWeight: 600, color: "#0F172A", marginBottom: "8px" }}>{q.query}</p>
                          <div style={{ display: "flex", gap: "7px", flexWrap: "wrap", marginBottom: "8px" }}>
                            <span style={{ fontSize: "13px", fontWeight: 700, padding: "3px 10px", borderRadius: "100px", background: intentStyle.bg, color: intentStyle.color }}>
                              {q.intent}
                            </span>
                            <span style={{ fontSize: "13px", fontWeight: 700, padding: "3px 10px", borderRadius: "100px", background: aiStyle.bg, color: aiStyle.color }}>
                              {q.ai_answer_likelihood} AI likelihood
                            </span>
                            <span style={{ fontSize: "13px", padding: "3px 10px", borderRadius: "100px", background: "#F8FAFC", color: "#64748B" }}>
                              {q.difficulty} difficulty
                            </span>
                            <span style={{ fontSize: "13px", padding: "3px 10px", borderRadius: "100px", background: "#F8FAFC", color: "#64748B" }}>
                              {q.content_format}
                            </span>
                          </div>
                          {q.why_prioritize && <p style={{ fontSize: "14px", color: "#64748B" }}>{q.why_prioritize}</p>}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Long-tail opportunities + trend data */}
            {result.long_tail_opportunities?.length > 0 && (
              <div style={{ ...card, overflow: "hidden" }}>
                <div style={{ padding: "16px 20px", borderBottom: "1px solid #E2E8F0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <p style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 700, fontSize: "17px" }}>Long-Tail Opportunities</p>
                  {!result.has_real_trend_data && (
                    <span style={{ fontSize: "13px", color: "#94A3B8" }}>AI-estimated trends</span>
                  )}
                </div>
                {result.long_tail_opportunities.map((lt: any, i: number) => {
                  const trendColor = lt.monthly_trend === "Rising" ? "#10B981" : lt.monthly_trend === "Declining" ? "#EF4444" : "#94A3B8";
                  return (
                    <div key={i} style={{ padding: "14px 20px", borderBottom: "1px solid #F8FAFC", display: "flex", gap: "14px", alignItems: "flex-start" }}>
                      <TrendIcon direction={lt.monthly_trend} />
                      <div style={{ flex: 1 }}>
                        <p style={{ fontSize: "15px", fontWeight: 600, color: "#0F172A" }}>{lt.query}</p>
                        {lt.ai_visibility_opportunity && (
                          <p style={{ fontSize: "14px", color: "#64748B", marginTop: "4px" }}>{lt.ai_visibility_opportunity}</p>
                        )}
                      </div>
                      <span style={{ fontSize: "13px", fontWeight: 700, color: trendColor, flexShrink: 0 }}>{lt.monthly_trend}</span>
                    </div>
                  );
                })}
              </div>
            )}

            {/* FAQ / Question queries */}
            {result.question_queries?.length > 0 && (
              <div style={{ ...card, overflow: "hidden" }}>
                <div style={{ padding: "16px 20px", borderBottom: "1px solid #E2E8F0" }}>
                  <p style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 700, fontSize: "17px" }}>Question Queries for AI Engines</p>
                </div>
                {result.question_queries.map((q: any, i: number) => (
                  <div key={i} style={{ padding: "14px 20px", borderBottom: "1px solid #F8FAFC" }}>
                    <p style={{ fontSize: "15px", fontWeight: 600, color: "#0F172A", marginBottom: "6px" }}>{q.question}</p>
                    <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                      <span style={{ fontSize: "13px", background: "#F5F3FF", color: "#7C3AED", padding: "3px 10px", borderRadius: "100px", fontWeight: 600 }}>{q.ideal_answer_length}</span>
                      {q.content_gap && <p style={{ fontSize: "14px", color: "#64748B" }}>Gap: {q.content_gap}</p>}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Content calendar */}
            {result.content_calendar?.length > 0 && (
              <div style={{ ...card, overflow: "hidden" }}>
                <div style={{ padding: "16px 20px", borderBottom: "1px solid #E2E8F0", display: "flex", alignItems: "center", gap: "10px" }}>
                  <Calendar size={17} color="#7C3AED" />
                  <p style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 700, fontSize: "17px" }}>Content Calendar</p>
                </div>
                {result.content_calendar.map((item: any, i: number) => {
                  const priorityColor = item.priority === "High" ? "#EF4444" : item.priority === "Medium" ? "#F59E0B" : "#3B82F6";
                  const priorityBg   = item.priority === "High" ? "#FEF2F2" : item.priority === "Medium" ? "#FFFBEB" : "#EFF6FF";
                  return (
                    <div key={i} style={{ padding: "16px 20px", borderBottom: "1px solid #F8FAFC", display: "flex", gap: "14px", alignItems: "flex-start" }}>
                      <span style={{ fontSize: "13px", fontWeight: 700, textTransform: "uppercase", background: priorityBg, color: priorityColor, padding: "4px 12px", borderRadius: "100px", flexShrink: 0, marginTop: "2px" }}>
                        {item.priority}
                      </span>
                      <div style={{ flex: 1 }}>
                        <p style={{ fontSize: "16px", fontWeight: 600, color: "#0F172A", marginBottom: "5px" }}>{item.title}</p>
                        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                          <span style={{ fontSize: "14px", color: "#64748B" }}>{item.format}</span>
                          <span style={{ fontSize: "14px", color: "#64748B" }}>·</span>
                          <span style={{ fontSize: "14px", color: "#64748B" }}>Traffic: {item.estimated_traffic_potential}</span>
                        </div>
                        {item.primary_query && <p style={{ fontSize: "14px", color: "#94A3B8", marginTop: "4px" }}>Target: {item.primary_query}</p>}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* GSC note at bottom */}
            {result.gsc_note && (
              <div style={{ display: "flex", gap: "10px", alignItems: "flex-start", padding: "14px 18px", background: "#FFFBEB", borderRadius: "10px", border: "1px solid #FDE68A" }}>
                <Info size={16} color="#F59E0B" style={{ flexShrink: 0, marginTop: "2px" }} />
                <p style={{ fontSize: "14px", color: "#92400E" }}>{result.gsc_note}</p>
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
