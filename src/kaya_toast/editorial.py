from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from kaya_toast.config import load_positioning, load_preferences
from kaya_toast.draft import extract_report_ideas
from kaya_toast.intelligence import STRATEGY_REPORTS_DIR
from kaya_toast.preference import summarize_feedback


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EDITORIAL_REPORTS_DIR = PROJECT_ROOT / "reports" / "editorial"


@dataclass(frozen=True)
class EditorialContext:
    daily_report_path: Path
    strategy_report_path: Path | None
    preferences: dict[str, Any]
    positioning: dict[str, Any]
    feedback_summary: dict[str, Any]


def generate_editorial_report(
    report_path: str | Path,
    output_dir: str | Path | None = None,
) -> Path:
    source_report = Path(report_path)
    ideas = extract_report_ideas(source_report)
    if not ideas:
        raise ValueError(f"No content ideas found in report: {source_report}")

    context = EditorialContext(
        daily_report_path=source_report,
        strategy_report_path=find_strategy_report(source_report),
        preferences=load_preferences(),
        positioning=load_positioning(),
        feedback_summary=summarize_feedback(),
    )
    editorial_dir = Path(output_dir) if output_dir is not None else EDITORIAL_REPORTS_DIR
    output_path = editorial_dir / f"{_report_date(source_report)}-kaya-toast-editorial.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_editorial_report(ideas, context), encoding="utf-8")
    return output_path


def render_editorial_report(ideas: list[dict[str, Any]], context: EditorialContext) -> str:
    ranked_ideas = sorted(ideas, key=_editorial_score, reverse=True)
    selected = ranked_ideas[0]
    alternatives = ranked_ideas[1:4]
    strategy_text = _read_optional_text(context.strategy_report_path)

    sections = [
        "# kaya-toast Editorial Recommendation",
        "",
        "## Today's Recommended Idea",
        "",
        _render_recommended_idea(selected),
        "## Why This Idea",
        "",
        _render_why_this_idea(selected, context, strategy_text),
        "## Why Not The Other Top Ideas",
        "",
        _render_alternatives(alternatives),
        "## Suggested LinkedIn Angle",
        "",
        _suggest_linkedin_angle(selected),
        "",
        "## Risk Of Sounding Generic",
        "",
        _generic_risk(selected, context),
        "",
        "## Stronger Operator Framing",
        "",
        _operator_framing(selected, context),
        "",
        "## Recommended Next Action",
        "",
        _next_action(selected),
        "",
        "## Inputs Used",
        "",
        _render_inputs(context),
    ]
    return "\n".join(sections).rstrip() + "\n"


def find_strategy_report(report_path: str | Path, strategy_dir: str | Path = STRATEGY_REPORTS_DIR) -> Path | None:
    report_date = _report_date(Path(report_path))
    exact = Path(strategy_dir) / f"{report_date}-kaya-toast-strategy.md"
    if exact.exists():
        return exact
    reports = sorted(Path(strategy_dir).glob("*-kaya-toast-strategy.md"))
    return reports[-1] if reports else None


def _render_recommended_idea(idea: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"- Topic: {idea.get('topic', idea.get('heading', 'Untitled idea'))}",
            f"- Idea ID: {idea.get('idea_id', 'unknown')}",
            f"- Recommendation: {idea.get('recommendation', 'unknown')}",
            f"- Final score: {idea.get('final_score', '0')}",
            f"- Fluff risk: {idea.get('fluff_risk', idea.get('fluff_score', '0'))}",
            f"- Positioning fit: {idea.get('positioning_fit', '0')}",
            "",
        ]
    )


def _render_why_this_idea(
    idea: dict[str, Any],
    context: EditorialContext,
    strategy_text: str,
) -> str:
    audience = str(idea.get("target_audience", "AI-native PM readers")).rstrip(".")
    reasons = [
        f"It is the strongest available {idea.get('recommendation', 'candidate')} idea by editorial score.",
        f"It fits the preferred audience: {audience}.",
        f"It can be framed through operator judgment instead of generic AI productivity: {idea.get('suggested_angle', '')}",
    ]
    if idea.get("memory-informed_recommendation"):
        reasons.append(f"Preference memory says: {idea['memory-informed_recommendation']}.")
    if _topic_in_text(idea, strategy_text):
        reasons.append("The latest strategy report also names this topic as a recommended content bet.")
    liked = context.feedback_summary.get("most_liked_categories", [])
    if liked and idea.get("category") in liked:
        reasons.append(f"It is aligned with liked category memory: {idea.get('category')}.")
    return _render_list(reasons)


def _render_alternatives(ideas: list[dict[str, Any]]) -> str:
    if not ideas:
        return "None.\n"
    lines = []
    for idea in ideas:
        reason = _alternative_reason(idea)
        lines.append(f"- {idea.get('topic', idea.get('heading', 'Untitled idea'))}: {reason}")
    return "\n".join(lines) + "\n"


def _alternative_reason(idea: dict[str, Any]) -> str:
    recommendation = str(idea.get("recommendation", ""))
    fluff = _int_value(idea.get("fluff_risk", idea.get("fluff_score", 0)))
    warning = str(idea.get("positioning_warning", ""))
    if recommendation == "park":
        return "promising, but parked; needs sharper proof or operator framing before drafting."
    if recommendation == "reject":
        return "rejected by the daily scoring logic."
    if fluff >= 50:
        return "higher generic/fluff risk than the recommended idea."
    if "prompt" in warning.lower():
        return "risks drifting into prompt-bro positioning."
    return "weaker editorial priority today after score, positioning, and memory checks."


def _suggest_linkedin_angle(idea: dict[str, Any]) -> str:
    angle = str(idea.get("suggested_angle", "")).strip()
    topic = str(idea.get("topic", idea.get("heading", "this idea"))).strip()
    if not angle:
        angle = "Tie the idea to product operating model redesign."
    return (
        f"Use '{topic}' to argue that AI-native PM work is less about faster artifacts "
        f"and more about designing better decision loops. Base angle: {angle}"
    )


def _generic_risk(idea: dict[str, Any], context: EditorialContext) -> str:
    risk_points = []
    fluff = _int_value(idea.get("fluff_risk", idea.get("fluff_score", 0)))
    warning = str(idea.get("positioning_warning", ""))
    disliked_angles = _flatten_strings(context.preferences.get("dislikes", {}).get("angles", []))
    angle = str(idea.get("suggested_angle", "")).lower()

    if fluff >= 50:
        risk_points.append("High: daily report flagged material fluff risk.")
    elif fluff >= 20:
        risk_points.append("Medium: some generic framing risk remains.")
    else:
        risk_points.append("Low: daily fluff score is low.")
    if warning and warning != "None":
        risk_points.append(f"Positioning watchout: {warning}.")
    if any(disliked.replace("_", " ") in angle for disliked in disliked_angles):
        risk_points.append("Avoid disliked generic productivity or AI-replaces-everything framing.")
    return _render_list(risk_points)


def _operator_framing(idea: dict[str, Any], context: EditorialContext) -> str:
    desired = _flatten_strings(context.positioning.get("desired_positioning", []))
    avoid = _flatten_strings(context.positioning.get("avoid_positioning", []))
    return "\n".join(
        [
            "Frame this from the seat of a PM/operator making workflow tradeoffs:",
            f"- Anchor in: {', '.join(desired) if desired else 'AI-native PM operator'}",
            f"- Avoid: {', '.join(avoid) if avoid else 'generic AI hype'}",
            f"- Stronger claim: {idea.get('topic', 'This topic')} matters because AI changes how teams review, escalate, and decide.",
        ]
    )


def _next_action(idea: dict[str, Any]) -> str:
    recommendation = str(idea.get("recommendation", "")).lower()
    fluff = _int_value(idea.get("fluff_risk", idea.get("fluff_score", 0)))
    final_score = _int_value(idea.get("final_score", 0))
    if recommendation == "post" and fluff < 50 and final_score >= 65:
        return "draft"
    if recommendation == "reject" or fluff >= 50:
        return "reject"
    return "park"


def _render_inputs(context: EditorialContext) -> str:
    strategy = str(context.strategy_report_path) if context.strategy_report_path else "None available"
    liked = ", ".join(context.feedback_summary.get("most_liked_categories", [])) or "None"
    rejected = ", ".join(context.feedback_summary.get("most_rejected_categories", [])) or "None"
    return "\n".join(
        [
            f"- Daily report: {context.daily_report_path}",
            f"- Strategy report: {strategy}",
            f"- Preference memory liked categories: {liked}",
            f"- Preference memory rejected categories: {rejected}",
            "- LLM: not required; deterministic editorial fallback used.",
            "",
        ]
    )


def _editorial_score(idea: dict[str, Any]) -> int:
    score = _int_value(idea.get("final_score", 0))
    score += _int_value(idea.get("positioning_fit", 0)) // 2
    score -= _int_value(idea.get("fluff_risk", idea.get("fluff_score", 0)))
    if idea.get("recommendation") == "post":
        score += 30
    elif idea.get("recommendation") == "park":
        score += 5
    elif idea.get("recommendation") == "reject":
        score -= 50
    return score


def _report_date(path: Path) -> str:
    match = re.match(r"(\d{4}-\d{2}-\d{2})-", path.name)
    if match:
        return match.group(1)
    return date.today().isoformat()


def _read_optional_text(path: Path | None) -> str:
    if path is None or not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _topic_in_text(idea: dict[str, Any], text: str) -> bool:
    topic = str(idea.get("topic", idea.get("heading", ""))).strip()
    return bool(topic and topic in text)


def _int_value(value: Any) -> int:
    try:
        return int(str(value).lstrip("+"))
    except ValueError:
        return 0


def _flatten_strings(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value) for value in values]


def _render_list(items: list[str]) -> str:
    if not items:
        return "None.\n"
    return "\n".join(f"- {item}" for item in items) + "\n"
