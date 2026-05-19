# launchd Daily Update

`kaya-toast` can run every weekday morning with macOS `launchd`.

The job runs:

```bash
/bin/bash "/Users/edwardchiang/Documents/AI PM news agent/kaya-toast/scripts/daily_update.sh"
```

It generates daily, weekly, and strategy reports, commits generated outputs, and pushes the `kaya-toast` project to GitHub.

## Install

Do not install automatically from the project. Install only after manual validation.

```bash
mkdir -p ~/Library/LaunchAgents
cp "/Users/edwardchiang/Documents/AI PM news agent/kaya-toast/launchd/com.eddiepiper.kaya-toast.daily.plist" ~/Library/LaunchAgents/com.eddiepiper.kaya-toast.daily.plist
launchctl load ~/Library/LaunchAgents/com.eddiepiper.kaya-toast.daily.plist
```

## Unload

```bash
launchctl unload ~/Library/LaunchAgents/com.eddiepiper.kaya-toast.daily.plist
```

## Manual Test

```bash
cd "/Users/edwardchiang/Documents/AI PM news agent/kaya-toast"
bash scripts/daily_update.sh
```

## Logs

Primary script log:

```bash
tail -f "/Users/edwardchiang/Documents/AI PM news agent/kaya-toast/logs/daily_update.log"
```

launchd stdout and stderr logs:

```bash
tail -f "/Users/edwardchiang/Documents/AI PM news agent/kaya-toast/logs/launchd.out.log"
tail -f "/Users/edwardchiang/Documents/AI PM news agent/kaya-toast/logs/launchd.err.log"
```

## Schedule

The plist runs Monday through Friday at 8:00 AM local machine time. On this Mac, local time is Singapore time when the system timezone is set to Asia/Singapore.
