from kaya_toast.classify import classify_article
from kaya_toast.collect import collect_from_json


def test_classification_assigns_context_engineering():
    article = next(
        article for article in collect_from_json("examples/sample_articles.json")
        if article.id == "a3"
    )

    result = classify_article(article)

    assert result.category == "context_engineering"
    assert "context engineering" in result.matched_keywords
    assert result.confidence > 0


def test_classification_assigns_governance():
    article = next(
        article for article in collect_from_json("examples/sample_articles.json")
        if article.id == "a4"
    )

    result = classify_article(article)

    assert result.category == "ai_governance"
