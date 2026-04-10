# CyberVPN — План внедрения IaC на Terraform + Ansible

> **Версия:** 2.0  
> **Дата аудита:** 8 апреля 2026  
> **Статус:** Рекомендовано к поэтапной реализации  
> **Основание:** документ обновлён после сверки с текущим состоянием монорепозитория и официальной документацией Terraform, Ansible, Hetzner, Cloudflare, Docker и Grafana.

---

## 1. Краткий вывод по аудиту

Исходный документ был полезен как стартовая концепция, но в нём было несколько проблем, которые для production-внедрения уже нельзя оставлять без правок:

- часть версионных рекомендаций устарела;
- несколько утверждений не подтверждаются официальной документацией;
- порядок внедрения слишком оптимистичен для текущего состояния репозитория;
- план недостаточно учитывал реальную структуру проекта: локальный `infra/docker-compose.yml`, Helix lab, monitoring stack, rollback scripts и backend tests.

### Что изменено принципиально

- **Не используем Terraform 1.15 как базу**. На дату аудита стабильный официальный релиз Terraform: `1.14.8`; ветка `1.15` ещё не является безопасной точкой опоры для внедрения.
- **Поднимаем рекомендованные версии Ansible и коллекций** до актуального 2026 уровня.
- **Убираем неподтверждённый тезис** о deprecation `datacenter` в Hetzner provider. На дату аудита я не нашёл официального подтверждения именно этой deprecation-линии.
- **Отказываемся от рекомендации `\"iptables\": false` для Docker**. Это не best practice. Для Docker-hosted сервисов используем Cloud Firewall + публикацию только нужных портов + правила в `DOCKER-USER`, а не отключение Docker iptables.
- **Меняем rollout-стратегию**: сначала edge-ноды и observability, потом workload deployment, и только после этого codify control-plane.
- **Не делаем `terraform apply -target` штатным сценарием**. Это допустимо только как break-glass операция.
- **Для новых лог-агентов не планируем Promtail**. На дату аудита Promtail уже EOL; для новых нод целевым агентом должен быть **Grafana Alloy**.

---

## 2. Что уже есть в репозитории и что нельзя игнорировать

Этот план должен опираться на уже существующий проект, а не на абстрактный IaC-шаблон.

### 2.1 Уже существующие артефакты

- `infra/docker-compose.yml` — локальный эталон текущей сервисной топологии;
- `infra/docker-compose.dev.yml` — dev-оверлей;
- `infra/README.md` — рабочие сценарии локального и lab-запуска;
- `infra/tests/test_helix_stack.sh` — верификация Helix stack;
- `infra/tests/verify_helix_rollback.sh` — rollback drill для Helix;
- `backend/tests/load/test_helix_load.py` — нагрузочные сценарии;
- `infra/prometheus/`, `infra/grafana/`, `infra/loki/`, `infra/otel/` — действующая observability-обвязка;
- `services/helix-adapter`, `services/helix-node`, `services/task-worker` — production-значимые сервисы, уже имеющие Dockerfile и свои runtime-контракты.

### 2.2 Практический вывод

IaC не должен “перепридумывать” этот стек. Правильный путь:

1. Использовать текущий `infra/docker-compose.yml` как **референс по сервисам, env-переменным, health endpoints и volumes**.
2. Не переносить giant compose-файл на edge-хосты как есть.
3. Разбить деплой на **малые Compose-проекты по роли хоста**:
   - `remnawave-node`
   - `helix-node`
   - `monitoring-agent`
   - позже `control-plane`
4. Внедрять IaC **сначала на edge-нодах**, не смешивая это с немедленной полной миграцией control-plane.

---

## 3. Целевое состояние

### 3.1 Что автоматизируем в первой очереди

- provisioning edge-ноды в Hetzner;
- выдачу и привязку primary IP;
- назначение firewall;
- публикацию DNS в Cloudflare;
- bootstrap ОС;
- hardening SSH;
- установку Docker Engine + Compose plugin;
- деплой `remnawave-node` и `helix-node`;
- установку node-level observability;
- rolling update и rollback-процедуры;
- инвентарь и связку Terraform → Ansible;
- PR/plan/apply pipeline для IaC.

### 3.2 Что сознательно выносим во вторую очередь

- полную автоматизацию control-plane;
- перенос PostgreSQL/Valkey/worker/backend/helix-adapter в отдельные IaC stacks;
- secret management уровня Vault/1Password Connect/Infisical как обязательную зависимость первого этапа;
- multi-region failover control-plane;
- self-service создание нод через UI.

Это не отказ от этих задач. Это декомпозиция риска.

---

## 4. Актуальный стек и версии на 2026-04-08

Ниже не “минимумы лишь бы завелось”, а рекомендуемые точки старта для нового внедрения.

| Компонент | Рекомендация для проекта | Комментарий |
|---|---|---|
| Terraform CLI | `1.14.x` | Официально стабильная ветка на дату аудита. 1.15 не брать как базу. |
| `hetznercloud/hcloud` provider | `>= 1.60.1, < 2.0` | Актуально после Hetzner IP lifecycle changes 2026. |
| `cloudflare/cloudflare` provider | `5.x` | Идти сразу на актуальную major-ветку, без новых внедрений на legacy patterns. |
| Ansible package | `13.x` | Текущая актуальная community-ветка. |
| `ansible-core` | `2.20.x` | Актуальная стабильная ветка на дату аудита. |
| `community.docker` | `5.x` | Использовать текущую ветку для `docker_compose_v2` и связанных модулей. |
| `hetzner.hcloud` collection | `>= 6.7.0, < 7.0` | Актуальная ветка под API-изменения Hetzner 2026. |
| Molecule | `26.x` | Для актуального тестового контура ролей. |
| Grafana Alloy | последняя стабильная `1.x` ветка | Для новых node log/metrics pipelines вместо Promtail. |

### Правило pinning

- pin по major/minor там, где высокая вероятность breaking changes;
- не писать `>= 0` и не оставлять широкие диапазоны “на авось”;
- обновлять версии сознательно отдельными PR;
- добавлять changelog-review в PR с обновлением провайдеров и коллекций.

---

## 5. Архитектурные решения, которые принимаем

### 5.1 Terraform отвечает только за infrastructure lifecycle

Terraform управляет:

- серверами;
- primary IP;
- firewall;
- placement groups;
- DNS;
- SSH key registration;
- outputs для дальнейшей конфигурации.

Terraform **не** должен:

- деплоить весь application runtime через provisioners;
- запускать shell-скрипты вместо Ansible;
- выполнять post-deploy логику, которую можно сделать playbook'ом.

### 5.2 Ansible отвечает за host configuration и workload deployment

Ansible управляет:

- пакетами ОС;
- Docker;
- users/SSH/sysctl;
- compose-файлами по ролям;
- env-файлами;
- rolling update;
- health checks;
- rollback.

### 5.3 Local compose остаётся эталоном, но не становится production deploy unit

`infra/docker-compose.yml` нужен как:

- источник реальных сервисных зависимостей;
- источник health endpoints;
- источник env naming;
- локальный/Helix lab контур.

Но production IaC должен раскладывать этот стек на role-specific units, иначе получится слишком большая blast radius на каждом хосте.

### 5.4 Внедрение идёт по модели edge-first

Для текущего репозитория это наименее рискованный порядок:

1. staging edge;
2. prod canary edge;
3. full edge rollout;
4. только потом control-plane codification.

---

## 6. Целевая структура IaC

Рекомендую следующую структуру.

```text
infra/
├── terraform/
│   ├── modules/
│   │   ├── edge_node/
│   │   ├── control_plane/
│   │   ├── firewall_policy/
│   │   └── common_labels/
│   └── live/
│       ├── staging/
│       │   ├── foundation/
│       │   ├── edge/
│       │   └── dns/
│       └── production/
│           ├── foundation/
│           ├── edge/
│           ├── dns/
│           └── control-plane/
├── ansible/
│   ├── ansible.cfg
│   ├── requirements.yml
│   ├── inventories/
│   │   ├── staging/
│   │   └── production/
│   ├── group_vars/
│   ├── host_vars/
│   ├── roles/
│   │   ├── base/
│   │   ├── docker/
│   │   ├── remnawave_edge/
│   │   ├── helix_edge/
│   │   ├── alloy_agent/
│   │   └── backup_restore/
│   ├── playbooks/
│   │   ├── site.yml
│   │   ├── edge-bootstrap.yml
│   │   ├── remnawave-rollout.yml
│   │   ├── helix-rollout.yml
│   │   ├── rollback-remnawave.yml
│   │   ├── rollback-helix.yml
│   │   └── security-audit.yml
│   └── templates/
└── docs/
```

### Почему именно так

- **`live/<env>/<stack>`** уменьшает blast radius и размер state;
- foundation, edge, dns и control-plane можно применять независимо;
- модули остаются только там, где реально есть повторяемая логика;
- Cloudflare-ресурсы не надо переусложнять абстракциями без необходимости.

### Важное ограничение по Cloudflare

Cloudflare сама рекомендует не злоупотреблять Terraform modules для своих ресурсов. Поэтому:

- модуль для **edge node** оправдан;
- модуль для **control-plane** оправдан;
- отдельный модуль для каждого маленького DNS record use case чаще всего не нужен;
- DNS stack лучше держать тонким и максимально читаемым.

---

## 7. Terraform: обновлённый подход

### 7.1 State layout

Разделяем state-файлы минимум на:

- `foundation`
- `edge`
- `dns`
- позже `control-plane`

Это сильно лучше одного огромного state, потому что:

- проще review;
- меньше вероятность болезненного drift/conflict;
- безопаснее apply;
- проще ограничивать blast radius в CI/CD.

### 7.2 Backend

Используем S3-compatible backend с:

- versioning;
- server-side encryption;
- отдельным bucket/path на stack;
- `use_lockfile = true`;
- backend credentials вне git.

### 7.3 Что храним в Terraform

Храним:

- имена нод;
- роли нод;
- locations;
- server types;
- firewall attachments;
- primary IP;
- DNS mapping;
- теги/labels;
- outputs для inventory.

Не храним:

- application secrets;
- panel tokens;
- runtime-generated keys;
- hand-written SSH passwords;
- произвольные shell bootstrap secrets.

### 7.4 Cloud-init

Cloud-init должен быть **минимальным**:

- создать admin user;
- положить authorized keys;
- настроить базовый SSH порт при необходимости;
- не деплоить бизнес-логику.

Не надо использовать cloud-init как второй Ansible.

### 7.5 `location` vs `datacenter`

Для этого проекта я рекомендую:

- по умолчанию использовать `location`;
- использовать `datacenter` только если реально нужна жёсткая привязка;
- не опираться на неподтверждённый тезис о deprecation `datacenter`.

### 7.6 Primary IP

Для новых нод используем выделенные Primary IP с версией провайдера `1.60.1+`, чтобы не попасть на изменения lifecycle после мая 2026.

### 7.7 Outputs contract для Ansible

Terraform должен отдавать **структурированный JSON-friendly output**, а не человекочитаемый текст.

Минимальный контракт:

- hostname;
- role;
- public IPv4;
- private IPv4, если появится;
- location;
- ssh port;
- labels.

---

## 8. Ansible: обновлённый подход

### 8.1 Роли

Минимальный набор ролей на первую очередь:

- `base`
  - apt packages
  - timezone
  - users
  - SSH hardening
  - sysctl
  - fail2ban
- `docker`
  - Docker Engine
  - Compose plugin
  - daemon config
  - log rotation
- `remnawave_edge`
  - compose template
  - env template
  - health checks
  - update/rollback hooks
- `helix_edge`
  - compose template
  - env template
  - readiness and rollback hooks
- `alloy_agent`
  - logs + metrics shipping
- `backup_restore`
  - config backup
  - restore drill helpers

### 8.2 Inventory

Штатный путь:

- Terraform даёт JSON outputs;
- CI или локальный helper генерирует YAML inventory snapshot;
- Ansible работает по этому snapshot.

Я **не рекомендую делать кастомный Python inventory script ядром системы**, потому что:

- он хрупкий;
- его надо сопровождать отдельно;
- он плохо масштабируется по окружениям и pipeline-контекстам;
- YAML snapshot проще ревьюить и воспроизводить.

Dynamic inventory plugin можно добавить позже, но стартовать проще и надёжнее с генерируемым inventory-файлом.

### 8.3 Секреты

Для первого этапа:

- inventory secrets: `ansible-vault`;
- CI secrets: GitHub Environments / secret store;
- provider tokens: только через environment variables или secret manager;
- per-node runtime secrets: vaulted vars или отдельный секретный source.

Для зрелой production-стадии:

- перейти на внешний secret manager;
- оставить `ansible-vault` только как fallback/bootstrap.

### 8.4 Rolling update

Все edge workload updates:

- `serial: 1`;
- health gate после каждой ноды;
- abort on first failure;
- отдельный rollback playbook;
- обязательный change window для production.

---

## 9. Security и network policy

### 9.1 Что оставляем обязательным

- SSH только по ключам;
- отключение password auth;
- ограничение admin access по source IP;
- Hetzner Cloud Firewall как внешний perimeter;
- image pinning по digest;
- secrets вне git;
- `no_log: true` для секретных задач;
- раздельные staging/prod secrets;
- ручное approval перед production apply.

### 9.2 Что меняем относительно старой версии документа

Старая рекомендация:

- отключить Docker iptables через `\"iptables\": false`.

Для этого проекта это **не рекомендую**.

Целевая практика:

- публикуем наружу только реально нужные порты;
- admin/metrics endpoints по возможности bind на loopback или private interface;
- ingress фильтруем на уровне Hetzner Cloud Firewall;
- если нужен host-level контроль для Docker traffic, используем правила в `DOCKER-USER`;
- UFW оставляем только как дополнительный слой, но не считаем его достаточной защитой для Docker-published портов.

### 9.3 Observability agent

Для новых нод:

- **не использовать Promtail** как новый стандарт;
- использовать **Grafana Alloy**;
- при необходимости временно поддерживать совместимость с существующим Loki pipeline.

Причина: Promtail уже вышел из жизненного цикла; строить на нём новый node rollout в 2026 бессмысленно.

---

## 10. CI/CD модель

### 10.1 Что должно происходить на PR

- `terraform fmt -check`
- `terraform validate`
- `terraform test`
- `tflint`
- `trivy config` или эквивалентный IaC scanner
- `ansible-lint`
- `molecule test` для изменённых ролей
- generation и публикация `terraform plan`
- summary-комментарий в PR

### 10.2 Что должно происходить после merge

После merge **не должно быть слепого auto-apply в production**.

Правильный процесс:

1. merge в `main`;
2. отдельный `workflow_dispatch` или release-driven запуск;
3. ручное approval через GitHub Environment;
4. `terraform apply` для конкретного stack;
5. отдельный запуск Ansible rollout;
6. post-deploy verification.

### 10.3 Почему так

Для этого репозитория `terraform apply -> ansible-playbook` в одной автоматической цепочке после каждого `git push` слишком рискован:

- меняются cloud-ресурсы и runtime одновременно;
- сложнее локализовать проблему;
- rollback становится менее предсказуемым;
- растёт шанс недоapply или partially configured host.

---

## 11. Repo-specific implementation roadmap

Ниже не “идеальная теория”, а маршрут, по которому реально можно идти в этом проекте.

### Фаза 0. Design freeze и scaffold

**Цель:** подготовить репозиторий и зафиксировать правила.

**Делаем:**

- создаём `infra/terraform/` и `infra/ansible/` структуру;
- фиксируем версии CLI/providers/collections;
- добавляем `.gitignore` для IaC артефактов;
- добавляем `README` для новых директорий;
- описываем naming convention для нод и DNS.

**Результат фазы:**

- репозиторий готов к первому `terraform init` и `ansible-galaxy install`.

### Фаза 1. Terraform foundation

**Цель:** codify foundation stacks для staging.

**Делаем:**

- S3-compatible backend;
- foundation stack;
- firewall policy;
- SSH key registration;
- labels/tags policy;
- edge stack на staging;
- dns stack на staging.

**Результат фазы:**

- staging edge-нода создаётся полностью через Terraform без ручных действий в панели провайдера.

### Фаза 2. Host bootstrap через Ansible

**Цель:** из “голого Ubuntu-хоста” делать стандартизированную edge-ноду.

**Делаем:**

- `base` role;
- `docker` role;
- inventory generation;
- secrets bootstrap;
- smoke playbook `edge-bootstrap.yml`.

**Результат фазы:**

- свежесозданная staging-нода автоматически получает hardening, Docker и базовую observability-обвязку.

### Фаза 3. Remnawave edge rollout

**Цель:** production-grade деплой VPN edge workload.

**Делаем:**

- compose/env templates для `remnawave-node`;
- health checks;
- rolling update playbook;
- rollback playbook;
- smoke verification после деплоя.

**Результат фазы:**

- staging Remnawave edge присоединяется к panel и переживает повторный idempotent rollout.

### Фаза 4. Helix edge rollout

**Цель:** безопасный rollout собственного transport stack.

**Делаем:**

- `helix_edge` role;
- per-node state dir policy;
- canary strategy;
- rollback hooks;
- проверка совместимости с существующими `infra/tests/test_helix_stack.sh` и `infra/tests/verify_helix_rollback.sh`.

**Результат фазы:**

- staging/lab Helix-нода деплоится через Ansible и проходит readiness/rollback проверки.

### Фаза 5. Observability и security gates

**Цель:** сделать rollout наблюдаемым и проверяемым.

**Делаем:**

- роль `alloy_agent`;
- dashboards/alerts alignment;
- CI checks для IaC;
- policy на ручной approval;
- inventory snapshot artifact;
- post-deploy verification checklist.

**Результат фазы:**

- на каждый rollout есть telemetry, health evidence и понятная точка отката.

### Фаза 6. Prod canary

**Цель:** выйти в production без big-bang миграции.

**Делаем:**

- одна prod VPN edge-нода как canary;
- одна prod Helix edge-нода как canary;
- 24h наблюдение;
- rollback drill;
- только затем расширение на остальные ноды.

**Результат фазы:**

- production rollout подтверждён на минимальной blast radius.

### Фаза 7. Control-plane codification

**Цель:** автоматизировать core stack только после стабилизации edge automation.

**Делаем:**

- отдельный `control-plane` stack;
- backup/restore runbooks;
- worker/backend/helix-adapter deployment;
- DR drills.

**Результат фазы:**

- control-plane codified без слома edge rollout-процесса.

### Фаза 8. Release promotion и secrets hardening

**Цель:** сделать control-plane rollout воспроизводимым и reviewable, без ручного
редактирования image refs и vault-файлов перед каждым релизом.

**Делаем:**

- отдельный build/publish pipeline для `backend`, `task-worker`, `helix-adapter`;
- promotion через environment-scoped `release.yml`, где внутренние сервисы идут
  только по digest-pinned `@sha256` refs;
- manual promotion workflow, который оставляет reviewable git change, а не
  “тихий” deploy вне репозитория;
- registry auth на хосте для private pulls;
- bootstrap `vault.yml` из структурированного source файла вместо ad-hoc copy/paste.

**Результат фазы:**

- staging и production control-plane деплоятся из явного release manifest;
- promotion path сохраняет commit, digests и build evidence;
- секреты готовятся из повторяемого source-of-truth, а не из ручной правки
  множества inventory-файлов.

---

## 12. Реалистичная оценка сроков

Старая оценка `10-14 дней` для этого проекта слишком оптимистична.

### Реалистично

- **1 инженер full-time:** `4-6 недель`
- **2 инженера с разделением Terraform/Ansible + review:** `2.5-4 недели`

### Почему дольше

- нужно не только написать HCL/YAML, но и пройти реальный rollout;
- есть Helix-specific rollback requirements;
- observability и security здесь не “опциональны”;
- контроль качества должен включать staging, canary и операционные проверки.

---

## 13. Правила, которые будут обязательными в реализации

- не хранить реальные токены в git;
- не использовать `terraform -target` как штатный процесс;
- не объединять production Terraform apply и Ansible rollout в непрозрачную “магическую” команду;
- не строить новые log pipelines на Promtail;
- не делать giant-модуль для каждого DNS record;
- не прятать инфраструктурный риск за `ignore_changes`, если это ломает предсказуемость;
- не изменять infra вручную в панелях после постановки ресурса под Terraform.

---

## 14. Критерии готовности

План считается реализованным корректно, когда:

- staging edge создаётся и конфигурируется без ручных шагов;
- inventory собирается из Terraform outputs воспроизводимо;
- Remnawave edge проходит idempotent redeploy;
- Helix edge проходит canary и rollback checks;
- CI показывает plan, lint и tests до apply;
- production rollout требует manual approval;
- control-plane internal images промотируются только через digest-pinned release manifests;
- есть документированный rollback path для Terraform и Ansible;
- все новые node logging/metrics агенты идут через Alloy, а не через Promtail.

---

## 15. Источники, использованные при аудите

- Terraform install page и release info: https://developer.hashicorp.com/terraform/install
- Terraform variable `ephemeral`: https://developer.hashicorp.com/terraform/language/block/variable
- Terraform ephemeral blocks: https://developer.hashicorp.com/terraform/language/block/ephemeral
- Terraform test framework: https://developer.hashicorp.com/terraform/language/tests
- Terraform S3 backend / lockfile: https://developer.hashicorp.com/terraform/language/backend/s3
- Ansible core release and maintenance: https://docs.ansible.com/projects/ansible-core/devel/reference_appendices/release_and_maintenance.html
- Ansible package releases on PyPI: https://pypi.org/project/ansible/
- `community.docker` collection docs: https://docs.ansible.com/ansible/latest/collections/community/docker/
- Hetzner Cloud changelog по API/IP lifecycle: https://docs.hetzner.cloud/changelog/
- `terraform-provider-hcloud` releases: https://github.com/hetznercloud/terraform-provider-hcloud/releases
- Cloudflare Terraform tutorials: https://developers.cloudflare.com/terraform/tutorial/
- Cloudflare Terraform best practices: https://developers.cloudflare.com/terraform/advanced-topics/best-practices/
- Docker packet filtering and firewalls: https://docs.docker.com/engine/network/packet-filtering-firewalls/
- Grafana Loki / Promtail deprecation notice: https://grafana.com/docs/loki/latest/send-data/promtail/
- Grafana Alloy migration from Promtail: https://grafana.com/docs/alloy/latest/tasks/migrate/from-promtail/
- Docker login action README: https://github.com/docker/login-action
- Docker build-push action README: https://github.com/docker/build-push-action
- GitHub Actions environments: https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments

---

## 16. Рекомендуемое следующее действие

Следующий практический шаг для проекта:

1. создать каркас `infra/terraform/live/staging/{foundation,edge,dns}` и `infra/ansible/roles/{base,docker}`;
2. описать первую staging edge-ноду;
3. прогнать полный цикл `terraform apply -> ansible bootstrap -> workload smoke check`;
4. только после этого переносить в план production rollout.

Именно этот путь даёт лучший баланс между скоростью и контролем риска для текущего состояния CyberVPN.
