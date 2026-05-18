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
class QualityResult:
    quality_score: int
    warnings: list[str] = field(default_factory=list)
    reject_reason: str | None = None


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
    preference_adjustment: int = 0
    final_score: int | None = None
    primary_pillar: str = "ai_native_pm"
    secondary_pillar: str | None = None
    pillar_confidence: float = 0.0
    pillar_score: int = 0
    positioning_fit_score: int = 0
    positioning_warning: str | None = None
    memory_recommendation: str = "No memory signal yet"
    quality_score: int = 100
    quality_warnings: list[str] = field(default_factory=list)
    quality_reject_reason: str | None = None

    def __post_init__(self) -> None:
        if self.final_score is None:
            object.__setattr__(
                self,
                "final_score",
                self.total_score + self.preference_adjustment + self.pillar_score,
            )
