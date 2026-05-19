from __future__ import annotations

import json
import os
import re
from datetime import date
from pathlib import Path
from typing import Any

from kaya_toast.config import load_llm, load_voice
from kaya_toast.interpret import call_openrouter


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DRAFTS_DIR = PROJECT_ROOT / "drafts"
PROMPT_PATH = PROJECT_ROOT / "prompts" / "linkedin_draft.md"
SOURCE_REVIEW_DIR = PROJECT_ROOT / "reports" / "source_review"
INTERNAL_PIPELINE_PHRASES = [
    "Source title points to",
    "Daily report rationale",
    "Suggested angle captured by the pipeline",
    "Source summary is missing",
    "source-grounded point",
    "source metadata",
    "The source says",
    "Grounded in source review",
]


def load_draft_prompt(path: str | Path = PROMPT_PATH) -> str:
    return Path(path).read_text(encoding="utf-8")


def draft_from_report(
    report_path: str | Path,
    idea_id: str | None = None,
    top: int | None = None,
    force: bool = False,
    drafts_dir: str | Path = DRAFTS_DIR,
    source_review_path: str | Path | None = None,
    use_source_review: bool = False,
) -> list[Path]:
    ideas = extract_report_ideas(report_path)
    selected = _select_ideas(
        ideas,
        idea_id=idea_id,
        top=top,
        include_non_post=use_source_review or source_review_path is not None,
    )
    draft_paths: list[Path] = []
    for idea in selected:
        if idea.get("recommendation") != "post" and not force:
            if not (use_source_review or source_review_path is not None):
                continue
        source_review = _load_source_review_for_idea(
            idea,
            report_path=report_path,
            explicit_path=source_review_path,
            enabled=use_source_review or source_review_path is not None,
        )
        draft_paths.append(write_draft(idea, drafts_dir=drafts_dir, source_review=source_review))
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


def write_draft(
    idea: dict[str, Any],
    drafts_dir: str | Path = DRAFTS_DIR,
    source_review: dict[str, Any] | None = None,
) -> Path:
    output_dir = Path(drafts_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    idea_id = str(idea["idea_id"])
    path = output_dir / f"{date.today().isoformat()}-{_safe_filename(idea_id)}.md"
    path.write_text(render_draft(idea, source_review=source_review), encoding="utf-8")
    return path


def render_draft(idea: dict[str, Any], source_review: dict[str, Any] | None = None) -> str:
    source_review = source_review or {}
    llm_draft = generate_llm_draft({**idea, "source_review": source_review})
    hooks = idea.get("hook_options", [])
    hook_lines = "\n".join(f"- {hook}" for hook in _three_hooks(idea, hooks))
    return "\n".join(
        [
            f"# LinkedIn Draft: {idea['idea_id']}",
            "",
            "## Source Grounding",
            _source_grounding(source_review),
            "",
            "## Key Evidence",
            _render_list(source_review.get("evidence", []) or _fallback_evidence(idea)),
            "## Claims To Avoid",
            _render_list(source_review.get("claims_to_avoid", []) or _fallback_claims()),
            "## Recommended Angle",
            str(source_review.get("strong_angle") or idea.get("suggested_angle", "")),
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
            llm_draft or _deterministic_draft(idea, source_review),
            "",
            "## Less GPT Version",
            _less_gpt_version(idea, source_review),
            "",
            "## Eddie-style Version",
            _eddie_style_version(idea, source_review),
            "",
            "## Enterprise Operator Angle",
            _enterprise_operator_angle(idea, source_review),
            "",
            "## Visual / Carousel Suggestion",
            _visual_suggestion(idea),
            "",
            "## CTA",
            "What part of your PM workflow would you redesign first with AI in the loop?",
            "",
            "## Risk Check",
            _risk_check(idea, source_review),
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
    include_non_post: bool = False,
) -> list[dict[str, Any]]:
    if idea_id:
        return [idea for idea in ideas if idea.get("idea_id") == idea_id]
    if top:
        if include_non_post:
            return ideas[:top]
        post_ideas = [idea for idea in ideas if idea.get("recommendation") == "post"]
        return post_ideas[:top]
    return []


def _deterministic_draft(idea: dict[str, Any], source_review: dict[str, Any] | None = None) -> str:
    source_review = source_review or {}
    topic = str(idea.get("topic", idea.get("heading", "This idea")))
    angle = str(idea.get("suggested_angle", ""))
    why = str(idea.get("why_it_matters", ""))
    evidence = source_review.get("evidence", [])
    evidence_line = _public_evidence_line(evidence, topic)
    return (
        f"{topic}\n\n"
        f"The common mistake is treating AI as a shortcut for PM output. {why}\n\n"
        f"The useful signal is narrower: {evidence_line}\n\n"
        f"The better move is to redesign the workflow around judgment, review, and decision quality. {angle}\n\n"
        "That is the real AI-native PM shift: not faster documents, better operating loops."
    )


def _less_gpt_version(idea: dict[str, Any], source_review: dict[str, Any] | None = None) -> str:
    topic = str(idea.get("topic", idea.get("heading", "This idea")))
    source_review = source_review or {}
    angle = str(source_review.get("strong_angle") or idea.get("suggested_angle", ""))
    return (
        f"I keep coming back to this: {topic}.\n\n"
        "For PMs, the useful question is not how to make AI write more. "
        f"It is where AI changes the way we decide, validate, and review work. {angle}"
    )


def _eddie_style_version(idea: dict[str, Any], source_review: dict[str, Any] | None = None) -> str:
    source_review = source_review or {}
    voice = load_voice()
    topic = str(idea.get("topic", idea.get("heading", "this shift")))
    angle = str(source_review.get("strong_angle") or idea.get("suggested_angle", ""))
    evidence = source_review.get("evidence", [])
    evidence_line = _public_evidence_line(evidence, topic)
    positioning = voice.get("preferred_positioning", ["Enterprise AI operator"])[0]
    return "\n".join(
        [
            f"{topic} is not a tooling story.",
            "",
            "That framing is useful, but too narrow.",
            "",
            f"The real shift is how PMs design workflows, decision loops, review points, and evidence quality when AI becomes part of the operating model. {evidence_line}",
            "",
            f"For an enterprise PM, the practical implication is simple: treat AI as part of the execution loop, not magic outside the system. {angle}",
            "",
            f"That is the lane: {positioning}",
        ]
    )


def _safe_filename(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-")
    return slug[:120] or "draft"


def _public_evidence_line(evidence: Any, topic: str) -> str:
    if not isinstance(evidence, list) or not evidence:
        return "Keep the claim narrow and tied to the PM workflow shift."
    for item in evidence:
        cleaned = _strip_internal_pipeline_language(str(item)).strip()
        if cleaned:
            return cleaned
    return f"Keep the claim focused on {topic} as a PM workflow shift."


def _strip_internal_pipeline_language(value: str) -> str:
    text = value
    replacements = {
        "Source title points to:": "The idea centers on",
        "Daily report rationale:": "",
        "Suggested angle captured by the pipeline:": "",
        "Source summary is missing; do not imply details beyond the daily report metadata.": "",
        "source-grounded point": "narrow point",
        "source metadata": "available evidence",
        "The source says": "The useful signal is",
        "Grounded in source review": "Grounded in review",
    }
    for phrase, replacement in replacements.items():
        text = text.replace(phrase, replacement)
    for phrase in INTERNAL_PIPELINE_PHRASES:
        text = re.sub(re.escape(phrase), "", text, flags=re.IGNORECASE)
    return " ".join(text.split())


def _load_source_review_for_idea(
    idea: dict[str, Any],
    report_path: str | Path,
    explicit_path: str | Path | None,
    enabled: bool,
) -> dict[str, Any]:
    if not enabled:
        return {}
    if explicit_path is not None:
        return parse_source_review(explicit_path)
    review_path = _matching_source_review_path(idea, report_path)
    if review_path is None:
        return {"missing": True}
    return parse_source_review(review_path)


def _matching_source_review_path(idea: dict[str, Any], report_path: str | Path) -> Path | None:
    report_date = _report_date(Path(report_path))
    idea_slug = _safe_filename(str(idea.get("idea_id", ""))).lower()
    expected = SOURCE_REVIEW_DIR / f"{report_date}-{idea_slug}-source-review.md"
    if expected.exists():
        return expected
    matches = sorted(SOURCE_REVIEW_DIR.glob(f"{report_date}-*-source-review.md"))
    topic = str(idea.get("topic", idea.get("heading", ""))).lower()
    for path in matches:
        if idea_slug in path.name or _safe_filename(topic).lower() in path.name:
            return path
    return None


def parse_source_review(path: str | Path) -> dict[str, Any]:
    text = Path(path).read_text(encoding="utf-8")
    return {
        "path": str(path),
        "evidence": _section_list(text, "Evidence Extracted"),
        "claims_to_avoid": _section_list(text, "Unsupported Claims to Avoid"),
        "strong_angle": _section_field(text, "Content Angle Recommendation", "Strong angle"),
        "weak_angle": _section_field(text, "Content Angle Recommendation", "Weak angle to avoid"),
        "recommended_action": _section_field(text, "Content Angle Recommendation", "Recommended action"),
        "quality_score": _section_text(text, "Source Quality Score").strip(),
    }


def _section_text(text: str, heading: str) -> str:
    marker = f"## {heading}"
    if marker not in text:
        return ""
    section = text.split(marker, 1)[1]
    next_heading = section.find("\n## ")
    if next_heading >= 0:
        section = section[:next_heading]
    return section.strip()


def _section_list(text: str, heading: str) -> list[str]:
    section = _section_text(text, heading)
    return [line.removeprefix("- ").strip() for line in section.splitlines() if line.startswith("- ")]


def _section_field(text: str, heading: str, field: str) -> str:
    prefix = f"- {field}: "
    for line in _section_text(text, heading).splitlines():
        if line.startswith(prefix):
            return line.removeprefix(prefix).strip()
    return ""


def _source_grounding(source_review: dict[str, Any]) -> str:
    if not source_review:
        return "No source review attached. Keep claims limited to the daily report metadata."
    if source_review.get("missing"):
        return "No matching source review found. Keep claims limited to the daily report metadata."
    return f"Grounded in source review: {source_review.get('path', 'attached source review')}"


def _fallback_evidence(idea: dict[str, Any]) -> list[str]:
    return [
        f"Daily report topic: {idea.get('topic', idea.get('heading', 'Untitled idea'))}",
        f"Daily report rationale: {idea.get('why_it_matters', 'No rationale captured.')}",
        f"Pipeline angle: {idea.get('suggested_angle', 'No angle captured.')}",
    ]


def _fallback_claims() -> list[str]:
    return [
        "Do not claim source details beyond the daily report metadata.",
        "Do not claim measurable impact or implementation results unless supported.",
        "Do not frame the post as generic AI productivity advice.",
    ]


def _three_hooks(idea: dict[str, Any], hooks: Any) -> list[str]:
    hook_list = [str(hook) for hook in hooks] if isinstance(hooks, list) else []
    topic = str(idea.get("topic", idea.get("heading", "this PM shift")))
    while len(hook_list) < 3:
        additions = [
            f"{topic} is not a tooling story. It is an operating model story.",
            "AI-native PM work starts when the workflow changes, not when the tool changes.",
            "The hard part is not generating more output. It is improving the decision loop.",
        ]
        hook_list.append(additions[len(hook_list) % len(additions)])
    return hook_list[:3]


def _enterprise_operator_angle(idea: dict[str, Any], source_review: dict[str, Any]) -> str:
    angle = str(source_review.get("strong_angle") or idea.get("suggested_angle", ""))
    return (
        "Frame this as an operator problem: how teams redesign review loops, stakeholder alignment, "
        f"and decision quality. Recommended angle: {angle}"
    )


def _visual_suggestion(idea: dict[str, Any]) -> str:
    topic = str(idea.get("topic", idea.get("heading", "the idea")))
    return (
        f"A simple 3-panel carousel: 1) old PM workflow for {topic}, "
        "2) source-grounded tension, 3) AI-native operating loop."
    )


def _risk_check(idea: dict[str, Any], source_review: dict[str, Any]) -> str:
    risks = []
    if source_review.get("missing") or not source_review:
        risks.append("Source review missing; avoid detailed source claims.")
    score = str(source_review.get("quality_score", "")).strip()
    if score:
        risks.append(f"Source quality score: {score}.")
    if str(idea.get("fluff_risk", "")).strip():
        risks.append(f"Fluff risk from daily report: {idea.get('fluff_risk')}.")
    weak = str(source_review.get("weak_angle", "")).strip()
    if weak:
        risks.append(f"Avoid weak angle: {weak}.")
    return _render_list(risks or ["No major risk flagged by available metadata."]).rstrip()


def _report_date(path: Path) -> str:
    match = re.match(r"(\d{4}-\d{2}-\d{2})-", path.name)
    if match:
        return match.group(1)
    return date.today().isoformat()


def _render_list(items: list[str]) -> str:
    if not items:
        return "None.\n"
    return "\n".join(f"- {item}" for item in items) + "\n"
