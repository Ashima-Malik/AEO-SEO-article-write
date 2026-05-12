export function scoreColor(score: number): string {
  if (score >= 90) return "#10B981";
  if (score >= 80) return "#3B82F6";
  if (score >= 70) return "#F59E0B";
  if (score >= 60) return "#F97316";
  return "#EF4444";
}
export function scoreLabel(score: number): string {
  if (score >= 90) return "Excellent";
  if (score >= 80) return "Good";
  if (score >= 70) return "Acceptable";
  if (score >= 60) return "Needs Work";
  return "Not Ready";
}
export function scoreBg(score: number): string {
  if (score >= 90) return "#F0FDF4";
  if (score >= 80) return "#EFF6FF";
  if (score >= 70) return "#FFFBEB";
  if (score >= 60) return "#FFF7ED";
  return "#FEF2F2";
}
export function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return String(n);
}
export function cn(...classes: (string | undefined | false)[]): string {
  return classes.filter(Boolean).join(" ");
}
