from pathlib import Path

from kaya_toast import cli
from kaya_toast.interpret import interpret_report, load_prompt_template


def _sample_report(path: Path) -> Path:
    path.write_text(
        "\n".join(
            [
                "# kaya-toast Daily Brief",
                "## Top LinkedIn Content Ideas",
                "",
                "### AI-native PMs are not faster PRD writers",
                "",
                "- Topic: AI-native PMs are not faster PRD writers",
                "- Category: ai_native_pm_mindset",
                "- Suggested angle: Challenge productivity-only AI adoption.",
                "- Final Score: 90",
                "- Recommendation: post",
                "",
                "## Parked Ideas",
                "",
                "None.",
            ]
        ),
        encoding="utf-8",
    )
    return path


def test_prompt_template_loads():
    prompt = load_prompt_template()

    assert "avoid hype" in prompt.lower()
    assert "do not generate a full linkedin post" in prompt.lower()


def test_no_api_key_skips_gracefully(tmp_path: Path, monkeypatch):
    report_path = _sample_report(tmp_path / "daily.md")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    result = interpret_report(
        report_path,
        config={"enabled": True, "model": "test-model"},
    )

    assert result.status == "skipped"
    assert "OPENROUTER_API_KEY" in result.warning
    assert "## Strategic Interpretation" not in report_path.read_text(encoding="utf-8")


def test_interpret_command_works_with_mocked_response(tmp_path: Path, monkeypatch):
    report_path = _sample_report(tmp_path / "daily.md")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(cli, "load_sources", lambda: {"sources": []})
    monkeypatch.setattr(
        "kaya_toast.interpret.load_llm",
        lambda: {
            "enabled": True,
            "model": "test-model",
            "temperature": 0.3,
            "max_tokens": 100,
        },
    )
    monkeypatch.setattr(
        "kaya_toast.interpret.call_openrouter",
        lambda _prompt, _idea, _config, _api_key: "Strategic interpretation: focus on operating loops.",
    )

    result = cli.main(["interpret", "--input", str(report_path)])

    assert result == 0
    text = report_path.read_text(encoding="utf-8")
    assert "## Strategic Interpretation" in text
    assert "Strategic interpretation: focus on operating loops." in text


def test_daily_interpret_does_not_break_deterministic_run(tmp_path: Path, monkeypatch):
    from kaya_toast.collect import CollectionResult
    from kaya_toast.models import Article

    article = Article(
        id="a1",
        title="AI-native product managers design workflow review loops",
        url="https://example.com",
        source="Mock RSS",
        summary="Product managers design, validate, review, and orchestrate AI workflows.",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("kaya_toast.workflow.DAILY_REPORTS_DIR", tmp_path / "reports" / "daily")
    monkeypatch.setattr("kaya_toast.workflow.RUN_HISTORY_PATH", tmp_path / "data" / "run_history.json")
    monkeypatch.setattr("kaya_toast.workflow.LATEST_RSS_PATH", tmp_path / "data" / "latest.json")
    monkeypatch.setattr(
        "kaya_toast.workflow.collect_from_rss_sources",
        lambda _sources: CollectionResult([article], {"Mock RSS": 1}, []),
    )
    monkeypatch.setattr("kaya_toast.workflow.load_sources", lambda: {"sources": []})
    monkeypatch.setattr(
        "kaya_toast.interpret.interpret_report",
        lambda report_path: type("Result", (), {"warning": "skipped", "report_path": report_path})(),
    )

    result = cli.main(["daily", "--interpret"])

    assert result == 0
    assert list((tmp_path / "reports" / "daily").glob("*-kaya-toast.md"))
