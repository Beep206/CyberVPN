# CyberVPN Storefront, Identity, And Access Model Spec

**Date:** 2026-04-17  
**Status:** Domain specification  
**Purpose:** define the canonical model for brands, storefronts, auth realms, principals, sessions, scopes, and access boundaries across official CyberVPN surfaces, partner storefronts, partner workspaces, admin surfaces, and service integrations.

---

## 1. Document Role

This document defines the platform model for:

- brands and storefronts;
- auth realms and principal classes;
- login, session, and realm isolation;
- partner organizations and workspace access;
- token scopes and access control.

---

## 2. Core Entities

Required entities:

- `brands`
- `storefronts`
- `storefront_domains`
- `auth_realms`
- `merchant_profiles`
- `support_profiles`
- `communication_profiles`
- `storefront_legal_doc_sets`
- `customer_accounts`
- `partner_accounts`
- `partner_account_users`
- `partner_account_roles`
- `admin_accounts`
- `service_principals`

---

## 3. Principal Classes

The platform supports:

- `customer`
- `partner_operator`
- `admin`
- `service`

No principal class should be overloaded to simulate another.

---

## 4. Realm Rules

Canonical rules:

- every account belongs to exactly one `auth_realm_id`;
- every account stores `origin_storefront_id`;
- login and registration resolve realm by host or explicit realm context;
- the same email may exist across different realms;
- cross-realm automatic login is prohibited;
- tokens must encode principal type and realm audience.

---

## 5. Storefront Rules

Storefronts are public-facing sales or self-service surfaces.

They resolve:

- brand identity;
- merchant profile;
- support profile;
- communication profile;
- legal documents;
- pricebook and offer policy;
- auth realm.

Partner storefronts must remain isolated from official CyberVPN customer web sessions.

---

## 6. Session And Token Rules

The platform requires:

- customer session tokens;
- partner operator session tokens;
- admin session tokens;
- service tokens.

Each token class must be scoped and audience-bound.

Cookie rules:

- cookie names and domains are realm-aware;
- partner storefront sessions must not silently reuse CyberVPN official cookies;
- realm-specific logout must not overreach into other realms.

---

## 7. RBAC And Scope Rules

The access model must support:

- role-based access control;
- explicit permissions;
- explicit scopes for API tokens;
- row-level visibility enforcement on the server.

Partner workspace roles should support, at minimum:

- owner
- finance
- analyst
- traffic manager
- support manager

Admin role families should support, at minimum:

- support
- finance ops
- fraud/risk
- platform admin

---

## 8. Cross-Channel Access Rules

Channel classes:

- official web frontend;
- partner storefronts;
- partner portal;
- Telegram Bot;
- Telegram Mini App;
- mobile apps;
- desktop apps.

Each channel must respect:

- realm-aware login;
- entitlement-driven access;
- support-context resolution;
- surface-specific policy rules.

---

## 9. Acceptance Conditions

The identity and access model is acceptable only when:

- realm isolation is enforceable;
- the same person may have separate accounts across realms without accidental crossover;
- partner operators are organization users, not only promoted customers;
- all major surface families can authenticate and authorize through the same conceptual model.
