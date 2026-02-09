# PRD: Full Internationalization of CyberVPN Mobile App (36 Locales)

| Field | Value |
|-------|-------|
| **Document** | PRD_MOBILE_I18N_36_LOCALES |
| **Status** | Draft |
| **Priority** | P1 |
| **Target** | 100% translation coverage, 0 hardcoded strings |
| **Locales** | 36 |
| **RTL** | 5 locales (ar, he, fa, ur, ku) |

---

## 1. Problem Statement

CyberVPN Mobile currently supports **27 locales**. The target is **36 locales** with **100% translation coverage**. The mobile app is missing **13 locales**, and 2 existing locales (`da`, `zh_Hant`) are outside the target list and must be removed.

---

## 2. Target Locale List (36 locales)

### High Priority (5)

| # | Code | Language | Status | RTL |
|---|------|----------|--------|-----|
| 1 | `en` | English | Exists | - |
| 2 | `hi` | Hindi | Exists | - |
| 3 | `id` | Indonesian | Exists | - |
| 4 | `ru` | Russian | Exists | - |
| 5 | `zh` | Chinese Simplified (zh-CN) | Exists | - |

### Medium Priority (5)

| # | Code | Language | Status | RTL |
|---|------|----------|--------|-----|
| 6 | `ar` | Arabic (ar-SA) | Exists | RTL |
| 7 | `fa` | Farsi (fa-IR) | Exists | RTL |
| 8 | `tr` | Turkish | Exists | - |
| 9 | `vi` | Vietnamese | Exists | - |
| 10 | `ur` | Urdu (ur-PK) | **NEW** | RTL |

### Low Priority (8)

| # | Code | Language | Status | RTL |
|---|------|----------|--------|-----|
| 11 | `th` | Thai | Exists | - |
| 12 | `bn` | Bengali (bn-BD) | **NEW** | - |
| 13 | `ms` | Malay | Exists | - |
| 14 | `es` | Spanish | Exists | - |
| 15 | `kk` | Kazakh (kk-KZ) | **NEW** | - |
| 16 | `be` | Belarusian (be-BY) | **NEW** | - |
| 17 | `my` | Burmese (my-MM) | **NEW** | - |
| 18 | `uz` | Uzbek (uz-UZ) | **NEW** | - |

### Non-Viable (6)

| # | Code | Language | Status | RTL |
|---|------|----------|--------|-----|
| 19 | `ha` | Hausa (ha-NG) | **NEW** | - |
| 20 | `yo` | Yoruba (yo-NG) | **NEW** | - |
| 21 | `ku` | Kurdish Sorani (ku-IQ) | **NEW** | RTL |
| 22 | `am` | Amharic (am-ET) | **NEW** | - |
| 23 | `fr` | French | Exists | - |
| 24 | `tk` | Turkmen (tk-TM) | **NEW** | - |

### Additional (12)

| # | Code | Language | Status | RTL |
|---|------|----------|--------|-----|
| 25 | `ja` | Japanese | Exists | - |
| 26 | `ko` | Korean | Exists | - |
| 27 | `he` | Hebrew (he-IL) | Exists | RTL |
| 28 | `de` | German | Exists | - |
| 29 | `pt` | Portuguese | Exists | - |
| 30 | `it` | Italian | Exists | - |
| 31 | `nl` | Dutch | Exists | - |
| 32 | `pl` | Polish | Exists | - |
| 33 | `fil` | Filipino (fil-PH) | **NEW** | - |
| 34 | `uk` | Ukrainian | Exists | - |
| 35 | `cs` | Czech | Exists | - |
| 36 | `ro` | Romanian | Exists | - |
| - | `hu` | Hungarian (hu-HU) | **NEW** | - |
| - | `sv` | Swedish | Exists | - |

### Summary

- **Existing** (in target): 23 locales
- **New** to add: 13 locales (ur, bn, kk, be, my, uz, ha, yo, ku, am, tk, fil, hu)
- **To remove**: 2 locales (`da` Danish, `zh_Hant` Chinese Traditional) — not in target list
- **RTL locales**: 5 (ar, he, fa, ur, ku)

---

## 3. Goals

| # | Goal | Metric |
|---|------|--------|
| G1 | 100% string coverage | 0 untranslated keys across all 36 locales |
| G2 | 0 hardcoded UI strings | All user-visible text via `AppLocalizations` |
| G3 | Full RTL support | 5 RTL locales (ar, he, fa, ur, ku) |
| G4 | Relative date localization | `l10n_formatters.dart` uses ARB, not English fallback |
| G5 | Platform parity | Mobile locale list matches target 36-locale list |

---

## 4. Non-Goals

- Translation quality review / proofreading (separate QA effort)
- Dynamic locale download (all locales bundled at build time)
- Locale-specific content (images, videos, app store assets)
- Currency conversion logic changes

---

## 5. Current State Audit

### 5.1 Files Requiring Changes

| File | Change Type | Description |
|------|-------------|-------------|
| `lib/core/l10n/locale_config.dart` | Modify | Add 13 new locale codes, add `ur`/`ku` to RTL set, remove `da`/`zh_Hant` |
| `lib/core/l10n/arb/app_en.arb` | Modify | Add ~21 new keys (relative dates + hardcoded strings) |
| `lib/core/l10n/arb/app_{locale}.arb` | Create (13) | New ARB files for each new locale with 100% keys |
| `lib/core/l10n/arb/app_da.arb` | **Delete** | Danish not in target list |
| `lib/core/l10n/arb/app_zh_Hant.arb` | **Delete** | Chinese Traditional not in target list |
| `lib/core/utils/l10n_formatters.dart` | Modify | Add 13 new locales to `_normalizeLocale`, remove `da`/`zh_Hant`, integrate relative dates |
| `lib/features/settings/data/repositories/language_repository.dart` | Modify | Add 13 new `LanguageItem` entries, remove Danish + zh_Hant |
| `l10n.yaml` | No change | gen-l10n auto-discovers ARB files |
| `lib/app/app.dart` | Modify | Fix hardcoded `'Notification'` fallback |
| `lib/features/settings/presentation/screens/debug_screen.dart` | Modify | Localize ~3 error SnackBar strings |
| `lib/features/settings/presentation/screens/trusted_wifi_screen.dart` | Modify | Localize 1 error string |
| `lib/features/profile/presentation/screens/social_accounts_screen.dart` | Modify | Localize ~4 hardcoded strings |
| `lib/features/profile/presentation/screens/delete_account_screen.dart` | Modify | Localize `'DELETE'` hint text |
| `test/core/l10n/locale_config_test.dart` | Modify | Update tests for 36 locales, 5 RTL |

### 5.2 Hardcoded Strings to Eliminate

| Location | String | New ARB Key |
|----------|--------|-------------|
| `app.dart:396` | `'Notification'` | `notificationFallbackTitle` |
| `debug_screen.dart:323` | `'Failed to export logs: $e'` | `debugExportLogsFailed` |
| `debug_screen.dart:392` | `'Failed to clear cache: $e'` | `debugClearCacheFailed` |
| `debug_screen.dart:442` | `'Failed to reset settings: $e'` | `debugResetSettingsFailed` |
| `trusted_wifi_screen.dart:94` | `'Failed to add network: $e'` | `settingsTrustedWifiAddFailed` |
| `social_accounts_screen.dart:135` | `'Completing $provider link...'` | `profileSocialCompletingLink` |
| `social_accounts_screen.dart:158` | `'Failed to complete OAuth link: $e'` | `profileSocialOAuthFailed` |
| `social_accounts_screen.dart:225` | `'Failed to link $provider: $e'` | `profileSocialLinkFailed` |
| `social_accounts_screen.dart:290` | `'Failed to unlink $provider: $e'` | `profileSocialUnlinkFailed` |
| `delete_account_screen.dart:530` | `hintText: 'DELETE'` | `deleteAccountConfirmHint` |

### 5.3 Relative Date Keys to Add to ARB

These keys replace the hardcoded English fallback in `L10nFormatters._getLocaleString`:

| ARB Key | English Value | ICU Format |
|---------|--------------|------------|
| `relativeJustNow` | `just now` | Simple |
| `relativeYesterday` | `yesterday` | Simple |
| `relativeMinutesAgo` | `{count, plural, =1{1 minute ago} other{{count} minutes ago}}` | Plural |
| `relativeHoursAgo` | `{count, plural, =1{1 hour ago} other{{count} hours ago}}` | Plural |
| `relativeDaysAgo` | `{count, plural, =1{1 day ago} other{{count} days ago}}` | Plural |
| `relativeWeeksAgo` | `{count, plural, =1{1 week ago} other{{count} weeks ago}}` | Plural |
| `relativeMonthsAgo` | `{count, plural, =1{1 month ago} other{{count} months ago}}` | Plural |
| `relativeYearsAgo` | `{count, plural, =1{1 year ago} other{{count} years ago}}` | Plural |
| `relativeInSeconds` | `in a few seconds` | Simple |
| `relativeInMinutes` | `{count, plural, =1{in 1 minute} other{in {count} minutes}}` | Plural |
| `relativeInHours` | `{count, plural, =1{in 1 hour} other{in {count} hours}}` | Plural |

---

## 6. Epics & Tasks

### Epic 1: Locale Infrastructure (add 13, remove 2)

**Goal**: Register all 36 locales in configuration, remove `da` and `zh_Hant`.

#### E1.1 Update `locale_config.dart`
- Replace `supportedLocaleCodes` list with exactly 36 codes
- Set `rtlLocaleCodes` to `{'ar', 'he', 'fa', 'ur', 'ku'}` (5 RTL)
- Remove `da` and `zh_Hant`
- Update doc comment: "All 36 supported locales"

#### E1.2 Update `language_repository.dart`
- Add 13 new `LanguageItem` entries:

| Code | Native Name | English Name | Flag |
|------|-------------|--------------|------|
| `ur` | اردو | Urdu | PK |
| `bn` | বাংলা | Bengali | BD |
| `kk` | Қазақша | Kazakh | KZ |
| `be` | Беларуская | Belarusian | BY |
| `my` | မြန်မာ | Burmese | MM |
| `uz` | O'zbekcha | Uzbek | UZ |
| `ha` | Hausa | Hausa | NG |
| `yo` | Yorùbá | Yoruba | NG |
| `ku` | کوردی | Kurdish | IQ |
| `am` | አማርኛ | Amharic | ET |
| `tk` | Türkmen | Turkmen | TM |
| `fil` | Filipino | Filipino | PH |
| `hu` | Magyar | Hungarian | HU |

- Remove `da` (Danish) and `zh_Hant` (Chinese Traditional) entries

#### E1.3 Update `l10n_formatters.dart`
- Add 13 new locales to `_normalizeLocale` map:
  - `ur` -> `ur_PK`, `bn` -> `bn_BD`, `kk` -> `kk_KZ`, `be` -> `be_BY`
  - `my` -> `my_MM`, `uz` -> `uz_UZ`, `ha` -> `ha_NG`, `yo` -> `yo_NG`
  - `ku` -> `ku_IQ`, `am` -> `am_ET`, `tk` -> `tk_TM`, `fil` -> `fil_PH`
  - `hu` -> `hu_HU`
- Remove `da` -> `da_DK` and `zh_Hant` -> `zh_TW` mappings

#### E1.4 Update tests
- `locale_config_test.dart`: Expect exactly 36 locales, 5 RTL codes
- Verify all 36 codes are present in `supportedLocaleCodes`
- Verify `da` and `zh_Hant` are NOT present

---

### Epic 2: Create 13 New ARB Files + 21 New Keys (100% coverage)

**Goal**: Every locale has a complete ARB file with all ~601 keys (580 existing + 21 new).

#### E2.1 Add new keys to `app_en.arb` (template)
- Add 11 relative date keys (Section 5.3)
- Add 10 hardcoded string keys (Section 5.2)
- Total new keys: **21**

#### E2.2 Update all 23 existing locale ARB files
- Add translations for all 21 new keys to every existing ARB
- Verify 0 missing keys in any existing file

#### E2.3 Create 13 new locale ARB files
- Each file must contain ALL keys from `app_en.arb` (including new ones)
- Files to create:
  - `app_ur.arb`, `app_bn.arb`, `app_kk.arb`, `app_be.arb`
  - `app_my.arb`, `app_uz.arb`, `app_ha.arb`, `app_yo.arb`
  - `app_ku.arb`, `app_am.arb`, `app_tk.arb`, `app_fil.arb`
  - `app_hu.arb`

#### E2.4 Delete obsolete ARB files
- Delete `app_da.arb` (Danish)
- Delete `app_zh_Hant.arb` (Chinese Traditional)

#### E2.5 Run `flutter gen-l10n` and verify
- All generated files compile
- `AppLocalizations.supportedLocales` lists exactly 36 locales
- 0 missing key warnings

---

### Epic 3: Eliminate All Hardcoded Strings

**Goal**: Zero hardcoded user-visible strings remain.

#### E3.1 Fix `app.dart` notification fallback
- Replace `'Notification'` with `l10n.notificationFallbackTitle`

#### E3.2 Fix `debug_screen.dart` error messages
- Replace 3 hardcoded SnackBar strings with ARB keys
- Use parameterized messages for error details: `{error}`

#### E3.3 Fix `trusted_wifi_screen.dart`
- Replace `'Failed to add network: $e'` with `l10n.settingsTrustedWifiAddFailed(e.toString())`

#### E3.4 Fix `social_accounts_screen.dart`
- Replace 4 hardcoded strings with parameterized ARB keys
- Provider name passed as `{provider}` placeholder

#### E3.5 Fix `delete_account_screen.dart`
- Replace `hintText: 'DELETE'` with `l10n.deleteAccountConfirmHint`

---

### Epic 4: Localize Relative Date Formatter

**Goal**: `L10nFormatters._formatRelativeDate` uses ARB translations instead of English fallback.

#### E4.1 Refactor `_getLocaleString` to accept `AppLocalizations`
- Change `_formatRelativeDate` signature to accept `AppLocalizations`
- Map each relative date key to the corresponding `AppLocalizations` getter
- Remove the `// TODO: Integrate with AppLocalizations` comment

#### E4.2 Update all callers of `formatDate` with `DateFormatType.relative`
- Pass `AppLocalizations` instance from widget context
- Verify all call sites provide the l10n parameter

#### E4.3 Ensure correct plural forms in all 36 ARB files
- Pay special attention to languages with complex plural rules:
  - Arabic (6 plural forms: zero, one, two, few, many, other)
  - Polish/Czech/Russian/Ukrainian/Belarusian (few/many distinctions)
  - Bengali, Hindi, Urdu (different plural rules)

---

### Epic 5: RTL Hardening for 5 Locales

**Goal**: All 5 RTL locales (ar, he, fa, ur, ku) render correctly.

#### E5.1 Update `LocaleConfig.rtlLocaleCodes`
- Set to `{'ar', 'he', 'fa', 'ur', 'ku'}` (was `{'ar', 'he', 'fa'}`)

#### E5.2 Audit all widgets for RTL-aware layout
- Check `Row`, `Padding`, `Align` widgets for hardcoded `left`/`right`
- Replace with `start`/`end` equivalents:
  - `EdgeInsets.only(left:)` -> `EdgeInsetsDirectional.only(start:)`
  - `Alignment.centerLeft` -> `AlignmentDirectional.centerStart`
- Check icon mirroring for directional icons (arrows, chevrons)

#### E5.3 Test RTL rendering
- Verify all screens in `ar`, `ur`, `ku` locales
- Ensure speed indicators and gauges remain LTR (already forced)
- Verify text input fields work correctly in RTL

---

### Epic 6: Validation & CI

**Goal**: Ensure 100% coverage is enforced automatically.

#### E6.1 Create ARB validation script
- Script: `scripts/validate_arb_coverage.dart`
- Checks:
  - Every ARB file has exactly the same keys as `app_en.arb` (excluding `@`-metadata)
  - No ARB file has empty string values
  - All plural forms are present for languages requiring them
  - Exactly 36 ARB files exist (excluding template metadata)
- Run as part of CI / pre-commit

#### E6.2 Create coverage report
- Output: table showing % coverage per locale
- Target: 100% for all 36 locales
- Flag any locale below 100% as build failure

#### E6.3 Add `flutter gen-l10n` to CI pipeline
- Ensure code generation runs in CI
- Fail build if gen-l10n produces warnings or errors

---

## 7. Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| AC1 | Exactly 36 locales in `LocaleConfig.supportedLocaleCodes` | Unit test |
| AC2 | 36 ARB files exist (1 per target locale) | File count check |
| AC3 | Every ARB file has 100% of template keys | Validation script |
| AC4 | 5 RTL locales in `rtlLocaleCodes`: ar, he, fa, ur, ku | Unit test |
| AC5 | 0 hardcoded user-visible strings in `lib/` | Grep audit |
| AC6 | `_getLocaleString` uses `AppLocalizations`, not English fallback | Code review |
| AC7 | `flutter gen-l10n` completes with 0 warnings | CI check |
| AC8 | `flutter build apk` succeeds | Build check |
| AC9 | All 13 new `LanguageItem` entries in `language_repository.dart` | Unit test |
| AC10 | `l10n_formatters.dart` handles all 36 locale codes | Unit test |
| AC11 | `da` and `zh_Hant` fully removed (ARB, config, repository) | Grep audit |

---

## 8. Plural Form Reference

Languages with non-trivial plural rules (ICU `plural` categories):

| Language | Plural Forms | Notes |
|----------|-------------|-------|
| Arabic (ar) | zero, one, two, few, many, other | 6 forms |
| Polish (pl) | one, few, many, other | 4 forms |
| Russian (ru) | one, few, many, other | 4 forms |
| Ukrainian (uk) | one, few, many, other | 4 forms |
| Czech (cs) | one, few, many, other | 4 forms |
| Belarusian (be) | one, few, many, other | 4 forms |
| French (fr) | one, many, other | 3 forms |
| Portuguese (pt) | one, many, other | 3 forms |
| Bengali (bn) | one, other | 2 forms |
| Hindi (hi) | one, other | 2 forms |
| Urdu (ur) | one, other | 2 forms |
| Kurdish (ku) | one, other | 2 forms |
| Amharic (am) | one, other | 2 forms |
| Hungarian (hu) | one, other | 2 forms |
| Filipino (fil) | one, other | 2 forms (based on Tagalog) |
| All others | one, other | Standard 2 forms |

---

## 9. Risk & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Missing `intl` locale data for rare languages (ha, yo, tk, ku) | Date/number formatting falls back | Fallback formatters already in place |
| Incorrect plural forms | Bad UX for counts | Reference CLDR plural rules, test each |
| Flutter `Locale` resolution fails for `ku` or `my` | App crashes on locale switch | Add `localeResolutionCallback` fallback to `en` |
| Large APK size from 36 locale bundles | +~2MB | Acceptable for VPN app |
| Translation quality for rare languages | Bad UX | Separate QA pass (out of scope) |
| Removing `zh_Hant` breaks existing Chinese Traditional users | Lost users | Fallback to `zh` (Simplified) via locale resolution |
| Removing `da` breaks existing Danish users | Lost users | Fallback to `en` via locale resolution |

---

## 10. Execution Order

```
E1 (Infrastructure) ──> E2 (ARB files) ──> E3 (Hardcoded strings)
                                        ──> E4 (Relative dates)
                                        ──> E5 (RTL hardening)
                         All above ──────> E6 (Validation & CI)
```

E3, E4, E5 can run in parallel after E2 completes. E6 is the final validation gate.

---

## 11. Definition of Done

- [ ] `flutter gen-l10n` produces 0 warnings
- [ ] `flutter test` passes (including updated locale_config_test)
- [ ] Validation script reports 100% coverage for all 36 locales
- [ ] `grep -r "hardcoded string patterns" lib/` returns 0 results (excluding debug-only)
- [ ] RTL rendering verified for ar, he, fa, ur, ku
- [ ] `da` and `zh_Hant` fully removed from codebase
- [ ] `flutter build apk --release` succeeds
- [ ] PR reviewed and merged
