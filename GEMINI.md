# GEMINI.md (Agent Instructions for WSL)

When operating in this repository as an AI agent on a **WSL Ubuntu** environment (especially within **Antigravity**), you should adhere to standard Linux bash practices.

## 1. Syntax for Chaining Commands
You can safely use standard bash operators like `&&` and `||`. 
Example: `command1 && command2`

## 2. Terminal Background Jobs
Next.js and FastAPI servers can block the AI terminal if not handled properly.
- **MANDATORY**: When launching dev servers, prefer using `nohup` and backgrounding them to prevent the UI from hanging on EOF.
  Example: `nohup npm run dev > /tmp/next.log 2>&1 &`

## 3. Git Commits and Husky Hooks
Husky hooks should run normally in WSL. If they prompt for interactive input, you can append `--no-verify` to bypass them.
- Example: `git commit --no-verify -m "chore: commit message"`

## 4. Background Dev Servers
Next.js telemetry prompts can hang the background process.
- **MANDATORY**: Disable telemetry before running dev servers: `NEXT_TELEMETRY_DISABLED=1 npm run dev`

## 5. IDE Settings (User Hint)
If hangs persist, ensure that **Terminal > Integrated > Shell Integration** is **DISABLED** in your IDE (Antigravity/VS Code) settings to prevent escape sequence conflicts.
