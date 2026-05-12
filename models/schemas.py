from pydantic import BaseModel, field_validator
from typing import Optional, List, Literal, Any
from enum import Enum


class InputType(str, Enum):
    DOCUMENT = "document"
    URL = "url"
    TEXT = "text"


class ContentType(str, Enum):
    ARTICLE = "article"
    BIO = "bio"
    PRODUCT_PAGE = "product_page"
    GENERAL = "general"


class SubscriptionTier(str, Enum):
    STARTER = "starter"
    PRO = "pro"
    AGENCY = "agency"


class TokenWarningLevel(str, Enum):
    OK = "ok"           # < 80% tokens used
    WARNING = "warning" # >= 80% — analysis still works, warning shown
    BLOCKED = "blocked" # >= 100% — blocked until next monthly reset


# ---------- Request Models ----------

class AnalyzeURLRequest(BaseModel):
    url: str
    target_keyword: Optional[str] = None
    target_keywords: Optional[List[str]] = None   # up to 5; overrides target_keyword if provided
    content_type: Optional[ContentType] = None
    user_tone_prompt: Optional[str] = None        # e.g. "Write in a confident, direct tone for senior PMs"
    user_brief: Optional[str] = None              # user's brief — expertise, audience, key points to cover


class AnalyzeTextRequest(BaseModel):
    text: str
    target_keyword: Optional[str] = None
    target_keywords: Optional[List[str]] = None   # up to 5; overrides target_keyword if provided
    content_type: Optional[ContentType] = None
    filename: Optional[str] = None
    user_tone_prompt: Optional[str] = None        # e.g. "Conversational but expert, like a newsletter"
    user_brief: Optional[str] = None              # user's brief — expertise, audience, key points to cover


# ---------- Token Usage Models ----------

class AgentTokenUsage(BaseModel):
    agent_name: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


class AnalysisTokenUsage(BaseModel):
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    per_agent: List[AgentTokenUsage] = []


# ---------- SEO Score Models ----------

class ScoringCriterion(BaseModel):
    name: str
    score: int
    max_score: int
    rating: Literal["excellent", "good", "acceptable", "needs_work", "missing"]
    issue: Optional[str] = None
    fix: Optional[str] = None
    severity: Literal["critical", "high", "medium", "low"] = "medium"


class EEATAnalysis(BaseModel):
    experience_score: int
    expertise_score: int
    authority_score: int
    trust_score: int
    signals_found: List[str]
    signals_missing: List[str]


class SEOScore(BaseModel):
    overall: int
    rating: str
    rating_emoji: str
    publish_recommendation: str
    criteria: List[ScoringCriterion]
    eeat: EEATAnalysis
    top_issues: List[str]
    quick_wins: List[str]


# ---------- Content Models ----------

class ExtractedContent(BaseModel):
    title: Optional[str] = None
    h1: Optional[str] = None
    meta_description: Optional[str] = None
    url_slug: Optional[str] = None
    headings: List[dict] = []
    paragraphs: List[str] = []
    full_text: str = ""
    word_count: int = 0
    images: List[dict] = []
    internal_links: List[str] = []
    external_links: List[str] = []
    has_faq: bool = False
    has_author_bio: bool = False
    detected_content_type: ContentType = ContentType.GENERAL


class DiffChunk(BaseModel):
    type: Literal["unchanged", "added", "removed"]
    content: str
    rule_applied: Optional[str] = None


class OptimizationChange(BaseModel):
    location: str
    original: str
    optimized: str
    rule: str
    impact: Literal["critical", "high", "medium", "low"]


# ---------- Full Analysis Response ----------

class SEOAnalysisResponse(BaseModel):
    analysis_id: str
    input_type: InputType
    content_type: ContentType
    target_keyword: Optional[str]

    score_before: SEOScore
    score_after: SEOScore

    extracted: ExtractedContent
    optimized_content: str
    diff_chunks: List[DiffChunk]
    changes_made: List[OptimizationChange]

    suggested_title_tag: str
    suggested_meta_description: str
    suggested_url_slug: str
    word_count_original: int
    word_count_optimized: int

    # Token usage for this specific analysis
    token_usage: AnalysisTokenUsage

    # Warning shown to client if approaching/at budget limit
    warning_level: TokenWarningLevel = TokenWarningLevel.OK
    warning_message: Optional[str] = None

    processing_time_seconds: float
    agents_used: List[str]


# ---------- Usage / Billing Models ----------

class CreateCheckoutRequest(BaseModel):
    tier: SubscriptionTier
    success_url: str
    cancel_url: str


class UsageStatus(BaseModel):
    tier: SubscriptionTier

    # Analysis count
    analyses_used: int
    analyses_limit: int
    analyses_remaining: int

    # Token budget
    tokens_used_this_month: int
    token_budget: int           # -1 = unlimited (agency)
    tokens_remaining: int       # -1 = unlimited
    token_usage_pct: float      # 0.0 to 1.0

    # Warning
    warning_level: TokenWarningLevel
    warning_message: Optional[str] = None

    # Cost tracking (for admin dashboard)
    estimated_cost_usd: float = 0.0

    # Reset date
    reset_date: Optional[str]


# ---------- Admin Models ----------

class UpdateRulesRequest(BaseModel):
    rules_markdown: str
    version_note: Optional[str] = None


# ---------- AI Writer Models ----------

class CompetitorArticleSummary(BaseModel):
    url: str
    title: str
    word_count: int
    main_angle: str
    strengths: List[str]
    weaknesses: List[str]
    missing_elements: List[str]
    has_faq: bool
    has_figures: bool
    eeat_level: str  # "low", "medium", "high"


class CompetitorAnalysisResult(BaseModel):
    articles_analyzed: List[CompetitorArticleSummary]
    common_strengths: List[str]
    common_weaknesses: List[str]
    content_gaps: List[str]
    differentiation_angle: str
    recommended_structure: str
    long_tail_opportunities: List[str]

    @field_validator("recommended_structure", mode="before")
    @classmethod
    def coerce_to_string(cls, v: Any) -> str:
        """LLM sometimes returns a dict/list instead of a plain string — coerce it."""
        if isinstance(v, dict):
            return " → ".join(
                f"{k}: {val}" if val and str(val).strip() else str(k)
                for k, val in v.items()
            )
        if isinstance(v, list):
            return " → ".join(str(s) for s in v)
        if v is None:
            return ""
        return str(v)


class AIWriterRequest(BaseModel):
    competitor_urls: List[str] = []         # 0-5 competitor article URLs to analyze (optional)
    topic_prompt: str                        # e.g. "Write a guide on how RAG works for production engineers"
    target_keywords: Optional[List[str]] = None
    content_type: Optional[ContentType] = None
    user_tone_prompt: Optional[str] = None


class AIWriterResponse(BaseModel):
    writer_id: str
    topic_prompt: str
    content_type: ContentType
    target_keywords: List[str]
    competitor_analysis: CompetitorAnalysisResult
    written_content: str
    suggested_title_tag: str
    suggested_meta_description: str
    suggested_url_slug: str
    token_usage: AnalysisTokenUsage
    processing_time_seconds: float
    agents_used: List[str]


# ---------- Site Comparison Models ----------

class RadarChartData(BaseModel):
    """7-pillar radar chart data — normalize each pillar score to 0-100."""
    dimensions: List[str]           # pillar names
    your_scores: List[float]        # 0-100 per pillar
    competitor_scores: List[float]


class BarChartData(BaseModel):
    """Criterion-by-criterion bar chart — raw scores vs max."""
    labels: List[str]               # criterion short names
    your_scores: List[int]
    competitor_scores: List[int]
    max_scores: List[int]


class ScoreGapItem(BaseModel):
    """Single criterion gap — used for the gap table."""
    criterion: str
    your_score: int
    competitor_score: int
    max_score: int
    gap: int                        # competitor_score - your_score (positive = competitor ahead)
    severity: str                   # critical | high | medium | low


class VisualizationData(BaseModel):
    """All chart-ready data for the frontend."""
    radar: RadarChartData
    bar: BarChartData
    score_gaps: List[ScoreGapItem]          # sorted by gap descending (worst for you first)
    your_overall: int
    competitor_overall: int
    score_delta: int                        # your_overall - competitor_overall
    keyword_overlap: List[str]              # keywords both sites target
    your_unique_keywords: List[str]
    competitor_unique_keywords: List[str]
    eeat_comparison: dict                   # {"your": {...}, "competitor": {...}}


class NextStep(BaseModel):
    priority: str                           # "critical" | "high" | "medium"
    action: str
    reason: str
    estimated_impact: str                   # e.g. "+8-12 SEO points"


class ComparisonInsights(BaseModel):
    your_strengths: List[str]
    your_weaknesses: List[str]
    competitor_strengths: List[str]
    competitor_weaknesses: List[str]
    content_gaps: List[str]                 # topics competitor covers that you don't
    your_opportunities: List[str]           # areas where you can clearly beat them
    executive_summary: str                  # 2-3 sentence overview
    next_steps: List[NextStep]


class SiteSnapshot(BaseModel):
    """Lightweight profile card for one site."""
    url: str
    title: str
    overall_score: int
    rating: str
    rating_emoji: str
    word_count: int
    primary_keywords: List[str]
    content_type: str
    has_faq: bool
    has_author_bio: bool
    internal_link_count: int
    external_link_count: int


class CompareRequest(BaseModel):
    your_url: str
    competitor_url: str


class CompareResponse(BaseModel):
    compare_id: str
    your_site: SiteSnapshot
    competitor_site: SiteSnapshot
    your_score: SEOScore
    competitor_score: SEOScore
    insights: ComparisonInsights
    visualization_data: VisualizationData
    token_usage: AnalysisTokenUsage
    processing_time_seconds: float
    agents_used: List[str]


# ---------- Site Audit Models ----------

class AuditCheck(BaseModel):
    name: str
    passed: bool
    severity: str                   # "critical" | "high" | "medium" | "low" | "info"
    value: Optional[str] = None     # actual value found (e.g. "72 chars")
    recommendation: Optional[str] = None


class AuditSection(BaseModel):
    name: str                       # e.g. "On-Page SEO", "Technical", "Social"
    score: int                      # 0-100 for this section
    checks: List[AuditCheck]


class AuditRequest(BaseModel):
    url: str
    target_keyword: Optional[str] = None


class AuditResponse(BaseModel):
    audit_id: str
    url: str
    overall_score: int              # 0-100
    grade: str                      # A/B/C/D/F
    sections: List[AuditSection]
    critical_issues: List[str]      # top critical issues as plain strings
    top_recommendations: List[str]  # AI-generated top 3 priority fixes
    token_usage: AnalysisTokenUsage
    processing_time_seconds: float


# ---------- Keyword Cluster Models ----------

class KeywordClusterRequest(BaseModel):
    topic: str
    seed_keywords: Optional[List[str]] = None
    content_type: Optional[ContentType] = None
    industry: Optional[str] = None  # accepted, not used yet


class KeywordGroup(BaseModel):
    intent: str                     # "informational" | "transactional" | "navigational" | "long_tail"
    keywords: List[str]
    rationale: str                  # why these keywords fit this intent


class KeywordClusterResponse(BaseModel):
    topic: str
    primary_keyword: str
    clusters: List[KeywordGroup]
    paa_questions: List[str]        # People Also Ask questions
    semantic_keywords: List[str]    # LSI / entity keywords
    negative_keywords: List[str]    # keywords to avoid (too broad/competitive)
    token_usage: AnalysisTokenUsage
    processing_time_seconds: float


# ---------- Content Brief Models ----------

class BriefSection(BaseModel):
    heading: str                    # e.g. "## What is RAG?"
    level: int                      # 2 = H2, 3 = H3
    target_word_count: int
    key_points: List[str]           # bullet points to cover
    suggested_keywords: List[str]


class ContentBriefRequest(BaseModel):
    primary_keyword: str
    target_keywords: Optional[List[str]] = None
    content_type: Optional[ContentType] = None
    topic_context: Optional[str] = None   # extra context about what to cover
    competitor_urls: Optional[List[str]] = None  # optional: fetch and use as reference
    industry: Optional[str] = None


class ContentBriefResponse(BaseModel):
    brief_id: str
    primary_keyword: str
    target_keywords: List[str]
    content_type: ContentType
    suggested_title: str
    suggested_meta_description: str
    suggested_url_slug: str
    target_word_count: int
    target_reading_level: str       # e.g. "Professional / Advanced"
    sections: List[BriefSection]
    faq_questions: List[str]        # 5 FAQ questions to include
    eeat_signals_to_include: List[str]
    internal_link_suggestions: List[str]
    external_source_suggestions: List[str]
    content_angle: str              # the unique angle / hook
    token_usage: AnalysisTokenUsage
    processing_time_seconds: float


# ---------- Bulk Analysis Models ----------

class BulkAnalyzeRequest(BaseModel):
    urls: List[str]                 # 2-10 URLs
    target_keyword: Optional[str] = None
    content_type: Optional[ContentType] = None


class BulkURLResult(BaseModel):
    url: str
    status: str                     # "success" | "failed"
    error: Optional[str] = None
    overall_score: Optional[int] = None
    rating: Optional[str] = None
    rating_emoji: Optional[str] = None
    top_issues: List[str] = []
    quick_wins: List[str] = []
    token_usage: Optional[AnalysisTokenUsage] = None


class BulkAnalyzeResponse(BaseModel):
    bulk_id: str
    total_urls: int
    successful: int
    failed: int
    results: List[BulkURLResult]
    aggregate_token_usage: AnalysisTokenUsage
    processing_time_seconds: float


# ---------- Export Models ----------

class ExportRequest(BaseModel):
    title: str
    content: str                    # markdown content to export
    export_type: str = "html"       # "html" only for now