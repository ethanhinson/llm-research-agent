---
title: "MicrosoftDocs/mcp"
date: 2026-08-07
type: release
score: 7
score_label: significance
tags: [release, tool-use, agent-frameworks, mcp]
validated: false
sources_count: 1
content_source: full
status: new
---

# MicrosoftDocs/mcp

## Summary
Microsoft Learn MCP Server is a Model Context Protocol integration that gives AI assistants (Claude, Copilot, Cursor, etc.) direct access to official Microsoft documentation and code samples. It eliminates hallucinations by grounding responses in first-party technical sources rather than training data or web searches.

## How It Works
The server exposes three tools via MCP: `microsoft_docs_search` for semantic search across Microsoft docs, `microsoft_docs_fetch` to retrieve pages as markdown, and `microsoft_code_sample_search` for official code snippets. It is available as a remote HTTP endpoint (`https://learn.microsoft.com/api/mcp`), a CLI package (`@microsoft/learn-cli`), and bundled agent skills (microsoft-docs, microsoft-code-reference, microsoft-skill-creator) that guide when and how to use the tools. Installation is one-click in most IDEs (VS Code, GitHub Copilot CLI, Claude Desktop, Visual Studio, Cursor) and requires manual config in others; no authentication keys are needed.

## Why It Matters
For developers working with Azure, .NET, and other Microsoft technologies, this reduces the gap between stale model knowledge and current APIs. By ensuring AI outputs reference only official, trusted documentation, it cuts time spent debugging hallucinated method names, invalid SDK versions, or incorrect configurations—directly improving code quality and compilation success in heavy coding workflows.

## Sources
- [MicrosoftDocs/mcp](https://github.com/MicrosoftDocs/mcp) — github · 1820

## Related
