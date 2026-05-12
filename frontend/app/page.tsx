"use client";
import Link from "next/link";
import { ArrowRight, Zap, Search, Globe, Hash, PenTool, BarChart2, CheckCircle, TrendingUp, Brain, Target } from "lucide-react";

const FEATURES = [
  {
    icon: Search, color: "#7C3AED", bg: "#F5F3FF",
    title: "SEO Analyzer",
    desc: "Score any page against a 100-point rubric across 13 criteria. Get exact fixes with impact ratings.",
  },
  {
    icon: Brain, color: "#0EA5E9", bg: "#F0F9FF",
    title: "AI Rewriter",
    desc: "Parallel GPT-4o rewrites with live web research. Articles go from 500 to 4,000+ optimized words.",
  },
  {
    icon: Globe, color: "#10B981", bg: "#F0FDF4",
    title: "Site Audit",
    desc: "20-point technical audit: Core Web Vitals, meta tags, schema, canonicals, and mobile signals.",
  },
  {
    icon: Hash, color: "#F59E0B", bg: "#FFFBEB",
    title: "Keyword Clusters",
    desc: "Group keywords by search intent — informational, transactional, navigational — with PAA questions.",
  },
  {
    icon: PenTool, color: "#EC4899", bg: "#FDF2F8",
    title: "AI Writer",
    desc: "Analyze competitor URLs and write an article that beats them on every content gap.",
  },
  {
    icon: BarChart2, color: "#6366F1", bg: "#EEF2FF",
    title: "Competitor Compare",
    desc: "Head-to-head SEO comparison with prioritized next steps and estimated score impact.",
  },
];

const STEPS = [
  { n: "01", title: "Paste your URL or content", desc: "Drop in a URL, paste text, or upload a .docx file." },
  { n: "02", title: "5 AI agents analyze in parallel", desc: "Extractor → Scorer → Rewriter → Validator → URL Auditor run simultaneously." },
  { n: "03", title: "Get your score + rewritten article", desc: "See exactly what changed, why, and download the optimized version as Word." },
];

const STATS = [
  { value: "100pt", label: "Scoring Rubric" },
  { value: "13", label: "SEO Criteria" },
  { value: "5", label: "AI Agents" },
  { value: "4000+", label: "Words Generated" },
];

export default function LandingPage() {
  return (
    <div style={{ fontFamily: "'Inter', sans-serif", background: "#FFFFFF", color: "#0F172A" }}>

      {/* ── Nav ── */}
      <nav style={{
        position: "sticky", top: 0, zIndex: 50,
        background: "rgba(255,255,255,0.92)", backdropFilter: "blur(12px)",
        borderBottom: "1px solid #E2E8F0",
      }}>
        <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "0 24px", display: "flex", alignItems: "center", height: "64px", gap: "32px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div style={{
              width: 34, height: 34, borderRadius: 10,
              background: "linear-gradient(135deg, #7C3AED, #6D28D9)",
              display: "flex", alignItems: "center", justifyContent: "center",
              boxShadow: "0 2px 8px rgba(124,58,237,0.35)",
            }}>
              <Zap size={16} color="white" />
            </div>
            <span style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 800, fontSize: "18px", letterSpacing: "-0.3px" }}>
              RankReady
            </span>
          </div>

          <div style={{ flex: 1 }} />

          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Link href="/analyzer" style={{
              background: "linear-gradient(135deg, #7C3AED, #6D28D9)",
              color: "white", borderRadius: "10px", padding: "9px 20px",
              fontWeight: 600, fontSize: "14px", textDecoration: "none",
              boxShadow: "0 2px 8px rgba(124,58,237,0.3)",
              display: "inline-flex", alignItems: "center", gap: "6px",
            }}>
              Try Free <ArrowRight size={14} />
            </Link>
          </div>
        </div>
      </nav>

      {/* ── Hero ── */}
      <section style={{
        background: "linear-gradient(180deg, #F5F3FF 0%, #FFFFFF 60%)",
        padding: "96px 24px 80px",
        textAlign: "center",
        position: "relative", overflow: "hidden",
      }}>
        {/* Decorative blobs */}
        <div style={{
          position: "absolute", top: "-120px", left: "50%", transform: "translateX(-50%)",
          width: "800px", height: "800px", borderRadius: "50%",
          background: "radial-gradient(circle, rgba(124,58,237,0.08) 0%, transparent 70%)",
          pointerEvents: "none",
        }} />

        <div style={{ maxWidth: "800px", margin: "0 auto", position: "relative" }}>
          <div style={{
            display: "inline-flex", alignItems: "center", gap: "8px",
            background: "#F5F3FF", border: "1px solid #DDD6FE", borderRadius: "100px",
            padding: "6px 16px", marginBottom: "28px",
          }}>
            <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#7C3AED" }} />
            <span style={{ fontSize: "13px", fontWeight: 600, color: "#7C3AED" }}>
              AI-Powered SEO + AEO Platform
            </span>
          </div>

          <h1 style={{
            fontFamily: "'Plus Jakarta Sans', sans-serif",
            fontWeight: 800, fontSize: "clamp(42px, 6vw, 68px)",
            lineHeight: 1.1, letterSpacing: "-1.5px", marginBottom: "24px",
          }}>
            Rank higher.{" "}
            <span style={{
              background: "linear-gradient(135deg, #7C3AED, #0EA5E9)",
              WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
            }}>
              Get cited by AI.
            </span>
          </h1>

          <p style={{
            fontSize: "19px", color: "#475569", lineHeight: 1.7,
            maxWidth: "600px", margin: "0 auto 40px",
          }}>
            The only SEO tool that scores your content, rewrites it with live web research,
            and audits whether ChatGPT and AI engines are citing you.
          </p>

          <div style={{ display: "flex", gap: "12px", justifyContent: "center", flexWrap: "wrap" }}>
            <Link href="/analyzer" style={{
              background: "linear-gradient(135deg, #7C3AED, #6D28D9)",
              color: "white", borderRadius: "12px", padding: "14px 28px",
              fontWeight: 700, fontSize: "16px", textDecoration: "none",
              boxShadow: "0 4px 20px rgba(124,58,237,0.35)",
              display: "inline-flex", alignItems: "center", gap: "8px",
            }}>
              Analyze Your Content Free <ArrowRight size={16} />
            </Link>
            <Link href="/writer" style={{
              background: "#FFFFFF", color: "#334155",
              border: "1.5px solid #E2E8F0",
              borderRadius: "12px", padding: "14px 28px",
              fontWeight: 600, fontSize: "16px", textDecoration: "none",
              display: "inline-flex", alignItems: "center", gap: "8px",
            }}>
              <PenTool size={16} /> Write an Article
            </Link>
          </div>
        </div>
      </section>

      {/* ── Stats bar ── */}
      <section style={{ background: "#0F172A", padding: "28px 24px" }}>
        <div style={{
          maxWidth: "1000px", margin: "0 auto",
          display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "24px",
          textAlign: "center",
        }}>
          {STATS.map(s => (
            <div key={s.value}>
              <div style={{
                fontFamily: "'Plus Jakarta Sans', sans-serif",
                fontWeight: 800, fontSize: "32px", color: "#A78BFA", lineHeight: 1,
              }}>{s.value}</div>
              <div style={{ fontSize: "13px", color: "#64748B", marginTop: "6px" }}>{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Features ── */}
      <section style={{ padding: "96px 24px", background: "#FFFFFF" }}>
        <div style={{ maxWidth: "1200px", margin: "0 auto" }}>
          <div style={{ textAlign: "center", marginBottom: "64px" }}>
            <h2 style={{
              fontFamily: "'Plus Jakarta Sans', sans-serif",
              fontWeight: 800, fontSize: "clamp(32px, 4vw, 44px)",
              letterSpacing: "-0.8px", marginBottom: "16px",
            }}>
              Everything your content team needs
            </h2>
            <p style={{ fontSize: "18px", color: "#64748B", maxWidth: "520px", margin: "0 auto" }}>
              Six specialized AI agents working together — no subscriptions, no limits per analysis.
            </p>
          </div>

          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
            gap: "20px",
          }}>
            {FEATURES.map(f => (
              <div key={f.title} style={{
                background: "#FFFFFF", border: "1.5px solid #E2E8F0",
                borderRadius: "16px", padding: "28px",
                boxShadow: "0 1px 3px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.04)",
                transition: "all 0.2s",
              }}
                onMouseEnter={e => {
                  (e.currentTarget as HTMLElement).style.boxShadow = "0 4px 12px rgba(0,0,0,0.08), 0 16px 40px rgba(0,0,0,0.06)";
                  (e.currentTarget as HTMLElement).style.borderColor = "#DDD6FE";
                  (e.currentTarget as HTMLElement).style.transform = "translateY(-2px)";
                }}
                onMouseLeave={e => {
                  (e.currentTarget as HTMLElement).style.boxShadow = "0 1px 3px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.04)";
                  (e.currentTarget as HTMLElement).style.borderColor = "#E2E8F0";
                  (e.currentTarget as HTMLElement).style.transform = "translateY(0)";
                }}>
                <div style={{
                  width: 48, height: 48, borderRadius: 12,
                  background: f.bg, display: "flex", alignItems: "center", justifyContent: "center",
                  marginBottom: "18px",
                }}>
                  <f.icon size={22} color={f.color} />
                </div>
                <h3 style={{
                  fontFamily: "'Plus Jakarta Sans', sans-serif",
                  fontWeight: 700, fontSize: "18px", marginBottom: "10px", color: "#0F172A",
                }}>{f.title}</h3>
                <p style={{ fontSize: "15px", color: "#64748B", lineHeight: 1.6 }}>{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ── */}
      <section style={{ padding: "96px 24px", background: "#F8F7FF" }}>
        <div style={{ maxWidth: "1000px", margin: "0 auto" }}>
          <div style={{ textAlign: "center", marginBottom: "64px" }}>
            <h2 style={{
              fontFamily: "'Plus Jakarta Sans', sans-serif",
              fontWeight: 800, fontSize: "clamp(32px, 4vw, 44px)",
              letterSpacing: "-0.8px", marginBottom: "16px",
            }}>How it works</h2>
            <p style={{ fontSize: "18px", color: "#64748B" }}>
              From raw content to fully optimized article in under 60 seconds.
            </p>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "32px" }}>
            {STEPS.map((step, i) => (
              <div key={step.n} style={{ textAlign: "center", position: "relative" }}>
                {i < STEPS.length - 1 && (
                  <div style={{
                    position: "absolute", top: "24px", left: "60%", right: "-40%",
                    height: "2px",
                    background: "linear-gradient(90deg, #DDD6FE, transparent)",
                  }} />
                )}
                <div style={{
                  width: 48, height: 48, borderRadius: "50%",
                  background: "linear-gradient(135deg, #7C3AED, #6D28D9)",
                  color: "white", display: "flex", alignItems: "center", justifyContent: "center",
                  fontFamily: "'Plus Jakarta Sans', sans-serif",
                  fontWeight: 800, fontSize: "15px",
                  margin: "0 auto 20px",
                  boxShadow: "0 4px 16px rgba(124,58,237,0.3)",
                }}>
                  {step.n}
                </div>
                <h3 style={{
                  fontFamily: "'Plus Jakarta Sans', sans-serif",
                  fontWeight: 700, fontSize: "18px", marginBottom: "10px",
                }}>{step.title}</h3>
                <p style={{ fontSize: "15px", color: "#64748B", lineHeight: 1.6 }}>{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Score preview ── */}
      <section style={{ padding: "96px 24px", background: "#FFFFFF" }}>
        <div style={{ maxWidth: "1000px", margin: "0 auto", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "64px", alignItems: "center" }}>
          <div>
            <div style={{
              display: "inline-flex", alignItems: "center", gap: "8px",
              background: "#F0FDF4", border: "1px solid #BBF7D0", borderRadius: "100px",
              padding: "5px 14px", marginBottom: "24px",
            }}>
              <TrendingUp size={13} color="#10B981" />
              <span style={{ fontSize: "13px", fontWeight: 600, color: "#10B981" }}>Average +32 point improvement</span>
            </div>
            <h2 style={{
              fontFamily: "'Plus Jakarta Sans', sans-serif",
              fontWeight: 800, fontSize: "clamp(28px, 3.5vw, 40px)",
              letterSpacing: "-0.6px", lineHeight: 1.2, marginBottom: "20px",
            }}>
              See exactly what's holding your content back
            </h2>
            <p style={{ fontSize: "17px", color: "#64748B", lineHeight: 1.7, marginBottom: "28px" }}>
              The 100-point rubric scores 13 specific criteria — keyword placement, E-E-A-T signals,
              heading structure, FAQ presence, internal links, and more. Every issue comes with an exact fix.
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {["Keyword in H1 + first 100 words", "E-E-A-T signals: Experience, Expertise, Authority, Trust", "FAQ section with featured snippet answers", "Author bio with credential signals"].map(item => (
                <div key={item} style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <CheckCircle size={18} color="#7C3AED" style={{ flexShrink: 0 }} />
                  <span style={{ fontSize: "15px", color: "#334155" }}>{item}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Score card preview */}
          <div style={{
            background: "#FFFFFF", border: "1.5px solid #E2E8F0", borderRadius: "20px",
            padding: "28px", boxShadow: "0 8px 40px rgba(0,0,0,0.08)",
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "24px" }}>
              <div>
                <p style={{ fontSize: "13px", color: "#94A3B8", marginBottom: "4px" }}>Before optimization</p>
                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                  <span style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 800, fontSize: "42px", color: "#EF4444" }}>38</span>
                  <div>
                    <div style={{ fontSize: "13px", fontWeight: 600, color: "#EF4444" }}>Not Ready</div>
                    <div style={{ fontSize: "12px", color: "#94A3B8" }}>/ 100 points</div>
                  </div>
                </div>
              </div>
              <div style={{
                background: "#F0FDF4", border: "1px solid #BBF7D0",
                borderRadius: "10px", padding: "8px 14px", textAlign: "center",
              }}>
                <div style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 800, fontSize: "20px", color: "#10B981" }}>+42</div>
                <div style={{ fontSize: "11px", color: "#10B981" }}>pts gained</div>
              </div>
            </div>

            {[
              { name: "Keyword in H1", before: 0, after: 5, max: 5 },
              { name: "E-E-A-T Signals", before: 3, after: 15, max: 15 },
              { name: "FAQ Section", before: 0, after: 10, max: 10 },
              { name: "H2/H3 Frequency", before: 5, after: 15, max: 15 },
              { name: "Author Bio", before: 0, after: 5, max: 5 },
            ].map(row => (
              <div key={row.name} style={{ marginBottom: "14px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "5px" }}>
                  <span style={{ fontSize: "13px", color: "#334155", fontWeight: 500 }}>{row.name}</span>
                  <span style={{ fontSize: "13px", color: "#10B981", fontWeight: 600 }}>{row.after}/{row.max}</span>
                </div>
                <div style={{ height: "6px", background: "#F1F5F9", borderRadius: "3px", overflow: "hidden" }}>
                  <div style={{
                    height: "100%", borderRadius: "3px",
                    background: "linear-gradient(90deg, #7C3AED, #0EA5E9)",
                    width: `${(row.after / row.max) * 100}%`,
                    transition: "width 0.6s ease",
                  }} />
                </div>
              </div>
            ))}

            <div style={{ marginTop: "20px", padding: "12px 16px", background: "#F0FDF4", borderRadius: "10px" }}>
              <p style={{ fontSize: "13px", color: "#10B981", fontWeight: 600 }}>After optimization: 80/100 — Publish with confidence</p>
            </div>
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section style={{
        padding: "96px 24px",
        background: "linear-gradient(135deg, #7C3AED 0%, #6D28D9 50%, #4F46E5 100%)",
        textAlign: "center",
      }}>
        <div style={{ maxWidth: "640px", margin: "0 auto" }}>
          <div style={{
            width: 56, height: 56, borderRadius: 16, margin: "0 auto 24px",
            background: "rgba(255,255,255,0.15)",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <Target size={26} color="white" />
          </div>
          <h2 style={{
            fontFamily: "'Plus Jakarta Sans', sans-serif",
            fontWeight: 800, fontSize: "clamp(32px, 4vw, 48px)",
            color: "white", letterSpacing: "-0.8px", marginBottom: "20px", lineHeight: 1.15,
          }}>
            Ready to rank on page one?
          </h2>
          <p style={{ fontSize: "18px", color: "rgba(255,255,255,0.8)", marginBottom: "36px", lineHeight: 1.6 }}>
            Free to use. No login required. Paste your URL and get your score in 60 seconds.
          </p>
          <Link href="/analyzer" style={{
            background: "#FFFFFF", color: "#7C3AED",
            borderRadius: "12px", padding: "16px 36px",
            fontWeight: 800, fontSize: "17px", textDecoration: "none",
            display: "inline-flex", alignItems: "center", gap: "10px",
            boxShadow: "0 4px 24px rgba(0,0,0,0.2)",
          }}>
            Analyze My Content <ArrowRight size={18} />
          </Link>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer style={{ background: "#0F172A", padding: "40px 24px", textAlign: "center" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "10px", marginBottom: "12px" }}>
          <div style={{
            width: 28, height: 28, borderRadius: 8,
            background: "linear-gradient(135deg, #7C3AED, #6D28D9)",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <Zap size={13} color="white" />
          </div>
          <span style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 700, fontSize: "15px", color: "white" }}>
            RankReady
          </span>
        </div>
        <p style={{ fontSize: "13px", color: "#475569", marginBottom: "16px" }}>
          AI-powered SEO & AEO platform · Built with GPT-4o · 5-agent pipeline
        </p>
        <a
          href="https://www.linkedin.com/in/ashima-malik-ph-d-10740711a/"
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display: "inline-flex", alignItems: "center", gap: "8px",
            background: "rgba(10,102,194,0.15)", border: "1px solid rgba(10,102,194,0.3)",
            borderRadius: "100px", padding: "7px 18px", textDecoration: "none",
            transition: "background 0.15s",
          }}
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="#0A66C2">
            <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
          </svg>
          <span style={{ fontSize: "13px", fontWeight: 600, color: "#60A5FA" }}>Ashima Malik, Ph.D</span>
        </a>
      </footer>
    </div>
  );
}
