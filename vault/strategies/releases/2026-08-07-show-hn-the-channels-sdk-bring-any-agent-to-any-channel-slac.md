---
title: "Show HN: The Channels SDK – Bring Any Agent to Any Channel (Slack, MS Teams)"
date: 2026-08-07
type: release
score: 7
score_label: significance
tags: [release, agent-frameworks, tool-use]
validated: false
sources_count: 1
content_source: full
status: new
---

# Show HN: The Channels SDK – Bring Any Agent to Any Channel (Slack, MS Teams)

## Summary
Channels SDK is a release that enables any AG-UI-compatible agent to run natively in Slack, Microsoft Teams, and other communication platforms. It lets agents understand conversations, stream responses, call tools, render platform-native UI, and pause for human approval without leaving the chat interface.

## How It Works
A long-running Node.js process hosts the agent and Channels listener. When a user messages the agent in Slack or Teams, CopilotKit Intelligence receives the platform event and delivers it to the Channels process. The agent executes over AG-UI, calls tools, and returns responses that Intelligence renders as native Slack Block Kit or Teams Adaptive Cards. The developer's infrastructure runs the agent and business logic; CopilotKit Intelligence manages platform credentials and delivery. Setup can be automated via `npx copilotkit@latest channels setup`, which uses a coding agent to configure the Slack/Teams apps and project credentials.

## Why It Matters
Practitioners building multi-channel AI agents can now deploy a single agent across communication platforms teams already use, with native interactive UI and approval gates built directly into conversations. This eliminates the friction of maintaining separate integrations or forcing users to leave their chat platform. The open-source, MIT-licensed SDK and available self-hosting option for enterprise deployments make it practical for teams wanting to keep agent logic and credentials in their own infrastructure while outsourcing only platform connectivity.

## Sources
- [Show HN: The Channels SDK – Bring Any Agent to Any Channel (Slack, MS Teams)](https://github.com/CopilotKit/channels-sdk) — hackernews · 113

## Related
