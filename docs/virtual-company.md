# CyberVPN Virtual IT Company

## Overview

CyberVPN operates as a virtual IT company powered by 32 AI agents organized into 17 departments. Each agent is a specialist with preloaded skills, scoped tool access, and a defined role in the company hierarchy.

All agent configurations are stored in `.claude/agents/` as Markdown files with YAML frontmatter.

**Entry Point:** Tell the `ceo-orchestrator` your task — he convenes the Board of Directors, decomposes the work, assigns to departments, and reports back.

---

## Org Chart

```
YOU (Founder — FINAL decision authority on strategy, money, scope, risk)
|
ceo-orchestrator (CEO — executor, recommends & orchestrates, NOT owner)
|
+-- Board of Directors (consulted on non-trivial tasks)
|   +-- cto-architect (CTO — technical strategy)
|   +-- product-manager (CPO — requirements, Task Master)
|   +-- marketing-lead (CMO — brand, growth)
|   +-- finance-strategist (CFO — pricing, unit economics)
|
+-- hr-agent-factory (HR — creates/retires agents)
|
+-- Frontend Department
|   +-- frontend-lead (Tech Lead, delegates)
|   |   +-- ui-engineer (components, styling)
|   |   +-- 3d-engineer (Three.js, WebGL)
|
+-- Backend Department
|   +-- backend-lead (Tech Lead, delegates)
|       +-- backend-dev (implementation)
|
+-- Mobile Department
|   +-- mobile-lead (Flutter, app stores)
|
+-- DevOps / SRE
|   +-- devops-lead (infrastructure, delegates)
|       +-- devops-engineer (Dockerfiles, CI)
|
+-- QA / Testing
|   +-- qa-lead (test strategy, delegates)
|       +-- test-runner (writes tests)
|
+-- Security
|   +-- security-engineer (audits, read-only)
|
+-- Product
|   +-- product-manager (PRD, Task Master, roadmap)
|
+-- Marketing & Growth
|   +-- marketing-lead (strategy, delegates)
|       +-- content-writer (copy, emails, social)
|       +-- seo-specialist (SEO, ASO, analytics)
|
+-- Design
|   +-- design-lead (UI/UX, brand, accessibility)
|
+-- Localization
|   +-- i18n-manager (41 locale, RTL)
|
+-- Services
|   +-- telegram-bot-dev (aiogram 3, CryptoBot)
|   +-- task-worker-dev (TaskIQ, background jobs)
|
+-- Finance
|   +-- finance-strategist (pricing, metrics, advisory)
|
+-- Legal & Compliance
|   +-- dpo-officer (GDPR, privacy, DPIA — read-only)
|   +-- abuse-handler (DMCA, abuse reports, hosting coordination)
|   +-- compliance-officer (jurisdictional strategy, ToS, sanctions)
|   +-- security-audit-coordinator (external audits, SOC 2, pentest)
|
+-- VPN Operations
|   +-- infrastructure-engineer (600+ servers, 40+ countries, peering)
|   +-- payments-specialist (crypto, IAP, chargebacks, PCI)
|   +-- protocol-engineer (WireGuard, OpenVPN, post-quantum crypto)
|   +-- noc-agent (24/7 monitoring, failover, incident response)
|
+-- Customer Success
    +-- customer-success-agent (VPN troubleshooting, KB, churn reduction)
```

---

## All Agents (32)

### Department 1: Executive & Board of Directors

#### 1. ceo-orchestrator
| Field | Value |
|-------|-------|
| **Role** | CEO / Chief Orchestrator |
| **Model** | opus |
| **Permission Mode** | default |
| **Tools** | Read, Write, Edit, Bash, Glob, Grep, Task, WebSearch, WebFetch |
| **Skills** | clean-architecture, monorepo-architecture, requirements-analysis, product-strategist, startup-metrics-framework |
| **Can Delegate** | Yes — to ALL agents |
| **Scope** | Entire monorepo |

**The single entry point for the founder.** Takes any task, convenes the Board of Directors (CTO + PM + Marketing Director) in parallel, synthesizes their input into a unified plan, then assigns work to department leads. Resolves cross-department conflicts. Reports progress and suggests next steps.

**Board Meeting Protocol:**
1. Receive task from founder
2. Launch board members in parallel (CTO for tech, PM for tasks, Marketing for brand)
3. Merge recommendations, resolve conflicts
4. Create tasks in Task Master via PM
5. Assign to department leads
6. Track and report

#### 2. cto-architect
| Field | Value |
|-------|-------|
| **Role** | CTO / Principal Architect (Board Member) |
| **Model** | opus |
| **Permission Mode** | default |
| **Tools** | Read, Write, Edit, Glob, Grep, Bash, WebSearch, Task |
| **Skills** | clean-architecture, clean-ddd-hexagonal, monorepo-architecture, microservices-patterns, api-security-best-practices, software-architecture, api-design-principles |
| **Can Delegate** | Yes (Task tool) |
| **Scope** | Entire monorepo |

Makes architecture decisions, writes technical plans, reviews cross-cutting concerns. Board member — consulted by CEO on technical aspects of every non-trivial task. Delegates implementation to department leads.

#### 3. hr-agent-factory
| Field | Value |
|-------|-------|
| **Role** | HR Director / Agent Factory |
| **Model** | opus |
| **Permission Mode** | default |
| **Tools** | Read, Write, Edit, Bash, Glob, Grep, Task, WebFetch, WebSearch |
| **Skills** | monorepo-management |
| **Can Delegate** | Yes (Task tool) |
| **Scope** | `.claude/` |

Creates, modifies, and retires agents. Has triple skill sourcing:
1. **Built-in catalog** — 200+ local skills listed in system prompt
2. **Glob/Grep** — scans `.claude/skills/` and plugin directories
3. **skills.sh** — online marketplace (35,800+ skills), installs via `npx skills add <owner/repo>`

---

### Department 2: Frontend Engineering

#### 3. frontend-lead
| Field | Value |
|-------|-------|
| **Role** | Senior Frontend Engineer / Tech Lead |
| **Model** | opus |
| **Tools** | Read, Write, Edit, Bash, Glob, Grep, Task |
| **Skills** | nextjs-senior-dev, nextjs-app-router-patterns, next-best-practices, react-best-practices, react-patterns, react-performance-optimization, typescript-strict-mode, cache-components, i18n-expert, vercel-deployment |
| **Can Delegate** | Yes — to ui-engineer, 3d-engineer |
| **Scope** | `admin/`, `frontend/` |

Owns Next.js 16 admin dashboard and public frontend. Feature-Sliced Design + Atomic Design. React Compiler (no manual memoization).

#### 4. ui-engineer
| Field | Value |
|-------|-------|
| **Role** | UI / Component Developer |
| **Model** | opus |
| **Tools** | Read, Write, Edit, Bash, Glob, Grep |
| **Skills** | tailwindcss-fundamentals-v4, tailwind-design-system, zustand-state-management, tanstack-query, framer-motion-animator, web-accessibility, frontend-design |
| **Can Delegate** | No |
| **Scope** | `admin/src/shared/`, `admin/src/widgets/`, `admin/src/entities/` |

Builds reusable Atomic Design components. Tailwind CSS 4, Zustand 5, TanStack Query v5, Motion 12, Lenis smooth scroll.

#### 5. 3d-engineer
| Field | Value |
|-------|-------|
| **Role** | Three.js / R3F Specialist |
| **Model** | opus |
| **Tools** | Read, Write, Edit, Bash, Glob, Grep |
| **Skills** | three-js, r3f-fundamentals, r3f-materials, react-performance-optimization |
| **Can Delegate** | No |
| **Scope** | `admin/src/3d/` |

Owns all 3D code: cyberpunk globe, particle effects, shaders. Three.js 0.174, R3F 9.1, Drei 10.7.

---

### Department 3: Backend Engineering

#### 6. backend-lead
| Field | Value |
|-------|-------|
| **Role** | Senior Backend Engineer / Tech Lead |
| **Model** | opus |
| **Tools** | Read, Write, Edit, Bash, Glob, Grep, Task |
| **Skills** | fastapi-expert, fastapi-clean-architecture, python-best-practices, python-async-patterns, sqlalchemy-orm, sqlalchemy-postgres, postgresql-expert, clean-architecture, clean-ddd-hexagonal, api-security-best-practices, api-design-principles, software-architecture, alembic, database-migration-management |
| **Can Delegate** | Yes — to backend-dev |
| **Scope** | `backend/` |

Owns FastAPI backend. Clean Architecture + DDD. Python 3.13, SQLAlchemy 2.0 async, PostgreSQL 17, Redis, Pydantic 2, JWT + TOTP 2FA, Argon2id.

#### 7. backend-dev
| Field | Value |
|-------|-------|
| **Role** | Backend Developer |
| **Model** | opus |
| **Tools** | Read, Write, Edit, Bash, Glob, Grep |
| **Skills** | fastapi, fastapi-validation, pydantic, python-async-patterns, redis-best-practices, caching-strategy, error-handling-patterns, logging-best-practices, alembic, api-design-principles |
| **Can Delegate** | No |
| **Scope** | `backend/src/` |

Implements features: API routes, use cases, repository implementations, Redis caching.

---

### Department 4: Mobile Engineering

#### 8. mobile-lead
| Field | Value |
|-------|-------|
| **Role** | Senior Flutter Engineer |
| **Model** | opus |
| **Tools** | Read, Write, Edit, Bash, Glob, Grep, Task |
| **Skills** | flutter-expert, senior-flutter, flutter-development, flutter-internationalization, revenuecat, mobile-security-coder, push-notification-setup, appstore-readiness |
| **Can Delegate** | Yes |
| **Scope** | `cybervpn_mobile/` |

Owns Flutter app. Riverpod 3.0, GoRouter 17, flutter_v2ray_plus (VPN engine), RevenueCat (IAP), Firebase, 41 locales.

---

### Department 5: DevOps / SRE

#### 9. devops-lead
| Field | Value |
|-------|-------|
| **Role** | Senior DevOps / SRE Engineer |
| **Model** | opus |
| **Tools** | Read, Write, Edit, Bash, Glob, Grep, Task |
| **Skills** | senior-devops, docker-expert, docker-compose-orchestration, deployment-pipeline-design, github-actions, prometheus-monitoring, secrets-management, cost-optimization, kubernetes-orchestration, monitoring-observability, cloud-cost-management |
| **Can Delegate** | Yes — to devops-engineer |
| **Scope** | `infra/`, `.github/` |

Owns infrastructure: Docker Compose (profiles), Caddy 2.9, PostgreSQL 17, Valkey/Redis, Prometheus + Grafana + AlertManager. CI/CD pipelines.

#### 10. devops-engineer
| Field | Value |
|-------|-------|
| **Role** | DevOps Engineer |
| **Model** | opus |
| **Tools** | Read, Write, Edit, Bash, Glob, Grep |
| **Skills** | docker, docker-containerization, devops, github-actions, dependency-management, monitoring-observability |
| **Can Delegate** | No |
| **Scope** | `infra/` |

Maintains Dockerfiles, Compose configs, Grafana dashboards, Prometheus alert rules, Caddy configs.

---

### Department 6: QA / Testing

#### 11. qa-lead
| Field | Value |
|-------|-------|
| **Role** | QA Lead / Test Architect |
| **Model** | opus |
| **Tools** | Read, Write, Edit, Bash, Glob, Grep, Task |
| **Skills** | playwright-expert, pytest, python-testing-patterns, webapp-testing, contract-test-validator |
| **Can Delegate** | Yes — to test-runner |
| **Scope** | All `tests/` directories |

Test strategy: pytest + pytest-asyncio (backend), Playwright (frontend E2E), flutter_test (mobile). Coverage target 80%+.

#### 12. test-runner
| Field | Value |
|-------|-------|
| **Role** | Test Engineer |
| **Model** | opus |
| **Tools** | Read, Write, Edit, Bash, Glob, Grep |
| **Skills** | pytest, python-testing-patterns |
| **Can Delegate** | No |
| **Scope** | `*/tests/` |

Writes individual test cases. Arrange-Act-Assert structure. Factory fixtures. Edge case testing.

---

### Department 7: Security

#### 13. security-engineer
| Field | Value |
|-------|-------|
| **Role** | Application Security Engineer |
| **Model** | opus |
| **Permission Mode** | plan (read-only — does NOT modify code) |
| **Tools** | Read, Glob, Grep, Bash, WebSearch |
| **Skills** | api-security-best-practices, api-security-hardening, api-authentication, reviewing-security, mobile-security-coder, secrets-management |
| **Can Delegate** | No |
| **Scope** | Entire monorepo (read-only) |

Security audits, vulnerability reviews, threat modeling. OWASP Top 10 compliance checks. Produces audit reports with severity ratings and remediation steps.

---

### Department 8: Product

#### 14. product-manager
| Field | Value |
|-------|-------|
| **Role** | Product Manager |
| **Model** | opus |
| **Tools** | Read, Write, Edit, Glob, Grep, Task, WebSearch |
| **Skills** | requirements-analysis, product-strategist, business-analyst, product-analytics, analytics-tracking |
| **Can Delegate** | Yes (via Task Master) |
| **Scope** | `.taskmaster/`, `docs/`, `plan/` |

PRDs, roadmap, task prioritization via Task Master. Tracks DAU, MAU, churn, conversion, NPS.

---

### Department 9: Marketing & Growth

#### 15. marketing-lead
| Field | Value |
|-------|-------|
| **Role** | Head of Marketing / Growth Lead |
| **Model** | opus |
| **Tools** | Read, Write, Edit, Glob, Grep, Task, WebSearch, WebFetch |
| **Skills** | marketing-strategy-pmm, marketing-demand-acquisition, marketing-cro, growth-marketer, brand-strategist, competitor-analysis, startup-metrics-framework, lead-research-assistant |
| **Can Delegate** | Yes — to content-writer, seo-specialist |
| **Scope** | `docs/` |

Go-to-market strategy, AARRR funnels, competitive analysis, CRO, brand positioning. Tracks CAC, LTV, MRR, churn.

#### 16. content-writer
| Field | Value |
|-------|-------|
| **Role** | Content Writer / Copywriter |
| **Model** | opus |
| **Tools** | Read, Write, Edit, Glob, Grep, WebSearch |
| **Skills** | copywriting, landing-page-copywriter, content-creator, seo-content-writer, email-marketing, social-media |
| **Can Delegate** | No |
| **Scope** | `docs/` |

Landing pages, email campaigns, social media, blog articles, app store descriptions. Cyberpunk brand voice.

#### 17. seo-specialist
| Field | Value |
|-------|-------|
| **Role** | SEO & ASO Specialist |
| **Model** | opus |
| **Tools** | Read, Write, Edit, Glob, Grep, WebSearch, WebFetch |
| **Skills** | seo, seo-audit, seo-content-writer, analytics-tracking, app-store-optimization |
| **Can Delegate** | No |
| **Scope** | `admin/`, `frontend/` |

Web SEO (generateMetadata, robots.ts, sitemap.ts, JSON-LD, hreflang for 27+ locales, Core Web Vitals). App Store Optimization for iOS/Android.

---

### Department 10: Design

#### 18. design-lead
| Field | Value |
|-------|-------|
| **Role** | UI/UX & Brand Designer |
| **Model** | opus |
| **Tools** | Read, Write, Edit, Glob, Grep, WebSearch |
| **Skills** | frontend-design, web-design-guidelines, brand-strategist, brand-designer, web-accessibility, accessibility-compliance, tailwind-design-system |
| **Can Delegate** | No |
| **Scope** | `admin/src/shared/`, `frontend/` |

Owns cyberpunk design system. Colors: neon-cyan (#00ffff), matrix-green (#00ff88), neon-pink (#ff00ff). Fonts: Orbitron + JetBrains Mono. WCAG 2.2 AA compliance. RTL support.

---

### Department 11: Localization

#### 19. i18n-manager
| Field | Value |
|-------|-------|
| **Role** | Localization Manager |
| **Model** | opus |
| **Tools** | Read, Write, Edit, Bash, Glob, Grep, WebSearch |
| **Skills** | i18n-localization, internationalization-i18n, flutter-internationalization, i18n-expert |
| **Can Delegate** | No |
| **Scope** | `admin/messages/`, `cybervpn_mobile/lib/l10n/`, `admin/src/i18n/` |

Manages 41 locales across 3 platforms:
- **Next.js:** next-intl 4.7, JSON message files
- **Flutter:** intl + ARB files
- **Telegram Bot:** fluent.runtime, FTL files

RTL support: ar-SA, he-IL, fa-IR, ur-PK, ku-IQ.

---

### Department 12: Services

#### 20. telegram-bot-dev
| Field | Value |
|-------|-------|
| **Role** | Telegram Bot Developer |
| **Model** | opus |
| **Tools** | Read, Write, Edit, Bash, Glob, Grep |
| **Skills** | telegram-bot-builder, telegram-dev, python-async-patterns, python-best-practices, webhook-integration |
| **Can Delegate** | No |
| **Scope** | `services/telegram-bot/` |

Owns Telegram bot (aiogram 3). VPN subscription management, CryptoBot payments, QR code generation, multi-language support.

#### 21. task-worker-dev
| Field | Value |
|-------|-------|
| **Role** | Background Jobs Developer |
| **Model** | opus |
| **Tools** | Read, Write, Edit, Bash, Glob, Grep |
| **Skills** | python-background-jobs, background-job-processing, event-driven, async-python-patterns, resilience-patterns, concurrency-patterns |
| **Can Delegate** | No |
| **Scope** | `services/task-worker/` |

Owns TaskIQ worker. Jobs: subscription expiration, notifications, analytics aggregation, data cleanup, payment webhooks. Prometheus metrics on port 9091.

---

### Department 13: Finance

#### 22. finance-strategist
| Field | Value |
|-------|-------|
| **Role** | Finance & Monetization Strategist |
| **Model** | opus |
| **Permission Mode** | plan (advisory, read-only) |
| **Tools** | Read, Write, Edit, Glob, Grep, WebSearch, WebFetch |
| **Skills** | pricing-strategy, startup-metrics-framework, startup-business-models, indie-monetization-strategist, gtm-pricing, payment-gateway-integration, referral-program, xlsx, stripe-integration, cloud-cost-management |
| **Can Delegate** | No |
| **Scope** | `docs/`, `plan/` |

Pricing tiers, unit economics (CAC, LTV, payback), payment flow optimization (CryptoBot vs RevenueCat vs direct), regional pricing for 27+ markets, financial projections.

### Department 14: Legal & Compliance

#### 23. dpo-officer
| Field | Value |
|-------|-------|
| **Role** | Data Protection Officer |
| **Model** | opus |
| **Permission Mode** | plan (read-only, audits only) |
| **Tools** | Read, Glob, Grep, WebSearch, WebFetch |
| **Skills** | gdpr-data-handling, gdpr-dsgvo-expert, data-privacy-compliance, security-compliance-audit, compliance-auditor, compliance-architecture, reviewing-security, api-security-best-practices |
| **Can Delegate** | No |
| **Scope** | Весь монорепо (read-only) |

GDPR compliance, DPIA assessments, privacy-by-design reviews, data processing audits, no-log policy verification, regulatory monitoring (GDPR, CCPA, LGPD, PIPEDA).

#### 24. abuse-handler
| Field | Value |
|-------|-------|
| **Role** | Abuse & Legal Compliance Handler |
| **Model** | opus |
| **Tools** | Read, Write, Edit, Glob, Grep, WebSearch, WebFetch |
| **Skills** | stride-analysis-patterns, reviewing-security, api-security-best-practices, compliance-architecture, security-compliance-audit |
| **Can Delegate** | No |
| **Scope** | `docs/legal/`, `docs/compliance/` |

DMCA takedowns, abuse report processing, hosting provider coordination, AUP enforcement, IP blacklist/delisting, law enforcement request handling, transparency reports.

#### 28. security-audit-coordinator
| Field | Value |
|-------|-------|
| **Role** | Security Audit Coordinator |
| **Model** | opus |
| **Tools** | Read, Write, Edit, Glob, Grep, WebSearch, WebFetch |
| **Skills** | senior-security, security-compliance, security-auditor, penetration-testing, security-compliance-audit, reviewing-security, api-security-best-practices, api-security-hardening, stride-analysis-patterns |
| **Can Delegate** | No |
| **Scope** | `docs/security/` |

Координация внешних аудитов (no-logs, pentest, SOC 2 Type II), управление remediation tracker, сертификация ISO 27001, vendor risk assessments.

#### 29. compliance-officer
| Field | Value |
|-------|-------|
| **Role** | Compliance Officer |
| **Model** | opus |
| **Tools** | Read, Write, Edit, Glob, Grep, WebSearch, WebFetch |
| **Skills** | learning-regional-compliance, security-compliance, compliance-architecture, compliance-auditor, security-compliance-audit, gdpr-data-handling, reviewing-security |
| **Can Delegate** | No |
| **Scope** | `docs/compliance/`, `docs/legal/` |

Юрисдикционная стратегия (Panama/BVI/Switzerland), GDPR/CCPA/LGPD, intelligence alliance awareness (Five/Nine/Fourteen Eyes), ToS/Privacy Policy, warrant canary, sanctions compliance (OFAC).

### Department 16: Customer Success

#### 30. customer-success-agent
| Field | Value |
|-------|-------|
| **Role** | Customer Success & VPN Support Agent |
| **Model** | opus |
| **Tools** | Read, Write, Edit, Glob, Grep, WebSearch, WebFetch |
| **Skills** | customer-support, customer-support-builder, copywriting, error-handling-patterns, networking, network-diagnostics |
| **Can Delegate** | No |
| **Scope** | `docs/support/`, `docs/faq/` |

VPN-специфичный troubleshooting (протоколы, DNS/IP leaks, platform issues), knowledge base, support bot flows, onboarding, churn reduction стратегии.

### Department 17: VPN Operations

#### 25. infrastructure-engineer
| Field | Value |
|-------|-------|
| **Role** | Infrastructure & Network Engineer |
| **Model** | opus |
| **Tools** | Read, Write, Edit, Bash, Glob, Grep, WebSearch, WebFetch, Task |
| **Skills** | server-management, terraform-engineer, terraform-infrastructure, network-engineer, networking, docker-compose-networking, network-diagnostics, senior-devops, docker-expert, docker-compose-orchestration, prometheus-monitoring, cost-optimization, secrets-management, kubernetes-orchestration, monitoring-observability, cloud-cost-management, monitoring-expert |
| **Can Delegate** | Yes (has Task tool) |
| **Scope** | `infra/`, `infra/terraform/`, `infra/ansible/`, `infra/monitoring/` |

600+ VPN servers across 40+ countries, Terraform + Ansible provisioning, IP rotation, BGP/peering, capacity planning, server fleet monitoring, hosting provider management.

#### 26. payments-specialist
| Field | Value |
|-------|-------|
| **Role** | Payments & Revenue Operations Specialist |
| **Model** | opus |
| **Tools** | Read, Write, Edit, Bash, Glob, Grep, WebSearch, WebFetch |
| **Skills** | pci-compliance, stripe-integration, payment-integration, payment-gateway-integration, reviewing-security, api-security-best-practices, webhook-integration |
| **Can Delegate** | No |
| **Scope** | `backend/src/payments/`, `backend/src/subscriptions/`, `services/telegram-bot/payments/` |

CryptoBot crypto payments, RevenueCat IAP management, high-risk merchant account management, chargeback prevention (<1%), PCI DSS compliance, anti-fraud measures, regional payment strategies.

#### 27. protocol-engineer
| Field | Value |
|-------|-------|
| **Role** | VPN Protocol Engineer |
| **Model** | opus |
| **Tools** | Read, Write, Edit, Bash, Glob, Grep, WebSearch, WebFetch |
| **Skills** | cryptography, data-encryption, zero-trust-architecture, protocol-reverse-engineering, reviewing-security, api-security-best-practices, api-security-hardening, python-async-patterns, python-best-practices |
| **Can Delegate** | No |
| **Scope** | `backend/src/vpn/`, `cybervpn_mobile/lib/vpn/`, `infra/wireguard/`, `infra/openvpn/` |

WireGuard (primary), OpenVPN (fallback), IKEv2/IPSec (mobile), post-quantum cryptography roadmap (ML-KEM/Kyber), protocol obfuscation (obfs4, Shadowsocks, V2Ray), DNS security (DoH/DoT), kill switch implementation.

#### 31. noc-agent
| Field | Value |
|-------|-------|
| **Role** | Network Operations Center (NOC) Agent |
| **Model** | opus |
| **Tools** | Read, Write, Edit, Bash, Glob, Grep, WebSearch, WebFetch |
| **Skills** | observability-engineer, observability-monitoring, incident-response-incident-response, site-reliability-engineer, prometheus-monitoring, senior-devops, network-engineer, network-diagnostics, networking, distributed-tracing, application-logging, logging-best-practices, monitoring-observability, monitoring-expert, kubernetes-orchestration |
| **Can Delegate** | No |
| **Scope** | `infra/monitoring/`, `infra/grafana/`, `infra/prometheus/`, `infra/alerting/` |

24/7 мониторинг (Prometheus + Grafana), автоматический failover, alerting (P0-P3), latency optimization, incident response процедуры, SLA management (99.9% uptime), capacity planning dashboards.

---

## Skills Catalog (by Category)

### Frontend / React / Next.js (18 skills)
| Skill | Used By |
|-------|---------|
| nextjs-senior-dev | frontend-lead |
| nextjs-app-router-patterns | frontend-lead |
| next-best-practices | frontend-lead |
| react-best-practices | frontend-lead |
| react-patterns | frontend-lead |
| react-performance-optimization | frontend-lead, 3d-engineer |
| typescript-strict-mode | frontend-lead |
| cache-components | frontend-lead |
| i18n-expert | frontend-lead, i18n-manager |
| vercel-deployment | frontend-lead |
| tailwindcss-fundamentals-v4 | ui-engineer |
| tailwind-design-system | ui-engineer, design-lead |
| zustand-state-management | ui-engineer |
| tanstack-query | ui-engineer |
| framer-motion-animator | ui-engineer |
| frontend-design | ui-engineer, design-lead |
| web-accessibility | ui-engineer, design-lead |
| web-design-guidelines | design-lead |

### 3D / WebGL (3 skills)
| Skill | Used By |
|-------|---------|
| three-js | 3d-engineer |
| r3f-fundamentals | 3d-engineer |
| r3f-materials | 3d-engineer |

### Backend / Python / FastAPI (20 skills)
| Skill | Used By |
|-------|---------|
| fastapi-expert | backend-lead, performance-engineer |
| fastapi-clean-architecture | backend-lead |
| fastapi | backend-dev |
| fastapi-validation | backend-dev |
| python-best-practices | backend-lead, telegram-bot-dev, protocol-engineer |
| python-async-patterns | backend-lead, backend-dev, telegram-bot-dev, protocol-engineer |
| pydantic | backend-dev |
| sqlalchemy-orm | backend-lead |
| sqlalchemy-postgres | backend-lead |
| postgresql-expert | backend-lead |
| redis-best-practices | backend-dev |
| caching-strategy | backend-dev |
| error-handling-patterns | backend-dev, customer-success-agent |
| logging-best-practices | backend-dev, noc-agent |
| async-python-patterns | task-worker-dev |
| python-background-jobs | task-worker-dev |
| alembic | backend-lead, backend-dev |
| api-design-principles | cto-architect, backend-lead, backend-dev |
| database-migration-management | backend-lead |
| software-architecture | cto-architect, backend-lead |

### Architecture (7 skills)
| Skill | Used By |
|-------|---------|
| clean-architecture | cto-architect, backend-lead |
| clean-ddd-hexagonal | cto-architect, backend-lead |
| monorepo-architecture | cto-architect |
| microservices-patterns | cto-architect |
| monorepo-management | hr-agent-factory |
| software-architecture | cto-architect, backend-lead |
| api-design-principles | cto-architect, backend-lead, backend-dev |

### Mobile / Flutter (8 skills)
| Skill | Used By |
|-------|---------|
| flutter-expert | mobile-lead |
| senior-flutter | mobile-lead |
| flutter-development | mobile-lead |
| flutter-internationalization | mobile-lead, i18n-manager |
| revenuecat | mobile-lead |
| mobile-security-coder | mobile-lead, security-engineer |
| push-notification-setup | mobile-lead |
| appstore-readiness | mobile-lead |

### DevOps / Infrastructure (23 skills)
| Skill | Used By |
|-------|---------|
| senior-devops | devops-lead, infrastructure-engineer, noc-agent |
| docker-expert | devops-lead, infrastructure-engineer |
| docker-compose-orchestration | devops-lead, infrastructure-engineer |
| docker | devops-engineer |
| docker-containerization | devops-engineer |
| devops | devops-engineer |
| deployment-pipeline-design | devops-lead |
| github-actions | devops-lead, devops-engineer |
| prometheus-monitoring | devops-lead, infrastructure-engineer, noc-agent |
| dependency-management | devops-engineer |
| server-management | infrastructure-engineer |
| terraform-engineer | infrastructure-engineer |
| terraform-infrastructure | infrastructure-engineer |
| network-engineer | infrastructure-engineer, noc-agent |
| networking | infrastructure-engineer, noc-agent, customer-success-agent |
| docker-compose-networking | infrastructure-engineer |
| network-diagnostics | infrastructure-engineer, noc-agent, customer-success-agent |
| kubernetes-orchestration | devops-lead, infrastructure-engineer, noc-agent |
| monitoring-observability | devops-engineer, devops-lead, infrastructure-engineer, noc-agent |
| monitoring-expert | infrastructure-engineer, noc-agent |
| cloud-cost-management | devops-lead, finance-strategist, infrastructure-engineer |
| cost-optimization | devops-lead, infrastructure-engineer |
| secrets-management | devops-lead, security-engineer, infrastructure-engineer |

### Security & Compliance (18 skills)
| Skill | Used By |
|-------|---------|
| api-security-best-practices | cto-architect, backend-lead, security-engineer, dpo-officer, abuse-handler, payments-specialist, protocol-engineer, security-audit-coordinator |
| api-security-hardening | security-engineer, protocol-engineer, security-audit-coordinator |
| api-authentication | security-engineer |
| reviewing-security | security-engineer, dpo-officer, abuse-handler, payments-specialist, protocol-engineer, compliance-officer, security-audit-coordinator |
| gdpr-data-handling | dpo-officer, compliance-officer |
| gdpr-dsgvo-expert | dpo-officer |
| data-privacy-compliance | dpo-officer |
| security-compliance-audit | dpo-officer, abuse-handler, compliance-officer, security-audit-coordinator |
| compliance-auditor | dpo-officer, compliance-officer |
| compliance-architecture | dpo-officer, abuse-handler, compliance-officer |
| stride-analysis-patterns | abuse-handler, security-audit-coordinator |
| pci-compliance | payments-specialist |
| senior-security | security-audit-coordinator |
| security-compliance | security-audit-coordinator, compliance-officer |
| security-auditor | security-audit-coordinator |
| penetration-testing | security-audit-coordinator |
| learning-regional-compliance | compliance-officer |
| mobile-security-coder | mobile-lead, security-engineer |

### Cryptography & Protocols (4 skills)
| Skill | Used By |
|-------|---------|
| cryptography | protocol-engineer |
| data-encryption | protocol-engineer |
| zero-trust-architecture | protocol-engineer |
| protocol-reverse-engineering | protocol-engineer |

### Payments (5 skills)
| Skill | Used By |
|-------|---------|
| stripe-integration | payments-specialist, finance-strategist |
| payment-integration | payments-specialist |
| payment-gateway-integration | payments-specialist, finance-strategist |
| webhook-integration | telegram-bot-dev, payments-specialist |
| revenuecat | mobile-lead |

### Testing / QA (5 skills)
| Skill | Used By |
|-------|---------|
| playwright-expert | qa-lead |
| pytest | qa-lead, test-runner |
| python-testing-patterns | qa-lead, test-runner |
| webapp-testing | qa-lead |
| contract-test-validator | qa-lead |

### Marketing / Growth (8 skills)
| Skill | Used By |
|-------|---------|
| marketing-strategy-pmm | marketing-lead |
| marketing-demand-acquisition | marketing-lead |
| marketing-cro | marketing-lead |
| growth-marketer | marketing-lead |
| brand-strategist | marketing-lead, design-lead |
| competitor-analysis | marketing-lead |
| startup-metrics-framework | marketing-lead, finance-strategist |
| lead-research-assistant | marketing-lead |

### Content / Copy (6 skills)
| Skill | Used By |
|-------|---------|
| copywriting | content-writer |
| landing-page-copywriter | content-writer |
| content-creator | content-writer |
| seo-content-writer | content-writer, seo-specialist |
| email-marketing | content-writer |
| social-media | content-writer |

### SEO / Analytics (4 skills)
| Skill | Used By |
|-------|---------|
| seo | seo-specialist |
| seo-audit | seo-specialist |
| analytics-tracking | product-manager, seo-specialist |
| app-store-optimization | seo-specialist |

### Product / Business (5 skills)
| Skill | Used By |
|-------|---------|
| requirements-analysis | product-manager |
| product-strategist | product-manager |
| business-analyst | product-manager |
| product-analytics | product-manager |
| accessibility-compliance | design-lead |

### Finance / Monetization (8 skills)
| Skill | Used By |
|-------|---------|
| pricing-strategy | finance-strategist |
| startup-business-models | finance-strategist |
| indie-monetization-strategist | finance-strategist |
| gtm-pricing | finance-strategist |
| payment-gateway-integration | finance-strategist, payments-specialist |
| referral-program | finance-strategist |
| xlsx | finance-strategist |
| cloud-cost-management | finance-strategist, devops-lead, infrastructure-engineer |

### Localization / i18n (4 skills)
| Skill | Used By |
|-------|---------|
| i18n-localization | i18n-manager |
| internationalization-i18n | i18n-manager |
| flutter-internationalization | i18n-manager, mobile-lead |
| i18n-expert | frontend-lead, i18n-manager |

### Communication / Bots (3 skills)
| Skill | Used By |
|-------|---------|
| telegram-bot-builder | telegram-bot-dev |
| telegram-dev | telegram-bot-dev |
| webhook-integration | telegram-bot-dev |

### Background Processing (4 skills)
| Skill | Used By |
|-------|---------|
| background-job-processing | task-worker-dev |
| event-driven | task-worker-dev |
| resilience-patterns | task-worker-dev |
| concurrency-patterns | task-worker-dev |

### Observability / SRE (7 skills)
| Skill | Used By |
|-------|---------|
| observability-engineer | noc-agent |
| observability-monitoring | noc-agent |
| monitoring-observability | devops-engineer, devops-lead, infrastructure-engineer, noc-agent |
| monitoring-expert | infrastructure-engineer, noc-agent |
| incident-response-incident-response | noc-agent |
| site-reliability-engineer | noc-agent |
| distributed-tracing | noc-agent |

### Customer Support (3 skills)
| Skill | Used By |
|-------|---------|
| customer-support | customer-success-agent |
| customer-support-builder | customer-success-agent |
| copywriting | content-writer, customer-success-agent |

---

## Statistics

| Metric | Value |
|--------|-------|
| Total agents | 33 |
| Departments | 17 |
| Model | All opus |
| Unique skills assigned | 163 |
| Skills installed (total) | 208 |
| Skills categories | 23 |
| Agents with Task (delegation) | 11 |
| Read-only agents (plan mode) | 2 |
| Agents with WebSearch | 18 |
| Agents with WebFetch | 14 |

---

## Agent Capabilities Matrix

| Agent | Write Code | Delegate | Web Research | Advisory Only |
|-------|:---:|:---:|:---:|:---:|
| ceo-orchestrator | + | + | + | - |
| cto-architect | + | + | + | - |
| hr-agent-factory | + | + | + | - |
| frontend-lead | + | + | - | - |
| ui-engineer | + | - | - | - |
| 3d-engineer | + | - | - | - |
| backend-lead | + | + | - | - |
| backend-dev | + | - | - | - |
| mobile-lead | + | + | - | - |
| devops-lead | + | + | - | - |
| devops-engineer | + | - | - | - |
| qa-lead | + | + | - | - |
| test-runner | + | - | - | - |
| security-engineer | - | - | + | + |
| product-manager | + | + | + | - |
| marketing-lead | + | + | + | - |
| content-writer | + | - | + | - |
| seo-specialist | + | - | + | - |
| design-lead | + | - | + | - |
| i18n-manager | + | - | + | - |
| telegram-bot-dev | + | - | - | - |
| task-worker-dev | + | - | - | - |
| finance-strategist | - | - | + | + |
| dpo-officer | - | - | + | + |
| abuse-handler | + | - | + | - |
| infrastructure-engineer | + | + | + | - |
| payments-specialist | + | - | + | - |
| protocol-engineer | + | - | + | - |
| security-audit-coordinator | + | - | + | - |
| compliance-officer | + | - | + | - |
| customer-success-agent | + | - | + | - |
| noc-agent | + | - | + | - |

---

## Conflict Resolution Protocol

When departments disagree (Marketing vs Finance on pricing, CTO vs PM on scope, Security vs Backend, etc.), the company follows a strict 4-step protocol:

### Step 1: Document Positions with Data
Each side presents their position backed by **evidence** — metrics, benchmarks, user data, market research, technical constraints. No opinion-only arguments.

### Step 2: Joint Escalation (NOT Separate)
Conflicting parties escalate **together** to the CEO. Both sides must be present simultaneously. No behind-the-back lobbying — CEO hears both perspectives at once.

### Step 3: CEO Recommends → Founder Decides
CEO-Orchestrator analyzes both sides, prepares a **recommendation** with trade-offs, and presents to the **Founder (you)**. The Founder makes the final call. CEO may resolve minor operational conflicts autonomously (code style, tooling).

### Step 4: Communicate Result & Rationale
After the Founder decides:
1. Decision stated clearly
2. **Rationale** explained — why this option won
3. Losing side's valid points acknowledged
4. Communicated to **ALL affected departments**, not just the parties
5. Logged in task/plan for future reference

### Common Conflict Scenarios

| Conflict | Resolution |
|----------|-----------|
| Marketing wants big discount, Finance says margins thin | Joint data → CFO models impact → CEO decides |
| CTO says refactor first, PM says ship now | Both present timeline + risk → CEO decides on urgency |
| Security blocks feature, Backend wants to ship | Security presents risk, Backend presents value → CEO + DPO decide |
| Design wants pixel-perfect, Frontend says perf hit | Design UX data vs Frontend perf data → CTO mediates → CEO approves |
| Infrastructure wants premium servers, Finance wants budget | Infra presents needs, Finance presents budget → CEO + NOC data decide |

---

## How to Use

### Standard workflow (recommended)
```
Use the ceo-orchestrator: "Add a referral system where users invite friends and get free days"
```
CEO will convene the board, decompose the task, assign to departments, and report back.

### Direct task to a department
```
Use the backend-lead agent to implement a new API endpoint for user profiles.
```

### Board consultation only
```
Use the cto-architect to assess the technical impact of migrating to Kubernetes.
```

### Hire a new employee
```
Use the hr-agent-factory to hire a Kubernetes specialist for production deployment.
```

### Security audit
```
Use the security-engineer to audit the authentication system in backend/.
```

### Parallel work
Multiple agents can work simultaneously on different areas of the codebase without conflicts.

---

## File Locations

| Path | Description |
|------|-------------|
| `.claude/agents/*.md` | Agent configuration files (22 files) |
| `.claude/skills/` | Project-specific skills |
| `.claude/commands/tm/` | Task Master slash commands |
| `.taskmaster/tasks/tasks.json` | Task database |
| `.taskmaster/docs/` | PRDs and requirements |
| `docs/virtual-company.md` | This file |
