# Storage Security Guidelines

**Version**: 1.0
**Last Updated**: 2026-02-01
**Applies To**: CyberVPN Mobile (Flutter)

## Quick Reference

### MUST use SecureStorage (`SecureStorageWrapper`)

Store in **encrypted** storage for data that, if compromised, could:
- Authenticate as the user
- Access protected resources
- Decrypt private communications
- Compromise user privacy

**Examples**:
- ✓ JWT access tokens
- ✓ JWT refresh tokens
- ✓ VPN configuration credentials (`configData` field)
- ✓ OAuth tokens (if stored locally)
- ✓ 2FA backup codes (if stored locally)
- ✓ API keys
- ✓ Encryption keys

### OK to use SharedPreferences (`LocalStorageWrapper`)

Store in **plaintext** for data that is:
- Non-sensitive metadata
- User preferences
- Public information
- App state

**Examples**:
- ✓ Theme mode (light/dark/system)
- ✓ Locale preference
- ✓ Onboarding completion flag
- ✓ Notification preferences
- ✓ UI settings (MTU, DNS provider, kill switch enabled)
- ✓ Server list cache (public metadata only)
- ✓ Favorite server IDs (just UUIDs, no credentials)
- ✓ VPN config metadata (server name, address, port, protocol - NO credentials)
- ✓ User profile public data (email, username, avatar URL)

---

## Storage Decision Tree

```
Is the data a credential or secret?
├─ Yes → Use SecureStorage
│   ├─ Token (JWT, OAuth, API key)?
│   │   └─ SecureStorage ✓
│   ├─ Password or passphrase?
│   │   └─ SecureStorage ✓
│   ├─ Encryption key?
│   │   └─ SecureStorage ✓
│   └─ VPN config credentials?
│       └─ SecureStorage ✓
│
└─ No → Could it help an attacker?
    ├─ Yes → Use SecureStorage
    │   └─ Example: 2FA backup codes, biometric enabled flag
    │
    └─ No → Can use SharedPreferences
        └─ Example: theme, locale, favorites list
```

---

## Implementation Patterns

### Pattern 1: Pure Sensitive Data

**Use Case**: JWT tokens, API keys

```dart
// SENSITIVE: JWT access token - must use SecureStorage for encryption at rest
static const String _accessTokenKey = 'access_token';

Future<void> saveToken(String token) async {
  await _secureStorage.write(key: _accessTokenKey, value: token);
}

Future<String?> getToken() async {
  return await _secureStorage.read(key: _accessTokenKey);
}
```

### Pattern 2: Split Storage (Metadata + Credentials)

**Use Case**: VPN configs (metadata is public, credentials are sensitive)

```dart
// NON-SENSITIVE: VPN config metadata - SharedPreferences is sufficient
static const String _configMetaKey = 'vpn_config_meta';

// SENSITIVE: VPN config credentials - must use SecureStorage for encryption at rest
static const String _configDataKey = 'vpn_config_data';

Future<void> saveConfig(VpnConfig config) async {
  // Store public metadata in SharedPreferences
  await _localStorage.setString(
    _configMetaKey,
    jsonEncode({
      'id': config.id,
      'name': config.name,
      'serverAddress': config.serverAddress,
      'port': config.port,
      'protocol': config.protocol,
    }),
  );

  // Store sensitive credentials in SecureStorage
  await _secureStorage.write(
    key: _configDataKey,
    value: config.configData,
  );
}

Future<VpnConfig?> getConfig() async {
  final metaJson = await _localStorage.getString(_configMetaKey);
  if (metaJson == null) return null;

  final meta = jsonDecode(metaJson);
  final configData = await _secureStorage.read(key: _configDataKey);
  if (configData == null) return null;

  return VpnConfig(
    id: meta['id'],
    name: meta['name'],
    serverAddress: meta['serverAddress'],
    port: meta['port'],
    protocol: meta['protocol'],
    configData: configData,
  );
}
```

### Pattern 3: Pure Non-Sensitive Data

**Use Case**: App settings, preferences

```dart
// NON-SENSITIVE: UI theme preference - SharedPreferences is sufficient
static const String _themeKey = 'theme_mode';

Future<void> saveTheme(String theme) async {
  await _localStorage.setString(_themeKey, theme);
}

Future<String?> getTheme() async {
  return await _localStorage.getString(_themeKey);
}
```

---

## Data Classification Reference

### Authentication & Authorization

| Data Type | Storage | Reason |
|-----------|---------|--------|
| JWT Access Token | SecureStorage | Authenticates user, grants API access |
| JWT Refresh Token | SecureStorage | Can generate new access tokens |
| OAuth Token | SecureStorage | Third-party account access |
| API Key | SecureStorage | Server authentication credential |
| Session ID | SecureStorage | Session hijacking risk |

### VPN Configuration

| Data Type | Storage | Reason |
|-----------|---------|--------|
| Config Data (credentials) | SecureStorage | Contains passwords/keys |
| Config Metadata (name, server, port) | SharedPreferences | Public server information |
| Last Selected Server ID | SharedPreferences | Just a UUID reference |
| Protocol Preference | SecureStorage | Security-related setting |

### User Profile

| Data Type | Storage | Reason |
|-----------|---------|--------|
| Password (raw) | ❌ Never store | Use backend auth |
| Email | SharedPreferences | Public profile data |
| Username | SharedPreferences | Public profile data |
| Avatar URL | SharedPreferences | Public profile data |
| User ID | SharedPreferences | Public identifier |

### Two-Factor Authentication

| Data Type | Storage | Reason |
|-----------|---------|--------|
| TOTP Secret | ❌ Never store locally | Backend only |
| 2FA Enabled Flag | SecureStorage | Security setting |
| Backup Codes | SecureStorage | Account recovery credential |

### App Settings

| Data Type | Storage | Reason |
|-----------|---------|--------|
| Theme Mode | SharedPreferences | UI preference |
| Locale | SharedPreferences | UI preference |
| Dynamic Color | SharedPreferences | UI preference |
| Kill Switch Enabled | SharedPreferences | Feature toggle (non-credential) |
| DNS Provider | SharedPreferences | Preference (not the actual DNS config) |
| Custom DNS | SharedPreferences | User-provided server (public) |
| MTU Value | SharedPreferences | Network setting (non-sensitive) |
| Notification Preferences | SharedPreferences | UI preferences |
| Log Level | SharedPreferences | Debug setting |

### Feature Flags & State

| Data Type | Storage | Reason |
|-----------|---------|--------|
| Onboarding Complete | SharedPreferences | App state flag |
| Biometric Enabled | SecureStorage | Security feature flag |
| Auto-Connect | SharedPreferences | Feature preference |
| Split Tunnel Apps | SharedPreferences | List of app package names |
| Clipboard Auto-Detect | SharedPreferences | Feature preference |

### Server & Network

| Data Type | Storage | Reason |
|-----------|---------|--------|
| Server List Cache | SharedPreferences | Public server metadata |
| Favorite Server IDs | SharedPreferences | List of UUIDs (no credentials) |
| Server Ping Results | SharedPreferences | Performance metrics |
| Speed Test History | SharedPreferences | Network performance data |

---

## Security Best Practices

### 1. Never Store These Locally

- ❌ Raw passwords
- ❌ Credit card numbers
- ❌ Social Security Numbers
- ❌ Private keys (unless encrypted separately)
- ❌ Unencrypted personally identifiable information (PII)

### 2. SecureStorage Platform Details

**Android**:
- Uses EncryptedSharedPreferences (AES256-GCM)
- Keys stored in Android Keystore
- Protected by device lock screen

**iOS**:
- Uses Keychain Services
- Protected by Secure Enclave
- Accessibility: `first_unlock` (accessible after first device unlock)

### 3. SharedPreferences Risks

- ✗ Stored in plaintext XML files
- ✗ Readable via device backups
- ✗ Accessible on rooted/jailbroken devices
- ✗ No encryption at rest
- ✓ Fast read/write
- ✓ Good for non-sensitive data

### 4. Migration Strategy

When moving from insecure to secure storage:

```dart
Future<void> migrate() async {
  // 1. Read from old location
  final oldValue = await _localStorage.getString('old_key');
  if (oldValue == null) return;

  // 2. Write to new secure location
  await _secureStorage.write(key: 'new_key', value: oldValue);

  // 3. Delete old insecure data
  await _localStorage.remove('old_key');

  // 4. Mark migration complete
  await _localStorage.setBool('migration_complete', true);
}
```

### 5. Code Review Checklist

Before committing storage code:

- [ ] Verified data classification (sensitive vs. non-sensitive)
- [ ] Used correct storage method (SecureStorage vs. SharedPreferences)
- [ ] Added inline comment documenting storage decision
- [ ] No credentials in SharedPreferences
- [ ] Migration logic for existing users (if changing storage)
- [ ] Error handling for storage operations
- [ ] Logged storage operations for debugging (without logging the actual data)

---

## Common Mistakes

### ❌ WRONG: Token in SharedPreferences

```dart
// DON'T DO THIS - tokens are sensitive!
await _localStorage.setString('access_token', token);
```

**Fix**:
```dart
// CORRECT: Use SecureStorage for tokens
await _secureStorage.write(key: 'access_token', value: token);
```

### ❌ WRONG: Entire Config in SharedPreferences

```dart
// DON'T DO THIS - configData contains credentials!
await _localStorage.setString('vpn_config', jsonEncode({
  'name': config.name,
  'configData': config.configData, // ← Contains passwords!
}));
```

**Fix**:
```dart
// CORRECT: Split storage - metadata in SharedPreferences, credentials in SecureStorage
await _localStorage.setString('vpn_config_meta', jsonEncode({
  'id': config.id,
  'name': config.name,
  'serverAddress': config.serverAddress,
}));

await _secureStorage.write(
  key: 'vpn_config_data',
  value: config.configData,
);
```

### ❌ WRONG: No Documentation

```dart
await _localStorage.setString('user_pref', value);
```

**Fix**:
```dart
// NON-SENSITIVE: UI theme preference - SharedPreferences is sufficient
static const String _themeKey = 'user_pref';
await _localStorage.setString(_themeKey, value);
```

---

## FAQs

### Q: Should I store user IDs in SecureStorage?

**A**: No, if the user ID is just an identifier (UUID) and doesn't grant access by itself. Use SharedPreferences.

However, if the user ID is sensitive (e.g., Social Security Number), use SecureStorage.

### Q: What about encrypted data in SharedPreferences?

**A**: If you're implementing your own encryption, you still need to store the encryption key somewhere - which should be in SecureStorage. At that point, just use SecureStorage directly.

### Q: Can I cache API responses in SharedPreferences?

**A**: Only if the response contains no sensitive data. Check each field:
- Public server list → OK
- User profile with email → OK (if email is non-sensitive)
- Payment history → Use SecureStorage (financial data)

### Q: How do I handle migration?

**A**: See the VpnRepositoryImpl migration example in `vpn_repository_impl.dart`:
1. Check if migration is needed (use a flag)
2. Read from old location
3. Write to new secure location
4. Delete old data
5. Mark migration complete

### Q: What if SecureStorage fails?

**A**: Implement fallback logic:
```dart
try {
  await _secureStorage.write(key: 'token', value: token);
} catch (e) {
  AppLogger.error('Failed to save token securely', error: e);
  // Don't fall back to SharedPreferences for credentials!
  // Instead, return an error to the user
  throw SecureStorageException('Unable to save credentials securely');
}
```

---

## References

- [flutter_secure_storage package](https://pub.dev/packages/flutter_secure_storage)
- [shared_preferences package](https://pub.dev/packages/shared_preferences)
- [Android EncryptedSharedPreferences](https://developer.android.com/reference/androidx/security/crypto/EncryptedSharedPreferences)
- [iOS Keychain Services](https://developer.apple.com/documentation/security/keychain_services)
- [OWASP Mobile Security Testing Guide](https://github.com/OWASP/owasp-mstg)

---

**Remember**: When in doubt, use SecureStorage. It's better to over-protect than under-protect user data.
