from __future__ import annotations

from datetime import date
from pathlib import Path

from kaya_toast.models import ContentIdea
from kaya_toast.preference import summarize_feedback


def generate_report(
    ideas: list[ContentIdea],
    reports_dir: str | Path = "reports",
    source_summary: dict | None = None,
) -> Path:
    output_dir = Path(reports_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"{date.today().isoformat()}-kaya-toast.md"
    report_path.write_text(render_report(ideas, source_summary), encoding="utf-8")
    return report_path


def render_report(ideas: list[ContentIdea], source_summary: dict | None = None) -> str:
    post_ideas = [idea for idea in ideas if idea.recommendation == "post"]
    parked_ideas = [idea for idea in ideas if idea.recommendation == "park"]
    rejected_ideas = [idea for idea in ideas if idea.recommendation == "reject"]
    fluff_warnings = [idea for idea in ideas if idea.fluff_score >= 50]

    sections = [
        "# kaya-toast Daily Brief",
        "",
        "## Preference Memory",
        "",
        _render_preference_memory(ideas),
        "## Source Summary",
        "",
        _render_source_summary(source_summary, ideas),
        "## AI-native PM Ideas",
        "",
        _render_pillar_ideas(ideas, "ai_native_pm"),
        "## AI-native Banking Ideas",
        "",
        _render_pillar_ideas(ideas, "ai_native_banking"),
        "## Founder Systems Ideas",
        "",
        _render_pillar_ideas(ideas, "founder_systems"),
        "## Healthcare / Caregiver AI Ideas",
        "",
        _render_pillar_ideas(ideas, "healthcare_caregiver_ai"),
        "## Top LinkedIn Content Ideas",
        "",
        _render_ideas(post_ideas),
        "## Parked Ideas",
        "",
        _render_ideas(parked_ideas),
        "## Rejected Ideas",
        "",
        _render_ideas(rejected_ideas),
        "## Fluff Warnings",
        "",
        _render_fluff(fluff_warnings),
    ]
    return "\n".join(sections).rstrip() + "\n"


def _render_ideas(ideas: list[ContentIdea]) -> str:
    if not ideas:
        return "None.\n"

    blocks = []
    for idea in ideas:
        hooks = "\n".join(f"  - {hook}" for hook in idea.hook_options)
        blocks.append(
            "\n".join(
                [
                    f"### {idea.topic}",
                    "",
                    f"- Idea ID: {idea.idea_id}",
                    f"- Topic: {idea.topic}",
                    f"- Category: {idea.category}",
                    f"- Primary pillar: {idea.primary_pillar}",
                    f"- Secondary pillar: {idea.secondary_pillar or 'None'}",
                    f"- Pillar confidence: {idea.pillar_confidence}",
                    f"- Pillar score: +{idea.pillar_score}",
                    f"- Positioning fit: {idea.positioning_fit_score}",
                    f"- Positioning warning: {idea.positioning_warning or 'None'}",
                    f"- Memory-informed recommendation: {idea.memory_recommendation}",
                    f"- Source: {idea.source}",
                    f"- Why it matters: {idea.why_it_matters}",
                    f"- Target audience: {idea.target_audience}",
                    f"- Suggested angle: {idea.suggested_angle}",
                    "- Hook options:",
                    hooks,
                    f"- Score: {idea.total_score}",
                    f"- Preference Adjustment: {_format_adjustment(idea.preference_adjustment)}",
                    f"- Final Score: {idea.final_score}",
                    f"- Fluff risk: {idea.fluff_score}",
                    f"- Recommendation: {idea.recommendation}",
                    "",
                ]
            )
        )
    return "\n".join(blocks)


def _render_fluff(ideas: list[ContentIdea]) -> str:
    if not ideas:
        return "None.\n"
    return "\n".join(
        f"- {idea.topic}: fluff risk {idea.fluff_score}, recommendation {idea.recommendation}"
        for idea in ideas
    ) + "\n"


def _render_preference_memory(ideas: list[ContentIdea]) -> str:
    summary = summarize_feedback()
    liked = ", ".join(summary["most_liked_categories"]) or "None"
    rejected = ", ".join(summary["most_rejected_categories"]) or "None"
    adjustments = [idea.preference_adjustment for idea in ideas if idea.preference_adjustment != 0]
    if adjustments:
        adjustment_summary = (
            f"{len(adjustments)} ideas adjusted; range "
            f"{_format_adjustment(min(adjustments))} to {_format_adjustment(max(adjustments))}"
        )
    else:
        adjustment_summary = "No active preference adjustments"

    return "\n".join(
        [
            f"- Total feedback records: {summary['total_records']}",
            f"- Most liked categories: {liked}",
            f"- Most rejected categories: {rejected}",
            f"- Current preference adjustment summary: {adjustment_summary}",
            "",
        ]
    )


def _format_adjustment(value: int) -> str:
    if value > 0:
        return f"+{value}"
    return str(value)


def _render_source_summary(
    source_summary: dict | None,
    ideas: list[ContentIdea],
) -> str:
    if source_summary is None:
        source_names = sorted({idea.source.split(":", 1)[0] for idea in ideas})
        source_summary = {
            "article_count": len(ideas),
            "source_names": source_names,
            "warnings": [],
        }

    source_names = source_summary.get("source_names", [])
    warnings = source_summary.get("warnings", [])
    return "\n".join(
        [
            f"- Articles collected: {source_summary.get('article_count', 0)}",
            f"- Sources: {', '.join(source_names) if source_names else 'None'}",
            "- Source warnings:",
            _render_source_warnings(warnings),
            "",
        ]
    )


def _render_source_warnings(warnings: list[str]) -> str:
    if not warnings:
        return "  - None"
    return "\n".join(f"  - {warning}" for warning in warnings)


def _render_pillar_ideas(ideas: list[ContentIdea], pillar: str) -> str:
    matching = [
        idea
        for idea in ideas
        if idea.primary_pillar == pillar or idea.secondary_pillar == pillar
    ][:5]
    if not matching:
        return "None.\n"
    return "\n".join(
        f"- {idea.topic} ({idea.recommendation}, final score {idea.final_score})"
        for idea in matching
    ) + "\n"
