import Link from "next/link";

export default function NotFound() {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100vh", gap: "12px", fontFamily: "system-ui, sans-serif" }}>
      <p style={{ fontSize: "48px", fontWeight: 800, color: "#E2E8F0" }}>404</p>
      <p style={{ fontSize: "16px", color: "#334155", fontWeight: 600 }}>Page not found</p>
      <Link href="/" style={{ padding: "8px 20px", background: "#7C3AED", color: "white", borderRadius: "8px", textDecoration: "none", fontSize: "14px" }}>
        Go home
      </Link>
    </div>
  );
}
