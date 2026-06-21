# Установленные Codex settings

## Максимальная автономность

```toml
approval_policy = "never"
sandbox_mode = "danger-full-access"
web_search = "live"
```

Wrapper также передаёт CLI flags bypass approvals/sandbox и bypass hook trust.

## Модель

```toml
model = "gpt-5.5"
review_model = "gpt-5.5"
model_reasoning_effort = "xhigh"
plan_mode_reasoning_effort = "xhigh"
model_reasoning_summary = "detailed"
model_verbosity = "high"
```

## Shell environment

```toml
[shell_environment_policy]
inherit = "all"
ignore_default_excludes = true
experimental_use_profile = true
```

`ignore_default_excludes = true` сохраняет переменные, содержащие
`KEY/SECRET/TOKEN`. Это специально выбрано для unrestricted режима и повышает
риск утечки credentials.

## Agents

```toml
[agents]
max_threads = 12
max_depth = 2
job_max_runtime_seconds = 14400
```

12 параллельных thread и delegation depth 2 — высокий уровень параллелизма без
бесконечного fan-out.

## Features

Включены hooks, memories, multi-agent, generated git commits, apps/connectors,
unified exec, shell snapshot, skill MCP dependency install, undo, fast tier
selection и prevent idle sleep.

## Apps/connectors

```toml
[apps._default]
enabled = true
default_tools_approval_mode = "approve"
destructive_enabled = true
open_world_enabled = true
approvals_reviewer = "auto_review"
```

Установленные connector tools могут выполнять destructive/open-world actions
без ручного approval.

## History

Transcripts сохраняются в history до 1 GiB. Tool outputs получают увеличенный
history budget. TUI notifications включены всегда.
