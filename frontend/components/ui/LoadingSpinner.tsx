export function LoadingSpinner({ size = 24, color = "#7C3AED" }: { size?: number; color?: string }) {
  return (
    <div
      style={{
        width: size, height: size, borderRadius: "50%",
        border: `2.5px solid ${color}20`,
        borderTopColor: color,
        animation: "spin 0.7s linear infinite",
        flexShrink: 0,
      }}
    />
  );
}

export function PageLoader({ message = "Processing..." }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-32 gap-5">
      <div style={{
        width: 48, height: 48, borderRadius: "50%",
        border: "3px solid #EDE9FE",
        borderTopColor: "#7C3AED",
        animation: "spin 0.8s linear infinite",
      }} />
      <div className="text-center space-y-1">
        <p style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 600, fontSize: "17px", color: "#0F172A" }}>
          {message}
        </p>
        <p style={{ fontSize: "14px", color: "#94A3B8" }}>This takes 30–60 seconds — AI is working</p>
      </div>
    </div>
  );
}

// Inject spin keyframe once
if (typeof document !== "undefined") {
  const id = "__rr_spin";
  if (!document.getElementById(id)) {
    const s = document.createElement("style");
    s.id = id;
    s.textContent = "@keyframes spin{to{transform:rotate(360deg)}}";
    document.head.appendChild(s);
  }
}
