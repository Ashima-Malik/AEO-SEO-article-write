"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { AppLayout } from "@/components/layout/AppLayout";
import { TopBar } from "@/components/layout/TopBar";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { api } from "@/lib/api";
import { scoreColor } from "@/lib/utils";
import { Download, CheckCircle, XCircle, AlertCircle, Copy, Check, Clock, TrendingUp, ChevronRight } from "lucide-react";

type Tab = "canvas" | "score" | "tokens";

// ── Markdown renderer ─────────────────────────────────────────────────────────
function inlineFormat(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) return <strong key={i}>{part.slice(2, -2)}</strong>;
    if (part.startsWith("*") && part.endsWith("*")) return <em key={i}>{part.slice(1, -1)}</em>;
    return part;
  });
}

function renderMarkdown(text: string, compact = false): React.ReactNode[] {
  if (!text) return [];
  const lines = text.split("\n");
  const els: React.ReactNode[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (line.startsWith("# "))
      els.push(<h1 key={i} style={{ fontFamily: "'Plus Jakarta Sans',sans-serif", fontSize: compact ? "20px" : "24px", fontWeight: 800, color: "#0F172A", margin: "20px 0 8px", lineHeight: 1.2 }}>{inlineFormat(line.slice(2))}</h1>);
    else if (line.startsWith("## "))
      els.push(<h2 key={i} style={{ fontFamily: "'Plus Jakarta Sans',sans-serif", fontSize: compact ? "16px" : "19px", fontWeight: 700, color: "#1E293B", margin: "18px 0 6px" }}>{inlineFormat(line.slice(3))}</h2>);
    else if (line.startsWith("### "))
      els.push(<h3 key={i} style={{ fontFamily: "'Plus Jakarta Sans',sans-serif", fontSize: compact ? "14px" : "16px", fontWeight: 600, color: "#334155", margin: "14px 0 5px" }}>{inlineFormat(line.slice(4))}</h3>);
    else if (line.startsWith("- ") || line.startsWith("* "))
      els.push(<div key={i} style={{ display: "flex", gap: "8px", marginBottom: "4px" }}><span style={{ color: "#7C3AED", flexShrink: 0 }}>•</span><span style={{ color: "#475569", lineHeight: 1.7, fontSize: "14px" }}>{inlineFormat(line.slice(2))}</span></div>);
    else if (line.trim() === "---")
      els.push(<hr key={i} style={{ border: "none", borderTop: "1px solid #E2E8F0", margin: "14px 0" }} />);
    else if (line.startsWith("> "))
      els.push(<div key={i} style={{ borderLeft: "3px solid #DDD6FE", paddingLeft: "12px", color: "#7C3AED", fontStyle: "italic", margin: "8px 0", fontSize: "14px" }}>{inlineFormat(line.slice(2))}</div>);
    else if (line.trim() === "")
      els.push(<div key={i} style={{ height: "6px" }} />);
    else
      els.push(<p key={i} style={{ color: "#475569", lineHeight: 1.75, marginBottom: "2px", fontSize: "14px" }}>{inlineFormat(line)}</p>);
    i++;
  }
  return els;
}

// ── Compact score pill ────────────────────────────────────────────────────────
function ScorePill({ label, score, highlight }: { label: string; score: number; highlight?: boolean }) {
  const color = scoreColor(score);
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "2px", padding: "10px 20px", borderRadius: "12px", background: highlight ? "#F5F3FF" : "#F8FAFC", border: `1.5px solid ${highlight ? "#DDD6FE" : "#E2E8F0"}` }}>
      <span style={{ fontSize: "11px", color: "#94A3B8", fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</span>
      <span style={{ fontFamily: "'Plus Jakarta Sans',sans-serif", fontSize: "28px", fontWeight: 800, color, lineHeight: 1 }}>{score}</span>
    </div>
  );
}

// ── Diff canvas ───────────────────────────────────────────────────────────────
function DiffCanvas({ chunks }: { chunks: any[] }) {
  return (
    <div style={{ lineHeight: 1.8, fontSize: "14px" }}>
      {(chunks || []).map((chunk: any, idx: number) => {
        const content = chunk.content || "";
        const rule = chunk.rule_applied;
        const hMatch = content.match(/^(#{1,6})\s(.+)/);
        const level = hMatch ? hMatch[1].length : 0;
        const hText = hMatch ? hMatch[2] : "";

        const headingSize = level === 1 ? "22px" : level === 2 ? "17px" : "14px";
        const headingWeight = level <= 2 ? 800 : 600;
        const headingColor = level === 1 ? "#0F172A" : level === 2 ? "#1E293B" : "#334155";
        const headingMargin = level <= 2 ? "20px 0 6px" : "14px 0 4px";

        if (hMatch) {
          if (chunk.type === "removed") return (
            <div key={idx} style={{ margin: "12px 0 4px", padding: "8px 12px", background: "#FEF2F2", borderLeft: "3px solid #EF4444", borderRadius: "0 6px 6px 0" }}>
              <span style={{ fontSize: "10px", fontWeight: 700, background: "#FECACA", color: "#DC2626", padding: "1px 6px", borderRadius: "3px", marginRight: "6px" }}>REMOVED</span>
              <span style={{ fontSize: headingSize, fontWeight: headingWeight, color: "#EF4444", textDecoration: "line-through" }}>{hText}</span>
              {rule && <p style={{ fontSize: "11px", color: "#EF4444", opacity: 0.65, marginTop: "3px" }}>↳ {rule}</p>}
            </div>
          );
          if (chunk.type === "added") return (
            <div key={idx} style={{ margin: "12px 0 4px", padding: "8px 12px", background: "#F0FDF4", borderLeft: "3px solid #10B981", borderRadius: "0 6px 6px 0" }}>
              <span style={{ fontSize: "10px", fontWeight: 700, background: "#DCFCE7", color: "#16A34A", padding: "1px 6px", borderRadius: "3px", marginRight: "6px" }}>OPTIMIZED</span>
              <span style={{ fontSize: headingSize, fontWeight: headingWeight, color: "#166534" }}>{hText}</span>
              {rule && <p style={{ fontSize: "11px", color: "#16A34A", opacity: 0.65, marginTop: "3px" }}>↳ {rule}</p>}
            </div>
          );
          return <div key={idx} style={{ margin: headingMargin }}><span style={{ fontSize: headingSize, fontWeight: headingWeight, color: headingColor }}>{hText}</span></div>;
        }

        if (chunk.type === "removed") return (
          <div key={idx} style={{ margin: "3px 0", padding: "5px 10px", background: "#FEF2F2", borderLeft: "2px solid #FCA5A5", borderRadius: "0 4px 4px 0" }}>
            <span style={{ color: "#B91C1C", textDecoration: "line-through", fontSize: "14px" }}>{content}</span>
            {rule && <span style={{ fontSize: "11px", color: "#EF4444", opacity: 0.6, display: "block", marginTop: "2px" }}>↳ {rule}</span>}
          </div>
        );
        if (chunk.type === "added") return (
          <div key={idx} style={{ margin: "3px 0", padding: "5px 10px", background: "#F0FDF4", borderLeft: "2px solid #86EFAC", borderRadius: "0 4px 4px 0" }}>
            <span style={{ color: "#166534", fontSize: "14px" }}>{content}</span>
            {rule && <span style={{ fontSize: "11px", color: "#16A34A", opacity: 0.6, display: "block", marginTop: "2px" }}>↳ {rule}</span>}
          </div>
        );
        return <span key={idx} style={{ color: "#475569" }}>{content}{"\n"}</span>;
      })}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function AnalysisResultPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<Tab>("canvas");
  const [canvasView, setCanvasView] = useState<"diff" | "optimized">("diff");
  const [downloading, setDownloading] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api.getAnalysis(id).then(setData).finally(() => setLoading(false));
  }, [id]);

  async function handleDownload() {
    setDownloading(true);
    try {
      const res = await api.downloadDocx(id);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `${data?.target_keyword || "seo"}_optimized.docx`; a.click();
    } finally { setDownloading(false); }
  }

  async function handleCopy() {
    await navigator.clipboard.writeText(data?.optimized_content || "");
    setCopied(true); setTimeout(() => setCopied(false), 2000);
  }

  if (loading) return (
    <AppLayout>
      <TopBar title="Analysis Result" />
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "60vh" }}>
        <LoadingSpinner size={36} />
      </div>
    </AppLayout>
  );
  if (!data) return (
    <AppLayout><TopBar title="Not Found" /><p style={{ padding: "24px", color: "#94A3B8" }}>Analysis not found.</p></AppLayout>
  );

  const improvement = (data.score_after?.overall || 0) - (data.score_before?.overall || 0);
  const TABS: { id: Tab; label: string }[] = [
    { id: "canvas", label: "Canvas" },
    { id: "score",  label: "Score Breakdown" },
    { id: "tokens", label: "Token Usage" },
  ];

  return (
    <AppLayout>
      {/* ── Sticky top bar ── */}
      <div style={{ position: "sticky", top: 0, zIndex: 10, background: "#FFFFFF", borderBottom: "1px solid #E2E8F0", boxShadow: "0 1px 8px rgba(0,0,0,0.04)" }}>
        <div style={{ padding: "12px 24px", display: "flex", alignItems: "center", gap: "16px" }}>
          {/* Title */}
          <div style={{ flex: 1, minWidth: 0 }}>
            <p style={{ fontFamily: "'Plus Jakarta Sans',sans-serif", fontWeight: 700, fontSize: "15px", color: "#0F172A", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {data.target_keyword || "SEO Analysis"}
            </p>
            <p style={{ fontSize: "12px", color: "#94A3B8", marginTop: "1px" }}>
              {data.content_type} · {data.word_count_original}→{data.word_count_optimized} words · <Clock size={10} style={{ display: "inline", marginRight: "2px" }} />{data.processing_time_seconds}s
            </p>
          </div>

          {/* Score pills */}
          <div style={{ display: "flex", alignItems: "center", gap: "8px", flexShrink: 0 }}>
            <ScorePill label="Before" score={data.score_before?.overall || 0} />
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", padding: "0 4px" }}>
              <TrendingUp size={14} color="#10B981" />
              <span style={{ fontFamily: "'Plus Jakarta Sans',sans-serif", fontWeight: 800, fontSize: "18px", color: "#10B981" }}>+{improvement}</span>
            </div>
            <ScorePill label="After" score={data.score_after?.overall || 0} highlight />
          </div>

          {/* Actions */}
          <div style={{ display: "flex", gap: "8px", flexShrink: 0 }}>
            <button onClick={handleCopy} className="btn-secondary" style={{ padding: "8px 14px", fontSize: "13px" }}>
              {copied ? <Check size={13} color="#10B981" /> : <Copy size={13} />} {copied ? "Copied" : "Copy"}
            </button>
            <button onClick={handleDownload} disabled={downloading} className="btn-primary" style={{ padding: "8px 14px", fontSize: "13px" }}>
              {downloading ? <LoadingSpinner size={13} /> : <Download size={13} />} .docx
            </button>
          </div>
        </div>

        {/* SEO suggestions bar */}
        <div style={{ padding: "8px 24px", borderTop: "1px solid #F1F5F9", background: "#FAFAFA", display: "flex", gap: "24px", overflowX: "auto" }}>
          {[
            { label: "Title", value: data.suggested_title_tag, len: (data.suggested_title_tag || "").length },
            { label: "Meta", value: data.suggested_meta_description, len: (data.suggested_meta_description || "").length },
            { label: "Slug", value: data.suggested_url_slug, len: null },
          ].map(item => item.value && (
            <div key={item.label} style={{ display: "flex", gap: "6px", alignItems: "baseline", flexShrink: 0 }}>
              <span style={{ fontSize: "11px", fontWeight: 700, color: "#94A3B8", textTransform: "uppercase" }}>{item.label}</span>
              <span style={{ fontSize: "12px", color: "#334155" }}>{item.value.slice(0, 80)}{item.value.length > 80 ? "…" : ""}</span>
              {item.len !== null && <span style={{ fontSize: "11px", color: item.len > 60 && item.label === "Title" ? "#EF4444" : item.len > 165 && item.label === "Meta" ? "#EF4444" : "#10B981" }}>{item.len}ch</span>}
            </div>
          ))}
        </div>

        {/* Tab bar */}
        <div style={{ padding: "0 24px", display: "flex", gap: "0", borderTop: "1px solid #F1F5F9" }}>
          {TABS.map(t => (
            <button key={t.id} onClick={() => setTab(t.id)} style={{
              padding: "10px 18px", border: "none", background: "transparent", cursor: "pointer",
              fontSize: "13px", fontWeight: tab === t.id ? 600 : 400,
              color: tab === t.id ? "#7C3AED" : "#94A3B8",
              borderBottom: tab === t.id ? "2px solid #7C3AED" : "2px solid transparent",
              marginBottom: "-1px",
            }}>{t.label}</button>
          ))}
        </div>
      </div>

      {/* ── Canvas tab — split screen ── */}
      {tab === "canvas" && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", height: "calc(100vh - 180px)", overflow: "hidden" }}>

          {/* Left: original */}
          <div style={{ borderRight: "1px solid #E2E8F0", display: "flex", flexDirection: "column" }}>
            <div style={{ padding: "10px 20px", background: "#F8FAFC", borderBottom: "1px solid #E2E8F0", display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ fontSize: "11px", fontWeight: 700, background: "#FEF2F2", color: "#DC2626", padding: "2px 8px", borderRadius: "4px" }}>ORIGINAL</span>
              <span style={{ fontSize: "12px", color: "#94A3B8" }}>{data.word_count_original} words</span>
            </div>
            <div style={{ flex: 1, overflowY: "auto", padding: "24px 28px" }}>
              {renderMarkdown(data.extracted?.full_text || "")}
            </div>
          </div>

          {/* Right: optimized with toggle */}
          <div style={{ display: "flex", flexDirection: "column" }}>
            <div style={{ padding: "10px 20px", background: "#F8FAFC", borderBottom: "1px solid #E2E8F0", display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ fontSize: "11px", fontWeight: 700, background: "#F0FDF4", color: "#16A34A", padding: "2px 8px", borderRadius: "4px" }}>OPTIMIZED</span>
              <span style={{ fontSize: "12px", color: "#94A3B8" }}>{data.word_count_optimized} words</span>
              <div style={{ marginLeft: "auto", display: "flex", gap: "4px" }}>
                {(["diff", "optimized"] as const).map(v => (
                  <button key={v} onClick={() => setCanvasView(v)} style={{
                    padding: "4px 12px", borderRadius: "6px", border: "1px solid", fontSize: "12px", fontWeight: 500, cursor: "pointer",
                    background: canvasView === v ? "#7C3AED" : "white",
                    color: canvasView === v ? "white" : "#64748B",
                    borderColor: canvasView === v ? "#7C3AED" : "#E2E8F0",
                  }}>{v === "diff" ? "Track Changes" : "Clean"}</button>
                ))}
              </div>
            </div>
            <div style={{ flex: 1, overflowY: "auto", padding: "24px 28px" }}>
              {canvasView === "diff"
                ? <DiffCanvas chunks={data.diff_chunks || []} />
                : renderMarkdown(data.optimized_content || "")
              }
            </div>
          </div>
        </div>
      )}

      {/* ── Score Breakdown tab ── */}
      {tab === "score" && (
        <div style={{ padding: "24px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", maxWidth: "1000px" }}>
          {/* Criteria */}
          <div style={{ background: "#FFF", border: "1.5px solid #E2E8F0", borderRadius: "16px", overflow: "hidden" }}>
            <div style={{ padding: "14px 18px", borderBottom: "1px solid #E2E8F0" }}>
              <p style={{ fontFamily: "'Plus Jakarta Sans',sans-serif", fontWeight: 700, fontSize: "15px" }}>Scoring Criteria</p>
            </div>
            {data.score_before.criteria?.map((c: any) => (
              <div key={c.name} style={{ padding: "11px 18px", display: "flex", alignItems: "flex-start", gap: "10px", borderBottom: "1px solid #F8FAFC" }}>
                {c.score === c.max_score
                  ? <CheckCircle size={14} color="#10B981" style={{ flexShrink: 0, marginTop: "2px" }} />
                  : c.score === 0
                    ? <XCircle size={14} color="#EF4444" style={{ flexShrink: 0, marginTop: "2px" }} />
                    : <AlertCircle size={14} color="#F59E0B" style={{ flexShrink: 0, marginTop: "2px" }} />}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{ fontSize: "13px", fontWeight: 500, color: "#0F172A" }}>{c.name}</p>
                  {c.fix && c.score < c.max_score && <p style={{ fontSize: "12px", color: "#94A3B8", marginTop: "2px" }}>{c.fix}</p>}
                </div>
                <span style={{ fontSize: "13px", fontWeight: 700, color: scoreColor((c.score / c.max_score) * 100), flexShrink: 0 }}>
                  {c.score}/{c.max_score}
                </span>
              </div>
            ))}
          </div>

          {/* E-E-A-T + Quick wins */}
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div style={{ background: "#FFF", border: "1.5px solid #E2E8F0", borderRadius: "16px", padding: "18px" }}>
              <p style={{ fontFamily: "'Plus Jakarta Sans',sans-serif", fontWeight: 700, fontSize: "15px", marginBottom: "16px" }}>E-E-A-T Signals</p>
              {[
                { label: "Experience", score: data.score_before.eeat?.experience_score },
                { label: "Expertise",  score: data.score_before.eeat?.expertise_score  },
                { label: "Authority",  score: data.score_before.eeat?.authority_score  },
                { label: "Trust",      score: data.score_before.eeat?.trust_score      },
              ].map(e => (
                <div key={e.label} style={{ marginBottom: "12px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "13px", marginBottom: "5px" }}>
                    <span style={{ color: "#475569", fontWeight: 500 }}>{e.label}</span>
                    <span style={{ fontWeight: 700, color: scoreColor(((e.score || 0) / 25) * 100) }}>{e.score || 0}/25</span>
                  </div>
                  <div style={{ height: "5px", background: "#E2E8F0", borderRadius: "3px" }}>
                    <div style={{ height: "100%", borderRadius: "3px", background: scoreColor(((e.score || 0) / 25) * 100), width: `${((e.score || 0) / 25) * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
            <div style={{ background: "#FFF", border: "1.5px solid #E2E8F0", borderRadius: "16px", padding: "18px" }}>
              <p style={{ fontFamily: "'Plus Jakarta Sans',sans-serif", fontWeight: 700, fontSize: "15px", marginBottom: "12px" }}>Quick Wins</p>
              {data.score_before.quick_wins?.map((w: string, i: number) => (
                <div key={i} style={{ display: "flex", gap: "8px", marginBottom: "8px" }}>
                  <ChevronRight size={13} color="#7C3AED" style={{ flexShrink: 0, marginTop: "2px" }} />
                  <span style={{ fontSize: "13px", color: "#475569" }}>{w}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── Token Usage tab ── */}
      {tab === "tokens" && data.agent_usage && (
        <div style={{ padding: "24px", maxWidth: "700px" }}>
          <div style={{ background: "#FFF", border: "1.5px solid #E2E8F0", borderRadius: "16px", overflow: "hidden" }}>
            <div style={{ padding: "14px 18px", borderBottom: "1px solid #E2E8F0" }}>
              <p style={{ fontFamily: "'Plus Jakarta Sans',sans-serif", fontWeight: 700, fontSize: "15px" }}>Token Usage per Agent</p>
            </div>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
              <thead>
                <tr style={{ background: "#F8FAFC" }}>
                  {["Agent", "Input", "Output", "Cost"].map(h => (
                    <th key={h} style={{ padding: "10px 16px", textAlign: "left", fontWeight: 600, color: "#64748B", fontSize: "12px", borderBottom: "1px solid #E2E8F0" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.agent_usage.map((a: any, i: number) => (
                  <tr key={i} style={{ borderBottom: "1px solid #F1F5F9" }}>
                    <td style={{ padding: "10px 16px", fontWeight: 500, color: "#0F172A" }}>{a.agent_name}</td>
                    <td style={{ padding: "10px 16px", color: "#64748B" }}>{a.input_tokens?.toLocaleString()}</td>
                    <td style={{ padding: "10px 16px", color: "#64748B" }}>{a.output_tokens?.toLocaleString()}</td>
                    <td style={{ padding: "10px 16px", color: "#7C3AED", fontWeight: 600 }}>${a.cost_usd?.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </AppLayout>
  );
}
