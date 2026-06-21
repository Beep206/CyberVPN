# Quick prompts

## Полная реализация

```text
Use $cybervpn-autonomous-delivery. Реализуй CYBA-XXX строго по приложенному ТЗ.
Работай автономно, не останавливайся после плана, устанавливай зависимости и
поднимай сервисы. Сначала repo_mapper + requirements_auditor, после реализации
verifier + adversarial_reviewer. Исправь все findings и заверши только с
TASK_STATUS: VERIFIED при PASS всех AC и required gates.
```

## Исправление недоработанного ТЗ

```text
Use $cybervpn-verify-done. Проведи gap analysis текущего diff относительно
исходного ТЗ и merge base. Найди всё, что было заявлено выполненным без
production path, interaction/persisted-state tests или runtime evidence.
Доработай найденные gaps автономно, затем повтори verifier и adversarial review.
```

## Backend + OpenAPI + web consumers

```text
Use $cybervpn-autonomous-delivery, $cybervpn-backend-quality and
$cybervpn-contract-sync. Реализуй изменение backend end to end, экспортируй
OpenAPI, регенерируй frontend/admin/partner clients, исправь consumers и
докажи zero drift второй генерацией.
```

## Migration

```text
Use $cybervpn-migration-safety. Реализуй migration/backfill с PostgreSQL clean
upgrade, populated upgrade, downgrade, re-upgrade и concurrency tests.
```

## Security review

```text
Use $cybervpn-security-review. Spawn security_reviewer and adversarial_reviewer,
проверь auth/RBAC/tenant/replay/idempotency/secrets и исправь подтверждённые
findings с regression tests.
```
