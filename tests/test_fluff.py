from kaya_toast.collect import collect_from_json
from kaya_toast.fluff import fluff_check


def test_fluff_detector_catches_prompt_bro_language():
    article = next(
        article for article in collect_from_json("examples/sample_articles.json")
        if article.id == "a5"
    )

    result = fluff_check(article)

    assert result.fluff_score >= 25
    assert any("top 10 prompts" in reason for reason in result.reasons)


def test_fluff_detector_catches_hype_language():
    article = next(
        article for article in collect_from_json("examples/sample_articles.json")
        if article.id == "a6"
    )

    result = fluff_check(article)

    assert result.fluff_score >= 50
    assert any("ai revolution" in reason for reason in result.reasons)
