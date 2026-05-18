from kaya_toast.models import Article, FluffResult


FLUFF_PHRASES = [
    "ai will change everything",
    "unlock productivity",
    "future-proof your career",
    "10 prompts",
    "top 10 prompts",
    "ai revolution",
    "game changer",
    "transform your life",
    "agentic revolution",
    "replace product managers",
    "no-code riches",
    "make money with ai",
]

AI_BUZZWORDS = ["ai", "agentic", "autonomous", "llm", "genai", "generative ai"]
PM_KEYWORDS = ["pm", "product", "product manager", "product management", "roadmap"]
TRANSFORMATION_CLAIMS = ["transform", "revolution", "future of work", "disrupt"]
OPERATIONAL_WORDS = [
    "design",
    "validate",
    "test",
    "decide",
    "review",
    "orchestrate",
    "prioritize",
    "prioritise",
    "discover",
    "govern",
    "measure",
]
PRACTICAL_VERBS = OPERATIONAL_WORDS


def _contains_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)


def fluff_check(article: Article) -> FluffResult:
    text = f"{article.title} {article.summary}".lower()
    reasons: list[str] = []
    score = 0

    for phrase in FLUFF_PHRASES:
        if phrase in text:
            reasons.append(f"fluff phrase: {phrase}")
            score += 25

    if _contains_any(text, AI_BUZZWORDS) and not _contains_any(text, PM_KEYWORDS):
        reasons.append("AI buzzwords without PM relevance")
        score += 30

    if _contains_any(text, TRANSFORMATION_CLAIMS) and not _contains_any(text, OPERATIONAL_WORDS):
        reasons.append("transformation claim without operational detail")
        score += 25

    if not _contains_any(text, PRACTICAL_VERBS):
        reasons.append("no practical verbs")
        score += 20

    return FluffResult(fluff_score=min(score, 100), reasons=reasons)
