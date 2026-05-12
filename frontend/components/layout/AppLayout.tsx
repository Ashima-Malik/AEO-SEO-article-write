"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Search, Globe, Hash, PenTool, BarChart2, Zap, Bot, Target, FileSearch } from "lucide-react";

const NAV_SEO = [
  { href: "/analyzer", icon: Search,    label: "SEO Analyzer"    },
  { href: "/audit",    icon: Globe,     label: "Site Audit"      },
  { href: "/keywords", icon: Hash,      label: "Keywords"        },
  { href: "/writer",   icon: PenTool,   label: "AI Writer"       },
  { href: "/compare",  icon: BarChart2, label: "Compare"         },
];
const NAV_AEO = [
  { href: "/aeo",            icon: Bot,        label: "AEO Audit"       },
  { href: "/aeo/citation",   icon: Target,     label: "Citation Tracker" },
  { href: "/aeo/query-plan", icon: FileSearch, label: "Query Planner"   },
];

function NavItem({ href, icon: Icon, label, accent }: { href: string; icon: any; label: string; accent?: string }) {
  const pathname = usePathname();
  const active = pathname === href || (href !== "/" && pathname.startsWith(href + "/"));
  const activeColor = accent || "#7C3AED";
  const activeBg = accent === "#EA580C" ? "#FFF7ED" : "#F5F3FF";

  return (
    <Link href={href} style={{ textDecoration: "none" }}>
      <div style={{
        display: "flex", alignItems: "center", gap: "11px",
        padding: "10px 14px", borderRadius: "10px", marginBottom: "3px",
        background: active ? activeBg : "transparent",
        color: active ? activeColor : "#64748B",
        fontWeight: active ? 600 : 400,
        fontSize: "15px",
        transition: "all 0.15s",
        cursor: "pointer",
      }}
        onMouseEnter={e => { if (!active) (e.currentTarget as HTMLElement).style.background = "#F8FAFC"; }}
        onMouseLeave={e => { if (!active) (e.currentTarget as HTMLElement).style.background = "transparent"; }}>
        <Icon size={18} style={{ flexShrink: 0, color: active ? activeColor : "#94A3B8" }} />
        {label}
      </div>
    </Link>
  );
}

export function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "#F1F5F9" }}>

      {/* ── Sidebar ── */}
      <aside style={{
        width: "256px", flexShrink: 0,
        position: "fixed", top: 0, left: 0, height: "100vh",
        background: "#FFFFFF",
        borderRight: "1px solid #E2E8F0",
        display: "flex", flexDirection: "column",
        zIndex: 30,
      }}>

        {/* Logo */}
        <Link href="/" style={{ textDecoration: "none" }}>
          <div style={{
            display: "flex", alignItems: "center", gap: "10px",
            padding: "18px 16px", borderBottom: "1px solid #F1F5F9",
          }}>
            <div style={{
              width: 32, height: 32, borderRadius: "9px", flexShrink: 0,
              background: "linear-gradient(135deg, #7C3AED, #6D28D9)",
              display: "flex", alignItems: "center", justifyContent: "center",
              boxShadow: "0 2px 8px rgba(124,58,237,0.3)",
            }}>
              <Zap size={15} color="white" />
            </div>
            <span style={{
              fontFamily: "'Plus Jakarta Sans', sans-serif",
              fontWeight: 800, fontSize: "16px", color: "#0F172A", letterSpacing: "-0.3px",
            }}>RankReady</span>
          </div>
        </Link>

        {/* Navigation */}
        <nav style={{ flex: 1, padding: "12px 10px", overflowY: "auto" }}>
          <p style={{ fontSize: "12px", fontWeight: 700, color: "#94A3B8", letterSpacing: "0.08em", textTransform: "uppercase", padding: "6px 14px 10px" }}>
            SEO Tools
          </p>
          {NAV_SEO.map(item => <NavItem key={item.href} {...item} />)}

          <p style={{ fontSize: "12px", fontWeight: 700, color: "#94A3B8", letterSpacing: "0.08em", textTransform: "uppercase", padding: "18px 14px 10px" }}>
            AEO Tools
          </p>
          {NAV_AEO.map(item => <NavItem key={item.href} {...item} accent="#EA580C" />)}
        </nav>

        {/* Footer */}
        <div style={{ padding: "14px 16px", borderTop: "1px solid #F1F5F9" }}>
          <div style={{ fontSize: "13px", color: "#94A3B8", lineHeight: 1.6 }}>
            Powered by <span style={{ color: "#7C3AED", fontWeight: 600 }}>GPT-4o</span>
            <br />SEO + AEO agent pipeline
          </div>
        </div>
      </aside>

      {/* ── Main content ── */}
      <main style={{
        marginLeft: "256px",
        flex: 1,
        minHeight: "100vh",
        background: "#F8FAFC",
        display: "flex",
        flexDirection: "column",
      }}>
        {children}
      </main>
    </div>
  );
}
