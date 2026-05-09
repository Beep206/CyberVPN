> CyberVPN Launch Program
> Версия: 0.1-draft
> Дата фиксации: 2026-05-03
> Статус: optional architecture note. Не является production topology approval.

# Home Lab / Non-Critical Home Server Option

## Purpose

Этот документ фиксирует возможный вариант использования домашнего выделенного компьютера в CyberVPN launch program. Вариант допустим только для non-critical задач, потому что дома возможны отключения электричества до 5 часов.

Главное правило: если домашний сервер выключился, клиентская часть CyberVPN должна оставаться доступной и рабочей.

## Decision

Домашний сервер можно использовать как **lab / staging-like / evidence / backup-restore / device-testing machine**, но не как production critical path.

Домашний сервер не должен быть единственной точкой отказа для:

- публичного сайта;
- web-кабинета;
- backend API;
- Telegram Bot production webhooks;
- payment webhooks;
- production PostgreSQL;
- production Valkey/Redis;
- production Remnawave control-plane;
- admin production;
- DNS/TLS edge;
- VPN exit nodes;
- primary monitoring/alerting;
- единственной копии backups.

VPN-ноды на домашнем сервере не планируются.

## Why Home Server Is Non-Critical Only

Отключение света на 5 часов создаёт неприемлемый production-риск:

- пользователь не сможет войти в кабинет;
- payment webhook может не доставиться или уйти в provider retry/timeout;
- provisioning может зависнуть;
- Telegram Bot/Mini App могут перестать отвечать;
- support/admin не смогут диагностировать live-инцидент;
- monitoring/alerts могут пропустить проблему, если они primary;
- домашний IP и домашний ISP не подходят для публичной VPN exit-node роли.

Поэтому домашний сервер можно использовать только так, чтобы его падение не ломало пользовательский B2C flow.

## Recommended Split

### External / cloud / managed production

Production critical services должны жить вне дома:

| Component | Reason |
|---|---|
| Public frontend/site/cabinet | Клиент должен иметь доступ независимо от домашнего питания |
| Backend API | Auth, subscription, payments, provisioning state |
| Telegram Bot production webhook receiver | Telegram webhook должен быть доступен постоянно |
| Payment webhook receiver | Платёжные события нельзя терять из-за выключения дома |
| Managed PostgreSQL | Source of truth, backups, RPO/RTO |
| Production Valkey/Redis if used | Queues/cache/rate limits для production |
| Production Remnawave control-plane | VPN access authority |
| Admin production | Support/admin должны работать во время incident |
| DNS/TLS/edge/reverse proxy | Public entrypoint должен быть стабильным |
| VPN exit nodes | Нужны datacenter/VPS IP, abuse handling, стабильность |
| Primary monitoring/alerts | Alerts должны работать, даже если домашний сервер выключен |

### Home server

Домашний сервер можно использовать для:

| Use case | Notes |
|---|---|
| Local development | Full local stack with Docker/Compose |
| Staging-like sandbox | Только если не объявляется production/staging authority |
| Remnawave local smoke | Useful dev evidence, but not production/staging evidence |
| Backup restore drills | Restore into isolated local environment |
| Evidence archive copy | Secondary copy, not the only evidence storage |
| Monitoring replica | Secondary Grafana/Prometheus/Loki copy, not primary alerting |
| Security scans | Dependency, secrets, frontend bundle/env scans |
| Release dry-runs | Build/deploy/rollback rehearsal |
| Device lab | Mobile/desktop/Android TV testing |
| Helix/Verta/Beep lab | Experimental private transport tests |
| Cost/reporting sandbox | Batch analysis without production dependency |

## Stage-by-Stage Usage

### S0 — Documentation & Decision Freeze

Allowed at home:

- docs work;
- local checks;
- evidence drafts;
- launch scope map;
- decision/evidence review.

Not required in cloud.

### S1 — Controlled Public Beta

Keep outside home:

- public site/cabinet;
- backend API;
- Telegram production webhooks;
- payment webhooks;
- production PostgreSQL;
- production Remnawave control-plane;
- production Valkey/Redis if required;
- at least one real VPN node;
- primary monitoring/alerts.

Allowed at home:

- local/staging-like clone;
- Docker/Remnawave local smoke;
- restore drills;
- secondary monitoring;
- release evidence archive;
- security scans.

### S2 — Public Release 1.0

Home server remains non-critical:

- dev/staging clone;
- backup restore tests;
- synthetic monitoring copy;
- reporting sandbox;
- support troubleshooting lab.

Do not host primary customer/payment/provisioning path at home.

### S3 — Partner / Reseller Platform

Allowed at home:

- partner reporting sandbox;
- anti-fraud experiments;
- settlement simulation;
- partner portal staging.

Not allowed at home:

- real partner portal production;
- payout/reconciliation authority;
- partner webhooks;
- primary partner reporting source of truth.

### S4 — Mobile Store Beta / Release

Allowed at home:

- mobile build/test lab;
- device testing;
- crash reproduction;
- store review screenshots;
- local API mock testing.

Not allowed at home:

- mobile production API;
- push/payment/auth backend;
- production signing secret storage as only copy/location.

### S5 — Desktop / Android TV / Device Expansion

Allowed at home:

- Windows/macOS/Linux/Android TV device lab;
- auto-update staging;
- diagnostics reproduction;
- platform-specific support testing.

Not allowed at home:

- production update server;
- production signing secrets;
- production device management authority.

### S6 — Helix / Verta / Beep Private Transport Beta

Allowed at home:

- lab/canary testing;
- protocol experiments;
- light-load private transport tests;
- security review sandbox.

Not allowed at home:

- default production transport;
- critical relay/edge;
- mass rollout control-plane.

### S7 — Platform Scale & Enterprise Hardening

Allowed at home:

- disaster recovery drills;
- offline restore tests;
- cost analysis;
- log archive copy;
- non-primary Grafana/Loki/Prometheus replica;
- security lab;
- GitOps dry-runs.

Not allowed at home:

- primary production cluster;
- primary secrets authority;
- primary alerting;
- only backup copy.

## Recommended Home Server Specs

### Minimum useful home lab

```text
CPU: 6-8 cores
RAM: 32 GB
Disk: 1 TB NVMe
Backup disk: 2-4 TB HDD/SSD or NAS
Network: 100+ Mbps stable
OS: Ubuntu Server 24.04 LTS or Debian 12
Runtime: Docker Engine + Docker Compose
UPS: optional for non-critical lab, recommended for comfort
```

### Comfortable home lab for staging-like work

```text
CPU: 8-12 cores
RAM: 64 GB
Disk: 2 TB NVMe
Backup: separate NAS/HDD/SSD
Network: stable 300 Mbps+ down / 100 Mbps+ up preferred
UPS: recommended
```

## Operational Rules

1. Home server outage must not affect user login, payments, provisioning or support.
2. Home server evidence is labelled `local` or `lab`, not production evidence.
3. Staging/prod evidence must come from the actual staging/prod environment.
4. Home server must not store production secrets as the only copy.
5. Home server must not be the only backup location.
6. Home monitoring may be secondary, but primary alerts must live outside home.
7. Home restore drills are useful, but production RPO/RTO still need evidence.
8. Any move of a home-hosted component into production critical path requires a new decision-log entry and risk acceptance.

