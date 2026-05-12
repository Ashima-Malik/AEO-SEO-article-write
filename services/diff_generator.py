"""
Generates side-by-side diff between original and optimized content.
Each chunk is tagged with the SEO rule that triggered the change.
"""

import difflib
from typing import List
from models.schemas import DiffChunk


def generate_diff(original: str, optimized: str, changes_summary: List[dict] = None) -> List[DiffChunk]:
    """
    Generate word-level diff chunks between original and optimized text.
    Returns list of DiffChunk objects for the frontend diff viewer.
    """
    # Split into sentences for more meaningful diffs
    original_sentences = _split_into_sentences(original)
    optimized_sentences = _split_into_sentences(optimized)

    matcher = difflib.SequenceMatcher(
        None,
        original_sentences,
        optimized_sentences,
        autojunk=False
    )

    chunks: List[DiffChunk] = []
    changes_map = _build_changes_map(changes_summary or [])

    for opcode, i1, i2, j1, j2 in matcher.get_opcodes():
        if opcode == "equal":
            text = " ".join(original_sentences[i1:i2])
            if text.strip():
                chunks.append(DiffChunk(type="unchanged", content=text))

        elif opcode == "replace":
            removed_text = " ".join(original_sentences[i1:i2])
            added_text = " ".join(optimized_sentences[j1:j2])

            rule = _find_matching_rule(removed_text, added_text, changes_map)

            if removed_text.strip():
                chunks.append(DiffChunk(type="removed", content=removed_text, rule_applied=rule))
            if added_text.strip():
                chunks.append(DiffChunk(type="added", content=added_text, rule_applied=rule))

        elif opcode == "delete":
            text = " ".join(original_sentences[i1:i2])
            if text.strip():
                rule = _find_matching_rule(text, "", changes_map)
                chunks.append(DiffChunk(type="removed", content=text, rule_applied=rule))

        elif opcode == "insert":
            text = " ".join(optimized_sentences[j1:j2])
            if text.strip():
                rule = _find_matching_rule("", text, changes_map)
                chunks.append(DiffChunk(type="added", content=text, rule_applied=rule))

    return chunks


def _split_into_sentences(text: str) -> List[str]:
    """Split text into sentences, preserving headings as separate units."""
    import re
    # Split on sentence boundaries and headings
    parts = re.split(r'(?<=[.!?])\s+|(?=\n#+\s)', text)
    return [p.strip() for p in parts if p.strip()]


def _build_changes_map(changes_summary: List[dict]) -> dict:
    """Build a lookup map from change content to rule."""
    mapping = {}
    for change in changes_summary:
        if "original" in change and "rule" in change:
            key = change["original"][:50].lower().strip()
            mapping[key] = change["rule"]
    return mapping


def _find_matching_rule(removed: str, added: str, changes_map: dict) -> str:
    """Try to match a diff chunk to a known SEO rule."""
    key = removed[:50].lower().strip()
    if key in changes_map:
        return changes_map[key]

    # Heuristic matching based on content signals
    combined = (removed + " " + added).lower()

    if any(w in combined for w in ["h1", "heading", "title"]):
        return "H1 must contain primary keyword in first 6 words"
    if any(w in combined for w in ["meta description", "meta desc"]):
        return "Meta description: keyword + CTA, 150-160 chars"
    if any(w in combined for w in ["faq", "frequently asked"]):
        return "FAQ section: 5 questions with 40-60 word standalone answers"
    if any(w in combined for w in ["alt text", "alt="]):
        return "Image alt text: 10-25 words, includes primary keyword"
    if any(w in combined for w in ["author bio", "about the author"]):
        return "Author bio required: credentials + LinkedIn link"
    if any(w in combined for w in ["internal link", "click here", "read more"]):
        return "Internal links: descriptive anchor text, minimum 2 per article"
    if any(w in combined for w in ["keyword", "first paragraph", "first 100"]):
        return "Primary keyword must appear in first 100 words naturally"

    return "SEO optimization applied"


def calculate_improvement_summary(diff_chunks: List[DiffChunk]) -> dict:
    """Calculate summary stats from diff."""
    total = len(diff_chunks)
    added = sum(1 for c in diff_chunks if c.type == "added")
    removed = sum(1 for c in diff_chunks if c.type == "removed")
    unchanged = sum(1 for c in diff_chunks if c.type == "unchanged")

    change_percentage = round((added + removed) / max(total, 1) * 100, 1)

    rules_applied = list(set(
        c.rule_applied for c in diff_chunks
        if c.rule_applied and c.type in ("added", "removed")
    ))

    return {
        "total_chunks": total,
        "chunks_changed": added + removed,
        "chunks_unchanged": unchanged,
        "change_percentage": change_percentage,
        "rules_applied": rules_applied,
        "rules_applied_count": len(rules_applied),
    }
