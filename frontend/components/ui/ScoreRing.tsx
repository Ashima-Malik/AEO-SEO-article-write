import { scoreColor } from "@/lib/utils";

interface ScoreRingProps {
  score: number;
  size?: number;
  showLabel?: boolean;
}

export function ScoreRing({ score, size = 72, showLabel = true }: ScoreRingProps) {
  const color = scoreColor(score);
  const strokeWidth = size > 60 ? 6 : 4;
  const radius = (size - strokeWidth * 2) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div className="relative flex items-center justify-center flex-shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" strokeWidth={strokeWidth} stroke="#E2E8F0" />
        <circle
          cx={size / 2} cy={size / 2} r={radius}
          fill="none" strokeWidth={strokeWidth} stroke={color}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 0.6s ease" }}
        />
      </svg>
      {showLabel && (
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span style={{
            fontFamily: "'Plus Jakarta Sans', sans-serif",
            fontWeight: 800,
            fontSize: size > 64 ? "22px" : size > 48 ? "16px" : "13px",
            color: "#0F172A",
            lineHeight: 1,
          }}>
            {score}
          </span>
          {size > 72 && (
            <span style={{ fontSize: "12px", color: "#94A3B8", marginTop: "2px" }}>/ 100</span>
          )}
        </div>
      )}
    </div>
  );
}
