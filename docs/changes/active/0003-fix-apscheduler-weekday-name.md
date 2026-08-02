---
id: 3
slug: fix-apscheduler-weekday-name
title: Fix APScheduler weekday name crash — "sunday" → "sun"
status: proposed
priority: high
type: fix
created: 2026-08-02
updated: 2026-08-02
depends_on: []
related: [2]
discovered_from: [2]
adrs: []
spec:
plan:
results:
trivial: true
auto_groomable: false
branch:
claimed_at:
pr:
issue:
blocked_by:
reconciled: false
---

<!-- docket:artifacts:start (generated — do not hand-edit) -->
<!-- docket:artifacts:end -->

## Why

After merging change 0002, the launchd-managed scheduler crashed on every startup with `ValueError: Invalid weekday name "sunday"`. APScheduler's cron trigger accepts only 3-char day abbreviations (`"sun"`, `"mon"`, etc.) — not full names — but this is only validated inside `scheduler.add_job()`, not at import or config-load time, so the crash was invisible until the scheduler actually ran. The agent was silently restart-looping for hours before the error was caught in `logs/agent-error.log`.

## What changes

One line in `agent/scheduler.py` — truncate `weekly_day` to its first 3 characters before passing it to APScheduler:

```python
weekly_day = weekly_day[:3].lower()
```

This normalises any full weekday name (`"sunday"`, `"monday"`, etc.) or already-abbreviated name (`"sun"`) to the form APScheduler expects. The fix is already applied locally but not committed.

## Out of scope

- Validating the full schedule config at startup (a broader hardening change)
- Changing `config.yml` to use 3-char names (the normalisation in code is more robust)

## Open questions

None.
