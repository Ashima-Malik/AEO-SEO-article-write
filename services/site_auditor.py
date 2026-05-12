"""
Site Auditor Service
---------------------
Pure HTML/BeautifulSoup analysis — no LLM, no token cost.
Checks 20+ technical and on-page SEO signals.
Returns structured AuditSection list + critical issues list.
"""

import re
import httpx
from bs4 import BeautifulSoup
from models.schemas import AuditCheck, AuditSection


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


async def fetch_page(url: str) -> tuple[BeautifulSoup, str, int]:
    """Fetch a URL and return (soup, raw_html, status_code)."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
        resp = await client.get(url, headers=HEADERS)
        soup = BeautifulSoup(resp.text, "html.parser")
        return soup, resp.text, resp.status_code


# ── Individual check functions ─────────────────────────────────────────────────

def _check_title(soup: BeautifulSoup, keyword: str | None) -> AuditCheck:
    tag = soup.find("title")
    if not tag or not tag.get_text(strip=True):
        return AuditCheck(name="Title Tag", passed=False, severity="critical",
                          value="Missing", recommendation="Add a title tag with primary keyword + year + brand, under 60 chars.")
    title = tag.get_text(strip=True)
    length = len(title)
    has_kw = keyword and keyword.lower() in title.lower()
    if length > 60:
        return AuditCheck(name="Title Tag", passed=False, severity="high",
                          value=f"{length} chars: \"{title[:50]}...\"",
                          recommendation=f"Shorten to under 60 chars. Currently {length} chars.")
    if keyword and not has_kw:
        return AuditCheck(name="Title Tag", passed=False, severity="high",
                          value=f"\"{title}\"",
                          recommendation=f"Include primary keyword \"{keyword}\" in the title tag.")
    return AuditCheck(name="Title Tag", passed=True, severity="info",
                      value=f"{length} chars: \"{title}\"")


def _check_meta_description(soup: BeautifulSoup, keyword: str | None) -> AuditCheck:
    tag = soup.find("meta", attrs={"name": "description"})
    if not tag or not tag.get("content", "").strip():
        return AuditCheck(name="Meta Description", passed=False, severity="high",
                          value="Missing",
                          recommendation="Add a meta description with keyword + CTA, 150-160 chars.")
    content = tag["content"].strip()
    length = len(content)
    if length < 120:
        return AuditCheck(name="Meta Description", passed=False, severity="medium",
                          value=f"{length} chars (too short)",
                          recommendation="Expand meta description to 150-160 chars.")
    if length > 165:
        return AuditCheck(name="Meta Description", passed=False, severity="medium",
                          value=f"{length} chars (too long — Google will truncate)",
                          recommendation="Shorten meta description to 150-160 chars.")
    return AuditCheck(name="Meta Description", passed=True, severity="info",
                      value=f"{length} chars")


def _check_h1(soup: BeautifulSoup, keyword: str | None) -> AuditCheck:
    h1s = soup.find_all("h1")
    if not h1s:
        return AuditCheck(name="H1 Tag", passed=False, severity="critical",
                          value="Missing", recommendation="Add exactly one H1 tag with your primary keyword in the first 3 words.")
    if len(h1s) > 1:
        return AuditCheck(name="H1 Tag", passed=False, severity="high",
                          value=f"{len(h1s)} H1 tags found",
                          recommendation="Use exactly one H1 per page. Remove duplicate H1 tags.")
    h1_text = h1s[0].get_text(strip=True)
    if keyword and keyword.lower() not in h1_text.lower():
        return AuditCheck(name="H1 Tag", passed=False, severity="high",
                          value=f"\"{h1_text}\"",
                          recommendation=f"Include primary keyword \"{keyword}\" in the H1, ideally in the first 3 words.")
    return AuditCheck(name="H1 Tag", passed=True, severity="info", value=f"\"{h1_text[:60]}\"")


def _check_heading_structure(soup: BeautifulSoup) -> AuditCheck:
    headings = soup.find_all(["h1", "h2", "h3", "h4"])
    if len(headings) < 3:
        return AuditCheck(name="Heading Structure", passed=False, severity="medium",
                          value=f"Only {len(headings)} headings found",
                          recommendation="Add more H2/H3 headings — aim for one heading every 300 words.")
    # Check for skipped levels (H1 → H3 without H2)
    levels = [int(h.name[1]) for h in headings]
    skipped = any(levels[i+1] - levels[i] > 1 for i in range(len(levels)-1))
    if skipped:
        return AuditCheck(name="Heading Structure", passed=False, severity="medium",
                          value=f"{len(headings)} headings, hierarchy skips detected",
                          recommendation="Fix heading hierarchy — never skip from H2 to H4. Use H1→H2→H3 in order.")
    return AuditCheck(name="Heading Structure", passed=True, severity="info",
                      value=f"{len(headings)} headings with proper hierarchy")


def _check_images(soup: BeautifulSoup) -> AuditCheck:
    images = soup.find_all("img")
    if not images:
        return AuditCheck(name="Image Alt Text", passed=False, severity="medium",
                          value="No images found",
                          recommendation="Add images with descriptive alt text including your primary keyword.")
    missing_alt = [img for img in images if not img.get("alt", "").strip()]
    if missing_alt:
        return AuditCheck(name="Image Alt Text", passed=False, severity="high",
                          value=f"{len(missing_alt)}/{len(images)} images missing alt text",
                          recommendation=f"Add descriptive alt text to {len(missing_alt)} image(s). Include primary keyword in at least one.")
    return AuditCheck(name="Image Alt Text", passed=True, severity="info",
                      value=f"All {len(images)} images have alt text")


def _check_canonical(soup: BeautifulSoup) -> AuditCheck:
    tag = soup.find("link", attrs={"rel": "canonical"})
    if not tag or not tag.get("href"):
        return AuditCheck(name="Canonical Tag", passed=False, severity="medium",
                          value="Missing",
                          recommendation="Add a canonical tag to prevent duplicate content issues.")
    return AuditCheck(name="Canonical Tag", passed=True, severity="info",
                      value=tag["href"])


def _check_viewport(soup: BeautifulSoup) -> AuditCheck:
    tag = soup.find("meta", attrs={"name": "viewport"})
    if not tag:
        return AuditCheck(name="Mobile Viewport", passed=False, severity="high",
                          value="Missing",
                          recommendation="Add <meta name='viewport' content='width=device-width, initial-scale=1'>")
    return AuditCheck(name="Mobile Viewport", passed=True, severity="info",
                      value=tag.get("content", "present"))


def _check_schema(soup: BeautifulSoup) -> AuditCheck:
    scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
    if not scripts:
        return AuditCheck(name="Schema Markup (JSON-LD)", passed=False, severity="medium",
                          value="Missing",
                          recommendation="Add Article schema + FAQ schema. Use Google's Rich Results Test to validate.")
    schema_types = []
    for s in scripts:
        text = s.get_text()
        if '"@type"' in text:
            match = re.search(r'"@type"\s*:\s*"([^"]+)"', text)
            if match:
                schema_types.append(match.group(1))
    return AuditCheck(name="Schema Markup (JSON-LD)", passed=True, severity="info",
                      value=f"Found: {', '.join(schema_types) or 'JSON-LD present'}")


def _check_og_tags(soup: BeautifulSoup) -> AuditCheck:
    og_title = soup.find("meta", property="og:title")
    og_desc = soup.find("meta", property="og:description")
    og_image = soup.find("meta", property="og:image")
    missing = []
    if not og_title: missing.append("og:title")
    if not og_desc: missing.append("og:description")
    if not og_image: missing.append("og:image")
    if missing:
        return AuditCheck(name="Open Graph Tags", passed=False, severity="low",
                          value=f"Missing: {', '.join(missing)}",
                          recommendation=f"Add missing Open Graph tags: {', '.join(missing)}. Required for rich social sharing.")
    return AuditCheck(name="Open Graph Tags", passed=True, severity="info",
                      value="og:title, og:description, og:image all present")


def _check_robots_meta(soup: BeautifulSoup) -> AuditCheck:
    tag = soup.find("meta", attrs={"name": "robots"})
    if tag:
        content = tag.get("content", "").lower()
        if "noindex" in content:
            return AuditCheck(name="Robots Meta", passed=False, severity="critical",
                              value=f"noindex detected: \"{content}\"",
                              recommendation="Remove noindex directive — this page is blocked from Google indexing.")
        if "nofollow" in content:
            return AuditCheck(name="Robots Meta", passed=False, severity="high",
                              value=f"nofollow detected: \"{content}\"",
                              recommendation="Review nofollow — Google cannot follow links on this page.")
    return AuditCheck(name="Robots Meta", passed=True, severity="info",
                      value=tag.get("content", "index, follow (default)") if tag else "index, follow (default)")


def _check_word_count(soup: BeautifulSoup) -> AuditCheck:
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    count = len(text.split())
    if count < 300:
        return AuditCheck(name="Word Count", passed=False, severity="high",
                          value=f"{count} words (thin content)",
                          recommendation="Expand content to at least 800 words. Thin content rarely ranks.")
    if count < 800:
        return AuditCheck(name="Word Count", passed=False, severity="medium",
                          value=f"{count} words (below recommended)",
                          recommendation="Consider expanding to 1000+ words for better topical coverage.")
    return AuditCheck(name="Word Count", passed=True, severity="info",
                      value=f"{count} words")


def _check_internal_links(soup: BeautifulSoup, page_url: str) -> AuditCheck:
    from urllib.parse import urlparse
    domain = urlparse(page_url).netloc
    all_links = soup.find_all("a", href=True)
    internal = [a for a in all_links if domain in a["href"] or a["href"].startswith("/")]
    if len(internal) < 2:
        return AuditCheck(name="Internal Links", passed=False, severity="medium",
                          value=f"{len(internal)} internal link(s)",
                          recommendation="Add at least 2 internal links with descriptive anchor text.")
    return AuditCheck(name="Internal Links", passed=True, severity="info",
                      value=f"{len(internal)} internal links")


def _check_external_links(soup: BeautifulSoup, page_url: str) -> AuditCheck:
    from urllib.parse import urlparse
    domain = urlparse(page_url).netloc
    all_links = soup.find_all("a", href=True)
    external = [a for a in all_links
                if a["href"].startswith("http") and domain not in a["href"]]
    if len(external) == 0:
        return AuditCheck(name="External Authority Links", passed=False, severity="low",
                          value="0 external links",
                          recommendation="Add 1-2 external links to high-authority sources (research papers, official docs).")
    return AuditCheck(name="External Authority Links", passed=True, severity="info",
                      value=f"{len(external)} external links")


def _check_favicon(soup: BeautifulSoup) -> AuditCheck:
    favicon = soup.find("link", rel=lambda r: r and "icon" in r)
    if not favicon:
        return AuditCheck(name="Favicon", passed=False, severity="low",
                          value="Missing", recommendation="Add a favicon for brand recognition in browser tabs.")
    return AuditCheck(name="Favicon", passed=True, severity="info", value="Present")


def _check_https(url: str) -> AuditCheck:
    if not url.startswith("https://"):
        return AuditCheck(name="HTTPS", passed=False, severity="critical",
                          value="HTTP (not secure)",
                          recommendation="Migrate to HTTPS immediately. Google ranks HTTPS pages higher and browsers warn users on HTTP.")
    return AuditCheck(name="HTTPS", passed=True, severity="info", value="HTTPS enabled")


# ── Section builders ──────────────────────────────────────────────────────────

def _score_section(checks: list[AuditCheck]) -> int:
    """0-100 score. Passing checks count as weight 1; failing checks penalize by severity."""
    weights = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 1}
    total_weight = sum(weights.get(c.severity, 1) for c in checks)
    passed_weight = sum(weights.get(c.severity, 1) for c in checks if c.passed)
    return round(passed_weight / total_weight * 100) if total_weight > 0 else 100


def build_audit_sections(soup: BeautifulSoup, url: str, keyword: str | None) -> list[AuditSection]:
    on_page_checks = [
        _check_title(soup, keyword),
        _check_meta_description(soup, keyword),
        _check_h1(soup, keyword),
        _check_heading_structure(soup),
        _check_word_count(soup),
    ]

    technical_checks = [
        _check_https(url),
        _check_canonical(soup),
        _check_viewport(soup),
        _check_schema(soup),
        _check_robots_meta(soup),
        _check_favicon(soup),
    ]

    content_checks = [
        _check_images(soup),
        _check_internal_links(soup, url),
        _check_external_links(soup, url),
        _check_og_tags(soup),
    ]

    sections = [
        AuditSection(name="On-Page SEO", score=_score_section(on_page_checks), checks=on_page_checks),
        AuditSection(name="Technical", score=_score_section(technical_checks), checks=technical_checks),
        AuditSection(name="Content & Links", score=_score_section(content_checks), checks=content_checks),
    ]
    return sections


def compute_overall_score(sections: list[AuditSection]) -> int:
    """Weighted average: On-Page 40%, Technical 40%, Content 20%."""
    weights = [0.4, 0.4, 0.2]
    return round(sum(s.score * w for s, w in zip(sections, weights)))


def score_to_grade(score: int) -> str:
    if score >= 90: return "A"
    if score >= 80: return "B"
    if score >= 70: return "C"
    if score >= 60: return "D"
    return "F"


def collect_critical_issues(sections: list[AuditSection]) -> list[str]:
    issues = []
    for section in sections:
        for check in section.checks:
            if not check.passed and check.severity in ("critical", "high"):
                issues.append(f"{check.name}: {check.value or 'failed'}")
    return issues
