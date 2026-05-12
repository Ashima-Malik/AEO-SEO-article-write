"use client";
import { useState } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
import { TopBar } from "@/components/layout/TopBar";
import { PageLoader } from "@/components/ui/LoadingSpinner";
import { api } from "@/lib/api";
import { PenTool, Plus, X, Copy, Check, Tag, Clock, Zap } from "lucide-react";

export default function WriterPage() {
  const [topic, setTopic]           = useState("");
  const [keywords, setKeywords]     = useState("");
  const [competitorUrls, setUrls]   = useState<string[]>(["", ""]);
  const [tone, setTone]             = useState("");
  const [loading, setLoading]       = useState(false);
  const [result, setResult]         = useState<any>(null);
  const [error, setError]           = useState("");
  const [copied, setCopied]         = useState(false);

  const card = { background: "#FFFFFF", border: "1.5px solid #E2E8F0", borderRadius: "16px", boxShadow: "0 1px 3px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.04)" };

  function addUrl() { setUrls(u => [...u, ""]); }
  function removeUrl(i: number) { setUrls(u => u.filter((_, idx) => idx !== i)); }
  function setUrl(i: number, val: string) { setUrls(u => u.map((v, idx) => idx === i ? val : v)); }

  async function handleWrite() {
    if (!topic.trim()) { setError("Please enter a topic."); return; }
    const validUrls = competitorUrls.filter(u => u.trim());
    const kwList = keywords.split(",").map(k => k.trim()).filter(Boolean);
    setLoading(true); setError(""); setResult(null);
    try {
      const data = await api.writeArticle(validUrls, kwList, topic, tone || undefined);
      setResult(data);
    } catch (e: any) { setError(e.message || "Write failed."); }
    finally { setLoading(false); }
  }

  async function handleCopy() {
    const text = result?.written_content;
    if (!text) return;
    await navigator.clipboard.writeText(text);
    setCopied(true); setTimeout(() => setCopied(false), 2000);
  }

  if (loading) return (
    <AppLayout>
      <TopBar title="AI Writer" />
      <PageLoader message={
        competitorUrls.filter(u => u.trim()).length > 0
          ? "Analyzing competitors + writing optimized article..."
          : "Writing optimized article..."
      } />
    </AppLayout>
  );

  return (
    <AppLayout>
      <TopBar title="AI Writer" subtitle="Write an SEO-optimized article — add competitor URLs for a gap analysis boost" />
      <div style={{ padding: "28px 32px", maxWidth: "800px" }}>

        <div style={{ ...card, padding: "26px", marginBottom: "24px", display: "flex", flexDirection: "column", gap: "20px" }}>
          <div>
            <label style={{ display: "block", fontSize: "16px", fontWeight: 600, color: "#334155", marginBottom: "9px" }}>Topic / Article Brief</label>
            <textarea
              value={topic} onChange={e => setTopic(e.target.value)} rows={3}
              placeholder="e.g. How to become an AI Product Manager in 2025 — include career paths, required skills, and salary data"
              className="rr-input" style={{ resize: "none" }}
            />
          </div>

          <div>
            <label style={{ display: "block", fontSize: "16px", fontWeight: 600, color: "#334155", marginBottom: "9px" }}>
              Target Keywords <span style={{ color: "#94A3B8", fontWeight: 400 }}>(optional, comma-separated)</span>
            </label>
            <input value={keywords} onChange={e => setKeywords(e.target.value)} placeholder="AI product manager, PM skills, AI PM salary" className="rr-input" />
          </div>

          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
              <label style={{ fontSize: "16px", fontWeight: 600, color: "#334155" }}>
                Competitor URLs <span style={{ color: "#94A3B8", fontWeight: 400 }}>(optional — paste top-ranking pages)</span>
              </label>
              <button onClick={addUrl} style={{ background: "none", border: "none", cursor: "pointer", color: "#7C3AED", fontSize: "15px", fontWeight: 500, display: "flex", alignItems: "center", gap: "5px" }}>
                <Plus size={16} /> Add URL
              </button>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "9px" }}>
              {competitorUrls.map((u, i) => (
                <div key={i} style={{ display: "flex", gap: "8px" }}>
                  <input
                    type="url" value={u} onChange={e => setUrl(i, e.target.value)}
                    placeholder={`https://competitor${i + 1}.com/article`}
                    className="rr-input"
                  />
                  {competitorUrls.length > 1 && (
                    <button onClick={() => removeUrl(i)} style={{ background: "none", border: "1.5px solid #E2E8F0", borderRadius: "8px", padding: "0 12px", cursor: "pointer", color: "#94A3B8", flexShrink: 0 }}>
                      <X size={16} />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div>
            <label style={{ display: "block", fontSize: "16px", fontWeight: 600, color: "#334155", marginBottom: "9px" }}>
              Tone Instructions <span style={{ color: "#94A3B8", fontWeight: 400 }}>(optional)</span>
            </label>
            <input value={tone} onChange={e => setTone(e.target.value)} placeholder="e.g. Expert but approachable, first-person, include personal anecdotes" className="rr-input" />
          </div>

          {error && (
            <div style={{ background: "#FEF2F2", border: "1px solid #FECACA", borderRadius: "10px", padding: "12px 16px", fontSize: "14px", color: "#DC2626" }}>
              {error}
            </div>
          )}

          <button onClick={handleWrite} disabled={!topic.trim()} className="btn-primary" style={{ justifyContent: "center", fontSize: "16px", padding: "14px" }}>
            <PenTool size={18} /> Write Optimized Article
          </button>
        </div>

        {result?.written_content && (
          <div style={{ ...card, overflow: "hidden" }}>
            {/* Header */}
            <div style={{ padding: "16px 20px", borderBottom: "1px solid #E2E8F0", display: "flex", alignItems: "center", gap: "10px" }}>
              <p style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 700, fontSize: "17px", flex: 1 }}>Generated Article</p>
              <button onClick={handleCopy} className="btn-secondary" style={{ padding: "7px 16px", fontSize: "14px" }}>
                {copied ? <Check size={15} color="#10B981" /> : <Copy size={15} />}
                {copied ? "Copied!" : "Copy"}
              </button>
            </div>

            {/* Meta tags strip */}
            {(result.suggested_title_tag || result.suggested_meta_description || result.suggested_url_slug) && (
              <div style={{ padding: "14px 20px", borderBottom: "1px solid #E2E8F0", background: "#F8FAFC", display: "flex", flexDirection: "column", gap: "8px" }}>
                {result.suggested_title_tag && (
                  <div style={{ display: "flex", gap: "8px", alignItems: "flex-start" }}>
                    <span style={{ fontSize: "12px", fontWeight: 700, color: "#7C3AED", background: "#F5F3FF", padding: "2px 8px", borderRadius: "6px", flexShrink: 0, marginTop: "2px" }}>TITLE</span>
                    <span style={{ fontSize: "14px", color: "#334155" }}>{result.suggested_title_tag}</span>
                  </div>
                )}
                {result.suggested_meta_description && (
                  <div style={{ display: "flex", gap: "8px", alignItems: "flex-start" }}>
                    <span style={{ fontSize: "12px", fontWeight: 700, color: "#3B82F6", background: "#EFF6FF", padding: "2px 8px", borderRadius: "6px", flexShrink: 0, marginTop: "2px" }}>META</span>
                    <span style={{ fontSize: "14px", color: "#334155" }}>{result.suggested_meta_description}</span>
                  </div>
                )}
                {result.suggested_url_slug && (
                  <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                    <span style={{ fontSize: "12px", fontWeight: 700, color: "#10B981", background: "#F0FDF4", padding: "2px 8px", borderRadius: "6px", flexShrink: 0 }}>SLUG</span>
                    <span style={{ fontSize: "14px", color: "#334155", fontFamily: "'JetBrains Mono', monospace" }}>{result.suggested_url_slug}</span>
                  </div>
                )}
              </div>
            )}

            {/* Stats strip */}
            <div style={{ padding: "10px 20px", borderBottom: "1px solid #E2E8F0", display: "flex", gap: "20px", background: "#FAFAFA" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "13px", color: "#64748B" }}>
                <Tag size={13} color="#94A3B8" />
                {result.target_keywords?.length > 0 ? result.target_keywords.join(" · ") : "No keywords"}
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "13px", color: "#64748B" }}>
                <Clock size={13} color="#94A3B8" />
                {result.processing_time_seconds}s
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "13px", color: "#64748B" }}>
                <Zap size={13} color="#94A3B8" />
                {result.agents_used?.join(" → ")}
              </div>
            </div>

            {/* Article body */}
            <div style={{ padding: "32px 40px", maxHeight: "70vh", overflowY: "auto", lineHeight: 1.8, fontSize: "16px", color: "#475569", whiteSpace: "pre-wrap" }}>
              {result.written_content}
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
