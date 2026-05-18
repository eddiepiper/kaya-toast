from __future__ import annotations

import json
import os
import re
from datetime import date
from pathlib import Path
from typing import Any

from kaya_toast.config import load_llm
from kaya_toast.interpret import call_openrouter


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DRAFTS_DIR = PROJECT_ROOT / "drafts"
PROMPT_PATH = PROJECT_ROOT / "prompts" / "linkedin_draft.md"


def load_draft_prompt(path: str | Path = PROMPT_PATH) -> str:
    return Path(path).read_text(encoding="utf-8")


def draft_from_report(
    report_path: str | Path,
    idea_id: str | None = None,
    top: int | None = None,
    force: bool = False,
    drafts_dir: str | Path = DRAFTS_DIR,
) -> list[Path]:
    ideas = extract_report_ideas(report_path)
    selected = _select_ideas(ideas, idea_id=idea_id, top=top)
    draft_paths: list[Path] = []
    for idea in selected:
        if idea.get("recommendation") != "post" and not force:
            continue
        draft_paths.append(write_draft(idea, drafts_dir=drafts_dir))
    return draft_paths


def extract_report_ideas(report_path: str | Path) -> list[dict[str, Any]]:
    ideas: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    collecting_hooks = False
    for line in Path(report_path).read_text(encoding="utf-8").splitlines():
        if line.startswith("### "):
            if current:
                ideas.append(current)
            current = {"heading": line.removeprefix("### ").strip(), "hook_options": []}
            collecting_hooks = False
        elif current is not None and line.startswith("- Hook options:"):
            collecting_hooks = True
        elif current is not None and collecting_hooks and line.startswith("  - "):
            current["hook_options"].append(line.removeprefix("  - ").strip())
        elif current is not None and line.startswith("- "):
            collecting_hooks = False
            key, _, value = line.removeprefix("- ").partition(": ")
            if key and value:
                current[key.lower().replace(" ", "_")] = value.strip()
    if current:
        ideas.append(current)
    return [idea for idea in ideas if "idea_id" in idea]


def write_draft(idea: dict[str, Any], drafts_dir: str | Path = DRAFTS_DIR) -> Path:
    output_dir = Path(drafts_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    idea_id = str(idea["idea_id"])
    path = output_dir / f"{date.today().isoformat()}-{_safe_filename(idea_id)}.md"
    path.write_text(render_draft(idea), encoding="utf-8")
    return path


def render_draft(idea: dict[str, Any]) -> str:
    llm_draft = generate_llm_draft(idea)
    hooks = idea.get("hook_options", [])
    hook_lines = "\n".join(f"- {hook}" for hook in hooks) if hooks else "- None"
    return "\n".join(
        [
            f"# LinkedIn Draft: {idea['idea_id']}",
            "",
            "## Topic",
            str(idea.get("topic", idea.get("heading", ""))),
            "",
            "## Target Audience",
            str(idea.get("target_audience", "Traditional PMs transitioning into AI PM roles.")),
            "",
            "## Suggested Angle",
            str(idea.get("suggested_angle", "")),
            "",
            "## Hook Options",
            hook_lines,
            "",
            "## Recommended Structure",
            "- Opening observation",
            "- PM pain point",
            "- AI-native shift",
            "- Practical example",
            "- Takeaway",
            "",
            "## Draft Version 1",
            llm_draft or _deterministic_draft(idea),
            "",
            "## Less GPT Version",
            _less_gpt_version(idea),
            "",
            "## Visual Suggestion",
            "A simple before-after decision loop diagram showing traditional PM workflow vs AI-native PM workflow.",
            "",
            "## CTA",
            "What part of your PM workflow would you redesign first with AI in the loop?",
            "",
        ]
    )


def generate_llm_draft(idea: dict[str, Any]) -> str:
    config = load_llm()
    if not config.get("enabled", False):
        return ""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return ""
    return call_openrouter(load_draft_prompt(), idea, config, api_key)


def _select_ideas(
    ideas: list[dict[str, Any]],
    idea_id: str | None,
    top: int | None,
) -> list[dict[str, Any]]:
    if idea_id:
        return [idea for idea in ideas if idea.get("idea_id") == idea_id]
    if top:
        post_ideas = [idea for idea in ideas if idea.get("recommendation") == "post"]
        return post_ideas[:top]
    return []


def _deterministic_draft(idea: dict[str, Any]) -> str:
    topic = str(idea.get("topic", idea.get("heading", "This idea")))
    angle = str(idea.get("suggested_angle", ""))
    why = str(idea.get("why_it_matters", ""))
    return (
        f"{topic}\n\n"
        f"The common mistake is treating AI as a shortcut for PM output. {why}\n\n"
        f"The better move is to redesign the workflow around judgment, review, and decision quality. {angle}\n\n"
        "That is the real AI-native PM shift: not faster documents, better operating loops."
    )


def _less_gpt_version(idea: dict[str, Any]) -> str:
    topic = str(idea.get("topic", idea.get("heading", "This idea")))
    return (
        f"I keep coming back to this: {topic}.\n\n"
        "For PMs, the useful question is not how to make AI write more. "
        "It is where AI changes the way we decide, validate, and review work."
    )


def _safe_filename(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-")
    return slug[:120] or "draft"
