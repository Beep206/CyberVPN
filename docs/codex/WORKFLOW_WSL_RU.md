# CyberVPN + Codex CLI workflow в WSL Ubuntu 24.04

## Новая задача

```bash
cd ~/projects/CyberVPN
git fetch origin
git switch main
git pull --ff-only
git switch -c codex/CYBA-900-short-name
scripts/codex/init-task.sh CYBA-900 "Название" "Наблюдаемый результат"
codex-yolo
```

Вставить prompt из `PROMPT_TEMPLATE_RU.md`.

## Во время работы

- Агент не ждёт approvals.
- Недостающие system packages устанавливаются через `sudo -n apt-get ...`.
- PostgreSQL/Redis/Docker services могут запускаться автоматически.
- Для нескольких writers используются worktrees.
- `.codex/current-task.json` обновляется после каждого существенного этапа.

## Локальный final gate

```bash
scripts/codex/verify-changed.sh
```

Затем независимые agents и final diff:

```bash
git status --short
git diff --check
git diff --stat
git diff "$(git merge-base HEAD origin/main)"...HEAD
```

## Non-interactive run

```bash
codex-yolo-exec -C "$PWD" "$(cat /tmp/cyba-900-prompt.txt)"
```

## Resume

```bash
codex-yolo resume --last
```

Проверяйте `/agent`, чтобы root agent дождался всех specialist/reviewer jobs.
