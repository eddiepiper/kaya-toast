from __future__ import annotations

import re
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DAILY_REPORTS_DIR = PROJECT_ROOT / "reports" / "daily"
STRATEGY_REPORTS_DIR = PROJECT_ROOT / "reports" / "strategy"


def extract_recurring_categories(ideas: list[dict[str, Any]]) -> list[tuple[str, int]]:
    return Counter(str(idea.get("category", "")) for idea in ideas if idea.get("category")).most_common()


def detect_repeated_angles(ideas: list[dict[str, Any]]) -> list[tuple[str, int]]:
    return Counter(str(idea.get("suggested_angle", "")) for idea in ideas if idea.get("suggested_angle")).most_common()


def identify_emerging_themes(ideas: list[dict[str, Any]]) -> list[str]:
    themes: list[str] = []
    for category, count in extract_recurring_categories(ideas)[:5]:
        themes.append(f"{category}: recurring in {count} ideas")
    for pillar, count in Counter(str(idea.get("primary_pillar", "")) for idea in ideas if idea.get("primary_pillar")).most_common(4):
        themes.append(f"{pillar}: pillar signal across {count} ideas")
    return themes


def detect_fluff_patterns(report_paths: list[Path]) -> list[str]:
    patterns: list[str] = []
    for path in report_paths:
        in_fluff = False
        for line in path.read_text(encoding="utf-8").splitlines():
            if line == "## Fluff Warnings":
                in_fluff = True
                continue
            if in_fluff and line.startswith("## "):
                in_fluff = False
            if in_fluff and line.startswith("- ") and line != "- None":
                patterns.append(line.removeprefix("- ").strip())
    return patterns[:8]


def suggest_positioning_opportunities(ideas: list[dict[str, Any]]) -> list[str]:
    opportunities = []
    categories = [category for category, _count in extract_recurring_categories(ideas)[:3]]
    if "ai_native_pm_mindset" in categories:
        opportunities.append("Own the AI-native PM transition as an operating model shift, not a productivity story.")
    if "agentic_workflows" in categories:
        opportunities.append("Explain agentic workflows through PM-designed review loops and escalation paths.")
    if "ai_governance" in categories:
        opportunities.append("Translate AI governance into practical product workflow design.")
    if not opportunities:
        opportunities.append("Anchor posts in practical PM workflow redesign and decision quality.")
    return opportunities


def suggest_topics_to_avoid(ideas: list[dict[str, Any]]) -> list[str]:
    avoid = [
        str(idea.get("topic", ""))
        for idea in ideas
        if int(str(idea.get("final_score", "0"))) < 50
        or int(str(idea.get("fluff_score", "0"))) >= 50
    ]
    return avoid[:8]


def generate_strategy_report(
    daily_reports_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> Path:
    daily_dir = Path(daily_reports_dir) if daily_reports_dir is not None else DAILY_REPORTS_DIR
    strategy_dir = Path(output_dir) if output_dir is not None else STRATEGY_REPORTS_DIR
    report_paths = recent_daily_reports(daily_dir)
    ideas = extract_ideas_from_reports(report_paths)
    output_path = strategy_dir / f"{date.today().isoformat()}-kaya-toast-strategy.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_strategy_report(ideas, report_paths), encoding="utf-8")
    return output_path


def render_strategy_report(ideas: list[dict[str, Any]], report_paths: list[Path]) -> str:
    emerging = identify_emerging_themes(ideas)
    repeated = [f"{angle}: {count} repeats" for angle, count in detect_repeated_angles(ideas)[:5]]
    fluff = detect_fluff_patterns(report_paths)
    avoid = suggest_topics_to_avoid(ideas)
    positioning = suggest_positioning_opportunities(ideas)
    bets = _content_bets(ideas)[:5]

    return "\n".join(
        [
            "# kaya-toast Strategy Brief",
            "",
            "## Strongest Emerging Themes",
            "",
            _render_list(emerging),
            "## Repeated PM Transition Patterns",
            "",
            _render_list(repeated),
            "## Contrarian Angles Worth Posting",
            "",
            _render_list(_contrarian_angles(ideas)),
            "## Topics Becoming Too Generic",
            "",
            _render_list(fluff or avoid),
            "## Positioning Opportunities",
            "",
            _render_list(positioning),
            "## Recommended Content Bets",
            "",
            _render_bets(bets),
            "## Topics to Avoid",
            "",
            _render_list(avoid),
            "## Suggested Next 5 Posts",
            "",
            _render_list([bet["topic"] for bet in bets]),
        ]
    ).rstrip() + "\n"


def recent_daily_reports(reports_dir: Path) -> list[Path]:
    if not reports_dir.exists():
        return []
    cutoff = date.today() - timedelta(days=13)
    reports = []
    for path in sorted(reports_dir.glob("*-kaya-toast.md")):
        match = re.match(r"(\d{4}-\d{2}-\d{2})-kaya-toast\.md$", path.name)
        if match and date.fromisoformat(match.group(1)) >= cutoff:
            reports.append(path)
    return reports


def extract_ideas_from_reports(report_paths: list[Path]) -> list[dict[str, Any]]:
    ideas: list[dict[str, Any]] = []
    for path in report_paths:
        current: dict[str, Any] | None = None
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("### "):
                if current:
                    ideas.append(current)
                current = {"topic": line.removeprefix("### ").strip()}
            elif current is not None and line.startswith("- "):
                key, _, value = line.removeprefix("- ").partition(": ")
                if key and value:
                    current[key.lower().replace(" ", "_")] = value.strip().lstrip("+")
        if current:
            ideas.append(current)
    return ideas


def _content_bets(ideas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bets = []
    for idea in ideas:
        final_score = int(str(idea.get("final_score", "0")))
        fluff_score = int(str(idea.get("fluff_score", "0")))
        bet = {
            "topic": str(idea.get("topic", "Untitled idea")),
            "audience_usefulness": min(25, final_score // 4),
            "differentiation": 20 if idea.get("primary_pillar") == "ai_native_pm" else 14,
            "credibility_fit": 20 if "enterprise" in str(idea.get("suggested_angle", "")).lower() else 15,
            "fluff_risk": max(0, 20 - fluff_score // 5),
            "career_positioning_value": 20 if final_score >= 70 else 12,
            "positioning_fit": int(str(idea.get("positioning_fit", "0")) or "0"),
            "memory_recommendation": str(idea.get("memory-informed_recommendation", "Not captured")),
        }
        bet["total"] = sum(value for key, value in bet.items() if isinstance(value, int))
        bets.append(bet)
    return sorted(bets, key=lambda item: item["total"], reverse=True)


def _contrarian_angles(ideas: list[dict[str, Any]]) -> list[str]:
    angles = []
    for idea in ideas[:8]:
        topic = str(idea.get("topic", "this topic"))
        angles.append(f"{topic}: the PM shift is workflow design, not AI adoption.")
    return angles[:5]


def _render_bets(bets: list[dict[str, Any]]) -> str:
    if not bets:
        return "None.\n"
    blocks = []
    for bet in bets:
        blocks.append(
            "\n".join(
                [
                    f"### {bet['topic']}",
                    f"- Audience usefulness: {bet['audience_usefulness']}",
                    f"- Differentiation: {bet['differentiation']}",
                    f"- Credibility fit: {bet['credibility_fit']}",
                    f"- Fluff risk: {bet['fluff_risk']}",
                    f"- Career positioning value: {bet['career_positioning_value']}",
                    f"- Positioning fit: {bet['positioning_fit']}",
                    f"- Memory-informed recommendation: {bet['memory_recommendation']}",
                    f"- Total: {bet['total']}",
                    "",
                ]
            )
        )
    return "\n".join(blocks)


def _render_list(items: list[str]) -> str:
    if not items:
        return "None.\n"
    return "\n".join(f"- {item}" for item in items) + "\n"
