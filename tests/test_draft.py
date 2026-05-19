from pathlib import Path

from kaya_toast.draft import (
    INTERNAL_PIPELINE_PHRASES,
    draft_from_report,
    load_draft_prompt,
    parse_source_review,
)


def _report(path: Path) -> Path:
    path.write_text(
        "\n".join(
            [
                "# kaya-toast Daily Brief",
                "## Top LinkedIn Content Ideas",
                "### Strong idea one",
                "- Idea ID: IDEA001",
                "- Topic: Strong idea one",
                "- Target audience: Traditional PMs",
                "- Suggested angle: Make AI-native workflows practical.",
                "- Hook options:",
                "  - Hook one",
                "- Score: 90",
                "- Final Score: 90",
                "- Recommendation: post",
                "### Strong idea two",
                "- Idea ID: IDEA002",
                "- Topic: Strong idea two",
                "- Target audience: Enterprise PMs",
                "- Suggested angle: Show workflow review loops.",
                "- Hook options:",
                "  - Hook two",
                "- Score: 80",
                "- Final Score: 80",
                "- Recommendation: post",
                "## Rejected Ideas",
                "### Weak idea",
                "- Idea ID: IDEA003",
                "- Topic: Weak idea",
                "- Suggested angle: Too generic.",
                "- Hook options:",
                "  - Weak hook",
                "- Score: 10",
                "- Final Score: 10",
                "- Recommendation: reject",
            ]
        ),
        encoding="utf-8",
    )
    return path


def test_draft_prompt_loads():
    prompt = load_draft_prompt()

    assert "traditional PMs transitioning into AI PMs" in prompt
    assert "No emojis" in prompt


def test_draft_command_creates_draft_file(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("kaya_toast.draft.load_llm", lambda: {"enabled": False})
    report = _report(tmp_path / "report.md")

    paths = draft_from_report(report, idea_id="IDEA001", drafts_dir=tmp_path / "drafts")

    assert len(paths) == 1
    assert paths[0].exists()
    assert "# LinkedIn Draft: IDEA001" in paths[0].read_text(encoding="utf-8")


def test_rejected_idea_is_not_drafted_unless_forced(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("kaya_toast.draft.load_llm", lambda: {"enabled": False})
    report = _report(tmp_path / "report.md")

    blocked = draft_from_report(report, idea_id="IDEA003", drafts_dir=tmp_path / "drafts")
    forced = draft_from_report(
        report,
        idea_id="IDEA003",
        force=True,
        drafts_dir=tmp_path / "drafts",
    )

    assert blocked == []
    assert len(forced) == 1


def test_top_three_creates_up_to_three_drafts(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("kaya_toast.draft.load_llm", lambda: {"enabled": False})
    report = _report(tmp_path / "report.md")

    paths = draft_from_report(report, top=3, drafts_dir=tmp_path / "drafts")

    assert len(paths) == 2


def test_no_api_key_still_produces_deterministic_outline(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr("kaya_toast.draft.load_llm", lambda: {"enabled": True, "model": "test"})
    report = _report(tmp_path / "report.md")

    path = draft_from_report(report, idea_id="IDEA001", drafts_dir=tmp_path / "drafts")[0]

    text = path.read_text(encoding="utf-8")
    assert "## Recommended Structure" in text
    assert "## Source Grounding" in text
    assert "## Claims To Avoid" in text
    assert "## Enterprise Operator Angle" in text
    assert "## Eddie-style Version" in text
    assert "## Risk Check" in text
    assert "That is the real AI-native PM shift" in text
    assert "not a tooling story" in text


def test_mock_llm_draft_generation(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test")
    monkeypatch.setattr("kaya_toast.draft.load_llm", lambda: {"enabled": True, "model": "test"})
    monkeypatch.setattr(
        "kaya_toast.draft.call_openrouter",
        lambda _prompt, _idea, _config, _key: "Mock LLM draft.",
    )
    report = _report(tmp_path / "report.md")

    path = draft_from_report(report, idea_id="IDEA001", drafts_dir=tmp_path / "drafts")[0]

    assert "Mock LLM draft." in path.read_text(encoding="utf-8")


def test_source_review_path_adds_grounding_sections(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("kaya_toast.draft.load_llm", lambda: {"enabled": False})
    report = _report(tmp_path / "report.md")
    source_review = _source_review(tmp_path / "source-review.md")

    path = draft_from_report(
        report,
        idea_id="IDEA001",
        source_review_path=source_review,
        drafts_dir=tmp_path / "drafts",
    )[0]

    text = path.read_text(encoding="utf-8")
    assert "Grounded in source review" in text
    assert "Source says the operating model changed." in text
    assert "Do not claim revenue impact." in text
    assert "## Visual / Carousel Suggestion" in text
    assert "## Eddie-style Version" in text


def test_draft_public_sections_do_not_contain_pipeline_phrases(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("kaya_toast.draft.load_llm", lambda: {"enabled": False})
    report = _report(tmp_path / "report.md")
    source_review = _source_review(tmp_path / "source-review.md")

    path = draft_from_report(
        report,
        idea_id="IDEA001",
        source_review_path=source_review,
        drafts_dir=tmp_path / "drafts",
    )[0]
    text = path.read_text(encoding="utf-8")

    for section in [
        "Draft Version 1",
        "Less GPT Version",
        "Eddie-style Version",
        "Enterprise Operator Angle",
    ]:
        section_text = _section_text(text, section)
        assert not _contains_internal_phrase(section_text)


def test_source_grounding_may_contain_grounding_metadata(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("kaya_toast.draft.load_llm", lambda: {"enabled": False})
    report = _report(tmp_path / "report.md")
    source_review = _source_review(tmp_path / "source-review.md")

    path = draft_from_report(
        report,
        idea_id="IDEA001",
        source_review_path=source_review,
        drafts_dir=tmp_path / "drafts",
    )[0]

    assert "Grounded in source review" in _section_text(
        path.read_text(encoding="utf-8"),
        "Source Grounding",
    )


def test_use_source_review_top_three_drafts_three_ideas(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("kaya_toast.draft.load_llm", lambda: {"enabled": False})
    report = _report(tmp_path / "2026-05-19-kaya-toast.md")

    paths = draft_from_report(
        report,
        top=3,
        use_source_review=True,
        drafts_dir=tmp_path / "drafts",
    )

    assert len(paths) == 3


def test_parse_source_review_extracts_grounding_fields(tmp_path: Path):
    path = _source_review(tmp_path / "source-review.md")

    parsed = parse_source_review(path)

    assert parsed["evidence"] == [
        "Source title points to: Strong idea one.",
        "Daily report rationale: Source says the operating model changed.",
        "Suggested angle captured by the pipeline: Treat AI as workflow redesign.",
        "Source summary is missing; do not imply details beyond the daily report metadata.",
    ]
    assert parsed["claims_to_avoid"] == ["Do not claim revenue impact."]
    assert parsed["strong_angle"] == "Treat AI as workflow redesign."
    assert parsed["quality_score"] == "88"


def _source_review(path: Path) -> Path:
    path.write_text(
        "\n".join(
            [
                "# Source Review: Strong idea one",
                "",
                "## Evidence Extracted",
                "- Source title points to: Strong idea one.",
                "- Daily report rationale: Source says the operating model changed.",
                "- Suggested angle captured by the pipeline: Treat AI as workflow redesign.",
                "- Source summary is missing; do not imply details beyond the daily report metadata.",
                "",
                "## Unsupported Claims to Avoid",
                "- Do not claim revenue impact.",
                "",
                "## Content Angle Recommendation",
                "- Strong angle: Treat AI as workflow redesign.",
                "- Weak angle to avoid: Generic productivity.",
                "- Recommended action: draft",
                "",
                "## Source Quality Score",
                "88",
            ]
        ),
        encoding="utf-8",
    )
    return path


def _section_text(text: str, heading: str) -> str:
    marker = f"## {heading}"
    section = text.split(marker, 1)[1]
    next_heading = section.find("\n## ")
    if next_heading >= 0:
        section = section[:next_heading]
    return section


def _contains_internal_phrase(text: str) -> bool:
    return any(phrase.lower() in text.lower() for phrase in INTERNAL_PIPELINE_PHRASES)
