# PRD: CyberVPN Mobile App — Internationalization Completion

**Document Version:** 1.0
**Date:** 2026-02-06
**Author:** Engineering Team
**Status:** Draft
**Priority:** P1 — High

---

## 1. Executive Summary

The CyberVPN mobile app (Flutter) has internationalization (i18n) infrastructure in place — `gen-l10n`, 27 supported locales, ARB files, generated Dart classes, RTL handling — but the actual adoption is critically low. **Only 4 out of ~305 Dart files** use `AppLocalizations`. An estimated **574+ user-visible strings** remain hardcoded in English across the UI layer. Additionally, **4 locales are 82% incomplete** (cs, da, sv, zh_Hant), **20 locales contain English placeholder text** instead of real translations, and **plural forms have CLDR compliance issues** in ru, pl, uk, and cs.

This PRD defines the work required to bring the mobile app to production-grade multilingual quality.

---

## 2. Problem Statement

### 2.1 Current State

| Metric | Value |
|--------|-------|
| Supported locales | 27 (incl. 3 RTL: ar, he, fa) |
| Template keys (app_en.arb) | 275 |
| Files using `AppLocalizations` | 4 out of ~305 |
| Hardcoded user-visible strings | ~574+ |
| Locales with real translations | 3 (ru, ar, fa) + partial he |
| Locales with English placeholders only | 20 (de, es, fr, hi, id, it, ja, ko, ms, nl, pl, pt, ro, th, tr, uk, vi, zh + partial he) |
| Severely incomplete locales (82% missing) | 4 (cs, da, sv, zh_Hant) |
| Missing keys across most locales | 14 (biometric/Telegram error strings) |
| Plural form CLDR violations | 4 locales (ru, pl, uk, cs) |

### 2.2 User Impact

- **Non-English users see English UI** — despite selecting their language in Settings, nearly all screens remain in English because `AppLocalizations` is not wired into the widgets.
- **Czech, Danish, Swedish, Traditional Chinese users** see English fallback for 82% of all messages, even for keys that exist in the ARB file.
- **Russian users** see incorrect plural forms for numbers like 21, 31, 101 (e.g., "21 дней" instead of "21 день") due to `=1{}` vs `one{}` misuse.
- **Polish & Ukrainian users** see English text for all plural-containing messages (completely untranslated).
- **App Store localization** is broken — the app claims 27-language support but delivers English.

### 2.3 Business Impact

- Potential app store rejection or low ratings in non-English markets.
- VPN users in censored regions (Iran, China, Russia) — the app's primary target — cannot use the app in their native language despite it being "supported."
- Competitive disadvantage vs. VPN apps with proper localization.

---

## 3. Goals & Success Criteria

### 3.1 Goals

1. **Wire all UI screens to `AppLocalizations`** — replace 574+ hardcoded strings.
2. **Complete all 27 locale ARB files** — 275 keys per locale, properly translated.
3. **Fix plural form compliance** — proper CLDR categories for all languages.
4. **Add missing keys** — 14 biometric/Telegram keys + 3 root detection keys.
5. **Establish guardrails** — lint rules, CI checks to prevent i18n regression.

### 3.2 Success Criteria

| Criteria | Target |
|----------|--------|
| `AppLocalizations` usage | 100% of user-visible strings |
| ARB key coverage per locale | 275/275 (100%) |
| Locales with real translations | 27/27 |
| Hardcoded English strings in UI | 0 |
| CLDR plural compliance | 100% |
| CI coverage check passing | Green |

---

## 4. Detailed Analysis

### 4.1 Locale Coverage Matrix

#### Tier 1 — Near-Complete (Real Translations)

| Locale | Keys | Missing | Untranslated | Plural Quality |
|--------|------|---------|-------------|---------------|
| ru (Russian) | 272/275 | 3 | 2 | `=1{}` bug |
| ar (Arabic) | 258/275 | 17 | 0 | Excellent |
| fa (Farsi) | 258/275 | 17 | 0 | Good |
| he (Hebrew) | 258/275 | 17 | ~5 | Good |

#### Tier 2 — Structure Present, English Placeholders

| Locale | Keys | Missing | Untranslated (English) |
|--------|------|---------|----------------------|
| de (German) | 261/275 | 14 | ~253 |
| es (Spanish) | 261/275 | 14 | ~253 |
| fr (French) | 261/275 | 14 | ~253 |
| pt (Portuguese) | 261/275 | 14 | ~260 |
| it (Italian) | 261/275 | 14 | ~260 |
| ja (Japanese) | 261/275 | 14 | ~253 |
| ko (Korean) | 261/275 | 14 | ~253 |
| zh (Chinese Simplified) | 261/275 | 14 | ~253 |
| tr (Turkish) | 261/275 | 14 | ~253 |
| nl (Dutch) | 261/275 | 14 | ~260 |
| pl (Polish) | 261/275 | 14 | ~260 |
| uk (Ukrainian) | 261/275 | 14 | ~260 |
| hi (Hindi) | 261/275 | 14 | ~260 |
| th (Thai) | 261/275 | 14 | ~260 |
| vi (Vietnamese) | 261/275 | 14 | ~260 |
| id (Indonesian) | 261/275 | 14 | ~260 |
| ms (Malay) | 261/275 | 14 | ~260 |
| ro (Romanian) | 261/275 | 14 | ~260 |

#### Tier 3 — Severely Incomplete (Stubs)

| Locale | Keys | Missing | Notes |
|--------|------|---------|-------|
| cs (Czech) | 50/275 | 225 | Only base keys, all English |
| da (Danish) | 50/275 | 225 | Only base keys, all English |
| sv (Swedish) | 50/275 | 225 | Only base keys, all English |
| zh_Hant (Trad. Chinese) | 50/275 | 225 | Only base keys, all English |

### 4.2 Missing Keys (14 keys absent from most locales)

These keys exist in `app_en.arb` but are missing from non-English ARB files:

```
errorTelegramAuthCancelled
errorTelegramAuthFailed
errorTelegramAuthExpired
errorTelegramNotInstalled
errorTelegramAuthInvalid
errorBiometricUnavailable
errorBiometricNotEnrolled
errorBiometricFailed
errorBiometricLocked
errorSessionExpired
errorAccountDisabled
errorRateLimitedWithCountdown    (plural)
errorOfflineLoginRequired
errorOfflineSessionExpired
```

**3 additional keys** missing from ar, fa, he, ru:
```
rootDetectionDialogTitle
rootDetectionDialogDescription
rootDetectionDialogDismiss
```

### 4.3 Plural Form Issues

| Locale | Issue | Severity |
|--------|-------|----------|
| **ru** | Uses `=1{...}` instead of `one{...}` in all 8 plural messages. Causes incorrect forms for 21, 31, 101, etc. | P1 |
| **pl** | All 7 plural messages are English copies. Needs `one/few/many/other` forms. | P0 |
| **uk** | All 7 plural messages are English copies. Needs `one/few/many/other` forms. | P0 |
| **cs** | `daysRemaining` is English copy. Needs `one/few/many/other` forms. Only 1 plural message exists (file is a stub). | P0 |
| **de, es** | Correctly use `one/other` for their small set of translated plurals. Remaining plurals are English copies. | P1 |
| **ar** | Excellent — uses all 6 CLDR categories (`zero/one/two/few/many/other`). | OK |
| **fa** | Correct — uses `one/other` (Farsi plural rules). | OK |

### 4.4 Hardcoded Strings by Feature Area

| Feature Area | Hardcoded Strings | Files Affected |
|-------------|-------------------|----------------|
| `features/settings/` | ~60 | 8+ screens |
| `features/profile/` | ~49 | 6+ screens |
| `features/config_import/` | ~39 | 4+ screens |
| `features/auth/` | ~23 | 5+ screens |
| `features/subscription/` | ~19 | 3+ screens |
| `features/onboarding/` | ~8 | 2 screens |
| `features/servers/` | ~7 | 2 screens |
| `features/notifications/` | ~5 | 2 screens |
| `features/referral/` | ~4 | 1 screen |
| `features/diagnostics/` | ~4 | 2 screens |
| `shared/widgets/` | ~4 | 3 widgets |
| Providers/Services | ~20 | 5+ files |
| **Total** | **~574+** | **~39 files** |

**Worst offending files:**
- `features/auth/presentation/screens/register_screen.dart` — 12+ hardcoded strings
- `features/auth/presentation/screens/biometric_settings_screen.dart` — 10+ hardcoded strings
- `features/config_import/presentation/screens/import_list_screen.dart` — 7+ hardcoded strings
- `features/subscription/presentation/screens/purchase_screen.dart` — 8+ hardcoded strings
- `features/subscription/presentation/screens/plans_screen.dart` — 6+ hardcoded strings

### 4.5 Infrastructure Assessment

| Component | Status | Notes |
|-----------|--------|-------|
| `l10n.yaml` config | OK | Properly configured |
| `gen-l10n` code generation | OK | Generates `AppLocalizations` + per-locale classes |
| `nullable-getter: false` | OK | Prevents null-check boilerplate |
| `MaterialApp` delegates | OK | All 4 delegates wired correctly |
| `supportedLocales` | OK | Uses `AppLocalizations.supportedLocales` |
| RTL handling | OK | `Directionality` widget in `app.dart` based on `LocaleConfig.isRtl()` |
| Locale persistence | OK | `SettingsProvider` → `SharedPreferences` |
| `context.l10n` extension | OK | Defined in `context_extensions.dart` — but unused by most screens |
| `@description` metadata on keys | MISSING | No ARB keys have `@key.description` entries (except `@@comment`) |
| CI/lint i18n checks | MISSING | No automation to detect hardcoded strings or missing keys |

---

## 5. Scope & Phases

### Phase 1: Foundation & Critical Fixes (Week 1-2)

**Objective:** Fix broken plural forms, complete stub locales, add missing keys.

#### 5.1.1 Fix Plural Form CLDR Compliance

- **ru**: Replace `=1{...}` with `one{...}` in all 8 plural messages. Ensure `few` and `many` forms handle 2-4, 5-20, 21+ patterns.
- **pl**: Translate all 7 plural messages with proper `one/few/many/other` forms.
- **uk**: Translate all 7 plural messages with proper `one/few/many/other` forms.

**Estimated effort:** 2-4 hours (translation + verification)

#### 5.1.2 Add Missing Keys to All Locales

- Add 14 biometric/Telegram error keys to all 26 non-English ARB files.
- Add 3 `rootDetectionDialog*` keys to ar, fa, he, ru.
- Provide English placeholder values initially; translate in Phase 2.

**Estimated effort:** 1-2 hours

#### 5.1.3 Complete Stub Locales (cs, da, sv, zh_Hant)

- Copy all 275 keys from `app_en.arb` to these 4 files as base.
- Mark them with `@@comment: "TODO: Professional translation required"`.

**Estimated effort:** 1 hour

### Phase 2: Wire UI to AppLocalizations (Week 2-4)

**Objective:** Replace all hardcoded strings with `context.l10n.keyName` calls.

#### 5.2.1 Add New ARB Keys for Undiscovered Strings

Before wiring screens, add ~300 new ARB keys to `app_en.arb` for strings that exist in code but have no ARB entry. Categories:

| Category | Estimated New Keys |
|----------|-------------------|
| Auth screens (register, login, biometric, app lock) | ~40 |
| Settings screens | ~30 |
| Profile screens | ~30 |
| Config import screens | ~25 |
| Subscription/purchase screens | ~35 |
| Server selection screens | ~15 |
| Notification screens | ~10 |
| Diagnostics/speed test screens | ~10 |
| Shared widgets & error screens | ~15 |
| Provider/service error messages | ~20 |
| Accessibility labels (tooltip, semantics) | ~20 |
| **Total estimated new keys** | **~250** |

**Estimated effort:** 2-3 days

#### 5.2.2 Replace Hardcoded Strings Feature-by-Feature

Migrate each feature module systematically:

1. `features/auth/` — register, login, biometric, app lock (5 screens)
2. `features/settings/` — all settings panels (8+ screens)
3. `features/profile/` — profile, 2FA, devices (6+ screens)
4. `features/config_import/` — import, QR scan, preview (4+ screens)
5. `features/subscription/` — plans, purchase, payment (3+ screens)
6. `features/servers/` — server list, selection (2 screens)
7. `features/onboarding/` — onboarding flow (2 screens)
8. `features/notifications/` — notification center (2 screens)
9. `features/referral/` — referral dashboard (1 screen)
10. `features/diagnostics/` — speed test, log viewer (2 screens)
11. `shared/widgets/` — error_view, global_error_screen (3 widgets)
12. Providers / services — error messages in Riverpod providers

**Pattern to use:**
```dart
// Before:
Text('Connect')

// After:
Text(context.l10n.connect)
```

**Estimated effort:** 5-7 days

#### 5.2.3 Run `flutter gen-l10n` and Verify Build

- Regenerate all localization classes after adding new keys.
- Fix any type errors from new placeholder usage.
- Verify app compiles and runs for en, ru, ar (LTR, Slavic plurals, RTL).

### Phase 3: Professional Translation (Week 4-6)

**Objective:** Replace English placeholder values with real translations for all 27 locales.

#### 5.3.1 Priority Tier 1 — High-Traffic Languages

Translate all ~525 keys (275 existing + ~250 new) for:

| Priority | Locales | Rationale |
|----------|---------|-----------|
| P0 | ru, fa, ar, zh | Censored-region users (primary market) |
| P1 | en, de, es, fr, pt | Major Western markets |
| P2 | tr, ja, ko, uk | Significant user bases |

**Method:** Professional translation service or vetted native speakers.

#### 5.3.2 Priority Tier 2 — Remaining Languages

| Priority | Locales | Rationale |
|----------|---------|-----------|
| P3 | it, nl, pl, hi, th, vi, id, ms, he, ro | Extended coverage |
| P4 | cs, da, sv, zh_Hant | Lower priority, stub locales |

**Method:** Translation service, AI-assisted with human review.

#### 5.3.3 Plural Form Review

For each translated locale, verify CLDR plural categories:

| Language Group | Required Categories |
|---------------|-------------------|
| en, de, es, fr, it, nl, pt, sv, da, hi, ro | `one`, `other` |
| ru, uk, pl, cs | `one`, `few`, `many`, `other` |
| ar | `zero`, `one`, `two`, `few`, `many`, `other` |
| ja, ko, zh, zh_Hant, vi, th, id, ms, tr, fa | `other` only |
| he | `one`, `two`, `other` |

### Phase 4: Quality Assurance & CI (Week 6-7)

#### 5.4.1 Add ARB Metadata

Add `@key` description entries to `app_en.arb` for all keys to provide translators with context:

```json
{
  "errorBiometricFailed": "Biometric authentication failed. Please try again.",
  "@errorBiometricFailed": {
    "description": "Error shown when fingerprint/face recognition fails on login"
  }
}
```

#### 5.4.2 CI Integration — Missing Key Detection

Add a CI script that:
1. Parses `app_en.arb` to get the canonical key list.
2. Compares each locale ARB against it.
3. Fails the build if any locale has missing keys.
4. Reports untranslated values (identical to English).

**Example:**
```bash
# scripts/check_i18n_coverage.py
# Exit code 1 if any locale is missing keys or has >5% untranslated
```

#### 5.4.3 Lint Rule — No Hardcoded Strings

Add a custom lint rule or analysis option to detect `Text('...')` without `AppLocalizations`:

```yaml
# analysis_options.yaml
analyzer:
  plugins:
    - custom_lint  # or equivalent
```

Alternatively, add a grep-based CI check:
```bash
# Fail if Text() widgets contain string literals in lib/ (excluding generated/)
grep -rn "Text('[A-Z]" lib/ --include="*.dart" | grep -v generated | grep -v test
```

#### 5.4.4 Visual QA — Screenshot Testing

Test each supported locale on a representative screen (e.g., Settings) to verify:
- Text renders correctly (no truncation, no overflow).
- RTL layout is correct for ar, he, fa.
- CJK characters display properly for ja, ko, zh, zh_Hant.
- Long German/Russian text doesn't break layouts.

---

## 6. Technical Architecture

### 6.1 File Structure (No Changes)

```
cybervpn_mobile/
├── l10n.yaml                           # gen-l10n config (unchanged)
├── lib/core/l10n/
│   ├── arb/
│   │   ├── app_en.arb                  # Template: ~525 keys (275 + ~250 new)
│   │   ├── app_ru.arb                  # 525 keys, fully translated
│   │   ├── app_ar.arb                  # 525 keys, fully translated
│   │   └── ... (27 locale files)
│   ├── generated/                      # Auto-generated (flutter gen-l10n)
│   │   ├── app_localizations.dart
│   │   └── app_localizations_*.dart
│   └── locale_config.dart              # Locale→code mapping, RTL set
└── lib/shared/extensions/
    └── context_extensions.dart         # context.l10n shortcut (exists)
```

### 6.2 Usage Pattern

```dart
// Every screen/widget that shows text:
import 'package:cybervpn_mobile/shared/extensions/context_extensions.dart';

class MyScreen extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Text(context.l10n.connect);  // Uses AppLocalizations via extension
  }
}
```

### 6.3 Key Naming Convention

Follow the existing pattern:

| Prefix | Usage | Example |
|--------|-------|---------|
| (none) | Core UI actions | `connect`, `disconnect`, `cancel` |
| `onboarding*` | Onboarding flow | `onboardingWelcomeTitle` |
| `settings*` | Settings screens | `settingsKillSwitchLabel` |
| `profile*` | Profile screens | `profileEditProfile` |
| `config*` | Config import | `configImportTitle` |
| `notification*` | Notifications | `notificationConnected` |
| `referral*` | Referral program | `referralDashboardTitle` |
| `diagnostics*` / `speedTest*` / `logViewer*` | Diagnostics | `speedTestStart` |
| `error*` | Error messages | `errorConnectionFailed` |
| `a11y*` | Accessibility labels | `a11yConnectButton` |
| `widget*` / `quickAction*` | Home widgets & quick actions | `widgetConnectLabel` |
| `subscription*` / `purchase*` | NEW — subscription screens | `subscriptionChoosePlan` |
| `auth*` / `biometric*` | NEW — auth screens | `authRegisterTitle` |
| `import*` | NEW — import list actions | `importClearAll` |

---

## 7. Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Translation quality (AI-generated or machine translation) | High | Medium | Use professional translators for P0/P1 languages; AI + human review for P3/P4 |
| New hardcoded strings introduced after cleanup | Medium | Medium | CI check to block PRs with `Text('...')` patterns |
| Layout breakage with long translations (de, ru) | Medium | Low | Add maxLines/overflow handling; visual QA per locale |
| RTL layout bugs (ar, he, fa) | Medium | Medium | Dedicated RTL testing pass; use `Directionality`-aware widgets |
| Scope creep — translating backend error messages | Low | Low | Out of scope: backend returns error codes, app maps to l10n keys |
| Key conflicts when merging new keys | Low | Low | Use feature-prefixed naming convention consistently |

---

## 8. Out of Scope

- **Backend API localization** — API returns error codes, not translated strings.
- **App Store metadata localization** — Separate task (store listing, screenshots).
- **Push notification localization** — Uses FCM topics, message content is server-side.
- **Adding new locales beyond 27** — Current set covers target markets adequately.
- **Dynamic language switching without restart** — Already works via Riverpod state.

---

## 9. Dependencies

| Dependency | Status |
|-----------|--------|
| Flutter `gen-l10n` toolchain | Available (already configured) |
| `context.l10n` extension | Available (already exists) |
| `intl` package | Available (already in pubspec) |
| Professional translation service / budget | Needs approval |
| CI pipeline access | Needs configuration |

---

## 10. Estimated Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Phase 1: Critical fixes | 1-2 weeks | Plurals fixed, missing keys added, stubs completed |
| Phase 2: Wire UI | 2-3 weeks | All 574+ strings use `context.l10n`, ~250 new ARB keys |
| Phase 3: Translation | 2-3 weeks | All 27 locales professionally translated |
| Phase 4: QA & CI | 1 week | CI coverage checks, visual QA, lint rules |
| **Total** | **6-9 weeks** | Production-grade i18n across 27 locales |

---

## 11. Appendix

### A. Complete List of 14 Missing Error Keys

```json
"errorTelegramAuthCancelled": "Telegram login was cancelled.",
"errorTelegramAuthFailed": "Telegram authentication failed. Please try again.",
"errorTelegramAuthExpired": "Telegram login expired. Please try again.",
"errorTelegramNotInstalled": "Telegram is not installed on this device.",
"errorTelegramAuthInvalid": "Invalid Telegram authentication data.",
"errorBiometricUnavailable": "Biometric authentication is not available on this device.",
"errorBiometricNotEnrolled": "No biometric data enrolled. Please set up fingerprint or face recognition in device settings.",
"errorBiometricFailed": "Biometric authentication failed. Please try again.",
"errorBiometricLocked": "Biometric authentication is locked. Try again later or use your password.",
"errorSessionExpired": "Your session has expired. Please log in again.",
"errorAccountDisabled": "Your account has been disabled. Please contact support.",
"errorRateLimitedWithCountdown": "Too many attempts. Please try again in {seconds, plural, =1{1 second} other{{seconds} seconds}}.",
"errorOfflineLoginRequired": "You need to be online to log in. Please check your connection.",
"errorOfflineSessionExpired": "Your cached session has expired. Please connect to the internet to log in."
```

### B. CLDR Plural Category Reference

| Language | Categories Required | Example (count=21) |
|----------|-------------------|--------------------|
| English | one, other | "21 days remaining" |
| Russian | one, few, many, other | "21 день" (one), "22 дня" (few), "25 дней" (many) |
| Arabic | zero, one, two, few, many, other | 6 forms needed |
| Japanese | other | Single form always |
| Polish | one, few, many, other | "21 dni" (many), "1 dzień" (one), "2 dni" (few) |
| Czech | one, few, many, other | "21 dní" (other), "1 den" (one), "2 dny" (few) |

### C. Russian Plural Fix Example

```json
// BEFORE (incorrect):
"daysRemaining": "{count, plural, =1{Остался 1 день} few{...} many{...} other{...}}"

// AFTER (correct):
"daysRemaining": "{count, plural, one{Остался {count} день} few{Осталось {count} дня} many{Осталось {count} дней} other{Осталось {count} дней}}"
```

The `one{}` CLDR category for Russian matches: 1, 21, 31, 41, 51, 61, 71, 81, 101, 1001...
The `=1{}` exact match only matches the number 1.
