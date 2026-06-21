# Full-access risk profile

Установленный профиль намеренно включает:

```toml
approval_policy = "never"
sandbox_mode = "danger-full-access"
web_search = "live"

[shell_environment_policy]
inherit = "all"
ignore_default_excludes = true
experimental_use_profile = true
```

Wrapper дополнительно запускает Codex с bypass approvals/sandbox и bypass hook
trust. Опциональный sudo installer создаёт:

```sudoers
<user> ALL=(ALL:ALL) NOPASSWD: ALL
```

Это означает полный доступ к WSL и ко всем доступным mount/network/credential
resources. Не храните production secrets в shell environment, если их чтение
Codex недопустимо. Отдельный disposable WSL distro остаётся наиболее надёжным
способом изоляции, хотя этот pack не требует изоляции.
