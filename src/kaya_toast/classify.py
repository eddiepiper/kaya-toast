from __future__ import annotations

from kaya_toast.models import Article, ClassificationResult


CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "ai_native_pm_mindset": [
        "ai-native",
        "product manager",
        "product management",
        "ai pm",
        "pm role",
    ],
    "ai_pm_skills": [
        "ai pm",
        "pm skills",
        "skill",
        "upskill",
        "career transition",
    ],
    "ai_workflow_redesign": [
        "workflow redesign",
        "decision loop",
        "operating rhythm",
        "product workflow",
    ],
    "agentic_workflows": [
        "agent",
        "agentic",
        "workflow automation",
        "autonomous workflow",
        "orchestration",
    ],
    "ai_prototyping": [
        "prototype",
        "prototyping",
        "mockup",
        "concept test",
        "experiment",
    ],
    "context_engineering": [
        "context engineering",
        "prompt architecture",
        "memory",
        "retrieval",
        "context layer",
    ],
    "human_in_loop_systems": [
        "human in the loop",
        "approval",
        "escalation",
        "review",
        "oversight",
    ],
    "ai_governance": [
        "governance",
        "risk",
        "audit",
        "compliance",
        "controls",
    ],
    "product_discovery_with_ai": [
        "discovery",
        "customer research",
        "user interview",
        "validate",
        "experiment",
    ],
    "traditional_pm_to_ai_pm": [
        "traditional pm",
        "ai pm",
        "career transition",
        "product manager skills",
        "upskill",
    ],
    "enterprise_ai_operating_models": [
        "enterprise ai",
        "operating model",
        "transformation",
        "workflow redesign",
        "business process",
    ],
}


def classify_article(article: Article) -> ClassificationResult:
    title = article.title.lower()
    text = f"{article.title} {article.summary}".lower()
    best_category = "ai_native_pm_mindset"
    best_matches: list[str] = []
    best_score = 0

    for category, keywords in CATEGORY_KEYWORDS.items():
        matches = [keyword for keyword in keywords if keyword.lower() in text]
        weighted_score = len(matches) + sum(
            1 for keyword in matches if keyword.lower() in title
        )
        if weighted_score > best_score:
            best_category = category
            best_matches = matches
            best_score = weighted_score

    confidence = min(1.0, len(best_matches) / 3) if best_matches else 0.0
    return ClassificationResult(
        category=best_category,
        matched_keywords=best_matches,
        confidence=round(confidence, 2),
    )


def classify_articles(articles: list[Article]) -> dict[str, ClassificationResult]:
    return {article.id: classify_article(article) for article in articles}
