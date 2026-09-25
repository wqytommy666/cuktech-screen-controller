# Claude Code instructions

Read and follow [`AGENTS.md`](AGENTS.md), then read
[`skills/cuktech-ap01-screen-kit/SKILL.md`](skills/cuktech-ap01-screen-kit/SKILL.md).

Detect the host OS first. Begin with `./macos/diagnose.sh` on macOS or
`scripts/diagnose-windows.ps1` on Windows. Daily content updates must use the
Wi-Fi Bridge and AP01 RAM slots. Do not perform a firmware installation unless the
exact AP01 model/build has been verified and the user confirms the one-time
installation immediately beforehand.

For a new computer or stock display, use [the first-install runbook](docs/agent-first-install.md).
Codex, WorkBuddy and other terminal-capable agents can read the same Markdown
without installing a Skill. Never assume the maintainer's local paths or accounts.
