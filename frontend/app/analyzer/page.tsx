"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { AppLayout } from "@/components/layout/AppLayout";
import { TopBar } from "@/components/layout/TopBar";
import { PageLoader } from "@/components/ui/LoadingSpinner";
import { api } from "@/lib/api";
import { useDropzone } from "react-dropzone";
import { Link2, FileText, AlignLeft, Upload, Search, ChevronDown, Tag, BookOpen, Sparkles } from "lucide-react";

type InputMode = "url" | "text" | "document";

export default function AnalyzerPage() {
  const [mode, setMode] = useState<InputMode>("url");
  const [url, setUrl] = useState("");
  const [text, setText] = useState("");
  const [keywords, setKeywords] = useState("");
  const [userBrief, setUserBrief] = useState("");
  const [contentType, setContentType] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
      "text/plain": [".txt"],
    },
    maxFiles: 1,
    onDrop: (files) => { if (files[0]) { setFile(files[0]); setMode("document"); } },
  });

  function parseKeywords(): string[] {
    return keywords.split(",").map(k => k.trim()).filter(Boolean).slice(0, 5);
  }

  async function handleAnalyze() {
    setLoading(true);
    setError("");
    try {
      const kwList = parseKeywords();
      const primaryKw = kwList[0] || undefined;
      const brief = userBrief.trim() || undefined;
      let result: any;
      if (mode === "url") {
        result = await api.analyzeUrl(url, primaryKw, contentType || undefined, undefined, kwList.length ? kwList : undefined, brief);
      } else if (mode === "text") {
        result = await api.analyzeText(text, primaryKw, contentType || undefined, undefined, kwList.length ? kwList : undefined, brief);
      } else if (mode === "document" && file) {
        result = await api.analyzeDocument(file, primaryKw, contentType || undefined);
      } else {
        setError("Please provide content to analyze.");
        return;
      }
      router.push(`/analyzer/${result.analysis_id}`);
    } catch (err: any) {
      setError(err.message || "Analysis failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  const tabs = [
    { id: "url" as InputMode, icon: Link2, label: "URL" },
    { id: "text" as InputMode, icon: AlignLeft, label: "Paste Text" },
    { id: "document" as InputMode, icon: FileText, label: "Upload File" },
  ];

  if (loading) return (
    <AppLayout>
      <TopBar title="SEO Analyzer" />
      <PageLoader message="Running 5-agent SEO analysis + web research..." />
    </AppLayout>
  );

  return (
    <AppLayout>
      <TopBar title="SEO Analyzer" subtitle="Score, optimize and download improved content" />

      <div style={{ padding: "28px 32px" }}>
        <div style={{ maxWidth: "680px" }}>

          {/* Hero hint */}
          <div style={{
            background: "linear-gradient(135deg, #F5F3FF, #EDE9FE)",
            border: "1px solid #DDD6FE", borderRadius: "14px",
            padding: "16px 20px", marginBottom: "28px",
            display: "flex", alignItems: "center", gap: "12px",
          }}>
            <div style={{
              width: 36, height: 36, borderRadius: 10, flexShrink: 0,
              background: "linear-gradient(135deg, #7C3AED, #6D28D9)",
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>
              <Sparkles size={16} color="white" />
            </div>
            <div>
              <p style={{ fontWeight: 600, fontSize: "16px", color: "#5B21B6", marginBottom: "2px" }}>
                5 AI agents run in parallel
              </p>
              <p style={{ fontSize: "14px", color: "#7C3AED" }}>
                Extractor → Scorer → Rewriter → Validator → URL Auditor · ~30–60 seconds
              </p>
            </div>
          </div>

          {/* Mode tabs */}
          <div style={{
            display: "flex", gap: "4px", padding: "4px",
            background: "#F1F5F9", borderRadius: "12px", marginBottom: "20px",
          }}>
            {tabs.map(t => (
              <button key={t.id} onClick={() => setMode(t.id)}
                style={{
                  flex: 1, display: "flex", alignItems: "center", justifyContent: "center",
                  gap: "8px", padding: "12px 18px", borderRadius: "9px",
                  border: "none", cursor: "pointer", fontFamily: "'Inter', sans-serif",
                  fontSize: "15px", fontWeight: 500, transition: "all 0.15s",
                  ...(mode === t.id
                    ? { background: "#FFFFFF", color: "#7C3AED", boxShadow: "0 1px 4px rgba(0,0,0,0.08)" }
                    : { background: "transparent", color: "#94A3B8" }),
                }}>
                <t.icon size={16} />
                {t.label}
              </button>
            ))}
          </div>

          {/* Input card */}
          <div style={{
            background: "#FFFFFF", border: "1.5px solid #E2E8F0",
            borderRadius: "16px", padding: "24px",
            boxShadow: "0 1px 3px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.04)",
          }}>
            <div style={{ marginBottom: "20px" }}>
              {mode === "url" && (
                <div>
                  <label style={{ display: "block", fontSize: "16px", fontWeight: 600, color: "#334155", marginBottom: "9px" }}>
                    Page URL
                  </label>
                  <div style={{ position: "relative" }}>
                    <Link2 size={18} style={{ position: "absolute", left: "14px", top: "50%", transform: "translateY(-50%)", color: "#94A3B8" }} />
                    <input
                      type="url" value={url} onChange={e => setUrl(e.target.value)}
                      placeholder="https://yoursite.com/article"
                      className="rr-input" style={{ paddingLeft: "44px" }}
                    />
                  </div>
                </div>
              )}

              {mode === "text" && (
                <div>
                  <label style={{ display: "block", fontSize: "16px", fontWeight: 600, color: "#334155", marginBottom: "9px" }}>
                    Paste your content
                  </label>
                  <textarea
                    value={text} onChange={e => setText(e.target.value)} rows={10}
                    placeholder={"# Your Article Title\n\nPaste your full content here..."}
                    className="rr-input" style={{ resize: "none", fontFamily: "'JetBrains Mono', monospace", fontSize: "15px" }}
                  />
                  <p style={{ fontSize: "14px", color: "#94A3B8", marginTop: "6px" }}>
                    {text.split(/\s+/).filter(Boolean).length} words · minimum 300 for meaningful analysis
                  </p>
                </div>
              )}

              {mode === "document" && (
                <div {...getRootProps()} style={{
                  borderRadius: "12px", padding: "40px 24px", textAlign: "center",
                  cursor: "pointer", transition: "all 0.15s",
                  border: `2px dashed ${isDragActive ? "#7C3AED" : "#E2E8F0"}`,
                  background: isDragActive ? "#F5F3FF" : "#FAFAFA",
                }}>
                  <input {...getInputProps()} />
                  <Upload size={28} style={{ margin: "0 auto 12px", color: "#94A3B8", display: "block" }} />
                  {file ? (
                    <div>
                      <p style={{ fontWeight: 600, fontSize: "15px", color: "#0F172A" }}>{file.name}</p>
                      <p style={{ fontSize: "13px", color: "#94A3B8", marginTop: "4px" }}>{(file.size / 1024).toFixed(0)} KB</p>
                    </div>
                  ) : (
                    <div>
                      <p style={{ fontSize: "15px", color: "#475569", fontWeight: 500 }}>Drop your .docx or .txt file here</p>
                      <p style={{ fontSize: "13px", color: "#94A3B8", marginTop: "4px" }}>or click to browse</p>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Keywords + content type row */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginBottom: "18px" }}>
              <div>
                <label style={{ display: "block", fontSize: "16px", fontWeight: 600, color: "#334155", marginBottom: "9px" }}>
                  Target Keywords <span style={{ color: "#94A3B8", fontWeight: 400 }}>(optional)</span>
                </label>
                <div style={{ position: "relative" }}>
                  <Tag size={16} style={{ position: "absolute", left: "14px", top: "50%", transform: "translateY(-50%)", color: "#94A3B8" }} />
                  <input
                    value={keywords} onChange={e => setKeywords(e.target.value)}
                    placeholder="e.g. product manager, ai pm"
                    className="rr-input" style={{ paddingLeft: "42px" }}
                  />
                </div>
                {keywords && (
                  <p style={{ fontSize: "14px", color: "#7C3AED", marginTop: "6px" }}>
                    {parseKeywords().length} keyword{parseKeywords().length !== 1 ? "s" : ""}: {parseKeywords().join(" · ")}
                  </p>
                )}
                {!keywords && (
                  <p style={{ fontSize: "14px", color: "#94A3B8", marginTop: "6px" }}>Comma-separated, up to 5</p>
                )}
              </div>

              <div>
                <label style={{ display: "block", fontSize: "16px", fontWeight: 600, color: "#334155", marginBottom: "9px" }}>
                  Content Type <span style={{ color: "#94A3B8", fontWeight: 400 }}>(optional)</span>
                </label>
                <div style={{ position: "relative" }}>
                  <select
                    value={contentType} onChange={e => setContentType(e.target.value)}
                    className="rr-input" style={{ appearance: "none", paddingRight: "36px" }}>
                    <option value="">Auto-detect</option>
                    <option value="article">Article</option>
                    <option value="bio">Bio</option>
                    <option value="product_page">Product Page</option>
                    <option value="general">General</option>
                  </select>
                  <ChevronDown size={16} style={{ position: "absolute", right: "14px", top: "50%", transform: "translateY(-50%)", color: "#94A3B8", pointerEvents: "none" }} />
                </div>
              </div>
            </div>

            {/* Writing brief */}
            <div style={{ marginBottom: "22px" }}>
              <label style={{ display: "flex", alignItems: "center", gap: "7px", fontSize: "16px", fontWeight: 600, color: "#334155", marginBottom: "9px" }}>
                <BookOpen size={16} color="#94A3B8" />
                Writing Brief <span style={{ color: "#94A3B8", fontWeight: 400 }}>(optional — improves AI output)</span>
              </label>
              <textarea
                value={userBrief} onChange={e => setUserBrief(e.target.value)} rows={3}
                placeholder="Describe your target audience, key points to cover, tone, expertise level, or any facts the AI should include..."
                className="rr-input" style={{ resize: "none" }}
              />
            </div>

            {error && (
              <div style={{
                background: "#FEF2F2", border: "1px solid #FECACA",
                borderRadius: "10px", padding: "12px 16px", marginBottom: "16px",
                fontSize: "14px", color: "#DC2626",
              }}>
                {error}
              </div>
            )}

            <button
              onClick={handleAnalyze}
              disabled={loading || (mode === "url" && !url) || (mode === "text" && text.length < 50) || (mode === "document" && !file)}
              className="btn-primary" style={{ width: "100%", justifyContent: "center", fontSize: "16px", padding: "13px" }}>
              <Search size={17} />
              Analyze &amp; Optimize
            </button>
          </div>

          {/* Tips */}
          <div style={{
            background: "#FFFBEB", border: "1px solid #FDE68A",
            borderRadius: "12px", padding: "18px 22px", marginTop: "16px",
          }}>
            <p style={{ fontSize: "15px", fontWeight: 600, color: "#92400E", marginBottom: "10px" }}>Tips for best results</p>
            <ul style={{ fontSize: "15px", color: "#78350F", display: "flex", flexDirection: "column", gap: "7px", listStyle: "none" }}>
              <li>→ Add multiple keywords separated by commas to target all of them</li>
              <li>→ The writing brief lets the AI tailor the article to your expertise and audience</li>
              <li>→ Web research runs automatically — current data and citations are included</li>
            </ul>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
