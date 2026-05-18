from pathlib import Path

from kaya_toast import cli
from kaya_toast.intelligence import (
    extract_ideas_from_reports,
    generate_strategy_report,
    identify_emerging_themes,
    suggest_topics_to_avoid,
)


def _daily_report(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "# kaya-toast Daily Brief",
                "### AI-native PMs are not faster PRD writers",
                "- Category: ai_native_pm_mindset",
                "- Primary pillar: ai_native_pm",
                "- Suggested angle: Challenge productivity-only AI adoption.",
                "- Final Score: 90",
                "- Fluff risk: 0",
                "### Top 10 prompts for PMs",
                "- Category: ai_native_pm_mindset",
                "- Primary pillar: ai_native_pm",
                "- Suggested angle: Generic prompt list.",
                "- Final Score: 10",
                "- Fluff risk: 90",
                "## Fluff Warnings",
                "- Top 10 prompts for PMs: fluff risk 90, recommendation reject",
            ]
        ),
        encoding="utf-8",
    )
    return path


def test_emerging_themes_are_detected_from_sample_data(tmp_path: Path):
    report = _daily_report(tmp_path / "reports" / "daily" / "2026-05-18-kaya-toast.md")
    ideas = extract_ideas_from_reports([report])

    themes = identify_emerging_themes(ideas)

    assert any("ai_native_pm_mindset" in theme for theme in themes)


def test_topics_to_avoid_are_detected(tmp_path: Path):
    report = _daily_report(tmp_path / "reports" / "daily" / "2026-05-18-kaya-toast.md")
    ideas = extract_ideas_from_reports([report])

    avoid = suggest_topics_to_avoid(ideas)

    assert "Top 10 prompts for PMs" in avoid


def test_strategy_command_creates_report(tmp_path: Path, monkeypatch):
    daily_dir = tmp_path / "reports" / "daily"
    output_dir = tmp_path / "reports" / "strategy"
    _daily_report(daily_dir / "2026-05-18-kaya-toast.md")
    monkeypatch.setattr("kaya_toast.intelligence.DAILY_REPORTS_DIR", daily_dir)
    monkeypatch.setattr("kaya_toast.intelligence.STRATEGY_REPORTS_DIR", output_dir)

    assert cli.main(["strategy"]) == 0
    report = next(output_dir.glob("*-kaya-toast-strategy.md"))
    text = report.read_text(encoding="utf-8")
    assert "# kaya-toast Strategy Brief" in text
    assert "## Suggested Next 5 Posts" in text


def test_suggested_next_posts_are_generated(tmp_path: Path):
    report = _daily_report(tmp_path / "reports" / "daily" / "2026-05-18-kaya-toast.md")
    output = generate_strategy_report(report.parent, tmp_path / "reports" / "strategy")

    text = output.read_text(encoding="utf-8")
    assert "## Recommended Content Bets" in text
    assert "## Suggested Next 5 Posts" in text


def test_strategy_report_format_is_stable(tmp_path: Path):
    report = _daily_report(tmp_path / "reports" / "daily" / "2026-05-18-kaya-toast.md")
    output = generate_strategy_report(report.parent, tmp_path / "reports" / "strategy")
    text = output.read_text(encoding="utf-8")

    for heading in [
        "## Strongest Emerging Themes",
        "## Repeated PM Transition Patterns",
        "## Contrarian Angles Worth Posting",
        "## Topics Becoming Too Generic",
        "## Positioning Opportunities",
        "## Recommended Content Bets",
        "## Topics to Avoid",
        "## Suggested Next 5 Posts",
    ]:
        assert heading in text
