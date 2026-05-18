from pathlib import Path

from kaya_toast import cli
from kaya_toast.collect import CollectionResult
from kaya_toast.config import load_pillars
from kaya_toast.models import Article
from kaya_toast.pillars import classify_pillar


def test_pillar_config_loads():
    config = load_pillars()

    assert config["pillars"]["ai_native_pm"]["priority"] == "primary"
    assert "ai_native_banking" in config["pillars"]


def test_pillar_classification_works():
    article = Article(
        id="banking-1",
        title="Banking AI workflows need compliance controls",
        url="https://example.com",
        source="Banking Source",
        summary="Banking PMs need audit, risk, compliance, and controls for AI decision systems.",
    )

    result = classify_pillar(article=article)

    assert result.primary_pillar == "ai_native_banking"
    assert result.score == 8


def test_daily_ai_native_pm_is_default(tmp_path: Path, monkeypatch):
    article = Article(
        id="pm-1",
        title="AI-native product managers redesign discovery workflow",
        url="https://example.com",
        source="Mock",
        summary="Product managers design, validate, review, and orchestrate AI workflow decisions.",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("kaya_toast.workflow.DAILY_REPORTS_DIR", tmp_path / "reports" / "daily")
    monkeypatch.setattr("kaya_toast.workflow.RUN_HISTORY_PATH", tmp_path / "data" / "history.json")
    monkeypatch.setattr("kaya_toast.workflow.LATEST_RSS_PATH", tmp_path / "data" / "rss.json")
    monkeypatch.setattr(
        "kaya_toast.workflow.collect_from_rss_sources",
        lambda _sources: CollectionResult([article], {"Mock": 1}, []),
    )
    monkeypatch.setattr("kaya_toast.workflow.load_sources", lambda: {"sources": []})

    assert cli.main(["daily"]) == 0
    report = next((tmp_path / "reports" / "daily").glob("*-kaya-toast.md"))
    text = report.read_text(encoding="utf-8")
    assert "Primary pillar: ai_native_pm" in text


def test_daily_pillar_all_includes_all_sections(tmp_path: Path, monkeypatch):
    articles = [
        Article(
            id="pm-1",
            title="AI-native product managers redesign discovery workflow",
            url="https://example.com/pm",
            source="Mock",
            summary="Product managers design, validate, review, and orchestrate AI workflow decisions.",
        ),
        Article(
            id="banking-1",
            title="Banking AI workflows need compliance controls",
            url="https://example.com/banking",
            source="Mock",
            summary="Banking teams need audit, risk, compliance, and controls.",
        ),
    ]
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("kaya_toast.workflow.DAILY_REPORTS_DIR", tmp_path / "reports" / "daily")
    monkeypatch.setattr("kaya_toast.workflow.RUN_HISTORY_PATH", tmp_path / "data" / "history.json")
    monkeypatch.setattr("kaya_toast.workflow.LATEST_RSS_PATH", tmp_path / "data" / "rss.json")
    monkeypatch.setattr(
        "kaya_toast.workflow.collect_from_rss_sources",
        lambda _sources: CollectionResult(articles, {"Mock": 2}, []),
    )
    monkeypatch.setattr("kaya_toast.workflow.load_sources", lambda: {"sources": []})

    assert cli.main(["daily", "--pillar", "all"]) == 0
    report = next((tmp_path / "reports" / "daily").glob("*-kaya-toast.md"))
    text = report.read_text(encoding="utf-8")
    assert "## AI-native PM Ideas" in text
    assert "## AI-native Banking Ideas" in text
    assert "Primary pillar: ai_native_banking" in text
