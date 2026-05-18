# Cron Setup

`kaya-toast` can be run from cron for weekday daily reports.

Example:

```cron
0 8 * * 1-5 cd "/Users/edwardchiang/Documents/AI PM news agent/kaya-toast" && python3 -m kaya_toast daily
```

Do not install cron automatically from the project. This file is documentation only.

Before using cron, validate manually:

```bash
python3 -m kaya_toast daily
python3 -m kaya_toast weekly
```
