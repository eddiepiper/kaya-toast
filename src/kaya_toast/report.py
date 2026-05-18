from __future__ import annotations

from datetime import date
from pathlib import Path

from kaya_toast.models import ContentIdea
from kaya_toast.preference import summarize_feedback


def generate_report(ideas: list[ContentIdea], reports_dir: str | Path = "reports") -> Path:
    output_dir = Path(reports_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"{date.today().isoformat()}-kaya-toast.md"
    report_path.write_text(render_report(ideas), encoding="utf-8")
    return report_path


def render_report(ideas: list[ContentIdea]) -> str:
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
