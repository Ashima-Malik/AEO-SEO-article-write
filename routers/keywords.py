"""
Keywords Router
---------------
POST /keywords/cluster  — Generate keyword clusters by search intent
POST /keywords/brief    — Generate a full content brief
"""

import time
import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks

from models.schemas import (
    KeywordClusterRequest, KeywordClusterResponse, KeywordGroup,
    ContentBriefRequest, ContentBriefResponse, BriefSection,
    ContentType,
)
from agents.keyword_clusterer import run_keyword_clusterer
from agents.brief_writer import run_brief_writer
from services.token_tracker import aggregate_token_usage
from services.auth import get_current_user, increment_user_tokens

router = APIRouter(prefix="/keywords", tags=["keywords"])


@router.post("/cluster", response_model=KeywordClusterResponse)
async def cluster_keywords(
    request: KeywordClusterRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    """
    Generate keyword clusters for a topic, grouped by search intent.

    Returns:
    - **primary_keyword**: best single keyword to target
    - **clusters**: informational, transactional, navigational, long-tail (5-8 keywords each)
    - **paa_questions**: 5 People Also Ask questions to use as H2/H3 headers
    - **semantic_keywords**: LSI / entity keywords to weave into content naturally
    - **negative_keywords**: keywords to avoid (too broad or off-target)

    All tokens tracked.
    """
    start_time = time.time()
    ct = request.content_type.value if request.content_type else "article"

    data, usage = await run_keyword_clusterer(
        topic=request.topic,
        seed_keywords=request.seed_keywords,
        content_type=ct,
    )
    token_usage = aggregate_token_usage([usage])

    clusters = [
        KeywordGroup(
            intent=c.get("intent", "informational"),
            keywords=c.get("keywords", []),
            rationale=c.get("rationale", ""),
        )
        for c in data.get("clusters", [])
    ]

    background_tasks.add_task(increment_user_tokens, user["id"], token_usage)

    return KeywordClusterResponse(
        topic=request.topic,
        primary_keyword=data.get("primary_keyword", request.topic),
        clusters=clusters,
        paa_questions=data.get("paa_questions", []),
        semantic_keywords=data.get("semantic_keywords", []),
        negative_keywords=data.get("negative_keywords", []),
        token_usage=token_usage,
        processing_time_seconds=round(time.time() - start_time, 2),
    )


@router.post("/brief", response_model=ContentBriefResponse)
async def generate_brief(
    request: ContentBriefRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    """
    Generate a complete content brief for a target keyword.

    Returns a full brief including:
    - Suggested title, meta description, URL slug
    - Target word count and reading level
    - Section-by-section outline (H2/H3) with key points per section
    - 5 FAQ questions (40-60 word answers, featured snippet bait)
    - E-E-A-T signals to include (one per dimension)
    - Internal link suggestions + authoritative external sources

    Replaces Clearscope / Surfer SEO briefs. Tokens tracked.
    """
    start_time = time.time()
    brief_id = str(uuid.uuid4())
    ct = request.content_type or ContentType.ARTICLE

    kws = request.target_keywords or []
    if request.primary_keyword not in kws:
        kws = [request.primary_keyword] + kws

    data, usage = await run_brief_writer(
        primary_keyword=request.primary_keyword,
        target_keywords=kws,
        content_type=ct.value,
        topic_context=request.topic_context,
    )
    token_usage = aggregate_token_usage([usage])

    sections = [
        BriefSection(
            heading=s.get("heading", ""),
            level=s.get("level", 2),
            target_word_count=s.get("target_word_count", 200),
            key_points=s.get("key_points", []),
            suggested_keywords=s.get("suggested_keywords", []),
        )
        for s in data.get("sections", [])
    ]

    background_tasks.add_task(increment_user_tokens, user["id"], token_usage)

    return ContentBriefResponse(
        brief_id=brief_id,
        primary_keyword=request.primary_keyword,
        target_keywords=kws[:5],
        content_type=ct,
        suggested_title=data.get("suggested_title", ""),
        suggested_meta_description=data.get("suggested_meta_description", ""),
        suggested_url_slug=data.get("suggested_url_slug", ""),
        target_word_count=data.get("target_word_count", 1500),
        target_reading_level=data.get("target_reading_level", "Professional"),
        sections=sections,
        faq_questions=data.get("faq_questions", []),
        eeat_signals_to_include=data.get("eeat_signals_to_include", []),
        internal_link_suggestions=data.get("internal_link_suggestions", []),
        external_source_suggestions=data.get("external_source_suggestions", []),
        content_angle=data.get("content_angle", ""),
        token_usage=token_usage,
        processing_time_seconds=round(time.time() - start_time, 2),
    )
