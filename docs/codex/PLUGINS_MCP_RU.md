# Plugins и MCP

## Включено автоматически

В `~/.codex/config.toml` и project config добавлен OpenAI Developer Docs MCP:

```toml
[mcp_servers.openai_developer_docs]
url = "https://developers.openai.com/mcp"
enabled = true
required = false
default_tools_approval_mode = "approve"
```

Проверка:

```text
/mcp
```

## Codex Security plugin

Открыть:

```text
/plugins
```

Найти и установить Codex Security. После установки использовать его для
авторизованного review изменений auth, payment, VPN, partner attribution,
protocol, desktop и infrastructure. Plugin не заменяет тесты и verifier.

## Необязательный Context7 MCP

```bash
codex mcp add context7 -- npx -y @upstash/context7-mcp
```

Использовать для version-sensitive APIs, а не перед каждой тривиальной
правкой.

## Необязательный Playwright MCP

```bash
codex mcp add playwright -- npx -y @playwright/mcp@latest
```

Полезен для browser smoke customer/admin/partner flows. MCP process наследует
full environment согласно user config и auto-approved tools, поэтому он имеет
тот же высокий risk profile.

## GitHub

Для branch/PR/status операций достаточно `gh` CLI:

```bash
gh auth login
gh auth status
```

Full-access Codex сможет использовать `gh` напрямую через shell.

## Встроенный локальный CyberVPN plugin

Репозиторий содержит marketplace `.agents/plugins/marketplace.json` и plugin
`plugins/cybervpn-autonomous-team`. После перезапуска Codex он отображается в
`/plugins`. Установка из CLI:

```bash
codex plugin add cybervpn-autonomous-team@cybervpn-local --json
```

Он содержит три namespaced workflow-skills для cross-stack delivery, security
scan и release-readiness. Project skills из `.agents/skills` остаются основным
автоматически доступным механизмом.
