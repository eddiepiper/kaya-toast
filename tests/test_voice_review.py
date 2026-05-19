from pathlib import Path

from kaya_toast.cli import main
from kaya_toast.voice_review import (
    analyze_draft_voice,
    generate_all_latest_voice_reviews,
    generate_voice_review,
)


def test_voice_review_command_creates_report(tmp_path: Path, monkeypatch):
    import kaya_toast.voice_review as voice_review

    monkeypatch.setattr(voice_review, "VOICE_REVIEW_DIR", tmp_path / "voice")
    draft = _draft(tmp_path / "2026-05-19-good-draft.md")

    result = main(["voice-review", "--draft", str(draft)])

    assert result == 0
    assert list((tmp_path / "voice").glob("*-voice-review.md"))


def test_generate_voice_review_contains_required_sections(tmp_path: Path):
    draft = _draft(tmp_path / "2026-05-19-good-draft.md")

    path = generate_voice_review(draft, output_dir=tmp_path / "voice")
    text = path.read_text(encoding="utf-8")

    assert "Overall verdict:" in text
    assert "Eddie voice fit:" in text
    assert "Enterprise operator fit:" in text
    assert "AI-native PM transition fit:" in text
    assert "Anti-fluff fit:" in text
    assert "Specificity:" in text
    assert "Practical usefulness:" in text
    assert "Human tone:" in text
    assert "Unsupported claim risk:" in text
    assert "## Lines To Rewrite" in text
    assert "## Final Recommendation" in text


def test_guardrail_penalizes_bad_language():
    signals = analyze_draft_voice(
        "AI will replace PMs. Here are 10 prompts for the future of work. Guaranteed results."
    )

    assert signals["prompt_bro_risk"] == "high"
    assert signals["unsupported_claim_risk"] == "high"
    assert signals["fluff_risk"] == "high"
    assert signals["eddie_voice_fit"] == "weak"
    assert "banned phrase" in signals["issues"]


def test_emoji_and_em_dash_lines_flagged():
    signals = analyze_draft_voice("Great PMs do this \U0001f680\nAI-native PMs win — always")

    assert len(signals["lines_to_rewrite"]) == 2
    assert "emoji" in signals["issues"]
    assert "em-dash" in signals["issues"]


def test_generic_ai_hype_is_penalized():
    signals = analyze_draft_voice("AI will change everything. This revolutionary game changer unlocks growth.")

    assert "generic AI optimism" in signals["issues"]
    assert signals["anti_fluff_fit"] == "weak"


def test_all_latest_reviews_latest_date_only(tmp_path: Path, monkeypatch):
    import kaya_toast.voice_review as voice_review

    monkeypatch.setattr(voice_review, "DRAFTS_DIR", tmp_path)
    _draft(tmp_path / "2026-05-18-old.md")
    _draft(tmp_path / "2026-05-19-one.md")
    _draft(tmp_path / "2026-05-19-two.md")

    paths = generate_all_latest_voice_reviews(output_dir=tmp_path / "voice")

    assert len(paths) == 2


def _draft(path: Path) -> Path:
    path.write_text(
        "\n".join(
            [
                "# LinkedIn Draft: good",
                "",
                "## Source Grounding",
                "Grounded in source review.",
                "",
                "## Draft Version 1",
                "AI-native PM work is about enterprise workflow, operator judgment, and decision loops.",
            ]
        ),
        encoding="utf-8",
    )
    return path
