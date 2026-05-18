from pathlib import Path

from kaya_toast.draft import draft_from_report, load_draft_prompt


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
    assert "That is the real AI-native PM shift" in text


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
