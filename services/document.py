"""
Service to extract structured content from:
1. .docx files (via python-docx + docx2txt)
2. Plain text / markdown
3. URLs (via httpx + BeautifulSoup)
"""

import re
import httpx
from io import BytesIO
from typing import Optional
from bs4 import BeautifulSoup
from docx import Document
import docx2txt

from models.schemas import ExtractedContent, ContentType


# ---------- Content Type Detection ----------

def detect_content_type(text: str, title: str = "") -> ContentType:
    """Heuristic detection of content type from text signals."""
    combined = (title + " " + text[:500]).lower()

    bio_signals = ["i am", "i'm a", "founder of", "years of experience",
                   "newsletter", "follow me", "linkedin", "ph.d", "author of",
                   "my work", "about me", "bio", "speaker"]
    product_signals = ["pricing", "free trial", "get started", "sign up",
                       "features", "integrations", "enterprise", "per month",
                       "per user", "testimonials", "customers", "demo"]
    article_signals = ["in this article", "in this guide", "you'll learn",
                       "how to", "what is", "step 1", "step 2", "conclusion",
                       "introduction", "overview", "summary"]

    bio_score = sum(1 for s in bio_signals if s in combined)
    product_score = sum(1 for s in product_signals if s in combined)
    article_score = sum(1 for s in article_signals if s in combined)

    scores = {"bio": bio_score, "product": product_score, "article": article_score}
    best = max(scores, key=scores.get)

    if scores[best] == 0:
        return ContentType.GENERAL
    if best == "bio":
        return ContentType.BIO
    if best == "product":
        return ContentType.PRODUCT_PAGE
    return ContentType.ARTICLE


# ---------- DOCX Extraction ----------

def extract_from_docx(file_bytes: bytes) -> ExtractedContent:
    """Extract structured content from a .docx file."""
    doc = Document(BytesIO(file_bytes))
    full_text_raw = docx2txt.process(BytesIO(file_bytes))

    title = None
    h1 = None
    headings = []
    paragraphs = []
    images = []

    for para in doc.paragraphs:
        if not para.text.strip():
            continue

        style_name = para.style.name if para.style else ""

        if "Title" in style_name and not title:
            title = para.text.strip()
        elif style_name == "Heading 1":
            if not h1:
                h1 = para.text.strip()
            headings.append({"level": 1, "text": para.text.strip()})
        elif style_name == "Heading 2":
            headings.append({"level": 2, "text": para.text.strip()})
        elif style_name == "Heading 3":
            headings.append({"level": 3, "text": para.text.strip()})
        else:
            paragraphs.append(para.text.strip())

    # Check for FAQ section
    full_lower = full_text_raw.lower()
    has_faq = "faq" in full_lower or "frequently asked" in full_lower or "question" in full_lower

    # Check for author bio
    has_author_bio = any(phrase in full_lower for phrase in [
        "about the author", "author bio", "written by", "about me"
    ])

    # Word count
    word_count = len(full_text_raw.split())

    # Detect content type
    detected_type = detect_content_type(full_text_raw, title or h1 or "")

    return ExtractedContent(
        title=title,
        h1=h1,
        headings=headings,
        paragraphs=paragraphs,
        full_text=full_text_raw,
        word_count=word_count,
        images=images,
        has_faq=has_faq,
        has_author_bio=has_author_bio,
        detected_content_type=detected_type,
    )


# ---------- Plain Text Extraction ----------

def extract_from_text(text: str, filename: Optional[str] = None) -> ExtractedContent:
    """Extract structured content from plain text or markdown."""
    lines = text.split("\n")
    headings = []
    paragraphs = []
    h1 = None
    title = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Markdown headings
        if line.startswith("# "):
            h1 = line[2:].strip() if not h1 else h1
            headings.append({"level": 1, "text": line[2:].strip()})
        elif line.startswith("## "):
            headings.append({"level": 2, "text": line[3:].strip()})
        elif line.startswith("### "):
            headings.append({"level": 3, "text": line[4:].strip()})
        else:
            paragraphs.append(line)

    # Extract internal/external links from markdown
    internal_links = re.findall(r'\[.*?\]\((/[^)]+)\)', text)
    external_links = re.findall(r'\[.*?\]\((https?://[^)]+)\)', text)

    full_lower = text.lower()
    has_faq = "faq" in full_lower or "frequently asked" in full_lower
    has_author_bio = "about the author" in full_lower or "written by" in full_lower

    word_count = len(text.split())
    detected_type = detect_content_type(text, h1 or "")

    return ExtractedContent(
        title=title,
        h1=h1,
        headings=headings,
        paragraphs=paragraphs,
        full_text=text,
        word_count=word_count,
        internal_links=internal_links,
        external_links=external_links,
        has_faq=has_faq,
        has_author_bio=has_author_bio,
        detected_content_type=detected_type,
    )


# ---------- URL Extraction ----------

async def extract_from_url(url: str) -> ExtractedContent:
    """
    Fetch and extract content from a public URL.
    Raises ValueError if the page requires authentication or returns an error.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; SEOAnalyzer/1.0)",
        "Accept": "text/html,application/xhtml+xml",
    }

    async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
        try:
            response = await client.get(url, headers=headers)
        except httpx.ConnectError:
            raise ValueError(f"Could not connect to {url}. Please check the URL and try again.")
        except httpx.TimeoutException:
            raise ValueError(f"Request timed out fetching {url}. The site may be too slow.")

    if response.status_code == 401 or response.status_code == 403:
        raise ValueError(
            "This page requires login or is behind a paywall. "
            "Please copy and paste the text content directly instead."
        )
    if response.status_code == 404:
        raise ValueError(f"Page not found (404): {url}")
    if response.status_code >= 400:
        raise ValueError(
            f"Could not access this page (HTTP {response.status_code}). "
            "Please paste the content as text instead."
        )

    soup = BeautifulSoup(response.text, "lxml")

    # Remove script/style/nav/footer noise
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
        tag.decompose()

    # Extract meta
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else None

    meta_desc_tag = soup.find("meta", attrs={"name": "description"})
    meta_description = meta_desc_tag.get("content", "").strip() if meta_desc_tag else None

    # Extract URL slug
    from urllib.parse import urlparse
    parsed = urlparse(url)
    url_slug = parsed.path.strip("/").split("/")[-1] if parsed.path else ""

    # Extract headings
    h1 = None
    headings = []
    for level in range(1, 7):
        for tag in soup.find_all(f"h{level}"):
            text = tag.get_text(strip=True)
            if level == 1 and not h1:
                h1 = text
            headings.append({"level": level, "text": text})

    # Extract paragraphs
    paragraphs = [p.get_text(strip=True) for p in soup.find_all("p") if p.get_text(strip=True)]

    # Extract images
    images = []
    for img in soup.find_all("img"):
        images.append({
            "src": img.get("src", ""),
            "alt": img.get("alt", ""),
            "caption": ""
        })

    # Extract links
    base_domain = f"{parsed.scheme}://{parsed.netloc}"
    internal_links = []
    external_links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("/") or base_domain in href:
            internal_links.append(href)
        elif href.startswith("http"):
            external_links.append(href)

    full_text = soup.get_text(separator=" ", strip=True)
    full_text = re.sub(r'\s+', ' ', full_text)

    full_lower = full_text.lower()
    has_faq = "faq" in full_lower or "frequently asked" in full_lower
    has_author_bio = "about the author" in full_lower or "written by" in full_lower

    word_count = len(full_text.split())
    detected_type = detect_content_type(full_text, title or h1 or "")

    return ExtractedContent(
        title=title,
        h1=h1,
        meta_description=meta_description,
        url_slug=url_slug,
        headings=headings,
        paragraphs=paragraphs,
        full_text=full_text,
        word_count=word_count,
        images=images,
        internal_links=list(set(internal_links))[:20],
        external_links=list(set(external_links))[:20],
        has_faq=has_faq,
        has_author_bio=has_author_bio,
        detected_content_type=detected_type,
    )
