# CyberVPN — Multi-Profile Support (Hiddify-style) — Agent Team Prompt

> Requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`.
> User presses **Shift+Tab** to enter delegate mode, then pastes this prompt.
> Teammates load `CLAUDE.md` automatically. Spawn prompts contain ONLY task-specific context.
> **Scope**: Implement multi-profile (multi-subscription) support in `cybervpn_mobile/` — local-only storage with Drift database, Hiddify-style profile switching, subscription URL management, and full UI integration.
> **Out of scope**: Backend API changes, admin dashboard (frontend/), infrastructure (infra/), Telegram bot, cloud sync between devices.

---

## 1. Executive Summary

**Problem Statement**: CyberVPN mobile currently supports a single subscription per user session. Power users and privacy-conscious individuals often maintain multiple VPN subscriptions (personal, work, different providers) and need seamless switching — a capability competitors like Hiddify already provide.

**Proposed Solution**: Implement Hiddify-style multi-profile management where each profile represents a subscription URL (remote) or a manually imported config (local). Users can add, remove, switch between, and auto-update multiple profiles. Profiles are stored in a local Drift (SQLite) database with encrypted sensitive fields.

**Success Criteria**:
1. User can add ≥5 profiles via subscription URL, QR code, clipboard, or deep link — each resolves to a list of VPN servers within ≤3 seconds
2. Active profile switch completes in <500ms (UI response) without VPN reconnection unless connected
3. Subscription auto-update refreshes all remote profiles within configurable interval (default: 1 hour) with ≤2% failure rate on stable networks
4. Profile data persists across app kills and device reboots with zero data loss (verified via integration tests)
5. `flutter analyze` passes with zero errors, `flutter test` passes all new + existing tests
6. All 27 existing locales include new profile-related strings

---

## 2. User Experience & Functionality

### User Personas

| Persona | Description | Primary Need |
|---------|-------------|--------------|
| **Multi-Sub User** | Has 2-3 VPN subscriptions from different providers (CyberVPN + third-party) | Quick switching between providers |
| **Privacy Power User** | Separates personal/work VPN profiles for operational security | Named profiles with clear boundaries |
| **Config Collector** | Imports configs from Telegram channels, QR codes, and subscription links | Batch import and organization |
| **Single-Sub User** | Existing user with one CyberVPN subscription (must not regress) | Zero friction — auto-migrated, invisible complexity |

### User Stories & Acceptance Criteria

**US-1: Add Remote Profile via Subscription URL**
> As a multi-sub user, I want to add a VPN subscription by pasting a URL so that the app fetches my available servers automatically.

Acceptance Criteria:
- Paste URL into "Add Profile" screen → app validates URL format (HTTP/HTTPS)
- App fetches URL content, parses subscription headers: `profile-title`, `subscription-userinfo`, `profile-update-interval`, `support-url`
- If URL returns Base64-encoded V2Ray/Clash/Sing-box configs → parse into individual `VpnConfigEntity` entries
- If fetch fails → show error with retry button, profile saved in "pending" state
- Duplicate URL detection: if URL already exists → show "Profile already exists" toast, navigate to existing profile
- New profile appears in profile list within ≤1 second of successful parse
- Auto-update interval extracted from `profile-update-interval` header, fallback: 1 hour

**US-2: Add Local Profile via QR/Clipboard/Deep Link**
> As a config collector, I want to import VPN configs from QR codes and clipboard so that I can use configs shared in communities.

Acceptance Criteria:
- QR scanner (existing `qr_scanner_screen.dart`) produces a `LocalProfile` entity
- Clipboard import (existing `clipboard_import_button.dart`) triggers profile creation
- Deep link handler (existing `deep_link_handler.dart`) triggers profile creation for `cybervpn://` and `v2ray://` schemes
- Local profiles have no subscription URL, no auto-update, no traffic/expiry metadata
- Local profiles show "Local" badge in profile list

**US-3: Switch Active Profile**
> As a multi-sub user, I want to switch between my profiles so that I can use different VPN servers from different subscriptions.

Acceptance Criteria:
- Profile list accessible from: (a) new "Profiles" tab in bottom nav, OR (b) profile selector in connection screen header
- Tap on profile → sets as active → server list refreshes to show only that profile's servers
- If VPN is connected → show confirmation dialog: "Switch profile? This will disconnect your current VPN session."
- On confirm → disconnect → switch → optionally auto-connect to best server of new profile
- Active profile indicator (highlighted border/checkmark) always visible in profile list
- Profile switch completes in <500ms (UI state change), VPN reconnect is separate async operation

**US-4: View Profile Details & Subscription Info**
> As a multi-sub user, I want to see my subscription details (traffic used, expiry date, server count) per profile.

Acceptance Criteria:
- Profile detail screen shows: name, subscription URL (masked, copyable), server count, last updated timestamp
- For remote profiles with `subscription-userinfo`: show traffic used/total (progress bar), expiry date, days remaining
- For expired profiles: show "Expired" badge with red indicator, disable "Connect" for that profile's servers
- "Update Now" button manually triggers subscription refresh
- "Test URL" button checks if subscription URL is still reachable (GET with timeout 10s)

**US-5: Edit, Delete, Reorder Profiles**
> As a user, I want to manage my profile list so that I can keep it organized.

Acceptance Criteria:
- Long-press on profile → context menu: Edit, Delete, Move Up/Down
- Edit: change profile name (local override), toggle auto-update
- Delete: confirmation dialog → removes profile + all associated configs from Drift DB
- Cannot delete the last remaining profile (show toast: "At least one profile required")
- Drag-to-reorder in profile list (using `ReorderableListView`)
- Active profile cannot be deleted (must switch first)

**US-6: Auto-Update Subscriptions**
> As a user, I want my remote profiles to auto-update so that I always have the latest server list.

Acceptance Criteria:
- Background update runs at each profile's configured interval (extracted from header, or default 1 hour)
- Update runs when app returns to foreground IF interval has elapsed
- Update runs on app startup IF interval has elapsed
- On update: fetch URL → parse → diff servers → add new, remove stale, keep existing with favorites preserved
- If update fails → retry with exponential backoff (1min, 5min, 15min), max 3 retries
- Show notification dot on profile if update found new servers
- Update does NOT interrupt active VPN connection — queues changes until disconnect

**US-7: Seamless Migration for Existing Users**
> As a single-sub user upgrading the app, I want my existing subscription to automatically become my first profile.

Acceptance Criteria:
- On first launch after update: auto-create "CyberVPN" profile from existing `SubscriptionEntity`
- Migrate all existing `VpnConfigEntity` entries to belong to this profile
- Mark as active profile
- User sees no disruption — identical UX to before, just with profile infrastructure underneath
- Migration runs once, tracked via `SharedPreferences` flag `profile_migration_v1_complete`

### Non-Goals (Out of Scope)

- Cloud sync of profiles between devices (future phase — architecture should support it)
- Profile sharing/export as file or link
- Per-profile DNS/split-tunnel settings (future: per-profile `SettingsOverride`)
- Admin dashboard profile management
- Backend API changes for multi-profile
- WireGuard/OpenVPN profile import (V2Ray-based only, matching current engine)
- Profile groups/folders (future enhancement)

---

## 3. Technical Specifications

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                       │
├──────────────┬──────────────┬──────────────┬────────────────┤
│ ProfileList  │ ProfileDetail│ AddProfile   │ ProfileSelector│
│ Screen       │ Screen       │ Screen       │ Widget         │
├──────────────┴──────────────┴──────────────┴────────────────┤
│                     PROVIDERS (Riverpod)                      │
├──────────────┬──────────────┬───────────────────────────────┤
│ ProfileList  │ ActiveProfile│ ProfileUpdate │ ProfileImport │
│ Notifier     │ Notifier     │ Notifier      │ Notifier      │
├──────────────┴──────────────┴───────────────┴───────────────┤
│                      DOMAIN LAYER                            │
├──────────────┬──────────────┬───────────────────────────────┤
│ ProfileEntity│ ProfileRepo  │ UseCases:                     │
│ (Freezed)    │ (abstract)   │  AddProfile, SwitchProfile,   │
│              │              │  UpdateSubscription,           │
│              │              │  DeleteProfile, MigrateProfiles│
├──────────────┴──────────────┴───────────────────────────────┤
│                       DATA LAYER                             │
├──────────────┬──────────────┬───────────────────────────────┤
│ Drift DB     │ Subscription │ Profile                       │
│ (SQLite)     │ Fetcher      │ Repository                    │
│ Tables:      │ (HTTP parser)│ Impl                          │
│  profiles,   │              │                               │
│  profile_    │              │                               │
│  configs     │              │                               │
├──────────────┴──────────────┴───────────────────────────────┤
│                  EXISTING INFRASTRUCTURE                      │
│  SecureStorage │ Dio │ V2Ray Engine │ SharedPreferences       │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```
1. ADD REMOTE PROFILE:
   User pastes URL → AddProfileNotifier.addByUrl(url)
     → SubscriptionFetcher.fetch(url) [Dio GET]
       → Parse HTTP headers (profile-title, subscription-userinfo, profile-update-interval)
       → Parse body (Base64 → V2Ray URIs → VpnConfigEntity[])
     → ProfileRepository.save(ProfileEntity + configs)
       → Drift INSERT into profiles + profile_configs tables
     → ProfileListNotifier.refresh()

2. SWITCH PROFILE:
   User taps profile → ActiveProfileNotifier.switchTo(profileId)
     → IF connected: show dialog → disconnect VPN
     → ProfileRepository.setActive(profileId)
       → Drift UPDATE active=false WHERE active=true
       → Drift UPDATE active=true WHERE id=profileId
     → ServerListNotifier rebuilds from new profile's configs
     → VpnConnectionNotifier.state → disconnected (ready for new profile)

3. AUTO-UPDATE:
   Timer fires / App foreground → ProfileUpdateNotifier.updateAllDue()
     → For each remote profile WHERE lastUpdate + interval < now:
       → SubscriptionFetcher.fetch(url) → parse
       → Diff: new configs, removed configs, unchanged
       → Drift UPSERT profile_configs, preserve isFavorite
       → Update profile.lastUpdatedAt
     → Emit notification if new servers found
```

### Database Schema (Drift)

```dart
// File: cybervpn_mobile/lib/core/data/database/app_database.dart

@DriftDatabase(tables: [Profiles, ProfileConfigs])
class AppDatabase extends _$AppDatabase {
  static const int schemaVersion = 1;
}

// Table: profiles
class Profiles extends Table {
  TextColumn get id => text()();                          // UUID v4
  TextColumn get name => text().withLength(min: 1, max: 255)();
  TextColumn get type => textEnum<ProfileType>()();       // remote | local
  TextColumn get subscriptionUrl => text().nullable()();  // encrypted at rest
  BoolColumn get isActive => boolean().withDefault(const Constant(false))();
  IntColumn get sortOrder => integer().withDefault(const Constant(0))();
  DateTimeColumn get createdAt => dateTime()();
  DateTimeColumn get lastUpdatedAt => dateTime().nullable()();
  // Subscription info (from headers)
  IntColumn get uploadBytes => integer().withDefault(const Constant(0))();
  IntColumn get downloadBytes => integer().withDefault(const Constant(0))();
  IntColumn get totalBytes => integer().withDefault(const Constant(0))();
  DateTimeColumn get expiresAt => dateTime().nullable()();
  IntColumn get updateIntervalMinutes => integer().withDefault(const Constant(60))();
  TextColumn get supportUrl => text().nullable()();
  TextColumn get testUrl => text().nullable()();

  @override
  Set<Column> get primaryKey => {id};
}

// Table: profile_configs (VPN server configs belonging to a profile)
class ProfileConfigs extends Table {
  TextColumn get id => text()();                          // UUID v4
  TextColumn get profileId => text().references(Profiles, #id)();
  TextColumn get name => text()();
  TextColumn get serverAddress => text()();
  IntColumn get port => integer()();
  TextColumn get protocol => textEnum<VpnProtocol>()();
  TextColumn get configData => text()();                  // full V2Ray URI / JSON
  TextColumn get remark => text().nullable()();
  BoolColumn get isFavorite => boolean().withDefault(const Constant(false))();
  IntColumn get sortOrder => integer().withDefault(const Constant(0))();
  IntColumn get latencyMs => integer().nullable()();      // last ping result
  DateTimeColumn get createdAt => dateTime()();

  @override
  Set<Column> get primaryKey => {id};
}

enum ProfileType { remote, local }
```

### Domain Entities (Freezed)

```dart
// File: cybervpn_mobile/lib/features/vpn_profiles/domain/entities/vpn_profile.dart

@freezed
sealed class VpnProfile with _$VpnProfile {
  /// Remote profile fetched from subscription URL
  const factory VpnProfile.remote({
    required String id,
    required String name,
    required String subscriptionUrl,
    required bool isActive,
    required int sortOrder,
    required DateTime createdAt,
    DateTime? lastUpdatedAt,
    @Default(0) int uploadBytes,
    @Default(0) int downloadBytes,
    @Default(0) int totalBytes,
    DateTime? expiresAt,
    @Default(60) int updateIntervalMinutes,
    String? supportUrl,
    String? testUrl,
    @Default([]) List<ProfileServer> servers,
  }) = RemoteVpnProfile;

  /// Local profile from manual import (QR, clipboard, deep link)
  const factory VpnProfile.local({
    required String id,
    required String name,
    required bool isActive,
    required int sortOrder,
    required DateTime createdAt,
    DateTime? lastUpdatedAt,
    @Default([]) List<ProfileServer> servers,
  }) = LocalVpnProfile;
}

@freezed
sealed class ProfileServer with _$ProfileServer {
  const factory ProfileServer({
    required String id,
    required String profileId,
    required String name,
    required String serverAddress,
    required int port,
    required VpnProtocol protocol,
    required String configData,
    String? remark,
    @Default(false) bool isFavorite,
    required int sortOrder,
    int? latencyMs,
    required DateTime createdAt,
  }) = _ProfileServer;
}

// Subscription metadata parsed from HTTP headers
@freezed
sealed class SubscriptionInfo with _$SubscriptionInfo {
  const factory SubscriptionInfo({
    String? title,
    @Default(0) int uploadBytes,
    @Default(0) int downloadBytes,
    @Default(0) int totalBytes,
    DateTime? expiresAt,
    @Default(60) int updateIntervalMinutes,
    String? supportUrl,
  }) = _SubscriptionInfo;

  const SubscriptionInfo._();

  bool get isExpired => expiresAt != null && expiresAt!.isBefore(DateTime.now());
  int get consumedBytes => uploadBytes + downloadBytes;
  double get usageRatio => totalBytes > 0 ? consumedBytes / totalBytes : 0.0;
  Duration get remaining => expiresAt != null
      ? expiresAt!.difference(DateTime.now())
      : Duration.zero;
}
```

### Integration Points

| Component | Integration | Details |
|-----------|------------|---------|
| **Existing VPN engine** | `VpnConfigEntity` → `ProfileServer` | `ProfileServer` maps 1:1 to `VpnConfigEntity` for connection. Adapter layer converts. |
| **Existing config_import** | `ImportedConfig` → `VpnProfile.local` | Existing parsers (vmess, vless, trojan, shadowsocks, subscription_url) feed into profile creation. |
| **Existing server list** | `ServerEntity` → scoped by active profile | `ServerListNotifier` filters by active profile ID. CyberVPN-native servers come from backend API (existing), third-party from local profile. |
| **Existing subscription** | `SubscriptionEntity` → migration | On first launch, existing subscription auto-migrates to a "CyberVPN" `RemoteVpnProfile`. |
| **Existing VPN connection** | `VpnConnectionNotifier` | No changes to connection logic. It receives a `VpnConfigEntity` (from `ProfileServer` adapter). |
| **Existing auth** | No changes | Auth manages CyberVPN account. Profiles are orthogonal — local storage layer. |
| **Navigation (GoRouter)** | New routes | `/profiles`, `/profiles/:id`, `/profiles/add`, `/profiles/add/url`, `/profiles/add/qr` |

### Security & Privacy

- **Subscription URLs**: Stored in Drift DB with field-level encryption via `flutter_secure_storage` master key. URL contains auth tokens — must not leak.
- **Config data**: V2Ray config JSON may contain server credentials — encrypted at rest in `profile_configs.configData`.
- **Drift DB location**: App-private directory (`getApplicationDocumentsDirectory()`), not accessible without root.
- **No PII in analytics**: Profile names, URLs, server addresses NEVER sent to Sentry/Firebase. Only anonymized events: `profile_added{type: remote|local}`, `profile_switched`, `profile_deleted`.
- **Export/backup prevention**: DB file excluded from Android Auto Backup via `android:fullBackupContent` rules (subscription URLs are auth-scoped, not portable).

### New Dependencies

| Package | Version | Purpose | Justification |
|---------|---------|---------|---------------|
| `drift` | `^2.27.0` | Type-safe SQLite ORM | Needed for local profile storage. Freezed-compatible, compile-time SQL verification, migrations support. Used by Hiddify-level apps. |
| `drift_dev` | `^2.27.0` | Code generation for Drift | Dev dependency, generates type-safe query classes. |
| `sqlite3_flutter_libs` | `^0.5.30` | Native SQLite binaries | Required by Drift on mobile platforms. |
| `path_provider` | `^2.1.6` | App documents directory | Needed for Drift DB file location. Already transitive dep — pinning explicitly. |
| `path` | `^1.9.1` | Path manipulation | Already transitive dep — pinning explicitly for DB path construction. |

**No version downgrades.** All new packages. Existing packages untouched.

---

## 4. Risks & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Drift DB migration on future schema changes | Medium | High | Implement `schemaVersion` with step migrations from day 1. Never break schema. |
| Subscription URL fetch blocked by network restrictions | Medium | Medium | Retry with exponential backoff. Support proxy-through-connected-VPN for fetching. |
| Config parser fails on unknown V2Ray format | High | Low | Graceful degradation — skip unparseable configs, log warning, show partial results. |
| Active profile switch while VPN connected causes crash | Low | High | State machine enforces disconnect-before-switch. Integration test covers this path. |
| Existing user migration loses data | Low | Critical | Migration is additive only (INSERT, not UPDATE/DELETE). Existing `SharedPreferences` and `SecureStorage` data untouched. Rollback: if migration flag set but DB empty → re-run. |
| Drift + build_runner conflicts with existing Freezed generation | Low | Medium | Drift uses separate `.drift.dart` files, no conflict with `.freezed.dart`. Verified compatible. |

### Phased Rollout

- **Phase A (this prompt)**: Core profile management — Drift DB, entities, repository, providers, all screens, migration, auto-update, full test coverage
- **Phase B (future)**: Profile groups/folders, per-profile DNS settings, per-profile split tunnel rules
- **Phase C (future)**: Cloud sync via backend API (requires new endpoints), profile sharing/export

---

## 5. Team

| Role | Agent name | Model | Working directory | subagent_type | Tasks |
|------|-----------|-------|-------------------|---------------|-------|
| Lead (you) | — | opus | all (coordination only) | — | 0 |
| Database & Data Layer | `data-layer-dev` | sonnet | `cybervpn_mobile/` | general-purpose | 6 |
| Domain & Business Logic | `domain-dev` | sonnet | `cybervpn_mobile/` | general-purpose | 5 |
| Presentation & UI | `ui-dev` | sonnet | `cybervpn_mobile/` | general-purpose | 7 |
| Integration & Migration | `integration-dev` | sonnet | `cybervpn_mobile/` | general-purpose | 5 |
| Test Engineer | `test-eng` | sonnet | `cybervpn_mobile/test/` | general-purpose | 6 |

---

## 6. Spawn Prompts

### data-layer-dev

```
You are data-layer-dev on the CyberVPN team (Multi-Profile). You build the Drift database, data sources, and data models.
Stack: Flutter, Dart 3.10+, Drift 2.27+, Freezed 3.x, Riverpod 3.x, Clean Architecture.
You work ONLY in cybervpn_mobile/.

CONTEXT — What already exists:
- No local database — app uses SecureStorage (encrypted) + SharedPreferences (plaintext) only
- VpnConfigEntity: id, name, serverAddress, port, protocol, configData, remark, isFavorite (Freezed)
- SubscriptionEntity: id, planId, userId, status, startDate, endDate, trafficUsed/Limit, devices, subscriptionLink (Freezed)
- ImportedConfig: id, name, rawUri, protocol, serverAddress, port, source, subscriptionUrl (Freezed)
- Existing parsers: vmess_parser, vless_parser, trojan_parser, shadowsocks_parser, subscription_url_parser
- pubspec.yaml at cybervpn_mobile/pubspec.yaml
- Core data utilities at lib/core/data/
- Core storage at lib/core/storage/ (secure_storage.dart, local_storage.dart)

KEY FILES TO READ FIRST:
- cybervpn_mobile/pubspec.yaml (current dependencies)
- cybervpn_mobile/lib/features/vpn/domain/entities/vpn_config_entity.dart
- cybervpn_mobile/lib/features/subscription/domain/entities/subscription_entity.dart
- cybervpn_mobile/lib/features/config_import/domain/entities/imported_config.dart
- cybervpn_mobile/lib/features/config_import/data/parsers/subscription_url_parser.dart
- cybervpn_mobile/lib/core/storage/secure_storage.dart

RULES:
- Use Context7 MCP to look up Drift documentation before writing any Drift code.
- Do NOT downgrade any existing package version.
- Do NOT modify existing entity files — create new entities in the new feature module.
- Follow existing file naming conventions: snake_case.dart.
- All Drift tables must have explicit primary keys.
- Subscription URLs must be encrypted at rest — use SecureStorage master key for field-level encryption.
- Run `dart run build_runner build --delete-conflicting-outputs` after creating Drift/Freezed files.
- Write comprehensive dartdoc comments on all public APIs.

YOUR TASKS:

DL-1: Add Drift + sqlite3_flutter_libs + path_provider dependencies (P0)
  - Add to pubspec.yaml dependencies:
    drift: ^2.27.0
    sqlite3_flutter_libs: ^0.5.30
    path_provider: ^2.1.6
    path: ^1.9.1
  - Add to dev_dependencies:
    drift_dev: ^2.27.0
  - Run `flutter pub get` to verify resolution
  - Verify NO version conflicts with existing packages
  - File: cybervpn_mobile/pubspec.yaml

DL-2: Create Drift database with profiles + profile_configs tables (P0)
  - Create directory: lib/core/data/database/
  - Create lib/core/data/database/app_database.dart:
    - Define `Profiles` table (see schema in PRD above)
    - Define `ProfileConfigs` table (see schema in PRD above)
    - Define `ProfileType` enum (remote, local)
    - Create `AppDatabase` class extending `_$AppDatabase`
    - Set schemaVersion = 1
    - Implement migration strategy (MigrationStrategy with onCreate)
    - Use lazy singleton pattern (opened on first access)
    - DB file path: `${appDocDir}/cybervpn_profiles.db`
  - Create lib/core/data/database/database_provider.dart:
    - Riverpod provider: `final appDatabaseProvider = Provider<AppDatabase>((ref) => AppDatabase());`
    - Disposal: override dispose to close DB
  - Run build_runner to generate `app_database.g.dart`
  - File: lib/core/data/database/app_database.dart (NEW), database_provider.dart (NEW)

DL-3: Create ProfileLocalDataSource with Drift queries (P0)
  - Create lib/features/vpn_profiles/data/datasources/profile_local_ds.dart:
    - Constructor takes `AppDatabase`
    - Methods (all return Drift-generated types, not domain entities):
      - `Future<List<ProfileWithConfigs>> watchAll()` → stream of all profiles with configs, ordered by sortOrder
      - `Stream<ProfileWithConfigs?> watchActiveProfile()` → stream of active profile with configs
      - `Future<ProfileData?> getById(String id)` → single profile by ID
      - `Future<ProfileData?> getBySubscriptionUrl(String url)` → find by URL (duplicate detection)
      - `Future<void> insert(ProfilesCompanion profile)` → insert new profile
      - `Future<void> insertConfigs(List<ProfileConfigsCompanion> configs)` → batch insert configs
      - `Future<void> update(String id, ProfilesCompanion companion)` → update profile fields
      - `Future<void> setActive(String id)` → transaction: set all active=false, set target active=true
      - `Future<void> delete(String id)` → transaction: delete configs WHERE profileId=id, then delete profile
      - `Future<void> deleteConfigsByProfileId(String profileId)` → clear all configs for a profile
      - `Future<void> updateSortOrders(Map<String, int> idToOrder)` → batch update sort orders
      - `Future<int> count()` → total profile count
    - Use Drift transactions for multi-table operations
    - Use Drift's `.watch()` for reactive streams
  - File: lib/features/vpn_profiles/data/datasources/profile_local_ds.dart (NEW)

DL-4: Create SubscriptionFetcher — HTTP-based subscription URL parser (P0)
  - Create lib/features/vpn_profiles/data/datasources/subscription_fetcher.dart:
    - Constructor takes `Dio` (existing DI)
    - Method: `Future<FetchResult> fetch(String url)`:
      1. GET url with headers: User-Agent: "CyberVPN/1.0", Accept: "*/*"
      2. Parse response headers:
         - `profile-title` → display name
         - `subscription-userinfo` → parse "upload=X; download=Y; total=Z; expire=T" format
         - `profile-update-interval` → update interval in hours (convert to minutes)
         - `support-url` → support/help link
         - `profile-web-page-url` → provider web page
      3. Parse response body:
         - Try Base64 decode
         - Split by newline
         - Each line is a V2Ray URI (vmess://, vless://, trojan://, ss://)
         - Use EXISTING parsers from config_import to parse each URI:
           - vmess_parser.dart → VmessParser.parse(uri)
           - vless_parser.dart → VlessParser.parse(uri)
           - trojan_parser.dart → TrojanParser.parse(uri)
           - shadowsocks_parser.dart → ShadowsocksParser.parse(uri)
         - If body is JSON (Sing-box format) → extract outbounds
         - If body is YAML (Clash format) → extract proxies
      4. Return FetchResult(subscriptionInfo, List<ParsedServer>)
    - Handle errors: timeout (10s), HTTP errors, parse errors
    - Log errors via existing Logger utility
  - Create lib/features/vpn_profiles/data/models/fetch_result.dart (Freezed):
    @freezed
    sealed class FetchResult with _$FetchResult {
      const factory FetchResult({
        required SubscriptionInfo info,
        required List<ParsedServer> servers,
      }) = _FetchResult;
    }
  - File: subscription_fetcher.dart (NEW), fetch_result.dart (NEW)

DL-5: Create data mappers — Drift ↔ Domain entity conversions (P1)
  - Create lib/features/vpn_profiles/data/mappers/profile_mapper.dart:
    - `ProfileMapper.toDomain(ProfileData row, List<ProfileConfigData> configs) → VpnProfile`
      - Map ProfileType.remote → VpnProfile.remote(...)
      - Map ProfileType.local → VpnProfile.local(...)
      - Map each ProfileConfigData → ProfileServer
    - `ProfileMapper.toCompanion(VpnProfile profile) → ProfilesCompanion`
    - `ProfileMapper.serverToCompanion(ProfileServer server) → ProfileConfigsCompanion`
    - `ProfileMapper.toVpnConfigEntity(ProfileServer server) → VpnConfigEntity`
      - Adapter: converts ProfileServer to existing VpnConfigEntity for VPN engine compatibility
  - Handle null-safety carefully — Drift rows use nullable differently than Freezed entities
  - File: profile_mapper.dart (NEW)

DL-6: Create encrypted URL storage wrapper (P1)
  - Create lib/features/vpn_profiles/data/security/encrypted_field.dart:
    - Uses existing SecureStorage to derive AES-256 key
    - `Future<String> encrypt(String plaintext)` → AES-GCM encrypt, return Base64
    - `Future<String> decrypt(String ciphertext)` → AES-GCM decrypt, return plaintext
    - Used by ProfileRepository to encrypt/decrypt subscriptionUrl before Drift INSERT/SELECT
  - Alternatively, use Drift's type converter with encryption:
    class EncryptedTextConverter extends TypeConverter<String, String> { ... }
  - Choose the approach that integrates cleanest with Drift — prefer type converter if possible
  - File: encrypted_field.dart (NEW)

DONE CRITERIA: `flutter pub get` succeeds. `dart run build_runner build --delete-conflicting-outputs` generates all Drift + Freezed files. All data source methods compile. No analyzer errors.
NOTIFY: Message domain-dev when DL-2 is done (they need DB provider for repository). Message domain-dev when DL-4 is done (they need SubscriptionFetcher for use cases).
```

### domain-dev

```
You are domain-dev on the CyberVPN team (Multi-Profile). You build domain entities, repository interfaces, and use cases.
Stack: Flutter, Dart 3.10+, Freezed 3.x, Riverpod 3.x, Clean Architecture.
You work ONLY in cybervpn_mobile/.

CONTEXT — What already exists:
- Core domain types: lib/core/domain/vpn_protocol.dart (VpnProtocol enum: v2ray, wireguard, openvpn)
- Core types: lib/core/types/ (Result<T> type for error handling)
- Existing repositories follow pattern: abstract class in domain/repositories/, impl in data/repositories/
- Existing use cases follow pattern: single-method classes in domain/usecases/
- Riverpod providers for DI in lib/core/di/

KEY FILES TO READ FIRST:
- cybervpn_mobile/lib/core/domain/vpn_protocol.dart
- cybervpn_mobile/lib/core/types/ (Result type)
- cybervpn_mobile/lib/features/vpn/domain/repositories/vpn_repository.dart (pattern reference)
- cybervpn_mobile/lib/features/subscription/domain/entities/subscription_entity.dart
- cybervpn_mobile/lib/features/config_import/domain/repositories/config_import_repository.dart
- cybervpn_mobile/lib/core/di/providers.dart (existing DI setup)

RULES:
- Use Context7 MCP to look up Riverpod 3.x docs before writing providers.
- Do NOT modify existing entity files or repositories.
- Domain layer must have ZERO Flutter imports — pure Dart only.
- All repository methods return Result<T> (existing pattern).
- Use cases are single-responsibility: one public method per class.
- Providers: autoDispose for screen-scoped, plain NotifierProvider for app-scoped.
- Profile list and active profile are APP-SCOPED (no autoDispose) — they persist across screens.

YOUR TASKS:

DOM-1: Create VpnProfile + ProfileServer + SubscriptionInfo domain entities (P0)
  - Create feature directory structure:
    lib/features/vpn_profiles/
    ├── domain/
    │   ├── entities/
    │   │   ├── vpn_profile.dart         ← VpnProfile (sealed: .remote, .local)
    │   │   ├── profile_server.dart      ← ProfileServer
    │   │   └── subscription_info.dart   ← SubscriptionInfo with computed props
    │   ├── repositories/
    │   └── usecases/
    ├── data/
    │   ├── datasources/
    │   ├── mappers/
    │   ├── repositories/
    │   └── security/
    └── presentation/
        ├── providers/
        ├── screens/
        └── widgets/
  - Implement all three Freezed entities exactly as specified in PRD Technical Specifications
  - VpnProfile must be sealed with .remote() and .local() factory constructors
  - SubscriptionInfo must have computed properties: isExpired, consumedBytes, usageRatio, remaining
  - Run build_runner after creating entities
  - File: vpn_profile.dart, profile_server.dart, subscription_info.dart (ALL NEW)

DOM-2: Create ProfileRepository abstract interface (P0)
  - Create lib/features/vpn_profiles/domain/repositories/profile_repository.dart:
    abstract class ProfileRepository {
      // Read operations
      Stream<List<VpnProfile>> watchAll();
      Stream<VpnProfile?> watchActiveProfile();
      Future<Result<VpnProfile>> getById(String id);
      Future<Result<VpnProfile?>> getBySubscriptionUrl(String url);

      // Write operations
      Future<Result<VpnProfile>> addRemoteProfile(String url, {String? name});
      Future<Result<VpnProfile>> addLocalProfile(String name, List<ProfileServer> servers);
      Future<Result<void>> setActive(String profileId);
      Future<Result<void>> update(VpnProfile profile);
      Future<Result<void>> updateSubscription(String profileId);
      Future<Result<void>> delete(String profileId);
      Future<Result<void>> reorder(List<String> profileIds);

      // Bulk operations
      Future<Result<int>> updateAllDueSubscriptions();
      Future<Result<void>> migrateFromLegacy();

      // Queries
      Future<Result<int>> count();
    }
  - Pure Dart, no implementation details
  - File: profile_repository.dart (NEW)

DOM-3: Create ProfileRepositoryImpl (P0, after DL-2, DL-4, DL-5)
  - Create lib/features/vpn_profiles/data/repositories/profile_repository_impl.dart:
    - Constructor takes: ProfileLocalDataSource, SubscriptionFetcher, ProfileMapper, SecureStorage
    - Implement all ProfileRepository methods:
      - addRemoteProfile: check duplicate URL → fetch subscription → save to DB
      - addLocalProfile: generate UUID → save to DB
      - setActive: validate profile exists → DB transaction
      - updateSubscription: fetch URL → diff configs → preserve favorites → upsert
      - delete: validate not last profile → validate not active → DB transaction
      - updateAllDueSubscriptions: iterate remote profiles → check interval → update each
      - migrateFromLegacy: read existing SubscriptionEntity + VpnConfigs → create profile → set flag
    - Error handling: wrap Drift exceptions in Result.failure with descriptive messages
    - Logging: use existing Logger for operations
  - File: profile_repository_impl.dart (NEW)

DOM-4: Create use cases (P1)
  - Create individual use case classes in lib/features/vpn_profiles/domain/usecases/:
    1. add_remote_profile.dart — AddRemoteProfile:
       - Validates URL format (Uri.tryParse, must have scheme)
       - Calls profileRepository.addRemoteProfile(url)
       - Returns Result<VpnProfile>
    2. add_local_profile.dart — AddLocalProfile:
       - Validates name not empty, servers not empty
       - Calls profileRepository.addLocalProfile(name, servers)
    3. switch_active_profile.dart — SwitchActiveProfile:
       - Checks if VPN is connected (via VpnRepository.isConnected)
       - If connected: returns Result.failure("VPN must be disconnected first")
       - If not: calls profileRepository.setActive(id)
    4. delete_profile.dart — DeleteProfile:
       - Checks profile count (must be >1)
       - Checks not active profile
       - Calls profileRepository.delete(id)
    5. update_subscriptions.dart — UpdateSubscriptions:
       - Calls profileRepository.updateAllDueSubscriptions()
       - Returns count of updated profiles
    6. migrate_legacy_profiles.dart — MigrateLegacyProfiles:
       - Checks SharedPreferences flag `profile_migration_v1_complete`
       - If not set: calls profileRepository.migrateFromLegacy()
       - Sets flag on success
  - Each use case is a single class with a single `call()` method
  - File: 6 new files in domain/usecases/

DOM-5: Create Riverpod providers for DI wiring (P1, after DL-2)
  - Create lib/features/vpn_profiles/di/profile_providers.dart:
    // Data sources
    final profileLocalDsProvider = Provider<ProfileLocalDataSource>((ref) {
      return ProfileLocalDataSource(ref.watch(appDatabaseProvider));
    });

    final subscriptionFetcherProvider = Provider<SubscriptionFetcher>((ref) {
      return SubscriptionFetcher(ref.watch(dioProvider));
    });

    // Repository
    final profileRepositoryProvider = Provider<ProfileRepository>((ref) {
      return ProfileRepositoryImpl(
        ref.watch(profileLocalDsProvider),
        ref.watch(subscriptionFetcherProvider),
        ProfileMapper(),
        ref.watch(secureStorageProvider),
      );
    });

    // Use cases
    final addRemoteProfileProvider = Provider((ref) => AddRemoteProfile(ref.watch(profileRepositoryProvider)));
    // ... etc for each use case

    // Core state (APP-SCOPED, no autoDispose)
    final profileListProvider = StreamProvider<List<VpnProfile>>((ref) {
      return ref.watch(profileRepositoryProvider).watchAll();
    });

    final activeProfileProvider = StreamProvider<VpnProfile?>((ref) {
      return ref.watch(profileRepositoryProvider).watchActiveProfile();
    });
  - Register providers in existing DI container (lib/core/di/providers.dart) — add import only
  - File: profile_providers.dart (NEW), update core/di/providers.dart import

DONE CRITERIA: All entities generate via build_runner. Repository interface compiles. Repository implementation compiles. All providers resolve. flutter analyze passes.
NOTIFY: Message ui-dev when DOM-1 is done (they need entities for screen design). Message integration-dev when DOM-3 + DOM-5 are done (they need wired repository for migration + router integration).
```

### ui-dev

```
You are ui-dev on the CyberVPN team (Multi-Profile). You build all presentation layer components — screens, widgets, providers/notifiers.
Stack: Flutter, Dart 3.10+, Riverpod 3.x, GoRouter 17, Material 3, Cyberpunk theme (Orbitron + JetBrains Mono), 27 locales.
You work ONLY in cybervpn_mobile/.

CONTEXT — What already exists:
- App theme: lib/app/theme/ (theme_provider.dart, dynamic_colors.dart, tokens.dart)
  - tokens.dart has AnimDurations: fast=150ms, medium=200ms, normal=300ms, slow=500ms
  - Colors: matrixGreen, neonCyan, neonPink, cyberpunkBlue, cyberpunkPurple
  - Fonts: Orbitron (display), JetBrains Mono (body/code)
- Bottom nav: lib/features/navigation/ (tab-based StatefulShellRoute)
  - Currently 4 tabs: Connection, Servers, Profile, Settings
- Router: lib/app/router/app_router.dart
- Shared widgets: lib/shared/widgets/
- Existing screens follow pattern: Screen widget (stateless) + separate provider (Riverpod)
- Localization: lib/core/l10n/arb/app_en.arb (base), 27 locales total
- Existing UI patterns:
  - Cards with neon border glow
  - Shimmer loading placeholders
  - Pull-to-refresh with RefreshIndicator
  - Bottom sheets for actions (see cancel_subscription_sheet.dart)
  - Animated list items (staggered fade-in)

KEY FILES TO READ FIRST:
- cybervpn_mobile/lib/app/theme/tokens.dart (design tokens)
- cybervpn_mobile/lib/app/router/app_router.dart (routing)
- cybervpn_mobile/lib/features/navigation/ (tab setup)
- cybervpn_mobile/lib/features/servers/presentation/screens/ (pattern reference — server list UI)
- cybervpn_mobile/lib/features/subscription/presentation/ (subscription card pattern)
- cybervpn_mobile/lib/features/config_import/presentation/screens/ (import screens pattern)
- cybervpn_mobile/lib/core/l10n/arb/app_en.arb (existing i18n strings)

RULES:
- Use Context7 MCP to look up Flutter Material 3 and Riverpod docs.
- Match existing cyberpunk aesthetic — Orbitron headings, JetBrains Mono body, neon accents, dark backgrounds.
- All user-facing strings via AppLocalizations (add keys to app_en.arb).
- Provider naming: PascalCaseNotifier, lowerCaseProvider.
- Notifiers: extend AsyncNotifier (app-scoped) or AutoDisposeAsyncNotifier (screen-scoped).
- Screens: stateless ConsumerWidget or HookConsumerWidget.
- Animations: use AnimDurations tokens from tokens.dart.
- Do NOT modify existing screens unless adding profile selector integration (US-3).
- Do NOT downgrade any package version.

YOUR TASKS:

UI-1: Create ProfileListScreen (P0, after DOM-1)
  - Create lib/features/vpn_profiles/presentation/screens/profile_list_screen.dart:
    - Header: "VPN Profiles" title (Orbitron) + "+" FAB to add profile
    - List: ReorderableListView.builder with ProfileCard widgets
    - Each ProfileCard shows:
      - Profile name (bold, Orbitron)
      - Type badge: "Remote" (neon-cyan) or "Local" (neon-pink)
      - For remote: server count, last updated, traffic usage mini-bar
      - For remote with subscription info: expiry countdown, usage ratio
      - Active indicator: glowing neon-green left border + checkmark icon
      - Expired badge: red "EXPIRED" for expired remote profiles
    - Tap: navigate to ProfileDetailScreen
    - Long-press: show bottom sheet with Edit/Delete/Set Active options
    - Pull-to-refresh: trigger updateAllDueSubscriptions()
    - Empty state: "No profiles yet. Add your first VPN subscription." with Add button
    - Loading state: shimmer placeholders (3 cards)
    - Error state: retry button with error message
  - Create ProfileCard widget in lib/features/vpn_profiles/presentation/widgets/profile_card.dart
  - File: profile_list_screen.dart (NEW), profile_card.dart (NEW)

UI-2: Create ProfileDetailScreen (P0, after DOM-1)
  - Create lib/features/vpn_profiles/presentation/screens/profile_detail_screen.dart:
    - Header: profile name + type badge + "..." menu (edit, delete)
    - Subscription info card (remote profiles only):
      - Traffic: circular progress indicator with used/total bytes
      - Expiry: date + "X days remaining" or "EXPIRED"
      - Last updated: relative timestamp
      - Update interval: "Every 1 hour"
    - Server list section:
      - List of ProfileServer entries
      - Each server: name, address:port, protocol badge, ping (if tested), favorite star
      - Tap server: connect (same flow as existing server list)
      - Long-press: copy config, toggle favorite
    - Action buttons:
      - "Set as Active" (if not active) — primary CTA
      - "Update Now" (remote only) — triggers manual subscription refresh
      - "Test URL" (remote only) — checks URL reachability
      - "Delete Profile" — danger zone at bottom
    - Loading/error states consistent with app pattern
  - File: profile_detail_screen.dart (NEW)

UI-3: Create AddProfileScreen + AddByUrlScreen (P0)
  - Create lib/features/vpn_profiles/presentation/screens/add_profile_screen.dart:
    - Choice screen: "How do you want to add a profile?"
    - Options (large cards with icons):
      1. "Subscription URL" — navigate to AddByUrlScreen
      2. "QR Code" — navigate to existing QR scanner (qr_scanner_screen.dart)
      3. "Clipboard" — attempt clipboard paste + parse
      4. "Manual" — navigate to manual config entry (future, disabled)
    - Each card: icon, title, subtitle, chevron
    - Cyberpunk-styled: neon border cards on dark background
  - Create lib/features/vpn_profiles/presentation/screens/add_by_url_screen.dart:
    - URL input field (JetBrains Mono, monospace)
    - "Paste" button (reads clipboard)
    - "Fetch" button (primary CTA)
    - On fetch:
      - Loading state with progress indicator
      - Success: show parsed profile name, server count, subscription info preview
      - "Save Profile" button to confirm
      - Error: show error with retry
    - Optional: custom name override field
  - File: add_profile_screen.dart (NEW), add_by_url_screen.dart (NEW)

UI-4: Create ProfileSelectorWidget for connection screen (P1, after DOM-5)
  - Create lib/features/vpn_profiles/presentation/widgets/profile_selector_widget.dart:
    - Compact horizontal widget showing active profile name + dropdown arrow
    - Tap: shows bottom sheet with all profiles for quick switching
    - Active profile highlighted with neon-green indicator
    - Shows mini traffic bar for remote profiles
  - Integrate into existing connection screen (VPN tab):
    - Add ProfileSelectorWidget above the Connect button
    - When profile changes: server list refreshes to show new profile's servers
  - This is the ONLY modification to an existing screen — minimal, additive only
  - Read the connection screen source FIRST to understand where to place the widget
  - File: profile_selector_widget.dart (NEW), minimal edit to connection screen

UI-5: Create ProfileListNotifier + AddProfileNotifier (P0, after DOM-5)
  - Create lib/features/vpn_profiles/presentation/providers/profile_list_notifier.dart:
    - Class: ProfileListNotifier extends Notifier<AsyncValue<List<VpnProfile>>> (APP-SCOPED)
    - build(): watches profileListProvider stream
    - Methods:
      - reorder(oldIndex, newIndex) → calls profileRepository.reorder()
      - deleteProfile(id) → calls deleteProfileUseCase
      - switchProfile(id) → calls switchActiveProfileUseCase
      - refreshSubscriptions() → calls updateSubscriptionsUseCase
  - Create lib/features/vpn_profiles/presentation/providers/add_profile_notifier.dart:
    - Class: AddProfileNotifier extends AutoDisposeAsyncNotifier<AddProfileState> (SCREEN-SCOPED)
    - build(): returns AddProfileState.idle
    - Methods:
      - addByUrl(url) → loading → fetchResult preview → awaitConfirmation → save → done
      - addFromImport(ImportedConfig) → convert to local profile → save → done
      - confirmSave() → saves previewed profile to DB
    - AddProfileState: idle | loading | preview(VpnProfile) | saving | done(VpnProfile) | error(String)
  - File: profile_list_notifier.dart (NEW), add_profile_notifier.dart (NEW)

UI-6: Add i18n strings for all profile-related UI (P1)
  - Update lib/core/l10n/arb/app_en.arb with new keys:
    "profiles": "Profiles",
    "profilesSubtitle": "Manage your VPN subscriptions",
    "addProfile": "Add Profile",
    "addProfileByUrl": "Subscription URL",
    "addProfileByUrlDesc": "Add a VPN subscription by pasting its URL",
    "addProfileByQr": "QR Code",
    "addProfileByQrDesc": "Scan a QR code containing a VPN configuration",
    "addProfileByClipboard": "Clipboard",
    "addProfileByClipboardDesc": "Import from clipboard content",
    "profileRemote": "Remote",
    "profileLocal": "Local",
    "profileActive": "Active",
    "profileExpired": "Expired",
    "profileServers": "{count} servers",
    "profileLastUpdated": "Updated {time}",
    "profileTrafficUsed": "{used} / {total}",
    "profileExpiresIn": "Expires in {days} days",
    "profileExpiredOn": "Expired on {date}",
    "profileUpdateNow": "Update Now",
    "profileTestUrl": "Test URL",
    "profileSetActive": "Set as Active",
    "profileDelete": "Delete Profile",
    "profileDeleteConfirm": "Delete \"{name}\"? This will remove the profile and all its server configurations. This action cannot be undone.",
    "profileDeleteLastError": "Cannot delete the last profile. At least one profile is required.",
    "profileDeleteActiveError": "Cannot delete the active profile. Switch to another profile first.",
    "profileSwitchDisconnect": "Switching profiles will disconnect your current VPN session. Continue?",
    "profileFetchSuccess": "Found {count} servers from subscription",
    "profileFetchError": "Failed to fetch subscription: {error}",
    "profileUrlHint": "Enter subscription URL (https://...)",
    "profileNameHint": "Profile name (optional)",
    "profileSaved": "Profile saved successfully",
    "profileUpdated": "Profile updated with {count} new servers",
    "profileNoServers": "No servers found in subscription",
    "profileDuplicateUrl": "A profile with this URL already exists",
    "profileMigrated": "Your existing subscription has been imported as a profile",
    "profileUpdateInterval": "Updates every {hours} hours",
    "profileEmpty": "No profiles yet",
    "profileEmptySubtitle": "Add your first VPN subscription to get started"
  - Do NOT modify any existing i18n keys
  - Only add to app_en.arb — other locales will use English as fallback
  - File: lib/core/l10n/arb/app_en.arb

UI-7: Create ProfileUpdateNotifier for auto-update (P2, after DOM-5)
  - Create lib/features/vpn_profiles/presentation/providers/profile_update_notifier.dart:
    - Class: ProfileUpdateNotifier extends Notifier<ProfileUpdateState> (APP-SCOPED)
    - Lifecycle:
      - On app startup (build): schedule check
      - On app resume (via WidgetsBindingObserver): check if any profile is due
    - Methods:
      - checkAndUpdate() → for each remote profile: if lastUpdated + interval < now → update
      - updateSingle(profileId) → force update one profile
    - State: idle | updating(profileId, progress) | completed(results)
    - Retry logic: exponential backoff (1min, 5min, 15min), max 3 retries per profile
    - Does NOT interrupt active VPN connection — queues results
  - File: profile_update_notifier.dart (NEW)

DONE CRITERIA: All screens render with mock data. All notifiers compile. All i18n keys added. flutter analyze passes. UI matches cyberpunk theme.
NOTIFY: Message integration-dev when UI-4 is done (connection screen integration). Message test-eng when UI-1, UI-2, UI-3 are done (ready for widget tests).
```

### integration-dev

```
You are integration-dev on the CyberVPN team (Multi-Profile). You handle migration, router integration, and cross-feature wiring.
Stack: Flutter, Dart 3.10+, Riverpod 3.x, GoRouter 17, Clean Architecture.
You work ONLY in cybervpn_mobile/.

CONTEXT — What already exists:
- Router: lib/app/router/app_router.dart (GoRouter with StatefulShellRoute, 4 tabs)
- Navigation: lib/features/navigation/ (tab-based shell)
- Config import: lib/features/config_import/ (QR, clipboard, deep link, subscription URL)
- Subscription: lib/features/subscription/ (RevenueCat, backend sync)
- VPN connection: lib/features/vpn/presentation/providers/vpn_connection_notifier.dart
- Server list: lib/features/servers/presentation/providers/ (current server list notifier)
- Splash/startup: lib/features/splash/ (initialization flow)
- App lifecycle: lib/app/app.dart (CyberVpnApp widget)
- Deep link: lib/core/routing/deep_link_handler.dart, deep_link_parser.dart
- Secure storage: lib/core/storage/secure_storage.dart
- Local storage: lib/core/storage/local_storage.dart (SharedPreferences wrapper)

KEY FILES TO READ FIRST:
- cybervpn_mobile/lib/app/router/app_router.dart (current routing)
- cybervpn_mobile/lib/features/navigation/ (tab structure)
- cybervpn_mobile/lib/features/splash/ (startup flow)
- cybervpn_mobile/lib/app/app.dart (app lifecycle)
- cybervpn_mobile/lib/core/routing/deep_link_handler.dart
- cybervpn_mobile/lib/features/config_import/presentation/providers/config_import_provider.dart
- cybervpn_mobile/lib/features/servers/presentation/providers/ (server list)
- cybervpn_mobile/lib/core/storage/local_storage.dart (SharedPreferences keys)

RULES:
- Use Context7 MCP to look up GoRouter and Riverpod docs.
- Minimize changes to existing files — additive only where possible.
- Do NOT break existing navigation, auth flow, or VPN connection.
- Do NOT modify auth, subscription purchase, or payment flows.
- Test every modified file by reading the file first, understanding its structure, then making targeted edits.
- When modifying existing files: read ENTIRE file first, understand context, then edit.

YOUR TASKS:

INT-1: Add Profiles tab to bottom navigation (P0, after UI-1)
  - File: lib/app/router/app_router.dart
  - Current: StatefulShellRoute with 4 branches (Connection, Servers, Profile, Settings)
  - Target: Add 5th branch "Profiles" BETWEEN Servers and Profile:
    - Connection | Servers | Profiles | Profile | Settings
    - OR replace Profile tab with Profiles (move user profile to Settings sub-page)
    - READ the router file first to understand the exact pattern
  - Add routes:
    GoRoute(path: '/profiles', builder: (_, __) => const ProfileListScreen())
    GoRoute(path: '/profiles/:id', builder: (_, state) => ProfileDetailScreen(id: state.pathParameters['id']!))
    GoRoute(path: '/profiles/add', builder: (_, __) => const AddProfileScreen())
    GoRoute(path: '/profiles/add/url', builder: (_, __) => const AddByUrlScreen())
  - Update navigation tab: icon = Icons.layers_outlined, label = l10n.profiles
  - File: lib/features/navigation/ (tab icon/label), lib/app/router/app_router.dart

INT-2: Integrate legacy profile migration into startup flow (P0, after DOM-3)
  - File: lib/features/splash/ (startup initialization)
  - After auth check succeeds and before navigating to main:
    1. Check SharedPreferences flag: `profile_migration_v1_complete`
    2. If false → run MigrateLegacyProfiles use case
    3. Migration: Read existing SubscriptionEntity from subscription provider → create "CyberVPN" RemoteVpnProfile → save to Drift DB → set as active → set flag
    4. If migration fails → log error, continue with empty profile (user can add manually)
    5. If flag already set → skip (normal startup)
  - This must be idempotent — multiple runs produce same result
  - File: startup/initialization files

INT-3: Wire server list to active profile (P1, after DOM-5, UI-4)
  - Current: ServerListNotifier fetches ALL servers from backend API
  - Target: ServerListNotifier scopes by active profile
    - If active profile is CyberVPN native → fetch from backend API (existing behavior)
    - If active profile is third-party remote → return profile's servers from Drift DB
    - If active profile is local → return profile's servers from Drift DB
  - Approach: Create ServerListAdapter that wraps existing server list logic
    - Watches activeProfileProvider
    - When profile changes: refreshes server list from appropriate source
    - Converts ProfileServer → ServerEntity for UI compatibility (or use ProfileServer directly if UI can handle it)
  - Minimize changes to existing ServerListNotifier — prefer adapter/decorator pattern
  - File: New adapter + minimal edits to server list provider

INT-4: Wire config_import → profile creation (P1, after DOM-3)
  - Current: Config import (QR, clipboard, deep link) creates ImportedConfig entities stored... somewhere
  - Target: Config import creates a LocalVpnProfile instead
  - Integration points:
    1. config_import_provider.dart: after successful import → call addLocalProfileUseCase
    2. deep_link_handler.dart: subscription URLs → call addRemoteProfileUseCase
    3. subscription_url_screen.dart: subscription URL input → redirect to AddByUrlScreen
  - Do NOT break existing import flows — wrap with profile creation
  - Read all import-related files FIRST to understand current flow
  - File: Targeted edits to config_import provider + deep link handler

INT-5: Wire VPN disconnect on profile switch (P1, after DOM-4)
  - When SwitchActiveProfile use case is called:
    1. Check VpnConnectionNotifier state
    2. If state is VpnConnected or VpnConnecting → require disconnect first
    3. UI shows confirmation dialog (handled by UI-4 ProfileSelectorWidget)
    4. On confirm: call VpnConnectionNotifier.disconnect() → await disconnect → proceed with switch
  - This wiring happens in the ProfileListNotifier.switchProfile() method
  - Must handle edge case: disconnect fails (timeout after 10s → force switch anyway)
  - File: Wire in ProfileListNotifier + read VpnConnectionNotifier for interface

DONE CRITERIA: 5-tab navigation works. Migration runs on first launch. Server list scopes by profile. Config import creates profiles. VPN disconnect on profile switch works. No existing features broken. flutter analyze passes.
NOTIFY: Message test-eng when INT-1 + INT-2 are done (ready for integration tests).
```

### test-eng

```
You are test-eng on the CyberVPN team (Multi-Profile). You write tests for all new profile features.
Stack: Flutter, Dart 3.10+, flutter_test, mocktail, golden_toolkit, Riverpod 3.x.
You work ONLY in cybervpn_mobile/test/.

CONTEXT — What already exists:
- Test directory: cybervpn_mobile/test/
- Existing test patterns: test/features/{feature}/presentation/screens/{screen}_test.dart
- Mock patterns: mocktail Mock classes, ProviderScope overrides
- Golden test setup: golden_toolkit with custom pump
- Existing mocks: may exist for Dio, SecureStorage, SharedPreferences, VpnRepository
- Important: CircularProgressIndicator without `value:` causes golden test timeouts — always set fixed value for snapshots

KEY FILES TO READ FIRST:
- cybervpn_mobile/test/ (existing test structure)
- cybervpn_mobile/test/features/ (test file patterns)
- Any existing *_test.dart file for pattern reference (e.g., wallet_screen_test.dart)

RULES:
- Use Context7 MCP to look up flutter_test and mocktail docs.
- Follow existing test patterns EXACTLY.
- Every mock must use `Mock` from mocktail, registered with `registerFallbackValue` where needed.
- Golden tests: set fixed `value:` on any CircularProgressIndicator to prevent timeout.
- Widget tests: wrap in `ProviderScope(overrides: [...])` for Riverpod.
- Do NOT modify production code — only test/ directory.
- Test file naming: {source_file}_test.dart.
- Wait for implementation agents to finish before writing tests for their code.

YOUR TASKS:

TST-1: Unit tests for domain entities (P0, after DOM-1)
  - Create test/features/vpn_profiles/domain/entities/:
    1. vpn_profile_test.dart:
       - Test VpnProfile.remote() creation with all fields
       - Test VpnProfile.local() creation with all fields
       - Test Freezed copyWith()
       - Test equality (same fields = equal)
       - Test inequality (different fields = not equal)
    2. subscription_info_test.dart:
       - Test isExpired: true when expiresAt is in the past
       - Test isExpired: false when expiresAt is in the future
       - Test isExpired: false when expiresAt is null
       - Test consumedBytes: uploadBytes + downloadBytes
       - Test usageRatio: consumedBytes / totalBytes (0.0 when total is 0)
       - Test remaining: Duration.zero when expired, positive when future
    3. profile_server_test.dart:
       - Test creation, copyWith, equality
  - File: 3 new test files

TST-2: Unit tests for repository implementation (P1, after DOM-3)
  - Create test/features/vpn_profiles/data/repositories/profile_repository_impl_test.dart:
    - Mock: ProfileLocalDataSource, SubscriptionFetcher, ProfileMapper, SecureStorage
    - Test addRemoteProfile:
      - Success: URL fetched, profile saved, returned
      - Duplicate URL: returns existing profile
      - Fetch failure: returns Result.failure
    - Test addLocalProfile:
      - Success: profile created with UUID, saved
      - Empty name: returns Result.failure
    - Test setActive:
      - Success: DB updated, stream emits new active
      - Nonexistent ID: returns Result.failure
    - Test delete:
      - Success: profile + configs removed
      - Last profile: returns Result.failure
      - Active profile: returns Result.failure
    - Test updateSubscription:
      - New servers added, stale removed, favorites preserved
      - Fetch failure: profile unchanged
    - Test updateAllDueSubscriptions:
      - Only profiles past their interval are updated
      - Returns count of updated profiles
  - File: profile_repository_impl_test.dart (NEW)

TST-3: Unit tests for use cases (P1, after DOM-4)
  - Create test/features/vpn_profiles/domain/usecases/:
    1. add_remote_profile_test.dart: URL validation, success/failure paths
    2. switch_active_profile_test.dart: VPN connected → failure, disconnected → success
    3. delete_profile_test.dart: last profile → failure, active → failure, success
    4. migrate_legacy_profiles_test.dart: already migrated → skip, first run → migrate
  - Mock: ProfileRepository, VpnRepository, SharedPreferences
  - File: 4 new test files

TST-4: Widget tests for ProfileListScreen (P2, after UI-1)
  - Create test/features/vpn_profiles/presentation/screens/profile_list_screen_test.dart:
    - Test: renders list of profiles with correct names
    - Test: shows "Remote"/"Local" badges
    - Test: active profile has green indicator
    - Test: expired profile shows "Expired" badge
    - Test: empty state shows add button
    - Test: pull-to-refresh triggers update
    - Test: long-press shows bottom sheet options
    - Test: tap navigates to detail screen
    - Mock: profileListProvider, activeProfileProvider (ProviderScope overrides)
  - File: profile_list_screen_test.dart (NEW)

TST-5: Widget tests for AddByUrlScreen (P2, after UI-3)
  - Create test/features/vpn_profiles/presentation/screens/add_by_url_screen_test.dart:
    - Test: URL input field renders
    - Test: "Paste" button reads clipboard
    - Test: "Fetch" button triggers loading state
    - Test: success state shows profile preview (name, server count)
    - Test: "Save" button creates profile
    - Test: error state shows retry button
    - Test: invalid URL shows validation error
    - Mock: addProfileNotifier, clipboard
  - File: add_by_url_screen_test.dart (NEW)

TST-6: Integration test for migration flow (P2, after INT-2)
  - Create test/features/vpn_profiles/integration/migration_test.dart:
    - Setup: mock existing subscription in SecureStorage/SharedPreferences
    - Test: migration creates profile on first launch
    - Test: migration sets profile_migration_v1_complete flag
    - Test: second launch skips migration
    - Test: migration failure doesn't crash app startup
    - Test: migrated profile has correct name "CyberVPN", isActive=true
    - Test: migrated profile contains all existing VPN configs
  - File: migration_test.dart (NEW)

DONE CRITERIA: All tests pass with `flutter test`. Zero skipped tests. Coverage: ≥80% for domain entities, ≥70% for repository, ≥60% for UI screens.
```

---

## 7. Task Registry & Dependencies

### Dependency Graph

```
                    ┌── DL-1 (Drift deps) ──────────────────────────┐
                    │                                                │
                    ├── DL-2 (Drift DB) ──→ DL-3 (LocalDS) ────────┤
                    │         │                                      │
START ──────────────┤         └──→ DOM-5 (DI providers) ───────────┤
                    │                      │                        │
                    ├── DOM-1 (entities) ──┤──→ UI-1 (list screen) │
                    │                      │──→ UI-2 (detail)      │
                    │                      │──→ UI-3 (add screen)  │
                    │                      └──→ TST-1 (entity tests)│
                    │                                               │
                    ├── DOM-2 (repo interface) ─────────────────────┤
                    │                                               │
                    ├── DL-4 (SubscriptionFetcher) ────→ DOM-3 ────┤
                    │                                    (repo impl)│
                    ├── DL-5 (mappers) ────────────────→ DOM-3 ────┤
                    │                                               │
                    ├── DL-6 (encryption) ─────────────→ DOM-3 ────┤
                    │                                               │
                    ├── DOM-3 (repo impl) ──→ INT-2 (migration) ───┤
                    │         │              INT-3 (server wire)    │
                    │         │              INT-4 (import wire)    │
                    │         │              INT-5 (vpn disconnect) │
                    │         └──→ TST-2 (repo tests)              │
                    │                                               │
                    ├── DOM-4 (use cases) ──→ TST-3 (use case tests)│
                    │                                               │
                    ├── DOM-5 (providers) ──→ UI-4 (selector) ─────┤
                    │                        UI-5 (notifiers)      │
                    │                        UI-7 (auto-update)    │
                    │                                               │
                    ├── UI-1 (list) ──→ INT-1 (navigation) ────────┤
                    │                   TST-4 (widget tests)       │
                    │                                               │
                    ├── UI-3 (add) ──→ TST-5 (add screen tests) ──┤
                    │                                               │
                    └── INT-2 (migration) ──→ TST-6 (migration test)│
```

### Full Task Table

| ID | Task | Agent | Depends on | Priority |
|----|------|-------|------------|----------|
| DL-1 | Add Drift dependencies to pubspec.yaml | data-layer-dev | — | P0 |
| DL-2 | Create Drift DB with profiles + profile_configs tables | data-layer-dev | DL-1 | P0 |
| DL-3 | Create ProfileLocalDataSource with Drift queries | data-layer-dev | DL-2 | P0 |
| DL-4 | Create SubscriptionFetcher (HTTP parser) | data-layer-dev | — | P0 |
| DL-5 | Create data mappers (Drift ↔ Domain) | data-layer-dev | DL-2, DOM-1 | P1 |
| DL-6 | Create encrypted URL storage wrapper | data-layer-dev | DL-2 | P1 |
| DOM-1 | Create domain entities (VpnProfile, ProfileServer, SubscriptionInfo) | domain-dev | — | P0 |
| DOM-2 | Create ProfileRepository abstract interface | domain-dev | DOM-1 | P0 |
| DOM-3 | Create ProfileRepositoryImpl | domain-dev | DL-2, DL-4, DL-5, DOM-2 | P0 |
| DOM-4 | Create use cases (6 classes) | domain-dev | DOM-2 | P1 |
| DOM-5 | Create Riverpod providers for DI | domain-dev | DL-2, DOM-3 | P1 |
| UI-1 | Create ProfileListScreen + ProfileCard | ui-dev | DOM-1 | P0 |
| UI-2 | Create ProfileDetailScreen | ui-dev | DOM-1 | P0 |
| UI-3 | Create AddProfileScreen + AddByUrlScreen | ui-dev | DOM-1 | P0 |
| UI-4 | Create ProfileSelectorWidget for connection screen | ui-dev | DOM-5 | P1 |
| UI-5 | Create ProfileListNotifier + AddProfileNotifier | ui-dev | DOM-5 | P0 |
| UI-6 | Add i18n strings to app_en.arb | ui-dev | — | P1 |
| UI-7 | Create ProfileUpdateNotifier (auto-update) | ui-dev | DOM-5 | P2 |
| INT-1 | Add Profiles tab to bottom navigation + routes | integration-dev | UI-1 | P0 |
| INT-2 | Integrate legacy migration into startup flow | integration-dev | DOM-3 | P0 |
| INT-3 | Wire server list to active profile | integration-dev | DOM-5, UI-4 | P1 |
| INT-4 | Wire config_import → profile creation | integration-dev | DOM-3 | P1 |
| INT-5 | Wire VPN disconnect on profile switch | integration-dev | DOM-4 | P1 |
| TST-1 | Unit tests for domain entities | test-eng | DOM-1 | P0 |
| TST-2 | Unit tests for repository implementation | test-eng | DOM-3 | P1 |
| TST-3 | Unit tests for use cases | test-eng | DOM-4 | P1 |
| TST-4 | Widget tests for ProfileListScreen | test-eng | UI-1 | P2 |
| TST-5 | Widget tests for AddByUrlScreen | test-eng | UI-3 | P2 |
| TST-6 | Integration test for migration flow | test-eng | INT-2 | P2 |

### Task Counts

| Agent | Tasks | IDs |
|-------|-------|-----|
| data-layer-dev | 6 | DL-1..6 |
| domain-dev | 5 | DOM-1..5 |
| ui-dev | 7 | UI-1..7 |
| integration-dev | 5 | INT-1..5 |
| test-eng | 6 | TST-1..6 |
| **TOTAL** | **29** | |

---

## 8. Lead Coordination Rules

1. **Spawn all 5 agents immediately.** Initial assignments:
   - `data-layer-dev` → DL-1 + DL-4 in parallel (P0 — Drift deps + SubscriptionFetcher are independent)
   - `domain-dev` → DOM-1 + DOM-2 in parallel (P0 — entities + interface are independent)
   - `ui-dev` → UI-6 first (i18n strings — no dependencies), then UI-1..3 once DOM-1 is done
   - `integration-dev` → Wait for DOM-3 + UI-1, or help domain-dev with DOM-3 research
   - `test-eng` → TST-1 as soon as DOM-1 is done

2. **Communication protocol:**
   - data-layer-dev finishes DL-1 → messages domain-dev ("Drift deps ready, pub get passed")
   - data-layer-dev finishes DL-2 → messages domain-dev ("DB schema ready, provider available")
   - data-layer-dev finishes DL-4 → messages domain-dev ("SubscriptionFetcher ready for repo impl")
   - domain-dev finishes DOM-1 → messages ui-dev ("Entities ready, build_runner done")
   - domain-dev finishes DOM-3 → messages integration-dev ("Repository impl ready for wiring")
   - domain-dev finishes DOM-5 → messages ui-dev ("Providers ready for notifiers")
   - ui-dev finishes UI-1 → messages integration-dev ("ProfileListScreen ready for navigation")
   - ui-dev finishes UI-1, UI-2, UI-3 → messages test-eng ("Screens ready for widget tests")
   - integration-dev finishes INT-2 → messages test-eng ("Migration ready for integration test")

3. **Parallel execution strategy:**
   - Wave 1 (immediate): DL-1, DL-4, DOM-1, DOM-2, UI-6
   - Wave 2 (after wave 1): DL-2, DL-3, DL-5, DL-6, DOM-3, UI-1, UI-2, UI-3, TST-1
   - Wave 3 (after wave 2): DOM-4, DOM-5, UI-5, INT-1, INT-2, TST-2
   - Wave 4 (after wave 3): UI-4, UI-7, INT-3, INT-4, INT-5, TST-3
   - Wave 5 (final): TST-4, TST-5, TST-6

4. **File conflict prevention:**
   - `data-layer-dev` owns: `lib/core/data/database/`, `lib/features/vpn_profiles/data/`, `pubspec.yaml`
   - `domain-dev` owns: `lib/features/vpn_profiles/domain/`, `lib/features/vpn_profiles/di/`
   - `ui-dev` owns: `lib/features/vpn_profiles/presentation/`, `lib/core/l10n/arb/app_en.arb`
   - `integration-dev` owns: `lib/app/router/`, `lib/features/navigation/`, `lib/features/splash/`, `lib/features/config_import/`, targeted edits to `lib/features/servers/`, `lib/features/vpn/`
   - `test-eng` owns: `test/features/vpn_profiles/` exclusively
   - **Shared file: pubspec.yaml** — only `data-layer-dev` modifies it (DL-1). Others do NOT touch it.
   - **Shared file: lib/core/di/providers.dart** — only `domain-dev` adds import (DOM-5). Others do NOT touch it.
   - Nobody modifies another agent's files without explicit lead approval.

5. **Do NOT start implementing if you are lead — delegate.** Use delegate mode exclusively.

6. **Progress tracking.** Use the shared TaskList (TaskCreate/TaskUpdate). Do NOT use beads (`bd`) — SQLite lock conflicts with parallel agents.

7. **If any agent is blocked >5 minutes:** reassign them to an independent task and come back to the blocked one later.

8. **build_runner coordination:** After any agent creates/modifies Freezed or Drift files, they MUST run:
   ```bash
   cd cybervpn_mobile && dart run build_runner build --delete-conflicting-outputs
   ```
   Only ONE agent runs build_runner at a time to prevent file lock conflicts. If conflict: wait 30s and retry.

---

## 9. Prohibitions

- Do NOT downgrade library versions (Flutter Riverpod 3.x, GoRouter 17, Drift 2.27+, Freezed 3.x)
- Do NOT break existing features (auth, VPN connection, subscription, payments, settings)
- Do NOT modify existing entity files (VpnConfigEntity, SubscriptionEntity, Profile, ServerEntity)
- Do NOT modify backend/ or frontend/ or infra/ directories
- Do NOT add cloud sync or backend API calls for profile management
- Do NOT use beads (`bd create/close`) — use TaskList instead
- Do NOT skip Context7 MCP doc lookup when using a library (especially Drift — it's new to this codebase)
- Do NOT use `:latest` Docker tags (not applicable here, but general rule)
- Do NOT store subscription URLs in plaintext — must be encrypted at rest
- Do NOT send PII (profile names, URLs, server addresses) to analytics
- Do NOT run `flutter pub get` while another agent is running `build_runner`

---

## 10. Final Verification (Lead runs after ALL tasks complete)

```bash
# ===== Dependencies =====
cd cybervpn_mobile && flutter pub get
# Must succeed with no version conflicts

# ===== Code Generation =====
cd cybervpn_mobile && dart run build_runner build --delete-conflicting-outputs
# Must complete with 0 errors

# ===== Static Analysis =====
cd cybervpn_mobile && flutter analyze --no-fatal-infos
# Must have 0 errors (warnings OK)

# ===== Tests =====
cd cybervpn_mobile && flutter test
# All new + existing tests must pass

# ===== Verify New Files Exist =====
# Database
ls cybervpn_mobile/lib/core/data/database/app_database.dart
ls cybervpn_mobile/lib/core/data/database/database_provider.dart

# Domain entities
ls cybervpn_mobile/lib/features/vpn_profiles/domain/entities/vpn_profile.dart
ls cybervpn_mobile/lib/features/vpn_profiles/domain/entities/profile_server.dart
ls cybervpn_mobile/lib/features/vpn_profiles/domain/entities/subscription_info.dart

# Repository
ls cybervpn_mobile/lib/features/vpn_profiles/domain/repositories/profile_repository.dart
ls cybervpn_mobile/lib/features/vpn_profiles/data/repositories/profile_repository_impl.dart

# Data sources
ls cybervpn_mobile/lib/features/vpn_profiles/data/datasources/profile_local_ds.dart
ls cybervpn_mobile/lib/features/vpn_profiles/data/datasources/subscription_fetcher.dart

# Screens
ls cybervpn_mobile/lib/features/vpn_profiles/presentation/screens/profile_list_screen.dart
ls cybervpn_mobile/lib/features/vpn_profiles/presentation/screens/profile_detail_screen.dart
ls cybervpn_mobile/lib/features/vpn_profiles/presentation/screens/add_profile_screen.dart
ls cybervpn_mobile/lib/features/vpn_profiles/presentation/screens/add_by_url_screen.dart

# Providers
ls cybervpn_mobile/lib/features/vpn_profiles/presentation/providers/profile_list_notifier.dart
ls cybervpn_mobile/lib/features/vpn_profiles/presentation/providers/add_profile_notifier.dart
ls cybervpn_mobile/lib/features/vpn_profiles/presentation/providers/profile_update_notifier.dart
ls cybervpn_mobile/lib/features/vpn_profiles/di/profile_providers.dart

# Tests
ls cybervpn_mobile/test/features/vpn_profiles/domain/entities/vpn_profile_test.dart
ls cybervpn_mobile/test/features/vpn_profiles/data/repositories/profile_repository_impl_test.dart

# ===== Verify Navigation =====
# 5 tabs should be defined in router
grep -c "StatefulShellBranch" cybervpn_mobile/lib/app/router/app_router.dart
# Must return 5

# ===== Verify Migration Flag =====
grep "profile_migration_v1_complete" cybervpn_mobile/lib/core/storage/local_storage.dart
# Must find the key

# ===== Verify Encryption =====
grep -r "encrypt" cybervpn_mobile/lib/features/vpn_profiles/data/
# Must find encryption logic for subscription URLs

# ===== Verify i18n =====
grep "profiles" cybervpn_mobile/lib/core/l10n/arb/app_en.arb
# Must find profile-related i18n keys

# ===== Verify No Version Downgrades =====
# Compare pubspec.yaml before/after — all existing versions must be >= original
```

All commands must pass with zero errors. If any fail, assign fix to the responsible agent.

---

## 11. Completion Checklist

### Database & Data Layer
- [ ] Drift + sqlite3_flutter_libs added to pubspec.yaml
- [ ] AppDatabase with profiles + profile_configs tables
- [ ] ProfileLocalDataSource with all CRUD operations
- [ ] SubscriptionFetcher parses HTTP headers + V2Ray configs
- [ ] Data mappers (Drift ↔ Domain) complete
- [ ] Subscription URL encryption at rest

### Domain & Business Logic
- [ ] VpnProfile entity (remote + local sealed class)
- [ ] ProfileServer entity
- [ ] SubscriptionInfo with computed properties
- [ ] ProfileRepository interface
- [ ] ProfileRepositoryImpl with full CRUD + subscription updates
- [ ] 6 use cases (add, switch, delete, update, migrate, add-local)
- [ ] Riverpod providers wired

### Presentation & UI
- [ ] ProfileListScreen with reorderable cards
- [ ] ProfileDetailScreen with subscription info + server list
- [ ] AddProfileScreen (choice: URL, QR, clipboard)
- [ ] AddByUrlScreen with fetch + preview + save
- [ ] ProfileCard widget (cyberpunk themed)
- [ ] ProfileSelectorWidget on connection screen
- [ ] ProfileListNotifier + AddProfileNotifier + ProfileUpdateNotifier
- [ ] All i18n strings in app_en.arb

### Integration
- [ ] Profiles tab in bottom navigation (5 tabs)
- [ ] GoRouter routes for all profile screens
- [ ] Legacy migration in startup flow
- [ ] Server list scoped by active profile
- [ ] Config import → profile creation
- [ ] VPN disconnect on profile switch

### Testing
- [ ] Entity unit tests (VpnProfile, SubscriptionInfo, ProfileServer)
- [ ] Repository implementation unit tests
- [ ] Use case unit tests
- [ ] ProfileListScreen widget tests
- [ ] AddByUrlScreen widget tests
- [ ] Migration integration test

### Quality
- [ ] `flutter pub get` succeeds
- [ ] `build_runner` generates all files
- [ ] `flutter analyze` — 0 errors
- [ ] `flutter test` — all pass
- [ ] No existing features broken
- [ ] No version downgrades
- [ ] Subscription URLs encrypted at rest
- [ ] No PII in analytics events
