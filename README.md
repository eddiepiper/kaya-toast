# kaya-toast

`kaya-toast` is a local-first, deterministic MVP for recommending high-signal LinkedIn content ideas about AI-native Product Management.

It helps traditional Product Managers transition into AI-native PMs through practical, strategic, enterprise-aware content ideas. Phase 1 and Phase 2 do not generate full LinkedIn posts, call external APIs, scrape the web, schedule jobs, or post to LinkedIn.

## What It Does

Pipeline:

```text
collect -> classify -> score -> fluff_check -> recommend -> report
```

Inputs are local JSON article summaries. Outputs are ranked Markdown briefings with post, park, and reject recommendations.

## Setup

```bash
python -m pip install -e ".[dev]"
```

## CLI

```bash
python -m kaya_toast --help
python -m kaya_toast run --input examples/sample_articles.json
python -m kaya_toast classify --input examples/sample_articles.json
python -m kaya_toast report --input examples/sample_articles.json
```

## Test

```bash
python -m pytest -q
```

## Current Scope

Included:

- Local JSON collection
- Deterministic classification
- Deterministic scoring
- Fluff detection
- Content idea templating
- Markdown reporting
- Tests

Excluded:

- Web UI
- Vector database
- Multi-agent orchestration
- LangChain, CrewAI, AutoGen
- LinkedIn posting
- External APIs
- Browser scraping
- Cron scheduling
- Database
- Full LinkedIn post generation
