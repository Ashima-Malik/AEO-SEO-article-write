interface TopBarProps {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}

export function TopBar({ title, subtitle, actions }: TopBarProps) {
  return (
    <div className="sticky top-0 z-10 px-6 py-4 flex items-center gap-4"
      style={{
        background: "rgba(255,255,255,0.92)",
        backdropFilter: "blur(12px)",
        borderBottom: "1px solid #E2E8F0",
      }}>
      <div className="flex-1 min-w-0">
        <h1 style={{
          fontFamily: "'Plus Jakarta Sans', sans-serif",
          fontWeight: 700, fontSize: "24px", color: "#0F172A", lineHeight: 1.3,
        }}>
          {title}
        </h1>
        {subtitle && (
          <p style={{ fontSize: "15px", color: "#94A3B8", marginTop: "3px" }}>{subtitle}</p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2 flex-shrink-0">{actions}</div>}
    </div>
  );
}
