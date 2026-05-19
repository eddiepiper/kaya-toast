from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kaya_toast.draft import DRAFTS_DIR, draft_from_report
from kaya_toast.draft import extract_report_ideas
from kaya_toast.preference import add_feedback
from kaya_toast.voice_review import generate_voice_review


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DAILY_REPORTS_DIR = PROJECT_ROOT / "reports" / "daily"
SUPPORTED_FEEDBACK = {"like", "use_later", "too_generic", "strong_angle"}


@dataclass(frozen=True)
class TelegramReviewResult:
    response: str
    paths: list[Path]


def handle_dry_run(command: str) -> TelegramReviewResult:
    return handle_command(command, dry_run=True)


def handle_command(command: str, dry_run: bool = False) -> TelegramReviewResult:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    parts = command.strip().split()
    if not parts:
        return TelegramReviewResult(_help_text(), [])

    action = parts[0].lstrip("/").lower()
    if action == "help":
        return TelegramReviewResult(_help_text(), [])

    report_path = latest_daily_report()
    if report_path is None:
        return TelegramReviewResult("No daily report found.", [])

    ideas = extract_report_ideas(report_path)
    if action == "top":
        return TelegramReviewResult(_top_response(ideas), [])
    if action == "idea":
        idea = _idea_by_number(ideas, parts)
        return TelegramReviewResult(_idea_response(idea), [])
    if action in SUPPORTED_FEEDBACK:
        idea = _idea_by_number(ideas, parts)
        if dry_run:
            return TelegramReviewResult(f"DRY RUN: would save {action} for {idea['idea_id']}", [])
        add_feedback(str(idea["idea_id"]), action, "telegram-review")
        return TelegramReviewResult(f"Saved {action} for {idea['idea_id']}", [])
    if action == "draft":
        idea = _idea_by_number(ideas, parts)
        paths = draft_from_report(report_path, idea_id=str(idea["idea_id"]), force=True, use_source_review=True)
        return TelegramReviewResult(_paths_response("Draft", paths), paths)
    if action == "voice_review":
        idea = _idea_by_number(ideas, parts)
        draft_paths = _matching_drafts(str(idea["idea_id"]))
        if not draft_paths:
            draft_paths = draft_from_report(report_path, idea_id=str(idea["idea_id"]), force=True, use_source_review=True)
        review_paths = [generate_voice_review(path) for path in draft_paths[:1]]
        return TelegramReviewResult(_paths_response("Voice review", review_paths), review_paths)

    token_status = "configured" if token else "not configured"
    return TelegramReviewResult(f"Unknown command. Telegram token is {token_status}.\n\n{_help_text()}", [])


def latest_daily_report(reports_dir: str | Path | None = None) -> Path | None:
    report_dir = Path(reports_dir) if reports_dir is not None else DAILY_REPORTS_DIR
    reports = sorted(report_dir.glob("*-kaya-toast.md"))
    return reports[-1] if reports else None


def _top_response(ideas: list[dict[str, Any]], limit: int = 5) -> str:
    if not ideas:
        return "No ideas found in latest daily report."
    lines = ["Top ideas:"]
    for index, idea in enumerate(ideas[:limit], start=1):
        lines.append(f"{index}. {idea.get('topic', idea.get('heading', 'Untitled idea'))} [{idea.get('recommendation', 'unknown')}]")
    return "\n".join(lines)


def _idea_response(idea: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"Idea: {idea.get('topic', idea.get('heading', 'Untitled idea'))}",
            f"Idea ID: {idea.get('idea_id', 'unknown')}",
            f"Recommendation: {idea.get('recommendation', 'unknown')}",
            f"Angle: {idea.get('suggested_angle', 'No angle captured.')}",
        ]
    )


def _idea_by_number(ideas: list[dict[str, Any]], parts: list[str]) -> dict[str, Any]:
    if len(parts) < 2:
        raise ValueError("Command requires an idea number.")
    try:
        number = int(parts[1])
    except ValueError as error:
        raise ValueError("Idea number must be numeric.") from error
    if number < 1 or number > len(ideas):
        raise ValueError(f"Idea number out of range: {number}")
    return ideas[number - 1]


def _matching_drafts(idea_id: str) -> list[Path]:
    slug = _safe_slug(idea_id)
    return sorted(DRAFTS_DIR.glob(f"*-{slug}.md"))


def _paths_response(label: str, paths: list[Path]) -> str:
    if not paths:
        return f"No {label.lower()} generated."
    return "\n".join(f"{label}: {path}" for path in paths)


def _help_text() -> str:
    return "\n".join(
        [
            "Commands:",
            "/top",
            "/idea 1",
            "/like 1",
            "/use_later 1",
            "/too_generic 1",
            "/strong_angle 1",
            "/draft 1",
            "/voice_review 1",
            "/help",
            "No LinkedIn auto-posting is supported.",
        ]
    )


def _safe_slug(value: str) -> str:
    import re

    return re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-")[:120] or "draft"
