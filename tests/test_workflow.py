import json
from pathlib import Path

from kaya_toast import cli
from kaya_toast.collect import CollectionResult
from kaya_toast.models import Article
from kaya_toast.workflow import append_run_history, run_daily, run_weekly


def _article(article_id: str = "rss-1") -> Article:
    return Article(
        id=article_id,
        title="AI-native product managers design workflow review loops",
        url="https://example.com/ai-native-pm",
        source="Mock RSS",
        summary=(
            "Product managers can design, validate, review, and orchestrate AI "
            "workflow decisions with enterprise governance controls."
        ),
        published_date="2026-05-18",
    )


def test_daily_command_creates_daily_report(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("kaya_toast.workflow.DAILY_REPORTS_DIR", tmp_path / "reports" / "daily")
    monkeypatch.setattr("kaya_toast.workflow.RUN_HISTORY_PATH", tmp_path / "data" / "run_history.json")
    monkeypatch.setattr("kaya_toast.workflow.LATEST_RSS_PATH", tmp_path / "data" / "latest_rss_articles.json")
    monkeypatch.setattr(
        "kaya_toast.workflow.collect_from_rss_sources",
        lambda _sources: CollectionResult([_article()], {"Mock RSS": 1}, []),
    )
    monkeypatch.setattr("kaya_toast.workflow.load_sources", lambda: {"sources": []})

    report_path = run_daily()

    assert report_path.exists()
    assert report_path.parent.name == "daily"
    assert "## Source Summary" in report_path.read_text(encoding="utf-8")


def test_weekly_command_creates_weekly_report_from_sample_daily_reports(tmp_path: Path, monkeypatch):
    daily_dir = tmp_path / "reports" / "daily"
    weekly_dir = tmp_path / "reports" / "weekly"
    daily_dir.mkdir(parents=True)
    sample = daily_dir / "2026-05-18-kaya-toast.md"
    sample.write_text(
        "\n".join(
            [
                "# kaya-toast Daily Brief",
                "### AI-native PMs are not faster PRD writers",
                "- Category: ai_native_pm_mindset",
                "- Why it matters: Better decision loops matter.",
                "- Suggested angle: Challenge productivity-only AI adoption.",
                "  - AI-native PM is not about writing PRDs faster.",
                "- Preference Adjustment: +10",
                "- Positioning fit: 45",
                "- Memory-informed recommendation: Memory-aligned",
                "- Final Score: 90",
                "## Fluff Warnings",
                "- prompt list content: fluff risk 95, recommendation reject",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("kaya_toast.workflow.DAILY_REPORTS_DIR", daily_dir)
    monkeypatch.setattr("kaya_toast.workflow.WEEKLY_REPORTS_DIR", weekly_dir)

    report_path = run_weekly()

    text = report_path.read_text(encoding="utf-8")
    assert report_path.exists()
    assert "## Best 3 LinkedIn Ideas This Week" in text
    assert "## Recommended Posting Plan" in text
    assert "Monday: strategic AI-native PM shift" in text
    assert "- Score: 90" in text
    assert "  - Hook options:" not in text
    assert "- Positioning fit: 45" in text
    assert "- Memory-informed recommendation: Memory-aligned" in text


def test_rss_fallback_works_from_latest_rss_articles(tmp_path: Path, monkeypatch):
    fallback_path = tmp_path / "data" / "latest_rss_articles.json"
    fallback_path.parent.mkdir(parents=True)
    fallback_path.write_text(
        json.dumps([_article("fallback-1").__dict__]),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("kaya_toast.workflow.DAILY_REPORTS_DIR", tmp_path / "reports" / "daily")
    monkeypatch.setattr("kaya_toast.workflow.RUN_HISTORY_PATH", tmp_path / "data" / "run_history.json")
    monkeypatch.setattr("kaya_toast.workflow.LATEST_RSS_PATH", fallback_path)
    monkeypatch.setattr(
        "kaya_toast.workflow.collect_from_rss_sources",
        lambda _sources: CollectionResult([], {"Broken RSS": 0}, ["Broken RSS: timeout"]),
    )
    monkeypatch.setattr("kaya_toast.workflow.load_sources", lambda: {"sources": []})

    report_path = run_daily()

    text = report_path.read_text(encoding="utf-8")
    assert report_path.exists()
    assert "used fallback" in text


def test_run_history_json_updates(tmp_path: Path):
    history_path = tmp_path / "data" / "run_history.json"

    record = append_run_history(
        articles_collected=3,
        ideas_generated=2,
        report_path="reports/daily/example.md",
        warnings=["source warning"],
        path=history_path,
    )

    records = json.loads(history_path.read_text(encoding="utf-8"))
    assert records[-1]["run_id"] == record["run_id"]
    assert records[-1]["articles_collected"] == 3
    assert records[-1]["warnings"] == ["source warning"]


def test_existing_run_input_still_works(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    project_sample = Path(__file__).resolve().parents[1] / "examples" / "sample_articles.json"

    assert cli.main(["run", "--input", str(project_sample)]) == 0
    assert list((tmp_path / "reports").glob("*-kaya-toast.md"))
