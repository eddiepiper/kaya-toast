from __future__ import annotations

import os
import re
from datetime import date
from pathlib import Path
from typing import Any

from kaya_toast.config import load_llm
from kaya_toast.draft import extract_report_ideas
from kaya_toast.interpret import call_openrouter


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_REVIEW_DIR = PROJECT_ROOT / "reports" / "source_review"
PROMPT_PATH = PROJECT_ROOT / "prompts" / "source_review.md"


def generate_source_reviews(
    report_path: str | Path,
    idea_id: str | None = None,
    top: int | None = None,
    output_dir: str | Path | None = None,
) -> list[Path]:
    report = Path(report_path)
    ideas = extract_report_ideas(report)
    selected = _select_ideas(ideas, idea_id=idea_id, top=top)
    if idea_id and not selected:
        raise ValueError(f"Idea ID not found in report: {idea_id}")
    if not selected:
        raise ValueError(f"No ideas selected from report: {report}")

    review_dir = Path(output_dir) if output_dir is not None else SOURCE_REVIEW_DIR
    paths = []
    for idea in selected:
        paths.append(write_source_review(idea, report, review_dir))
    return paths


def write_source_review(idea: dict[str, Any], report_path: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    idea_id = str(idea.get("idea_id", "source-review"))
    output_path = output_dir / f"{_report_date(report_path)}-{_safe_slug(idea_id)}-source-review.md"
    output_path.write_text(render_source_review(idea), encoding="utf-8")
    return output_path


def render_source_review(idea: dict[str, Any]) -> str:
    source = _source_details(idea)
    score = source_quality_score(idea)
    action = recommended_action(idea, score)
    llm_text = generate_llm_source_review(idea)
    evidence = _evidence_points(idea, source)

    sections = [
        f"# Source Review: {source['title']}",
        "",
        "## Source",
        f"- Title: {source['title']}",
        f"- Source: {source['source']}",
        f"- URL: {source['url']}",
        f"- Category: {idea.get('category', 'Unknown')}",
        f"- Idea ID: {idea.get('idea_id', 'unknown')}",
        "",
        "## Evidence Extracted",
        _render_list(evidence),
        "## PM Relevance",
        _pm_relevance(idea, source, llm_text),
        "",
        "## Enterprise / Operator Relevance",
        _operator_relevance(idea, source),
        "",
        "## Unsupported Claims to Avoid",
        _render_list(_unsupported_claims(idea, source)),
        "## Content Angle Recommendation",
        f"- Strong angle: {_strong_angle(idea)}",
        f"- Weak angle to avoid: {_weak_angle(idea)}",
        f"- Recommended action: {action}",
        "",
        "## Source Quality Score",
        str(score),
        "",
    ]
    return "\n".join(sections).rstrip() + "\n"


def source_quality_score(idea: dict[str, Any]) -> int:
    source = _source_details(idea)
    title = source["title"]
    score = 35
    if len(title.split()) >= 4:
        score += 15
    if source["summary"] != "Missing source summary in daily report.":
        score += 15
    if _has_pm_relevance(idea):
        score += 20
    if _has_operator_relevance(idea):
        score += 10
    if str(idea.get("recommendation", "")).lower() == "post":
        score += 10
    elif str(idea.get("recommendation", "")).lower() == "reject":
        score -= 20
    score -= min(30, _int_value(idea.get("fluff_risk", idea.get("fluff_score", 0))))
    if str(idea.get("quality_warnings", "")).strip() not in {"", "None"}:
        score -= 10
    return max(0, min(100, score))


def recommended_action(idea: dict[str, Any], score: int) -> str:
    recommendation = str(idea.get("recommendation", "")).lower()
    if score < 40 or recommendation == "reject":
        return "reject"
    if score < 50 or recommendation == "park":
        return "park"
    return "draft"


def generate_llm_source_review(idea: dict[str, Any]) -> str:
    config = load_llm()
    if not config.get("enabled", False):
        return ""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return ""
    return call_openrouter(load_source_review_prompt(), idea, config, api_key)


def load_source_review_prompt(path: str | Path = PROMPT_PATH) -> str:
    return Path(path).read_text(encoding="utf-8")


def _select_ideas(
    ideas: list[dict[str, Any]],
    idea_id: str | None,
    top: int | None,
) -> list[dict[str, Any]]:
    if idea_id:
        return [idea for idea in ideas if idea.get("idea_id") == idea_id]
    if top:
        return ideas[: max(0, top)]
    return []


def _source_details(idea: dict[str, Any]) -> dict[str, str]:
    topic = str(idea.get("topic", idea.get("heading", "Untitled idea")))
    raw_source = str(idea.get("source", "")).strip()
    source_name = raw_source or "Unknown"
    title = topic
    if ": " in raw_source:
        source_name, title = raw_source.split(": ", 1)
    summary = str(idea.get("source_summary", "")).strip() or "Missing source summary in daily report."
    url = str(idea.get("url", "")).strip() or "Not available in daily report."
    return {
        "title": title,
        "source": source_name,
        "url": url,
        "summary": summary,
    }


def _evidence_points(idea: dict[str, Any], source: dict[str, str]) -> list[str]:
    points = [
        f"Source title points to: {source['title']}.",
        f"Daily report rationale: {idea.get('why_it_matters', 'No rationale captured.')}",
        f"Suggested angle captured by the pipeline: {idea.get('suggested_angle', 'No angle captured.')}",
    ]
    if source["summary"] == "Missing source summary in daily report.":
        points.append("Source summary is missing; do not imply details beyond the daily report metadata.")
    return points[:4]


def _pm_relevance(idea: dict[str, Any], source: dict[str, str], llm_text: str) -> str:
    if llm_text:
        return llm_text
    if not _has_pm_relevance(idea):
        return (
            "Weak PM relevance from available metadata. The draft should not proceed unless the angle can be tied "
            "back to PM decision quality, discovery, prioritization, or workflow design."
        )
    return (
        "This matters for traditional PMs transitioning into AI-native PM roles because it can be framed as a "
        "workflow and decision-quality shift, not a generic AI tooling story. "
        f"Available source summary status: {source['summary']}"
    )


def _operator_relevance(idea: dict[str, Any], source: dict[str, str]) -> str:
    if not _has_operator_relevance(idea):
        return "Weak. The available metadata does not clearly show enterprise or operator relevance."
    return (
        "Relevant for operators because the idea can be anchored in governance, workflow ownership, review loops, "
        "stakeholder alignment, or operating-model design."
    )


def _unsupported_claims(idea: dict[str, Any], source: dict[str, str]) -> list[str]:
    claims = [
        "Do not claim the source proves measurable business impact unless the source metadata says so.",
        "Do not claim implementation details, customer results, or technical architecture not present in the daily report.",
        "Do not imply LinkedIn-ready certainty if the source summary is missing.",
    ]
    if source["url"] == "Not available in daily report.":
        claims.append("Do not cite a URL or tell readers to inspect a source link that is not available.")
    if str(idea.get("quality_warnings", "")).strip() not in {"", "None"}:
        claims.append(f"Respect quality warning: {idea.get('quality_warnings')}.")
    return claims


def _strong_angle(idea: dict[str, Any]) -> str:
    angle = str(idea.get("suggested_angle", "")).strip()
    if angle:
        return angle
    return "Connect the source to PM workflow redesign and decision quality."


def _weak_angle(idea: dict[str, Any]) -> str:
    warning = str(idea.get("positioning_warning", "")).strip()
    if warning and warning != "None":
        return warning
    return "Generic AI productivity, prompt tips, or hype without PM/operator evidence."


def _has_pm_relevance(idea: dict[str, Any]) -> bool:
    text = _idea_text(idea)
    signals = ["pm", "product", "roadmap", "workflow", "decision", "stakeholder", "discovery", "prioritization"]
    return any(signal in text for signal in signals)


def _has_operator_relevance(idea: dict[str, Any]) -> bool:
    text = _idea_text(idea)
    signals = ["enterprise", "operator", "operating", "governance", "stakeholder", "workflow", "regulated", "banking"]
    return any(signal in text for signal in signals)


def _idea_text(idea: dict[str, Any]) -> str:
    fields = [
        "topic",
        "heading",
        "category",
        "source",
        "why_it_matters",
        "target_audience",
        "suggested_angle",
        "positioning_warning",
        "quality_warnings",
    ]
    return " ".join(str(idea.get(field, "")) for field in fields).lower()


def _report_date(path: Path) -> str:
    match = re.match(r"(\d{4}-\d{2}-\d{2})-", path.name)
    if match:
        return match.group(1)
    return date.today().isoformat()


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug[:120] or "source-review"


def _int_value(value: Any) -> int:
    try:
        return int(str(value).lstrip("+"))
    except ValueError:
        return 0


def _render_list(items: list[str]) -> str:
    if not items:
        return "None.\n"
    return "\n".join(f"- {item}" for item in items) + "\n"
