# GEMINI.md (Agent Instructions for Windows)

When operating in this repository as an AI agent on a **Windows PowerShell** environment (especially within **Antigravity**), you MUST adhere to the following strict rules regarding terminal command execution to prevent hangs and syntax errors:

## 1. Syntax for Chaining Commands
Windows PowerShell 5.1 does **NOT** support the `&&` operator. 
- **DO NOT USE**: `command1 && command2`
- **USE INSTEAD**: `command1 ; command2` 
If conditional execution is strictly required, use: `if ($?) { command2 }` or `if (command1) { command2 }`

## 2. Preventing EOF Hangs (Antigravity/Windows)
If commands like `git status`, `npm install`, or `ls` appear to hang in the "Running..." state, it is likely the CLI failing to detect the End-of-File (EOF) signal.
- **MANDATORY**: For shell commands that interact with the file system or external tools, prefer prefixing them with `cmd /c` to ensure immediate process termination and signal unlocking.
  Example: `cmd /c git status` instead of just `git status`.

## 3. Git Commits and Husky Hooks
Husky hooks (e.g., `pre-commit`) often lack a proper interactive TTY session on Windows and will **hang infinitely**.
- **PROHIBITED**: `git commit -m "message"` (will hang)
- **MANDATORY**: You MUST append `--no-verify` to all `git commit` commands.
  Example: `git commit --no-verify -m "chore: commit message"`

## 4. Background Dev Servers
Next.js telemetry prompts can hang the background process.
- **MANDATORY**: Disable telemetry: `$env:NEXT_TELEMETRY_DISABLED=1; npm run dev`

## 5. Linting and Large Outputs
Linting tools like ESLint often produce large amounts of output or complex terminal escape sequences (colors/formatting) that can hang the Antigravity output buffer.
- **MANDATORY**: When running linting, use the `--quiet` flag (or equivalent) to only show errors and reduce terminal noise.
  Example: `cmd /c npm run lint -- --quiet`

## 6. IDE Settings (User Hint)
If hangs persist, ensure that **Terminal > Integrated > Shell Integration** is **DISABLED** in your IDE (Antigravity/VS Code) settings to prevent escape sequence conflicts.
