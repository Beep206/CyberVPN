# GEMINI.md (Agent Instructions for Windows)

When operating in this repository as an AI agent on a **Windows PowerShell** environment, you MUST adhere to the following strict rules regarding terminal command execution to prevent hangs and syntax errors:

## 1. Syntax for Chaining Commands
Windows PowerShell does **NOT** support the `&&` operator by default in older versions. 
- **DO NOT USE**: `command1 && command2`
- **USE INSTEAD**: `command1 ; command2` 
If conditional execution is strictly required, use: `if (command1) { command2 }`

## 2. Git Commits and Husky Hooks
The repository contains Husky hooks (e.g., `pre-commit` running `lint-staged`). When these hooks are triggered by an AI agent's background terminal, they often lack a proper interactive TTY session on Windows and will **hang infinitely**.
- **PROHIBITED**: `git commit -m "message"` (this will hang on the pre-commit hook)
- **MANDATORY**: You MUST append `--no-verify` to all `git commit` commands to bypass the hooks.
  Example: `git commit --no-verify -m "chore: commit message"`

*Note: Before bypassing hooks, you should manually run linters (`npm run lint`) to ensure you are not committing broken code.*

## 3. Background Dev Servers
When starting `npm run dev` or `next dev`, Next.js may prompt for Telemetry (`Would you like to help improve Next.js?`) which hangs the background process.
- **MANDATORY**: Always disable telemetry when starting the dev server:
  `$env:NEXT_TELEMETRY_DISABLED=1; npm run dev`
