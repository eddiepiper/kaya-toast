from kaya_toast.classify import classify_article
from kaya_toast.collect import collect_from_json
from kaya_toast.score import score_article


def _score(article_id: str):
    article = next(
        article for article in collect_from_json("examples/sample_articles.json")
        if article.id == article_id
    )
    return score_article(article, classify_article(article))


def test_scoring_produces_post():
    score = _score("a1")

    assert score.recommendation == "post"
    assert score.total_score >= 70


def test_scoring_produces_park():
    score = _score("a2")

    assert score.recommendation == "park"
    assert 50 <= score.total_score < 70


def test_scoring_produces_reject():
    score = _score("a6")

    assert score.recommendation == "reject"
    assert score.total_score < 50
