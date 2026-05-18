from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Article:
    id: str
    title: str
    url: str
    source: str
    summary: str
    published_date: str | None = None


@dataclass(frozen=True)
class ClassificationResult:
    category: str
    matched_keywords: list[str]
    confidence: float


@dataclass(frozen=True)
class ScoreResult:
    total_score: int
    positive_scores: dict[str, int]
    penalties: dict[str, int]
    recommendation: str


@dataclass(frozen=True)
class FluffResult:
    fluff_score: int
    reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ContentIdea:
    idea_id: str
    topic: str
    source_article_id: str
    category: str
    source: str
    why_it_matters: str
    target_audience: str
    suggested_angle: str
    hook_options: list[str]
    total_score: int
    fluff_score: int
    recommendation: str
