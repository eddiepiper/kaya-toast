from __future__ import annotations

from kaya_toast.classify import classify_article
from kaya_toast.models import Article, ContentIdea
from kaya_toast.quality import assess_title_quality, assess_topic_quality, is_generic_fragment_title, is_high_quality_title, is_weak_title, source_quality_boost
from kaya_toast.recommend import build_content_idea, recommend_articles
from kaya_toast.report import render_report
from kaya_toast.score import score_article


def _article(title: str, summary: str | None = None) -> Article:
    return Article(
        id=title.lower().replace(" ", "-"),
        title=title,
        url="https://martinfowler.com/example",
        source="Martin Fowler",
        summary=summary
        or "Product managers can design workflow review loops with AI governance and operational controls.",
    )


def _source_article(source: str, title: str, summary: str) -> Article:
    return Article(
        id=title.lower().replace(" ", "-"),
        title=title,
        url="https://example.com",
        source=source,
        summary=summary,
    )


def test_fragment_title_is_not_recommended_as_post():
    article = _article("Fragments: April 9")
    classification = classify_article(article)
    score = score_article(article, classification)
    idea = build_content_idea(article, classification, score)

    assert idea.recommendation == "reject"
    assert "generic fragment title" in idea.quality_warnings


def test_weak_fragment_titles_are_parked_or_rejected():
    article = _article("Fragments: May 14")
    classification = classify_article(article)
    idea = build_content_idea(article, classification, score_article(article, classification))

    assert idea.recommendation in {"park", "reject"}
    assert idea.recommendation != "post"


def test_strong_martin_fowler_title_still_passes():
    article = _article(
        "Bliki: Mythical Man Month",
        "Product managers can use this strategy lesson to review enterprise workflow planning and delivery risk.",
    )
    quality = assess_title_quality(article)

    assert quality.reject_reason is None
    assert "generic fragment title" not in quality.warnings


def test_duplicate_weak_topics_do_not_dominate_top_ideas():
    weak_articles = [_article("Fragments: April 9"), _article("Fragments: May 14")]
    strong = _article(
        "AI-native PM workflow governance for product managers",
        (
            "Traditional PMs and AI PMs design, validate, review, and orchestrate "
            "enterprise AI workflow governance controls with decision loops."
        ),
    )
    articles = weak_articles + [strong]
    classifications = {article.id: classify_article(article) for article in articles}
    scores = {
        article.id: score_article(article, classifications[article.id])
        for article in articles
    }

    ideas = recommend_articles(articles, classifications, scores)

    assert not ideas[0].topic.startswith("Fragments:")
    assert ideas[0].recommendation == "post"


def test_report_includes_quality_warnings():
    idea = ContentIdea(
        idea_id="fragment",
        topic="Fragments: April 9",
        source_article_id="a1",
        category="agentic_workflows",
        source="Martin Fowler: Fragments: April 9",
        why_it_matters="Weak source title.",
        target_audience="Traditional PMs",
        suggested_angle="Explain workflow design.",
        hook_options=["AI-native PM is not about writing PRDs faster."],
        total_score=0,
        fluff_score=0,
        recommendation="reject",
        quality_warnings=["generic fragment title", "duplicate weak topic"],
    )

    report = render_report([idea])

    assert "## Quality Warnings" in report
    assert "generic fragment title" in report


def test_quality_helpers_detect_weak_titles():
    assert is_generic_fragment_title("Fragments: April 9")
    assert is_weak_title("May 14")
    assert "duplicate weak topic" in assess_topic_quality(
        ContentIdea(
            idea_id="fragment",
            topic="Fragments: April 9",
            source_article_id="a1",
            category="agentic_workflows",
            source="Martin Fowler: Fragments: April 9",
            why_it_matters="Weak source title.",
            target_audience="Traditional PMs",
            suggested_angle="Explain workflow design.",
            hook_options=[],
            total_score=0,
            fluff_score=0,
            recommendation="reject",
        )
    ).warnings


def test_preferred_source_boost_promotes_strong_product_title():
    article = _source_article(
        "Product Talk",
        "Product discovery with AI needs stronger customer evidence",
        "Product managers validate, review, and prioritize customer discovery workflow decisions with AI.",
    )
    classification = classify_article(article)
    idea = build_content_idea(article, classification, score_article(article, classification))

    assert source_quality_boost(article) == 10
    assert is_high_quality_title(article.title)
    assert idea.source_quality_boost == 10
    assert idea.recommendation == "post"


def test_parked_but_promising_section_is_rendered():
    idea = ContentIdea(
        idea_id="promising",
        topic="Product discovery with AI needs stronger customer evidence",
        source_article_id="a1",
        category="product_discovery_with_ai",
        source="Product Talk: Product discovery with AI needs stronger customer evidence",
        why_it_matters="Evidence quality matters.",
        target_audience="Traditional PMs",
        suggested_angle="Show discovery workflow lessons.",
        hook_options=["AI discovery still needs evidence."],
        total_score=50,
        fluff_score=0,
        recommendation="park",
        final_score=55,
    )

    report = render_report([idea])

    assert "## Parked But Promising" in report
    assert "Product discovery with AI needs stronger customer evidence" in report


def test_duplicate_idea_ids_are_removed_from_recommendations():
    articles = [
        _source_article(
            "Product Talk",
            "AI-native PM workflow governance for product managers",
            "Product managers design, validate, review, and orchestrate AI workflow decisions.",
        ),
        _source_article(
            "Product Talk",
            "AI-native PM workflow governance for product managers",
            "Product managers design, validate, review, and orchestrate AI workflow decisions.",
        ),
    ]
    classifications = {article.id: classify_article(article) for article in articles}
    scores = {article.id: score_article(article, classifications[article.id]) for article in articles}

    ideas = recommend_articles(articles, classifications, scores)

    assert len([idea for idea in ideas if idea.idea_id == ideas[0].idea_id]) == 1


def test_fallback_topic_appears_at_most_once():
    articles = [
        _source_article(
            "AWS Machine Learning Blog",
            "AI workflow update",
            "Product managers use AI workflow strategy to design, validate, and review decisions.",
        ),
        _source_article(
            "Microsoft AI Blog",
            "AI product workflow update",
            "Product managers use AI workflow strategy to design, validate, and review decisions.",
        ),
    ]
    classifications = {article.id: classify_article(article) for article in articles}
    scores = {article.id: score_article(article, classifications[article.id]) for article in articles}

    ideas = recommend_articles(articles, classifications, scores)

    assert sum(idea.topic == "AI-native PMs are not faster PRD writers" for idea in ideas) <= 1


def test_strong_source_title_is_preferred_over_fallback_topic():
    article = _source_article(
        "Product Talk",
        "Product discovery with AI needs stronger customer evidence",
        "Product managers use AI to validate and review product discovery decisions.",
    )
    classification = classify_article(article)
    idea = build_content_idea(article, classification, score_article(article, classification))

    assert idea.topic == "Product discovery with AI needs stronger customer evidence"


def test_prompt_bro_positioning_warning_caps_recommendation_at_park():
    article = _article(
        "Structured-Prompt-Driven Development (SPDD)",
        "Product managers can use prompt architecture to design, validate, review, and orchestrate AI workflows.",
    )
    classification = classify_article(article)
    idea = build_content_idea(article, classification, score_article(article, classification))

    assert idea.positioning_warning == "Sounds like prompt-bro content"
    assert idea.recommendation == "park"


def test_hooks_vary_by_category():
    agentic = _source_article(
        "OpenAI News",
        "Agentic workflow controls for product managers",
        "Product managers design, validate, review, and orchestrate agentic workflow controls.",
    )
    discovery = _source_article(
        "Product Talk",
        "Product discovery with AI needs stronger customer evidence",
        "Product managers validate and review product discovery decisions with AI.",
    )
    agentic_idea = build_content_idea(
        agentic,
        classify_article(agentic),
        score_article(agentic, classify_article(agentic)),
    )
    discovery_idea = build_content_idea(
        discovery,
        classify_article(discovery),
        score_article(discovery, classify_article(discovery)),
    )

    assert agentic_idea.hook_options != discovery_idea.hook_options
    assert "Agentic workflows still need product judgment." in agentic_idea.hook_options
