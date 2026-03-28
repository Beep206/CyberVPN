# CyberVPN Phase 9 — 100% Completion: Locale Sync & Final Hardening — Agent Team Prompt

> Requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`.
> User presses **Shift+Tab** to enter delegate mode, then pastes this prompt.
> Teammates load `CLAUDE.md` automatically. Spawn prompts contain ONLY task-specific context.
> **Scope**: Sync all 39 locales across Frontend, Mobile, and Telegram Bot middleware. Verify Docker network segmentation is complete. Fix all remaining lint/build/test issues. Achieve 100% completion across all 8 phases.
> **Out of scope**: Certificate pinning SHA-256 values (require real production certs), TanStack Table `react-hooks/incompatible-library` warning (upstream library issue), professional human translation of locale placeholder files.

---

## Goal

This is **Phase 9 — 100% Completion**. Phases 1-8 built, polished, hardened, and nearly completed the entire CyberVPN platform. Phase 9 closes the final ~3% gap to achieve full 100% completion:

1. **39 locales everywhere** — Telegram Bot has 39 locales but middleware only loads 2. Frontend has 38 (missing zh-Hant). Mobile has 38 (missing zh-Hant). Sync ALL to 39.
2. **Bot i18n middleware** — Expand `SUPPORTED_LOCALES` from 2 → 39, expand `LANGUAGE_MAP` to cover all Telegram language codes.
3. **Docker network verification** — Phase 8 defined 4 tiered networks. Verify ALL services use them (no remaining `remnawave-network` references).
4. **Final lint/build/test sweep** — Ensure all platforms pass their respective checks with zero regressions.

### Task Summary

| # | Task | Platform | Severity | Files |
|---|------|----------|----------|-------|
| 1 | Add zh-Hant locale to Frontend (config + messages directory) | Frontend | P0 | ~10 files |
| 2 | Add zh-Hant locale to Mobile (ARB + language_repository + l10n.yaml) | Mobile | P0 | ~4 files |
| 3 | Expand Bot SUPPORTED_LOCALES from 2→39 + LANGUAGE_MAP for all Telegram codes | Telegram Bot | P0 | 2 files |
| 4 | Update Bot config.py default available_languages to all 39 locales | Telegram Bot | P0 | 1 file |
| 5 | Verify Docker 4-tier network assignment for all services | Infrastructure | P1 | 1 file |
| 6 | Frontend i18n config: add zh-Hant to locales array | Frontend | P0 | 1 file |
| 7 | Frontend CLAUDE.md: update "41 locales" reference to match reality (39) | Frontend | P2 | 1 file |
| 8 | Build/test/lint verification across all platforms | All | P0 | 0 (read-only) |

**Done criteria:**
1. `ls frontend/messages/ | wc -l` returns 39 (was 38)
2. `grep "zh-Hant" frontend/src/i18n/config.ts` matches
3. `ls cybervpn_mobile/lib/core/l10n/arb/app_zh_Hant.arb` exists
4. `grep "zh_Hant" cybervpn_mobile/lib/features/settings/data/repositories/language_repository.dart` matches
5. `grep "SUPPORTED_LOCALES" services/telegram-bot/src/middlewares/i18n.py | head -1` shows 39 locales (not 2)
6. `grep "available_languages" services/telegram-bot/src/config.py` shows all 39 locales
7. All services reference 4-tier Docker networks (cybervpn-frontend, cybervpn-backend, cybervpn-data, cybervpn-monitoring)
8. `cd frontend && npm run build` passes
9. `cd cybervpn_mobile && flutter analyze --no-fatal-infos 2>&1 | grep "error" | wc -l` returns 0
10. `python -c "import ast; ast.parse(open('services/telegram-bot/src/middlewares/i18n.py').read())"` passes
11. `cd infra && docker compose config -q` passes

---

## Current State Audit (Phase 9 starting point)

### What's DONE (from Phases 1-8)

| Component | Status | Detail |
|-----------|--------|--------|
| Frontend TypeScript | **0 `any` in production** | All eliminated |
| Frontend route boundaries | **36/36 (100%)** | error.tsx + loading.tsx + not-found.tsx |
| Frontend SEO | Complete | robots.ts, sitemap.ts, JSON-LD |
| Frontend i18n | **38 locales** | Missing zh-Hant (Traditional Chinese) |
| Frontend ESLint | **0 unused vars, 0 console.warn** | Phase 8 cleaned all |
| Frontend 3D | Working | Math.random purity fixed |
| Backend endpoints | **156+ across 34 routes** | Full API coverage |
| Backend metrics | **21/34 routes instrumented** | Phase 8 expanded from 15 |
| Backend except handling | **0 bare catches** | All have `as e` + logging |
| Backend tests | **All real** | 0 pass-only stubs |
| Mobile features | **20 features, 46 screens** | All wired |
| Mobile Dart analysis | **0 errors** | Phase 8 fixed all 671 issues |
| Mobile locales | **38 ARB files** | Missing zh-Hant |
| Mobile language_repository | **38 languages** | Missing zh-Hant entry |
| Infra Docker networks | **4 networks defined** | cybervpn-frontend/backend/data/monitoring |
| Infra REMNASHOP | **Fully removed** | .env, compose, directory all clean |
| Infra monitoring | **Backup script + externalized auth** | Phase 8 completed |
| Telegram Bot aiogram | **>=3.25** | Colored buttons working |
| Telegram Bot buttons | **227 style= usages** | primary/success/danger applied |
| Telegram Bot locales | **39 directories** | en, ru + 37 new (including zh-Hant) |
| Telegram Bot middleware | **2 active locales** | ⚠️ Only loads ru + en despite 39 dirs existing |

### What REMAINS (Phase 9 must fix ALL)

#### ISSUE-1: Frontend — Missing zh-Hant locale (38/39)

- `frontend/src/i18n/config.ts` has 38 locales. Missing: `zh-Hant` (Traditional Chinese)
- `frontend/messages/` has 38 directories. Missing: `zh-Hant/` directory with message JSON files
- Bot already has `zh-Hant` locale — Frontend and Mobile must match

**Files to modify:**
- `frontend/src/i18n/config.ts` — add `'zh-Hant'` to locales array
- Create `frontend/messages/zh-Hant/` directory with copies of `zh-CN/` JSON files (placeholder until translated)
- Update RTL locale list if needed (zh-Hant is NOT RTL)

#### ISSUE-2: Mobile — Missing zh-Hant locale (38/39)

- `cybervpn_mobile/lib/core/l10n/arb/` has 38 ARB files. Missing: `app_zh_Hant.arb`
- `language_repository.dart` has 38 LanguageItem entries. Missing: zh-Hant entry
- `l10n.yaml` may need update for zh_Hant

**Files to modify:**
- Create `cybervpn_mobile/lib/core/l10n/arb/app_zh_Hant.arb` — copy from `app_zh.arb`, change `@@locale` to `zh_Hant`
- `cybervpn_mobile/lib/features/settings/data/repositories/language_repository.dart` — add zh-Hant LanguageItem
- `cybervpn_mobile/l10n.yaml` — verify `zh_Hant` is included (Flutter uses underscore, not hyphen)

#### ISSUE-3: Telegram Bot — Middleware only loads 2 of 39 locales

Despite 39 locale directories existing with full .ftl translations, the bot only loads `ru` and `en`.

**Root cause chain:**
1. `config.py` line 224: `available_languages: list[str] = Field(default_factory=lambda: ["ru", "en"])`
2. `middlewares/__init__.py` line 80-82: `I18nManager(locales=settings.available_languages, ...)` — uses settings value
3. `middlewares/i18n.py` line 21: `SUPPORTED_LOCALES = ("ru", "en")` — fallback constant also only 2
4. `middlewares/i18n.py` lines 26-33: `LANGUAGE_MAP` only maps 7 Telegram language codes

**Fix requires updating:**
- `config.py`: Change `available_languages` default to all 39 locale codes
- `middlewares/i18n.py`: Expand `SUPPORTED_LOCALES` to all 39 codes, expand `LANGUAGE_MAP` to cover all Telegram language_code values

#### ISSUE-4: Docker network verification needed

Phase 8 defined 4 tiered networks at the bottom of `docker-compose.yml`:
```yaml
networks:
  cybervpn-frontend:
  cybervpn-backend:
  cybervpn-data:
  cybervpn-monitoring:
```

Need to verify ALL services reference these networks (not the old `remnawave-network`).
`grep -c "remnawave-network" infra/docker-compose.yml` already returns 0 — but need to verify all services have proper network assignments for the 4-tier model.

#### ISSUE-5: Frontend CLAUDE.md says "41 locales" but reality is 38→39

- `frontend/CLAUDE.md` mentions "41 locales" in two places (next-intl section)
- Actual locale count: 38 (will be 39 after zh-Hant added)
- Should be corrected to 39

---

## Team

| Role | Agent name | Model | subagent_type | Working directory | Tasks |
|------|-----------|-------|---------------|-------------------|-------|
| Lead (you) | -- | opus | -- | all (coordination) | 0 |
| Frontend Locale Sync | `frontend-i18n` | sonnet | ui-engineer | `frontend/` | 3 |
| Mobile Locale Sync | `mobile-i18n` | sonnet | mobile-lead | `cybervpn_mobile/` | 2 |
| Bot Middleware Expansion | `bot-i18n` | sonnet | telegram-bot-dev | `services/telegram-bot/` | 2 |
| Infra Network Verify | `infra-verify` | haiku | devops-engineer | `infra/` | 1 |
| Build Verification | `verify` | sonnet | general-purpose | all | 5 |

---

## Spawn Prompts

### frontend-i18n

```
You are frontend-i18n on the CyberVPN team (Phase 9). You add the missing zh-Hant (Traditional Chinese) locale to achieve 39 locales in the Frontend.
Stack: Next.js 16, React 19, TypeScript 5.9, next-intl 4.7.
You work ONLY in frontend/. Do NOT touch other directories.

CONTEXT — Current state:
- 38 locales in frontend/src/i18n/config.ts (all listed in const locales array)
- 38 message directories in frontend/messages/
- The Telegram Bot already has zh-Hant locale — Frontend must match
- zh-CN (Simplified Chinese) directory and messages already exist as a reference
- zh-Hant is NOT an RTL locale

KEY FILES TO READ FIRST:
1. frontend/src/i18n/config.ts — locale array + RTL list + default locale
2. frontend/messages/zh-CN/ — all JSON files (use as template for zh-Hant)
3. frontend/src/i18n/request.ts — namespace loading (verify new locale will be loaded)
4. frontend/CLAUDE.md — mentions "41 locales" which is incorrect

RULES:
- Do NOT downgrade any library version.
- Do NOT modify existing locale files — only add new ones.
- Do NOT change the default locale (en-EN).
- zh-Hant message files should initially be copies of zh-CN (placeholder until professionally translated).
- Follow the existing naming pattern: locale directories use hyphen format (zh-CN, not zh_CN).
- Update frontend/CLAUDE.md "41 locales" references to "39 locales" to match reality.

YOUR TASKS:

FI-1: Add zh-Hant to i18n config (P0)

  File: frontend/src/i18n/config.ts

  BEFORE:
  ```typescript
  export const locales = [
      // ...existing 38 locales...
      'fil-PH', 'uk-UA', 'cs-CZ', 'ro-RO', 'hu-HU', 'sv-SE'
  ] as const;
  ```

  AFTER — add 'zh-Hant' to the "Дополнительные" group:
  ```typescript
  export const locales = [
      // ...existing locales...
      'fil-PH', 'uk-UA', 'cs-CZ', 'ro-RO', 'hu-HU', 'sv-SE',
      // Traditional Chinese
      'zh-Hant'
  ] as const;
  ```

  Note: zh-Hant is NOT RTL, so do NOT add it to rtlLocales.

FI-2: Create zh-Hant message directory (P0)

  Copy ALL JSON files from frontend/messages/zh-CN/ to frontend/messages/zh-Hant/:

  STEP 1: Read the list of JSON files in zh-CN/:
    ls frontend/messages/zh-CN/

  STEP 2: Create zh-Hant directory and copy each file:
    mkdir -p frontend/messages/zh-Hant/
    For each .json file in zh-CN/, copy to zh-Hant/ with identical content
    (Traditional Chinese placeholder — uses Simplified Chinese until translated)

  STEP 3: Verify all files copied:
    diff <(ls frontend/messages/zh-CN/) <(ls frontend/messages/zh-Hant/)
    # Must show no differences in file names

FI-3: Fix locale count in CLAUDE.md (P2)

  File: frontend/CLAUDE.md
  Search for "41 locales" and replace with "39 locales" (2 occurrences).

VERIFICATION:
  ls frontend/messages/ | wc -l
  # Must be 39

  grep "zh-Hant" frontend/src/i18n/config.ts
  # Must match

  cd frontend && npm run build 2>&1 | tail -5
  # Must pass

DONE CRITERIA: 39 locale directories in messages/. zh-Hant in config.ts. CLAUDE.md updated. Build passes.
```

### mobile-i18n

```
You are mobile-i18n on the CyberVPN team (Phase 9). You add the missing zh-Hant (Traditional Chinese) locale to achieve 39 locales in the Flutter mobile app.
Stack: Flutter 3.x, Dart 3.x, Riverpod 3.x.
You work ONLY in cybervpn_mobile/. Do NOT touch frontend/, backend/, or services/.

CONTEXT — Current state:
- 38 ARB files in cybervpn_mobile/lib/core/l10n/arb/ (app_am.arb through app_zh.arb)
- 38 LanguageItem entries in language_repository.dart
- zh (Simplified Chinese) ARB exists — use as template for zh_Hant
- Flutter uses UNDERSCORE format (zh_Hant), NOT hyphen (zh-Hant)
- Telegram Bot already has zh-Hant locale — Mobile must match

KEY FILES TO READ FIRST:
1. cybervpn_mobile/lib/core/l10n/arb/app_zh.arb — template for Traditional Chinese
2. cybervpn_mobile/lib/features/settings/data/repositories/language_repository.dart — language list
3. cybervpn_mobile/l10n.yaml — Flutter l10n configuration
4. cybervpn_mobile/lib/core/l10n/arb/app_en.arb — reference for complete key set (English is the source)

RULES:
- Do NOT change existing ARB file content — only add new file.
- Flutter ARB locale format uses UNDERSCORE: zh_Hant (NOT zh-Hant)
- The new ARB file's "@@locale" value MUST be "zh_Hant"
- LanguageItem localeCode should be "zh_Hant" to match Flutter conventions
- Do NOT modify existing LanguageItem entries.
- Do NOT change l10n.yaml unless needed for zh_Hant support.

YOUR TASKS:

MI-1: Create zh_Hant ARB file (P0)

  File: cybervpn_mobile/lib/core/l10n/arb/app_zh_Hant.arb

  STEP 1: Read app_zh.arb to understand the format and all keys
  STEP 2: Create app_zh_Hant.arb as a copy of app_zh.arb with these changes:
    - "@@locale": "zh_Hant" (not "zh")
    - Keep all translation strings identical (Simplified Chinese as placeholder)
    - Update any @@comment to indicate Traditional Chinese

MI-2: Add zh_Hant to language_repository.dart (P0)

  File: cybervpn_mobile/lib/features/settings/data/repositories/language_repository.dart

  Add a new LanguageItem entry for Traditional Chinese. Find the correct alphabetical
  position (after Chinese Simplified entry):

  ```dart
  LanguageItem(
    localeCode: 'zh_Hant',
    nativeName: '中文繁體',
    englishName: 'Chinese (Traditional)',
    flagEmoji: '\u{1F1F9}\u{1F1FC}', // TW flag
  ),
  ```

  Also update the comment at the top: "All 36 locales" → "All 39 locales" (to match actual count).

VERIFICATION:
  ls cybervpn_mobile/lib/core/l10n/arb/app_zh_Hant.arb
  # Must exist

  grep "zh_Hant" cybervpn_mobile/lib/features/settings/data/repositories/language_repository.dart
  # Must match

  cd cybervpn_mobile && flutter analyze --no-fatal-infos 2>&1 | grep "error" | wc -l
  # Must be 0

DONE CRITERIA: app_zh_Hant.arb exists with correct @@locale. LanguageItem entry added. flutter analyze passes.
```

### bot-i18n

```
You are bot-i18n on the CyberVPN team (Phase 9). You expand the Telegram Bot i18n middleware from 2 active locales to 39 — enabling ALL existing locale directories.
Stack: Python 3.13, aiogram 3.25, fluent.runtime, structlog.
You work ONLY in services/telegram-bot/. Do NOT touch other directories.

CONTEXT — Current state:
- 39 locale directories exist in src/locales/ with full .ftl translations:
  am, ar, be, bn, cs, de, en, es, fa, fil, fr, ha, he, hi, hu, id, it, ja,
  kk, ko, ku, ms, my, nl, pl, pt, ro, ru, sv, th, tk, tr, uk, ur, uz, vi, yo, zh, zh-Hant
- BUT the middleware only loads 2 locales (ru, en)
- Three places need updating:
  1. config.py — available_languages default list
  2. middlewares/i18n.py — SUPPORTED_LOCALES constant
  3. middlewares/i18n.py — LANGUAGE_MAP dictionary

- The I18nManager is initialized via:
  middlewares/__init__.py:80-82:
  ```python
  i18n_manager = I18nManager(
      locales=settings.available_languages,
      default_locale=settings.default_language,
  )
  ```
  So settings.available_languages is the PRIMARY source for which locales get loaded.

- Bot uses aiogram 3.25+ with colored buttons (227 style= usages). Do NOT modify buttons.

KEY FILES TO READ FIRST:
1. services/telegram-bot/src/config.py — BotSettings class with available_languages field
2. services/telegram-bot/src/middlewares/i18n.py — SUPPORTED_LOCALES, LANGUAGE_MAP, I18nManager, I18nMiddleware
3. services/telegram-bot/src/middlewares/__init__.py — register_middlewares function (i18n init)
4. services/telegram-bot/src/locales/ — list of all 39 locale directories

RULES:
- Do NOT modify .ftl locale files — only Python config/middleware code.
- Do NOT modify keyboard files or button styles.
- Do NOT change the I18nManager or FluentTranslator classes — only their INPUT data.
- Do NOT change the default_locale (keep "ru").
- LANGUAGE_MAP must map Telegram's language_code values to our locale codes.
  Telegram sends 2-letter IETF codes (en, ru, uk, etc.) and sometimes full codes (en-US, pt-BR).
- The I18nMiddleware._resolve_locale already handles fallback to default — just ensure LANGUAGE_MAP covers all cases.
- Keep LANGUAGE_MAP sorted alphabetically for readability.

YOUR TASKS:

BI-1: Expand SUPPORTED_LOCALES and LANGUAGE_MAP in i18n.py (P0)

  File: services/telegram-bot/src/middlewares/i18n.py

  STEP 1: Replace SUPPORTED_LOCALES (line 21):

  BEFORE:
  ```python
  SUPPORTED_LOCALES = ("ru", "en")
  ```

  AFTER:
  ```python
  SUPPORTED_LOCALES = (
      "am", "ar", "be", "bn", "cs", "de", "en", "es", "fa", "fil",
      "fr", "ha", "he", "hi", "hu", "id", "it", "ja", "kk", "ko",
      "ku", "ms", "my", "nl", "pl", "pt", "ro", "ru", "sv", "th",
      "tk", "tr", "uk", "ur", "uz", "vi", "yo", "zh", "zh-Hant",
  )
  ```

  STEP 2: Replace LANGUAGE_MAP (lines 26-33):

  BEFORE:
  ```python
  LANGUAGE_MAP: dict[str, str] = {
      "ru": "ru",
      "uk": "ru",
      "be": "ru",
      "kk": "ru",
      "en": "en",
      "en-US": "en",
      "en-GB": "en",
  }
  ```

  AFTER — map ALL Telegram language codes to our locale codes:
  ```python
  LANGUAGE_MAP: dict[str, str] = {
      # Direct matches (Telegram code = our locale code)
      "am": "am",
      "ar": "ar",
      "be": "be",
      "bn": "bn",
      "cs": "cs",
      "de": "de",
      "en": "en",
      "es": "es",
      "fa": "fa",
      "fil": "fil",
      "fr": "fr",
      "ha": "ha",
      "he": "he",
      "hi": "hi",
      "hu": "hu",
      "id": "id",
      "it": "it",
      "ja": "ja",
      "kk": "kk",
      "ko": "ko",
      "ku": "ku",
      "ms": "ms",
      "my": "my",
      "nl": "nl",
      "pl": "pl",
      "pt": "pt",
      "ro": "ro",
      "ru": "ru",
      "sv": "sv",
      "th": "th",
      "tk": "tk",
      "tr": "tr",
      "uk": "uk",
      "ur": "ur",
      "uz": "uz",
      "vi": "vi",
      "yo": "yo",
      "zh": "zh",
      # Regional variants → base locale
      "en-US": "en",
      "en-GB": "en",
      "es-ES": "es",
      "es-MX": "es",
      "es-AR": "es",
      "fr-FR": "fr",
      "fr-CA": "fr",
      "pt-BR": "pt",
      "pt-PT": "pt",
      "zh-TW": "zh-Hant",
      "zh-HK": "zh-Hant",
      "zh-Hans": "zh",
      "zh-Hant": "zh-Hant",
      "de-DE": "de",
      "de-AT": "de",
      "it-IT": "it",
      "nl-NL": "nl",
      "nl-BE": "nl",
      "pl-PL": "pl",
      "ro-RO": "ro",
      "hu-HU": "hu",
      "sv-SE": "sv",
      "cs-CZ": "cs",
      "ar-SA": "ar",
      "ar-EG": "ar",
      "fa-IR": "fa",
      "he-IL": "he",
      "hi-IN": "hi",
      "bn-BD": "bn",
      "ur-PK": "ur",
      "id-ID": "id",
      "ms-MY": "ms",
      "tr-TR": "tr",
      "vi-VN": "vi",
      "th-TH": "th",
      "ja-JP": "ja",
      "ko-KR": "ko",
      "uk-UA": "uk",
  }
  ```

  This ensures that ANY Telegram language_code a user might have will be mapped to our locale.

BI-2: Expand available_languages default in config.py (P0)

  File: services/telegram-bot/src/config.py

  BEFORE (line 224):
  ```python
  available_languages: list[str] = Field(default_factory=lambda: ["ru", "en"])
  ```

  AFTER:
  ```python
  available_languages: list[str] = Field(
      default_factory=lambda: [
          "am", "ar", "be", "bn", "cs", "de", "en", "es", "fa", "fil",
          "fr", "ha", "he", "hi", "hu", "id", "it", "ja", "kk", "ko",
          "ku", "ms", "my", "nl", "pl", "pt", "ro", "ru", "sv", "th",
          "tk", "tr", "uk", "ur", "uz", "vi", "yo", "zh", "zh-Hant",
      ]
  )
  ```

  This is the PRIMARY control — I18nManager reads settings.available_languages to decide
  which locale bundles to load. With 39 locales listed, all 39 directories will be loaded.

VERIFICATION:
  python -c "import ast; ast.parse(open('services/telegram-bot/src/middlewares/i18n.py').read()); print('OK')"
  # Must print OK

  python -c "import ast; ast.parse(open('services/telegram-bot/src/config.py').read()); print('OK')"
  # Must print OK

  grep -c "SUPPORTED_LOCALES" services/telegram-bot/src/middlewares/i18n.py
  # Should match (constant exists)

  python -c "
import ast, sys
tree = ast.parse(open('services/telegram-bot/src/middlewares/i18n.py').read())
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if hasattr(target, 'id') and target.id == 'SUPPORTED_LOCALES':
                if isinstance(node.value, ast.Tuple):
                    print(f'SUPPORTED_LOCALES has {len(node.value.elts)} locales')
                    sys.exit(0)
print('SUPPORTED_LOCALES not found as tuple')
"
  # Must print: SUPPORTED_LOCALES has 39 locales

DONE CRITERIA: SUPPORTED_LOCALES has 39 entries. LANGUAGE_MAP covers all Telegram codes. config.py default has 39 locales. All Python files parse without syntax errors.
```

### infra-verify

```
You are infra-verify on the CyberVPN team (Phase 9). You verify Docker network segmentation is complete and all services reference the correct 4-tier networks.
You work ONLY in infra/. Do NOT modify files unless a service is still on the old network.

CONTEXT — Phase 8 defined 4 Docker networks:
- cybervpn-frontend — for public-facing services
- cybervpn-backend — for API/worker services
- cybervpn-data — for database/cache tier
- cybervpn-monitoring — for observability stack

Phase 8 already removed all `remnawave-network` references (confirmed: grep returns 0).

KEY FILE:
- infra/docker-compose.yml — the single source of truth for all services

YOUR TASK:

IV-1: Verify network assignments (P1)

  STEP 1: Run docker compose config to validate:
    cd infra && docker compose config -q && echo "VALID" || echo "INVALID"

  STEP 2: Check all profiles:
    docker compose --profile monitoring config -q && echo "Monitoring: VALID" || echo "INVALID"
    docker compose --profile bot config -q && echo "Bot: VALID" || echo "INVALID"

  STEP 3: List all networks referenced by services:
    docker compose config 2>/dev/null | grep -E "^\s+networks:" -A 20 | grep "cybervpn-" | sort | uniq -c | sort -rn

  STEP 4: Verify the 4 top-level networks exist:
    docker compose config 2>/dev/null | grep "name: cybervpn-" | sort -u
    # Must show exactly 4:
    # cybervpn-backend
    # cybervpn-data
    # cybervpn-frontend
    # cybervpn-monitoring

  STEP 5: Verify NO old network references remain:
    grep "remnawave-network" infra/docker-compose.yml | wc -l
    # Must be 0

  STEP 6: Verify network assignment logic:
    - Services that talk to PostgreSQL or Redis MUST be on cybervpn-data
    - Services that expose HTTP endpoints MUST be on cybervpn-backend or cybervpn-frontend
    - Monitoring services (prometheus, grafana, loki, tempo, etc.) MUST be on cybervpn-monitoring
    - Caddy (reverse proxy) should be on cybervpn-frontend + cybervpn-backend (bridges tiers)

  Report findings. If any service is missing proper network assignment, fix it.
  If everything looks correct, report "All services properly segmented across 4 networks."

DONE CRITERIA: docker compose config passes for all profiles. 4 networks defined. 0 old network refs. Report network assignment summary.
```

### verify

```
You are verify on the CyberVPN team (Phase 9). You run ALL builds, tests, lints, and verification checks across all platforms.
You work across ALL directories. You do NOT write production code — only fix minor issues (typos, missing imports) to unblock builds.

CONTEXT — Other agents are working on:
- frontend-i18n: Adding zh-Hant locale to Frontend (config + messages)
- mobile-i18n: Adding zh-Hant locale to Mobile (ARB + language_repository)
- bot-i18n: Expanding bot middleware from 2→39 active locales
- infra-verify: Verifying Docker network segmentation

RULES:
- Wait for each agent to finish before running their verification block.
- If a check fails, identify the RESPONSIBLE AGENT and report the issue to lead.
- You MAY fix minor issues (missing comma, import path, whitespace) to unblock builds.
- You MUST NOT make substantive logic changes — report to lead instead.
- Run checks in order: syntax → lint → build → test (fail-fast)
- Run all verification blocks as agents complete. Don't wait for all agents to finish.

YOUR TASKS:

VF-1: Frontend verification (after frontend-i18n complete)

  STEP 1: Locale count
  ls frontend/messages/ | wc -l
  → Must be 39

  STEP 2: zh-Hant in config
  grep "zh-Hant" frontend/src/i18n/config.ts
  → Must match

  STEP 3: zh-Hant messages exist
  ls frontend/messages/zh-Hant/ | wc -l
  → Must be > 0 (same number of files as zh-CN)

  STEP 4: Build
  cd frontend && npm run build 2>&1 | tail -10
  → Must pass

  STEP 5: Lint
  cd frontend && npm run lint 2>&1 | tail -5
  → Must pass

VF-2: Mobile verification (after mobile-i18n complete)

  STEP 1: ARB file exists
  ls cybervpn_mobile/lib/core/l10n/arb/app_zh_Hant.arb
  → Must exist

  STEP 2: Language repository updated
  grep "zh_Hant" cybervpn_mobile/lib/features/settings/data/repositories/language_repository.dart
  → Must match

  STEP 3: ARB count
  ls cybervpn_mobile/lib/core/l10n/arb/app_*.arb | wc -l
  → Must be 39

  STEP 4: Flutter analyze
  cd cybervpn_mobile && flutter analyze --no-fatal-infos 2>&1 | tail -10
  → 0 errors

VF-3: Bot verification (after bot-i18n complete)

  STEP 1: Python syntax check
  python -c "import ast; ast.parse(open('services/telegram-bot/src/middlewares/i18n.py').read()); print('i18n.py: OK')"
  python -c "import ast; ast.parse(open('services/telegram-bot/src/config.py').read()); print('config.py: OK')"
  → Both must print OK

  STEP 2: SUPPORTED_LOCALES count
  python -c "
import ast
tree = ast.parse(open('services/telegram-bot/src/middlewares/i18n.py').read())
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if hasattr(target, 'id') and target.id == 'SUPPORTED_LOCALES':
                if isinstance(node.value, ast.Tuple):
                    print(f'SUPPORTED_LOCALES: {len(node.value.elts)} locales')
"
  → Must print: SUPPORTED_LOCALES: 39 locales

  STEP 3: Config available_languages
  grep -A2 "available_languages" services/telegram-bot/src/config.py | head -5
  → Must show list with 39 locale codes

  STEP 4: Colored buttons still work (regression check)
  grep -rn "style=" services/telegram-bot/src/ --include="*.py" | wc -l
  → Must be >= 200 (was 227, should be unchanged)

  STEP 5: All Python files compile
  find services/telegram-bot/src/ -name "*.py" -exec python -m py_compile {} \; 2>&1 | wc -l
  → Must be 0

VF-4: Infrastructure verification (after infra-verify complete)

  STEP 1: Docker compose validation
  cd infra && docker compose config -q && echo "Default: OK" || echo "INVALID"
  cd infra && docker compose --profile monitoring config -q && echo "Monitoring: OK" || echo "INVALID"
  cd infra && docker compose --profile bot config -q && echo "Bot: OK" || echo "INVALID"
  → All must show OK

  STEP 2: Network count
  cd infra && docker compose config 2>/dev/null | grep "name: cybervpn-" | sort -u | wc -l
  → Must be 4

VF-5: Cross-platform locale consistency check

  STEP 1: Count comparison
  echo "Frontend: $(ls frontend/messages/ | wc -l) locales"
  echo "Mobile: $(ls cybervpn_mobile/lib/core/l10n/arb/app_*.arb | wc -l) locales"
  echo "Bot: $(ls services/telegram-bot/src/locales/ | wc -l) locales"
  → All must show 39

  STEP 2: zh-Hant presence everywhere
  ls frontend/messages/zh-Hant/ >/dev/null 2>&1 && echo "Frontend zh-Hant: OK" || echo "MISSING"
  ls cybervpn_mobile/lib/core/l10n/arb/app_zh_Hant.arb >/dev/null 2>&1 && echo "Mobile zh-Hant: OK" || echo "MISSING"
  ls services/telegram-bot/src/locales/zh-Hant/ >/dev/null 2>&1 && echo "Bot zh-Hant: OK" || echo "MISSING"
  → All must show OK

DONE CRITERIA: All 5 verification blocks pass. All platforms at 39 locales. Zero regressions.
```

---

## Task Registry & Dependencies

### Dependency Graph

```
                     +-- FI-1 (add zh-Hant to config.ts) ─────── independent
                     |
                     +-- FI-2 (create zh-Hant messages/) ──────── independent
                     |
                     +-- FI-3 (fix CLAUDE.md "41 locales") ────── independent
                     |
PHASE 9 START ───────+-- MI-1 (create app_zh_Hant.arb) ─────────── independent
                     |
                     +-- MI-2 (add to language_repository) ──────── independent
                     |
                     +-- BI-1 (expand SUPPORTED_LOCALES + LANGUAGE_MAP) ── independent
                     |
                     +-- BI-2 (expand config.py available_languages) ───── independent
                     |
                     +-- IV-1 (verify Docker networks) ──────────── independent
                     |
                     +-- VF-1 (frontend verify) ─────────────── after FI-*
                     |
                     +-- VF-2 (mobile verify) ───────────────── after MI-*
                     |
                     +-- VF-3 (bot verify) ──────────────────── after BI-*
                     |
                     +-- VF-4 (infra verify) ────────────────── after IV-1
                     |
                     +-- VF-5 (cross-platform consistency) ──── after VF-1, VF-2, VF-3
```

### Full Task Table

| ID | Task | Agent | Depends on | Priority |
|----|------|-------|------------|----------|
| FI-1 | Add zh-Hant to frontend/src/i18n/config.ts locales array | frontend-i18n | -- | P0 |
| FI-2 | Create frontend/messages/zh-Hant/ directory with JSON files | frontend-i18n | -- | P0 |
| FI-3 | Fix "41 locales" → "39 locales" in frontend/CLAUDE.md | frontend-i18n | -- | P2 |
| MI-1 | Create cybervpn_mobile/lib/core/l10n/arb/app_zh_Hant.arb | mobile-i18n | -- | P0 |
| MI-2 | Add zh_Hant LanguageItem to language_repository.dart | mobile-i18n | -- | P0 |
| BI-1 | Expand SUPPORTED_LOCALES (2→39) + LANGUAGE_MAP in i18n.py | bot-i18n | -- | P0 |
| BI-2 | Expand available_languages default in config.py (2→39) | bot-i18n | -- | P0 |
| IV-1 | Verify Docker 4-tier network assignment for all services | infra-verify | -- | P1 |
| VF-1 | Frontend: locale count + zh-Hant + build + lint | verify | FI-* | P0 |
| VF-2 | Mobile: ARB count + zh_Hant + flutter analyze | verify | MI-* | P0 |
| VF-3 | Bot: syntax + SUPPORTED_LOCALES count + config + colored buttons | verify | BI-* | P0 |
| VF-4 | Infra: compose validation + network count | verify | IV-1 | P0 |
| VF-5 | Cross-platform: all 3 services at 39 locales + zh-Hant everywhere | verify | VF-1..VF-3 | P0 |

### Task Counts

| Agent | Tasks | IDs |
|-------|-------|-----|
| frontend-i18n | 3 | FI-1, FI-2, FI-3 |
| mobile-i18n | 2 | MI-1, MI-2 |
| bot-i18n | 2 | BI-1, BI-2 |
| infra-verify | 1 | IV-1 |
| verify | 5 | VF-1, VF-2, VF-3, VF-4, VF-5 |
| **TOTAL** | **13** | |

---

## Lead Coordination Rules

1. **Spawn all 5 agents immediately.** Initial assignments:
   - `frontend-i18n` → FI-1 + FI-2 + FI-3 (sequential — config first, then messages, then docs)
   - `mobile-i18n` → MI-1 + MI-2 (sequential — ARB first, then language repo)
   - `bot-i18n` → BI-1 + BI-2 (sequential — middleware first, then config)
   - `infra-verify` → IV-1 (single task — fast)
   - `verify` → wait for dependencies, then VF-1 through VF-5 as agents complete

2. **Communication protocol:**
   - frontend-i18n finishes → messages verify ("frontend locales done, run VF-1")
   - mobile-i18n finishes → messages verify ("mobile locales done, run VF-2")
   - bot-i18n finishes → messages verify ("bot middleware expanded, run VF-3")
   - infra-verify finishes → messages verify ("infra networks verified, run VF-4")
   - verify runs VF-5 ONLY after VF-1 + VF-2 + VF-3 all pass

3. **Parallel execution strategy:**
   - Wave 1 (immediate, ALL parallel): FI-1, MI-1, BI-1, IV-1
   - Wave 2 (quick follow-ups): FI-2 (after FI-1), FI-3, MI-2 (after MI-1), BI-2 (after BI-1)
   - Wave 3 (verification): VF-1 (after FI-*), VF-2 (after MI-*), VF-3 (after BI-*), VF-4 (after IV-1)
   - Wave 4 (final): VF-5 (after VF-1 + VF-2 + VF-3)

4. **File conflict prevention:**
   - `frontend-i18n` owns: `frontend/src/i18n/config.ts`, `frontend/messages/zh-Hant/`, `frontend/CLAUDE.md`
   - `mobile-i18n` owns: `cybervpn_mobile/lib/core/l10n/arb/app_zh_Hant.arb`, `cybervpn_mobile/lib/features/settings/data/repositories/language_repository.dart`
   - `bot-i18n` owns: `services/telegram-bot/src/middlewares/i18n.py`, `services/telegram-bot/src/config.py`
   - `infra-verify` reads: `infra/docker-compose.yml` (may edit if network assignment is wrong)
   - `verify` writes NOTHING — only runs commands and reports
   - No file conflicts possible between agents

5. **Do NOT start implementing if you are lead — delegate.** Use delegate mode exclusively.

6. **Progress tracking.** Use the shared TaskList (TaskCreate/TaskUpdate). Do NOT use beads (`bd`) — SQLite lock conflicts with parallel agents.

7. **If any agent is blocked >5 minutes:** reassign them to an independent task or help unblock.

8. **Verification failures:** If verify reports a failure:
   - Frontend build error → assign to frontend-i18n
   - Flutter analyze error → assign to mobile-i18n
   - Python syntax error → assign to bot-i18n
   - Compose validation error → assign to infra-verify

---

## Prohibitions

- Do NOT downgrade library versions (Next.js 16, React 19, Python 3.13, Flutter 3.x, aiogram 3.25, etc.)
- Do NOT break existing working endpoints, pages, tests, or features
- Do NOT modify existing locale files (en, ru, zh-CN, etc.) — only ADD new zh-Hant files
- Do NOT change the default locale in any service (en-EN for frontend, ru for bot)
- Do NOT create files outside your assigned directory
- Do NOT use beads (`bd create/close`) — use TaskList instead
- Do NOT modify button styles or keyboard files in the telegram bot
- Do NOT modify existing ARB files in the mobile app
- Do NOT change the I18nManager or FluentTranslator Python classes
- Do NOT change docker-compose service names, ports, or volume names
- Do NOT manually translate locale files — use copies of zh-CN as placeholder
- Do NOT modify test files — locale additions should not require test changes
- Do NOT add `any` types in frontend code

---

## Final Verification (Lead runs after ALL tasks + VF-* complete)

```bash
# ===== CROSS-PLATFORM LOCALE SYNC =====
echo "=== Locale Counts ==="
echo "Frontend: $(ls frontend/messages/ | wc -l) locales"
echo "Mobile:   $(ls cybervpn_mobile/lib/core/l10n/arb/app_*.arb | wc -l) locales"
echo "Bot:      $(ls services/telegram-bot/src/locales/ | wc -l) locales"
# ALL must show 39

echo ""
echo "=== zh-Hant Presence ==="
ls frontend/messages/zh-Hant/ >/dev/null 2>&1 && echo "Frontend zh-Hant: OK" || echo "Frontend zh-Hant: MISSING"
ls cybervpn_mobile/lib/core/l10n/arb/app_zh_Hant.arb >/dev/null 2>&1 && echo "Mobile zh-Hant: OK" || echo "Mobile zh-Hant: MISSING"
ls services/telegram-bot/src/locales/zh-Hant/ >/dev/null 2>&1 && echo "Bot zh-Hant: OK" || echo "Bot zh-Hant: MISSING"
# ALL must show OK

# ===== BOT MIDDLEWARE =====
echo ""
echo "=== Bot SUPPORTED_LOCALES ==="
python3 -c "
import ast
tree = ast.parse(open('services/telegram-bot/src/middlewares/i18n.py').read())
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if hasattr(target, 'id') and target.id == 'SUPPORTED_LOCALES':
                if isinstance(node.value, ast.Tuple):
                    print(f'SUPPORTED_LOCALES: {len(node.value.elts)} locales')
"
# Must be 39

echo ""
echo "=== Bot config.py available_languages ==="
grep -c "\"am\"" services/telegram-bot/src/config.py
# Must be >= 1 (am is in the list)

# ===== BUILDS =====
echo ""
echo "=== Frontend Build ==="
cd frontend && npm run build 2>&1 | tail -3
# Must pass

echo ""
echo "=== Mobile Analyze ==="
cd ../cybervpn_mobile && flutter analyze --no-fatal-infos 2>&1 | tail -3
# 0 errors

echo ""
echo "=== Bot Syntax ==="
cd ../services/telegram-bot
python -c "import ast; ast.parse(open('src/middlewares/i18n.py').read()); ast.parse(open('src/config.py').read()); print('All Python: OK')"
# Must print OK

echo ""
echo "=== Infrastructure ==="
cd ../../infra && docker compose config -q && echo "Compose: VALID" || echo "Compose: INVALID"
docker compose config 2>/dev/null | grep "name: cybervpn-" | sort -u | wc -l
# Must be 4
```

All commands must pass with expected values. If any fail, assign fix to the responsible agent.

---

## Completion Checklist

### Frontend — zh-Hant Locale (frontend-i18n)
- [ ] `zh-Hant` added to `frontend/src/i18n/config.ts` locales array
- [ ] `frontend/messages/zh-Hant/` directory created with all JSON message files
- [ ] `frontend/CLAUDE.md` updated: "41 locales" → "39 locales"
- [ ] `ls frontend/messages/ | wc -l` returns 39
- [ ] `npm run build` passes
- [ ] `npm run lint` passes

### Mobile — zh-Hant Locale (mobile-i18n)
- [ ] `cybervpn_mobile/lib/core/l10n/arb/app_zh_Hant.arb` created with `"@@locale": "zh_Hant"`
- [ ] LanguageItem for zh_Hant added to language_repository.dart
- [ ] Comment in language_repository.dart updated to "39 locales"
- [ ] `ls cybervpn_mobile/lib/core/l10n/arb/app_*.arb | wc -l` returns 39
- [ ] `flutter analyze` passes with 0 errors

### Telegram Bot — Middleware Expansion (bot-i18n)
- [ ] `SUPPORTED_LOCALES` in i18n.py has 39 entries
- [ ] `LANGUAGE_MAP` in i18n.py maps all Telegram language codes
- [ ] `available_languages` in config.py defaults to 39 locales
- [ ] All Python files pass syntax check
- [ ] Colored buttons unchanged (227+ style= usages)

### Infrastructure — Network Verification (infra-verify)
- [ ] `docker compose config -q` passes for all profiles
- [ ] 4 networks defined: cybervpn-frontend, cybervpn-backend, cybervpn-data, cybervpn-monitoring
- [ ] 0 `remnawave-network` references

### Cross-Platform Consistency
- [ ] Frontend: 39 locales
- [ ] Mobile: 39 locales
- [ ] Bot: 39 locales (directories) + 39 active (middleware)
- [ ] zh-Hant present in ALL 3 services

### Build Verification
- [ ] `npm run build` passes (Frontend)
- [ ] `npm run lint` passes (Frontend)
- [ ] `flutter analyze --no-fatal-infos` passes (Mobile)
- [ ] All .py files compile (Bot)
- [ ] `docker compose config -q` passes (Infra)
