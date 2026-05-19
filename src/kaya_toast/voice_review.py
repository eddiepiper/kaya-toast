from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DRAFTS_DIR = PROJECT_ROOT / "drafts"
VOICE_REVIEW_DIR = PROJECT_ROOT / "reports" / "voice_review"


def generate_voice_review(
    draft_path: str | Path,
    output_dir: str | Path | None = None,
) -> Path:
    draft = Path(draft_path)
    review_dir = Path(output_dir) if output_dir is not None else VOICE_REVIEW_DIR
    review_dir.mkdir(parents=True, exist_ok=True)
    output_path = review_dir / f"{_report_date(draft)}-{_draft_slug(draft)}-voice-review.md"
    output_path.write_text(render_voice_review(draft), encoding="utf-8")
    return output_path


def generate_latest_voice_review(output_dir: str | Path | None = None) -> Path:
    latest = latest_draft()
    if latest is None:
        raise ValueError("No draft files found.")
    return generate_voice_review(latest, output_dir=output_dir)


def generate_all_latest_voice_reviews(output_dir: str | Path | None = None) -> list[Path]:
    drafts = latest_drafts()
    if not drafts:
        raise ValueError("No draft files found.")
    return [generate_voice_review(draft, output_dir=output_dir) for draft in drafts]


def latest_draft(drafts_dir: str | Path | None = None) -> Path | None:
    draft_dir = Path(drafts_dir) if drafts_dir is not None else DRAFTS_DIR
    drafts = sorted(draft_dir.glob("*.md"))
    return drafts[-1] if drafts else None


def latest_drafts(drafts_dir: str | Path | None = None) -> list[Path]:
    draft_dir = Path(drafts_dir) if drafts_dir is not None else DRAFTS_DIR
    drafts = sorted(draft_dir.glob("*.md"))
    if not drafts:
        return []
    latest_date = _report_date(drafts[-1])
    return [draft for draft in drafts if _report_date(draft) == latest_date]


def render_voice_review(draft_path: str | Path) -> str:
    draft = Path(draft_path)
    text = draft.read_text(encoding="utf-8")
    signals = analyze_draft_voice(text)
    verdict = _verdict(signals)
    sections = [
        f"# Voice Review: {_title(text, draft)}",
        "",
        f"- Overall verdict: {verdict}",
        f"- Eddie voice fit: {signals['eddie_voice_fit']}",
        f"- Enterprise operator fit: {signals['enterprise_operator_fit']}",
        f"- AI-native PM relevance: {signals['ai_native_pm_relevance']}",
        f"- Fluff risk: {signals['fluff_risk']}",
        f"- Prompt-bro risk: {signals['prompt_bro_risk']}",
        f"- Unsupported claim risk: {signals['unsupported_claim_risk']}",
        "",
        "## What Works",
        _render_list(_what_works(signals)),
        "## What Feels Off",
        _render_list(_what_feels_off(signals)),
        "## Lines To Rewrite",
        _render_list(signals["lines_to_rewrite"]),
        "## Suggested Rewrite Direction",
        _rewrite_direction(signals),
        "",
        "## Final Recommendation",
        verdict,
        "",
    ]
    return "\n".join(sections).rstrip() + "\n"


def analyze_draft_voice(text: str) -> dict[str, Any]:
    lines = text.splitlines()
    scannable_lines = [
        line
        for line in lines
        if not line.lstrip().lower().startswith("- do not")
        and line.strip().lower() not in {"## claims to avoid", "## unsupported claims to avoid"}
    ]
    scannable_text = "\n".join(scannable_lines)
    lower = scannable_text.lower()
    issues = []
    rewrite_lines = []
    penalties = 0

    checks = [
        ("emoji", _contains_emoji(text), 20),
        ("em-dash", "\u2014" in text, 10),
        ("guru tone", _contains_any(lower, ["guru", "thought leader", "masterclass", "unlock your potential"]), 20),
        ("prompt-bro language", _contains_any(lower, ["prompt hack", "prompt bro", "10 prompts", "mega prompt"]), 20),
        ("AI will replace PMs", "ai will replace pms" in lower or "ai replaces pms" in lower, 30),
        ("vague future-of-work claim", "future of work" in lower, 15),
        ("unsupported claim", _contains_any(lower, ["guaranteed", "proves", "will transform every", "always"]), 15),
    ]
    for label, failed, penalty in checks:
        if failed:
            issues.append(label)
            penalties += penalty

    for line in scannable_lines:
        line_lower = line.lower()
        if (
            _contains_emoji(line)
            or "\u2014" in line
            or _contains_any(line_lower, ["prompt hack", "future of work", "ai will replace pms", "guaranteed", "proves"])
        ):
            rewrite_lines.append(line.strip())

    operator_fit = "strong" if _contains_any(lower, ["enterprise", "operator", "workflow", "decision", "governance"]) else "weak"
    pm_fit = "strong" if _contains_any(lower, ["pm", "product", "ai-native", "decision loop", "workflow"]) else "weak"
    voice_fit = "strong" if penalties <= 10 and operator_fit == "strong" and pm_fit == "strong" else "medium"
    if penalties >= 50:
        voice_fit = "weak"

    return {
        "issues": issues,
        "penalties": penalties,
        "eddie_voice_fit": voice_fit,
        "enterprise_operator_fit": operator_fit,
        "ai_native_pm_relevance": pm_fit,
        "fluff_risk": _risk_label(penalties + (0 if operator_fit == "strong" else 15)),
        "prompt_bro_risk": "high" if "prompt-bro language" in issues else "low",
        "unsupported_claim_risk": "high" if "unsupported claim" in issues else "medium" if "Source Grounding" not in text else "low",
        "lines_to_rewrite": rewrite_lines[:8],
    }


def _verdict(signals: dict[str, Any]) -> str:
    penalties = int(signals["penalties"])
    if penalties >= 60 or signals["ai_native_pm_relevance"] == "weak":
        return "reject"
    if penalties >= 20 or signals["unsupported_claim_risk"] != "low":
        return "revise"
    return "approve"


def _what_works(signals: dict[str, Any]) -> list[str]:
    works = []
    if signals["enterprise_operator_fit"] == "strong":
        works.append("Enterprise/operator framing is visible.")
    if signals["ai_native_pm_relevance"] == "strong":
        works.append("AI-native PM relevance is clear.")
    if signals["unsupported_claim_risk"] == "low":
        works.append("Source grounding reduces unsupported claim risk.")
    return works or ["No strong voice signals found."]


def _what_feels_off(signals: dict[str, Any]) -> list[str]:
    issues = list(signals["issues"])
    if signals["enterprise_operator_fit"] == "weak":
        issues.append("enterprise/operator framing is weak")
    if signals["ai_native_pm_relevance"] == "weak":
        issues.append("AI-native PM relevance is weak")
    return issues or ["Nothing material flagged."]


def _rewrite_direction(signals: dict[str, Any]) -> str:
    if not signals["issues"] and signals["enterprise_operator_fit"] == "strong":
        return "Keep the draft. Tighten only for specificity and source-grounded evidence."
    return (
        "Rewrite toward concrete PM/operator judgment: remove hype, avoid prompt-bro phrasing, "
        "and keep claims limited to the source review and daily report metadata."
    )


def _risk_label(score: int) -> str:
    if score >= 50:
        return "high"
    if score >= 20:
        return "medium"
    return "low"


def _contains_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)


def _contains_emoji(text: str) -> bool:
    return any(ord(char) > 10000 for char in text)


def _title(text: str, draft: Path) -> str:
    for line in text.splitlines():
        if line.startswith("# LinkedIn Draft:"):
            return line.removeprefix("# LinkedIn Draft:").strip()
    return draft.stem


def _report_date(path: Path) -> str:
    match = re.match(r"(\d{4}-\d{2}-\d{2})-", path.name)
    if match:
        return match.group(1)
    return date.today().isoformat()


def _draft_slug(path: Path) -> str:
    stem = path.stem
    match = re.match(r"\d{4}-\d{2}-\d{2}-(.+)$", stem)
    return match.group(1) if match else stem


def _render_list(items: list[str]) -> str:
    if not items:
        return "None.\n"
    return "\n".join(f"- {item}" for item in items) + "\n"
