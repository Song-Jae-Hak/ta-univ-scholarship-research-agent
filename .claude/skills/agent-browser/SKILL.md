---
name: agent-browser
description: Fast browser automation via the agent-browser CLI (vercel-labs). Use when a task must drive a real Chrome from the shell — open pages, read JS-rendered content, click/type/fill forms, take snapshots/screenshots, scrape sites WebFetch can't render, or log in to a site. Installed globally at ~/.claude/bin/agent-browser.exe (v0.33.0), on the User PATH.
---

# agent-browser — browser automation CLI

`agent-browser` is a native CLI that drives a real Chrome (Chrome for Testing) for AI agents. It runs a persistent daemon, so separate CLI calls act on the same live browser/tab.

## Setup on this PC
- Binary: `C:\Users\user\.claude\bin\agent-browser.exe` (added to the **User PATH** → in a *new* terminal just call `agent-browser`; existing sessions must use the full path).
- Chrome for Testing is already installed (`agent-browser install` was run → `C:\Users\user\.agent-browser\browsers\`).
- Verify: `agent-browser --version`; diagnose with `agent-browser doctor`.
- ⚠️ In restricted/headless sandboxes the browser launch can **hang** (no output). If `agent-browser open` does not return within ~30s, fall back to `WebFetch` for static pages. Try `--args "--no-sandbox,--disable-dev-shm-usage"` on locked-down hosts.

## Core workflow
1. `agent-browser open <url>` — launch/navigate (https:// auto-added).
2. `agent-browser snapshot -i` — accessibility tree of interactive elements, each tagged `@e1 @e2 …`.
3. Act by ref: `agent-browser click @e2` · `agent-browser fill @e3 "text"` · `agent-browser type @e3 "text"` · `agent-browser press Enter`.
4. Read content: `agent-browser get text` · `agent-browser read <url>` (agent-readable text) · `agent-browser get title` · `agent-browser get url` · `agent-browser get html`.
5. Find without a snapshot: `agent-browser find role button click --name Submit` · `agent-browser find text "다음" click`.
6. `agent-browser screenshot [path] --full` / `--annotate` (numbered labels for vision models).
7. `agent-browser close --all` when done.

Chain in one shell line (browser persists via the daemon):
```
agent-browser open example.com && agent-browser snapshot -i
```

## Useful flags
- `--headed` show the window (default is headless).
- `--session <name>` isolate a session → run **multiple independent browsers concurrently** (e.g. one per researcher agent).
- `--profile <name|dir>` reuse Chrome login state / a persistent profile.
- `--json` machine-readable output · `--max-output <n>` truncate · `--content-boundaries` wrap output in markers.
- `--args "--no-sandbox,--disable-dev-shm-usage"` extra Chrome launch args.

## Full command reference
`agent-browser --help` is the source of truth for this standalone-binary install (it does **not** bundle the skills dir, so `agent-browser skills get core` will report "Skills directory not found" — that command only works after an `npm install -g agent-browser`).

## When NOT to use it
For plain static pages, `WebFetch` is faster and always available. Prefer `agent-browser` for JS-rendered pages, interaction (clicks/forms/login), screenshots, or multi-step flows.
