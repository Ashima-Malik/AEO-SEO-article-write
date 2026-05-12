"""
Report Generator Service
-------------------------
Converts analysis data into a print-ready HTML report.
No LLM calls — pure Python formatting. Zero token cost.
The frontend can render this HTML and trigger window.print() for PDF.
"""

import re
from datetime import datetime


def _md_to_html_basic(text: str) -> str:
    """Minimal markdown → HTML conversion for report body."""
    text = re.sub(r'^### (.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.+)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.+)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    text = re.sub(r'\n\n+', '</p><p>', text)
    text = re.sub(r'^\- (.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)
    text = re.sub(r'(<li>.*</li>)', r'<ul>\1</ul>', text, flags=re.DOTALL)
    return f"<p>{text}</p>"


_REPORT_CSS = """
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 900px; margin: 0 auto; padding: 40px 24px; color: #1a1a2e; line-height: 1.6; }
  .header { border-bottom: 3px solid #6366f1; padding-bottom: 24px; margin-bottom: 32px; }
  .header h1 { font-size: 28px; margin: 0 0 8px; color: #1a1a2e; }
  .header .meta { color: #64748b; font-size: 14px; }
  .score-badge { display: inline-block; background: #6366f1; color: white; font-size: 48px; font-weight: 700; padding: 12px 24px; border-radius: 12px; margin: 16px 0; }
  .score-badge.good { background: #22c55e; }
  .score-badge.acceptable { background: #f59e0b; }
  .score-badge.bad { background: #ef4444; }
  .section { margin: 32px 0; padding: 24px; border: 1px solid #e2e8f0; border-radius: 12px; }
  .section h2 { margin: 0 0 16px; font-size: 18px; color: #1a1a2e; border-bottom: 1px solid #e2e8f0; padding-bottom: 12px; }
  .check { display: flex; align-items: flex-start; gap: 12px; padding: 10px 0; border-bottom: 1px solid #f1f5f9; }
  .check:last-child { border-bottom: none; }
  .check-icon { font-size: 16px; margin-top: 2px; flex-shrink: 0; }
  .check-name { font-weight: 600; font-size: 14px; }
  .check-value { font-size: 13px; color: #64748b; margin-top: 2px; }
  .check-rec { font-size: 13px; color: #dc2626; margin-top: 4px; }
  .severity-critical { color: #dc2626; }
  .severity-high { color: #ea580c; }
  .severity-medium { color: #d97706; }
  .tag { display: inline-block; background: #f1f5f9; border-radius: 6px; padding: 2px 8px; font-size: 12px; margin: 2px; }
  .next-steps ol { padding-left: 20px; }
  .next-steps li { margin: 12px 0; font-size: 14px; }
  .content-body { white-space: pre-wrap; font-size: 15px; line-height: 1.8; }
  @media print { body { padding: 20px; } .no-print { display: none; } }
"""


def generate_analysis_report(
    title: str,
    url: str,
    score_before: int,
    score_after: int,
    rating: str,
    top_issues: list[str],
    quick_wins: list[str],
    optimized_content: str,
    changes_made: list[dict],
    suggested_title_tag: str,
    suggested_meta_description: str,
    suggested_url_slug: str,
) -> str:
    """Generate a print-ready HTML report for a full SEO analysis."""

    score_class = "good" if score_after >= 80 else ("acceptable" if score_after >= 60 else "bad")
    now = datetime.now().strftime("%B %d, %Y")

    issues_html = "".join(f"<li>{issue}</li>" for issue in top_issues[:5])
    wins_html = "".join(f"<li>{win}</li>" for win in quick_wins[:3])
    changes_html = "".join(
        f"<div class='check'><span class='check-icon'>✏️</span><div>"
        f"<div class='check-name'>{c.get('location', '')}</div>"
        f"<div class='check-value'>Rule: {c.get('rule', '')}</div></div></div>"
        for c in changes_made[:10]
    )

    content_preview = optimized_content[:3000] + ("..." if len(optimized_content) > 3000 else "")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SEO Analysis Report — {title}</title>
<style>{_REPORT_CSS}</style>
</head>
<body>
<div class="header">
  <h1>SEO Analysis Report</h1>
  <div class="meta">URL: {url} &nbsp;|&nbsp; Generated: {now}</div>
</div>

<div class="section">
  <h2>Score Summary</h2>
  <div>Before: <strong>{score_before}/100</strong> → After: <span class="score-badge {score_class}">{score_after}</span></div>
  <div style="margin-top:12px;color:#64748b;">Rating: {rating}</div>
</div>

<div class="section">
  <h2>SEO Metadata Suggestions</h2>
  <div class="check"><div><div class="check-name">Title Tag</div><div class="check-value">{suggested_title_tag}</div></div></div>
  <div class="check"><div><div class="check-name">Meta Description</div><div class="check-value">{suggested_meta_description}</div></div></div>
  <div class="check"><div><div class="check-name">URL Slug</div><div class="check-value">{suggested_url_slug}</div></div></div>
</div>

<div class="section">
  <h2>Top Issues to Fix</h2>
  <ul>{issues_html}</ul>
</div>

<div class="section">
  <h2>Quick Wins</h2>
  <ul>{wins_html}</ul>
</div>

<div class="section">
  <h2>Changes Made ({len(changes_made)} optimizations)</h2>
  {changes_html}
</div>

<div class="section">
  <h2>Optimized Content Preview</h2>
  <div class="content-body">{content_preview}</div>
</div>

<div style="text-align:center;margin-top:40px;color:#94a3b8;font-size:12px;">
  Generated by AI SEO Analyzer &nbsp;|&nbsp; {now}
</div>
</body>
</html>"""


def generate_audit_report(
    url: str,
    overall_score: int,
    grade: str,
    sections: list,
    top_recommendations: list[str],
) -> str:
    """Generate a print-ready HTML report for a site audit."""
    now = datetime.now().strftime("%B %d, %Y")
    score_class = "good" if overall_score >= 80 else ("acceptable" if overall_score >= 60 else "bad")

    severity_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "✅"}

    sections_html = ""
    for section in sections:
        checks_html = ""
        for check in section.checks:
            icon = "✅" if check.passed else severity_icon.get(check.severity, "⚠️")
            rec_html = f"<div class='check-rec'>→ {check.recommendation}</div>" if not check.passed and check.recommendation else ""
            checks_html += f"""
            <div class="check">
              <span class="check-icon">{icon}</span>
              <div>
                <div class="check-name">{check.name}</div>
                <div class="check-value">{check.value or ''}</div>
                {rec_html}
              </div>
            </div>"""
        sections_html += f"""
        <div class="section">
          <h2>{section.name} — {section.score}/100</h2>
          {checks_html}
        </div>"""

    recs_html = "".join(f"<li>{r}</li>" for r in top_recommendations)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Site Audit Report — {url}</title>
<style>{_REPORT_CSS}</style>
</head>
<body>
<div class="header">
  <h1>Technical Site Audit</h1>
  <div class="meta">{url} &nbsp;|&nbsp; {now}</div>
</div>

<div class="section">
  <h2>Overall Score</h2>
  <div class="score-badge {score_class}">{overall_score}</div>
  <div style="font-size:32px;font-weight:700;margin-left:16px;display:inline;">Grade: {grade}</div>
</div>

<div class="section next-steps">
  <h2>Top 3 Priority Recommendations</h2>
  <ol>{recs_html}</ol>
</div>

{sections_html}

<div style="text-align:center;margin-top:40px;color:#94a3b8;font-size:12px;">
  Generated by AI SEO Analyzer &nbsp;|&nbsp; {now}
</div>
</body>
</html>"""
