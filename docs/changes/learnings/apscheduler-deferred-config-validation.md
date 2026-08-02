---
name: apscheduler-deferred-config-validation
description: APScheduler validates cron trigger values only inside add_job(), not at import time — a misconfigured daemon silently restart-loops under launchd with no console output
metadata:
  type: feedback
  promotion_state: candidate
  changes: [3]
  updated: 2026-08-02
---

APScheduler does **not** validate cron trigger arguments (e.g. `day_of_week`) at import time or when building the trigger object. Validation fires inside `scheduler.add_job()` only, raising `ValueError: Invalid weekday name "sunday"` when the scheduler tries to register the job. A daemon managed by launchd (with `KeepAlive: true`) restart-loops silently after this — stdout says "Starting scheduler" each restart but the crash trace is only in the error log. The loop ran for hours before being noticed.

**Root cause:** `config.yml` used `"sunday"` (full name); APScheduler's cron trigger requires 3-char abbreviations (`"sun"`, `"mon"`, etc.).

**Fix:** Normalise at the boundary — `weekly_day = weekly_day[:3].lower()` — so APScheduler receives only valid input regardless of what the user writes in config.

**How to apply:**
1. Whenever scheduler config values come from user-controlled files (config.yml, env vars), normalise them before passing to `add_job()`.
2. After any scheduler config change, verify job registration actually succeeded: start the scheduler, wait 2–3 seconds, then check `scheduler.get_jobs()` returns the expected jobs before letting the process daemonise.
3. When a launchd service appears to start (log line visible) but immediately restarts, **check the error log first** — `tail logs/agent-error.log` — before assuming the process is healthy.
