# Storage Security Audit Report

**Date**: 2026-02-01
**Task**: #133 - Audit and fix secure storage usage
**Status**: CRITICAL SECURITY ISSUE FOUND

## Executive Summary

This audit identified **1 CRITICAL security vulnerability** where VPN configuration data containing sensitive credentials is stored in SharedPreferences instead of SecureStorage.

## Audit Findings

### CRITICAL ISSUES

#### 1. VPN Configurations with Credentials in SharedPreferences ⚠️

**Location**: `lib/features/vpn/data/repositories/vpn_repository_impl.dart`

**Issue**: VPN configs containing credentials (`configData` field) are stored in SharedPreferences:
- Lines 63-66: `saveConfig()` stores `configData` in SharedPreferences
- Lines 70-82: `getSavedConfigs()` retrieves configs from SharedPreferences
- Key: `_lastConfigKey = 'last_vpn_config'`
- Key: `_savedConfigsKey = 'saved_vpn_configs'`

**Risk**: VPN configurations contain authentication credentials (passwords, tokens) that are:
- Stored in plaintext in SharedPreferences
- Accessible via device backups
- Readable by root/jailbroken devices
- Not encrypted at rest

**Required Action**: Migrate VPN config storage to SecureStorage immediately.

---

### SECURE STORAGE (Correct Usage) ✓

#### Auth Tokens
**Location**: `lib/features/auth/data/datasources/auth_local_ds.dart`

**Properly Secured**:
- JWT access tokens → SecureStorage (`access_token`)
- JWT refresh tokens → SecureStorage (`refresh_token`)

**Location**: `lib/core/network/auth_interceptor.dart`
- Token reads/writes → SecureStorage

#### Biometric Settings
**Location**: `lib/features/auth/domain/usecases/biometric_service.dart`

**Properly Secured**:
- Biometric enabled flag → SecureStorage (`biometric_enabled`)

#### Protocol Preferences
**Location**: `lib/features/vpn/domain/usecases/protocol_fallback.dart`

**Properly Secured**:
- Preferred VPN protocol → SecureStorage (`preferred_vpn_protocol`)

---

### SHARED PREFERENCES (Correct Usage) ✓

#### User Profile Data
**Location**: `lib/features/auth/data/datasources/auth_local_ds.dart`

**Non-sensitive**:
- User profile (email, username, avatar) → SharedPreferences (`cached_user`)
- **Rationale**: Public profile data, no credentials

#### App Settings
**Location**: `lib/features/settings/data/repositories/settings_repository_impl.dart`

**Non-sensitive**:
- Theme mode, brightness, dynamic color
- UI preferences (locale, notification settings)
- VPN preferences (DNS provider, MTU, split tunneling flag)
- Log level
- **Rationale**: UI/UX preferences, no security risk

#### Server Data
**Location**: `lib/features/servers/data/datasources/server_local_ds.dart`

**Non-sensitive**:
- Server list cache → SharedPreferences (`cached_servers`)
- Favorite server IDs → SharedPreferences (`favorite_servers`)
- Cache timestamp → SharedPreferences (`servers_cache_timestamp`)
- **Rationale**: Public server metadata, no credentials

#### Local Storage Keys
**Location**: `lib/core/storage/local_storage.dart`

**Non-sensitive constants**:
- `themeKey = 'theme_mode'`
- `localeKey = 'locale'`
- `onboardingCompleteKey = 'onboarding_complete'`
- `lastServerKey = 'last_server_id'`
- `killSwitchKey = 'kill_switch_enabled'`
- `splitTunnelKey = 'split_tunnel_apps'`
- `autoConnectKey = 'auto_connect'`

---

## Storage Classification Matrix

| Data Type | Current Storage | Correct? | Reason |
|-----------|----------------|----------|--------|
| JWT Access Token | SecureStorage | ✓ | Sensitive auth credential |
| JWT Refresh Token | SecureStorage | ✓ | Sensitive auth credential |
| **VPN Config Data** | **SharedPreferences** | **✗** | **Contains credentials** |
| User Profile JSON | SharedPreferences | ✓ | Public profile data |
| Biometric Enabled | SecureStorage | ✓ | Security setting |
| Preferred Protocol | SecureStorage | ✓ | Security preference |
| Theme Settings | SharedPreferences | ✓ | UI preference |
| Locale | SharedPreferences | ✓ | UI preference |
| Notification Prefs | SharedPreferences | ✓ | UI preference |
| Server List Cache | SharedPreferences | ✓ | Public metadata |
| Favorite Server IDs | SharedPreferences | ✓ | User preference |
| Onboarding Complete | SharedPreferences | ✓ | App state |

---

## Sensitive Data Classification (Per Task Spec)

### MUST use SecureStorage:
1. ✓ JWT tokens (access & refresh)
2. ✗ **VPN configs with credentials** (CURRENTLY INSECURE)
3. N/A 2FA secrets (not stored locally, only handled via API)
4. N/A OAuth tokens (not stored locally, only handled via API callbacks)

### OK in SharedPreferences:
1. ✓ Settings (theme, locale, notifications)
2. ✓ Onboarding flag
3. ✓ Theme preferences
4. ✓ Locale
5. ✓ Notification preferences
6. ✓ Favorite server IDs (metadata only, no credentials)
7. N/A Speed test history (not implemented yet)

---

## Files Requiring Changes

### 1. VpnRepositoryImpl (CRITICAL)
**File**: `lib/features/vpn/data/repositories/vpn_repository_impl.dart`

**Required Changes**:
- Inject `SecureStorageWrapper` into constructor
- Store `configData` in SecureStorage
- Keep non-sensitive config metadata in SharedPreferences
- Implement migration logic for existing configs

**Migration Strategy**:
```dart
// Option 1: Store entire config in SecureStorage
await secureStorage.write(key: 'vpn_config_$id', value: jsonEncode(config));

// Option 2: Split storage (recommended)
// - Metadata in SharedPreferences (name, server, port, protocol)
// - Credentials in SecureStorage (configData only)
await localStorage.setString('vpn_config_meta_$id', jsonEncode(metadata));
await secureStorage.write(key: 'vpn_config_data_$id', value: config.configData);
```

---

## Files Audited

### Storage Infrastructure
- ✓ `lib/core/storage/secure_storage.dart`
- ✓ `lib/core/storage/local_storage.dart`

### Auth
- ✓ `lib/features/auth/data/datasources/auth_local_ds.dart`
- ✓ `lib/features/auth/domain/usecases/biometric_service.dart`
- ✓ `lib/core/network/auth_interceptor.dart`

### VPN
- ✓ `lib/features/vpn/data/repositories/vpn_repository_impl.dart` (ISSUE FOUND)
- ✓ `lib/features/vpn/domain/usecases/protocol_fallback.dart`

### Servers
- ✓ `lib/features/servers/data/datasources/server_local_ds.dart`

### Settings
- ✓ `lib/features/settings/data/repositories/settings_repository_impl.dart`

### Profile/2FA
- ✓ `lib/features/profile/data/datasources/profile_remote_ds.dart` (no local storage)

---

## Grep Patterns Used

```bash
# SecureStorage usage
grep -r "SecureStorageWrapper\|FlutterSecureStorage" cybervpn_mobile/lib

# SharedPreferences usage
grep -r "LocalStorageWrapper\|SharedPreferences" cybervpn_mobile/lib

# Storage operations
grep -r "\.(write|read|setString|getString|setBool|getBool|setInt|getInt)\(" cybervpn_mobile/lib

# Sensitive data keywords
grep -ri "token\|password\|secret\|credential\|oauth\|2fa" cybervpn_mobile/lib
```

---

## Recommendations

### Immediate (CRITICAL)
1. **Fix VPN config storage** in `vpn_repository_impl.dart`
   - Use SecureStorage for `configData` field
   - Implement migration for existing stored configs
   - Add integration test for migration

### High Priority
2. **Add storage security tests**
   - Verify sensitive data never touches SharedPreferences
   - Test migration logic thoroughly

3. **Document storage decisions**
   - Add inline comments to all storage call sites
   - Create STORAGE_GUIDELINES.md (next subtask)

### Medium Priority
4. **Code review checklist**
   - Add storage security checks to PR template
   - Lint rule to flag suspicious storage patterns

5. **Consider encryption layers**
   - Review if additional encryption needed for config backups
   - Evaluate ProGuard/R8 obfuscation for release builds

---

## Next Steps

Per task 133 subtasks:

1. ✓ **Subtask 1**: Audit complete (this document)
2. **Subtask 2**: Migrate VPN configs to SecureStorage
3. **Subtask 3**: Add documentation comments and guidelines

---

**Audited by**: Claude Agent (Task Master Task #133)
**Review required**: Yes - Security team review recommended
