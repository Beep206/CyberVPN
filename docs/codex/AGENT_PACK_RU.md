# CyberVPN agent pack

## Рекомендуемая оркестрация

### Обычная cross-stack задача

1. `repo_mapper` и `requirements_auditor` параллельно.
2. Один implementation specialist или root agent.
3. `test_engineer` при значительном тестовом контуре.
4. `security_reviewer` для auth/payment/VPN/attribution/protocol.
5. `verifier` и `adversarial_reviewer` параллельно.
6. Root agent исправляет findings.
7. `verifier` повторяет affected gates.

### Параллельные writers

Использовать отдельные git worktrees:

```bash
git fetch origin
git worktree add ../CyberVPN-CYBA-900-backend -b codex/CYBA-900-backend origin/main
git worktree add ../CyberVPN-CYBA-900-web -b codex/CYBA-900-web origin/main
```

Не разрешать двум агентам менять один generated contract или migration chain
одновременно.

## Прямой запуск ролей в prompt

```text
Spawn repo_mapper and requirements_auditor in parallel. Wait for both.
Delegate backend files to backend_engineer and partner files to
admin_partner_engineer with explicit file ownership. After integration spawn
verifier and adversarial_reviewer in parallel, resolve all findings, and rerun
verification.
```
