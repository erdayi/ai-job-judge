from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl


class ResumeProfile(BaseModel):
    target_roles: list[str] = Field(default_factory=list)
    core_skills: list[str] = Field(default_factory=list)
    secondary_skills: list[str] = Field(default_factory=list)
    project_keywords: list[str] = Field(default_factory=list)
    negative_directions: list[str] = Field(default_factory=list)
    ranking_weights: dict[str, int] = Field(default_factory=dict)


class ResumeUploadResponse(BaseModel):
    resume_id: str
    text_length: int
    preview: str
    extracted_text: str


class ResumeRulesRequest(BaseModel):
    resume_id: str | None = None
    resume_text: str | None = None


class ResumeRulesResponse(BaseModel):
    resume_id: str
    profile: ResumeProfile
    raw_rules: dict[str, Any]
    source: Literal["claude", "llm", "heuristic"]


class LinkCandidate(BaseModel):
    text: str = ""
    href: str
    selector: str | None = None
    attrs: dict[str, str] = Field(default_factory=dict)


class ElementCandidate(BaseModel):
    text: str
    selector: str | None = None
    tag: str | None = None
    role: str | None = None
    href: str | None = None
    attrs: dict[str, str] = Field(default_factory=dict)


class TextBlock(BaseModel):
    text: str
    selector: str | None = None
    links: list[LinkCandidate] = Field(default_factory=list)


class PageSnapshot(BaseModel):
    url: str
    title: str = ""
    visible_text: str = ""
    links: list[LinkCandidate] = Field(default_factory=list)
    buttons: list[ElementCandidate] = Field(default_factory=list)
    blocks: list[TextBlock] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class PaginationType(str, Enum):
    none = "none"
    next_button = "next_button"
    page_numbers = "page_numbers"
    load_more = "load_more"
    infinite_scroll = "infinite_scroll"


class PaginationPlan(BaseModel):
    type: PaginationType = PaginationType.none
    next_selector: str | None = None
    reason: str = ""


class PageAnalyzeResponse(BaseModel):
    is_job_page: bool
    requires_login: bool = False
    login_reason: str = ""
    pagination: PaginationPlan = Field(default_factory=PaginationPlan)
    extraction_hint: str = ""
    site_family: str = "unknown"
    site_hints: list[str] = Field(default_factory=list)


class JobItem(BaseModel):
    id: str | None = None
    title: str
    company: str | None = None
    department: str | None = None
    location: str | None = None
    description: str = ""
    requirements: str = ""
    skills: list[str] = Field(default_factory=list)
    detail_url: str | None = None
    detail_selector: str | None = None
    apply_url: str | None = None
    source_url: str | None = None
    confidence: float = 0.5


class JobsExtractResponse(BaseModel):
    jobs: list[JobItem]
    pagination: PaginationPlan = Field(default_factory=PaginationPlan)
    source: Literal["heuristic", "llm"] = "heuristic"


class JobsMatchRequest(BaseModel):
    jobs: list[JobItem]
    profile: ResumeProfile | None = None
    resume_id: str | None = None
    max_candidates: int = 30


class JobMatch(BaseModel):
    job: JobItem
    score: int
    decision: Literal["recommend", "maybe", "reject"]
    reasons: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)


class JobsMatchResponse(BaseModel):
    matches: list[JobMatch]
    total: int
    kept: int


class RankRequest(BaseModel):
    matches: list[JobMatch]
    profile: ResumeProfile | None = None
    resume_id: str | None = None
    top_n: int = 5


class FinalResult(BaseModel):
    rank: int
    score: int
    decision: Literal["recommend", "maybe", "reject"]
    title: str
    company: str | None = None
    reasons: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    job_url: str | None = None
    job: JobItem


class RankResponse(BaseModel):
    results: list[FinalResult]
    source: Literal["claude", "llm", "heuristic"]
    diagnostics: list[str] = Field(default_factory=list)


class ApplicationKitRequest(BaseModel):
    job: JobItem
    score: int | None = None
    decision: Literal["recommend", "maybe", "reject"] | None = None
    reasons: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    resume_id: str | None = None
    profile: ResumeProfile | None = None
    notes: str | None = None


class ApplicationKitResponse(BaseModel):
    source: Literal["claude", "llm", "heuristic"]
    fit_summary: str
    resume_focus: list[str] = Field(default_factory=list)
    cover_note: str
    interview_prep: list[str] = Field(default_factory=list)
    keywords_to_add: list[str] = Field(default_factory=list)
    risk_mitigation: list[str] = Field(default_factory=list)
    questions_to_prepare: list[str] = Field(default_factory=list)
    no_fabrication_warning: str = "不要编造简历中没有体现的经历、指标或技能。"
    diagnostics: list[str] = Field(default_factory=list)


class CombinedAnalyzeRequest(BaseModel):
    snapshot: PageSnapshot
    resume_id: str | None = None
    profile: ResumeProfile | None = None
    top_n: int = 5
    max_candidates: int = 30


class CombinedAnalyzeResponse(BaseModel):
    page: PageAnalyzeResponse
    extracted: JobsExtractResponse
    matched: JobsMatchResponse
    ranked: RankResponse
