import 'dart:convert';
import 'dart:math';

import 'package:cybervpn_mobile/core/constants/cache_constants.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Wrapper for flutter_secure_storage providing encrypted storage for sensitive data.
///
/// **USE THIS FOR**:
/// - Authentication tokens (JWT, OAuth, API keys)
/// - VPN configuration credentials
/// - Encryption keys
/// - 2FA secrets or backup codes
/// - Any data that could authenticate users or access protected resources
///
/// **Platform Security**:
/// - Android: EncryptedSharedPreferences with AES256-GCM, keys in Android Keystore
/// - iOS: Keychain Services with Secure Enclave, accessible after first unlock
///
/// **Performance Optimization**:
/// Values are cached in memory after first read to minimize I/O.
/// Cache is invalidated on write/delete operations.
/// Target: < 50ms for cached reads vs ~100-200ms for secure storage I/O.
///
/// **DO NOT USE** [LocalStorageWrapper] (SharedPreferences) for credentials!
/// See [STORAGE_GUIDELINES.md] for data classification rules.
class SecureStorageWrapper {
  final FlutterSecureStorage _storage;

  /// Maximum number of entries in the in-memory cache.
  static const int _maxCacheSize = 100;

  /// TTL for cached token values (access_token, refresh_token).
  /// See [CacheConstants.authTokenCacheTtl] for the centralized value.
  static const Duration _tokenCacheTtl = CacheConstants.authTokenCacheTtl;

  /// In-memory cache for read values.
  /// Key: storage key, Value: cached value (null means key was checked and not found)
  final Map<String, String?> _cache = {};

  /// Timestamps for when each cache entry was set, for TTL expiration.
  final Map<String, DateTime> _cacheTimestamps = {};

  /// Tracks which keys have been checked to distinguish "not in cache" from "checked, not found"
  final Set<String> _checkedKeys = {};

  /// Keys that are subject to TTL expiration (security-sensitive tokens).
  static const _ttlKeys = {accessTokenKey, refreshTokenKey, deviceTokenKey};

  SecureStorageWrapper({FlutterSecureStorage? storage})
      : _storage = storage ??
            const FlutterSecureStorage(
              aOptions: AndroidOptions(),
              iOptions: IOSOptions(
                accessibility: KeychainAccessibility.first_unlock,
              ),
            );

  /// Writes a value and updates the cache.
  Future<void> write({required String key, required String value}) async {
    await _storage.write(key: key, value: value);
    _cache[key] = value;
    _cacheTimestamps[key] = DateTime.now();
    _checkedKeys.add(key);
    _evictIfNeeded();
  }

  /// Reads a value, using cache if available.
  ///
  /// First read from storage populates the cache.
  /// Subsequent reads return cached value instantly.
  /// Token keys are subject to TTL expiration.
  Future<String?> read({required String key}) async {
    // Return from cache if key was already checked and not TTL-expired
    if (_checkedKeys.contains(key)) {
      if (_isCacheExpired(key)) {
        // TTL expired — re-read from storage
        _cache.remove(key);
        _cacheTimestamps.remove(key);
        _checkedKeys.remove(key);
      } else {
        return _cache[key];
      }
    }

    // Read from storage and cache the result
    final value = await _storage.read(key: key);
    _cache[key] = value;
    _cacheTimestamps[key] = DateTime.now();
    _checkedKeys.add(key);
    return value;
  }

  /// Returns true if a cached entry has exceeded its TTL.
  bool _isCacheExpired(String key) {
    if (!_ttlKeys.contains(key)) return false;
    final timestamp = _cacheTimestamps[key];
    if (timestamp == null) return true;
    return DateTime.now().difference(timestamp) > _tokenCacheTtl;
  }

  /// Evicts oldest entries when cache exceeds max size.
  void _evictIfNeeded() {
    while (_cache.length > _maxCacheSize) {
      final oldestKey = _cache.keys.first;
      _cache.remove(oldestKey);
      _cacheTimestamps.remove(oldestKey);
      _checkedKeys.remove(oldestKey);
    }
  }

  /// Deletes a key and invalidates the cache.
  Future<void> delete({required String key}) async {
    await _storage.delete(key: key);
    _cache.remove(key);
    _cacheTimestamps.remove(key);
    _checkedKeys.remove(key);
  }

  /// Deletes all keys and clears the cache.
  Future<void> deleteAll() async {
    await _storage.deleteAll();
    _cache.clear();
    _cacheTimestamps.clear();
    _checkedKeys.clear();
  }

  /// Checks if a key exists, using cache if available.
  Future<bool> containsKey({required String key}) async {
    if (_checkedKeys.contains(key)) {
      return _cache[key] != null;
    }
    return _storage.containsKey(key: key);
  }

  /// Clears the in-memory cache without affecting storage.
  ///
  /// Use this when you need to force a fresh read from storage.
  void invalidateCache() {
    _cache.clear();
    _cacheTimestamps.clear();
    _checkedKeys.clear();
  }

  /// Pre-warms the cache by loading critical keys.
  ///
  /// Call this during app initialization to minimize latency
  /// on first auth check. Reads are performed in parallel.
  Future<void> prewarmCache() async {
    final criticalKeys = [
      accessTokenKey,
      refreshTokenKey,
      cachedUserKey,
    ];

    await Future.wait(
      criticalKeys.map((key) => read(key: key)),
    );
  }

  /// Migrates from plaintext biometric credentials to device token auth.
  ///
  /// Call this once during app startup (after [prewarmCache]). If the old
  /// `biometric_credentials` key exists (plaintext email/password format),
  /// it is cleared and the user must re-enroll with the new device-bound
  /// token flow.
  ///
  /// Returns `true` if migration was performed (old format found and cleared).
  Future<bool> migrateCredentialFormat() async {
    final oldCredentials = await read(key: biometricCredentialsKey);
    if (oldCredentials == null || oldCredentials.isEmpty) {
      return false;
    }

    // Old format detected — clear it and require re-enrollment
    await delete(key: biometricCredentialsKey);
    return true;
  }

  // ── Storage Keys ────────────────────────────────────────────────────────────

  /// SENSITIVE: JWT access token - must use SecureStorage for encryption at rest
  static const String accessTokenKey = 'access_token';

  /// SENSITIVE: JWT refresh token - must use SecureStorage for encryption at rest
  static const String refreshTokenKey = 'refresh_token';

  /// NON-SENSITIVE: User ID is just an identifier, but stored here for consistency
  static const String userIdKey = 'user_id';

  /// SENSITIVE: Device ID for device fingerprinting - persists across app reinstalls
  static const String deviceIdKey = 'device_id';

  /// SENSITIVE: Device-bound token for biometric re-authentication.
  /// Replaces the previous plaintext credential storage (email/password).
  /// The device token is obtained from POST /mobile/auth/biometric/enroll
  /// and is cryptographically bound to this device.
  static const String biometricCredentialsKey = 'biometric_credentials';

  /// SENSITIVE: Device token for biometric re-authentication (Phase 2).
  static const String deviceTokenKey = 'device_token';

  /// SENSITIVE: App lock enabled flag - security setting
  static const String appLockEnabledKey = 'app_lock_enabled';

  /// SENSITIVE: Cached user data for offline mode - contains user profile
  static const String cachedUserKey = 'cached_user';

  // ── Token Management ────────────────────────────────────────────────────────

  /// Stores both access and refresh tokens atomically.
  ///
  /// Use this after successful login/registration to persist authentication.
  Future<void> setTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    await Future.wait([
      write(key: accessTokenKey, value: accessToken),
      write(key: refreshTokenKey, value: refreshToken),
    ]);
  }

  /// Retrieves the stored access token.
  ///
  /// Returns `null` if no token is stored (user not authenticated).
  Future<String?> getAccessToken() async {
    return read(key: accessTokenKey);
  }

  /// Retrieves the stored refresh token.
  ///
  /// Returns `null` if no token is stored (user not authenticated).
  Future<String?> getRefreshToken() async {
    return read(key: refreshTokenKey);
  }

  /// Clears both access and refresh tokens.
  ///
  /// Use this on logout to remove authentication credentials.
  Future<void> clearTokens() async {
    await delete(key: accessTokenKey);
    await delete(key: refreshTokenKey);
  }

  // ── Device ID Management ────────────────────────────────────────────────────

  /// Gets or creates a unique device identifier.
  ///
  /// On first call, generates a UUID v4 and persists it.
  /// Subsequent calls return the same ID.
  /// This ID survives app updates but may not survive app reinstalls on iOS.
  Future<String> getOrCreateDeviceId() async {
    final existing = await read(key: deviceIdKey);
    if (existing != null && existing.isNotEmpty) {
      return existing;
    }

    final newDeviceId = _generateUuidV4();
    await write(key: deviceIdKey, value: newDeviceId);
    return newDeviceId;
  }

  /// Generates a RFC 4122 compliant UUID v4 (random).
  String _generateUuidV4() {
    final random = Random.secure();
    final bytes = List<int>.generate(16, (_) => random.nextInt(256));

    // Set version to 4 (random UUID)
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    // Set variant to RFC 4122
    bytes[8] = (bytes[8] & 0x3f) | 0x80;

    final hex = bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
    return '${hex.substring(0, 8)}-${hex.substring(8, 12)}-'
        '${hex.substring(12, 16)}-${hex.substring(16, 20)}-${hex.substring(20)}';
  }

  // ── Device Token (Biometric Re-auth) ────────────────────────────────────────

  /// Stores a device-bound token for biometric re-authentication.
  ///
  /// The device token is obtained from the backend enrollment endpoint and
  /// replaces the previous plaintext email/password storage. The token is
  /// cryptographically bound to this device and cannot be used elsewhere.
  Future<void> setDeviceToken(String token) async {
    await write(key: deviceTokenKey, value: token);
  }

  /// Retrieves the stored device token for biometric re-authentication.
  ///
  /// Returns `null` if no device token is enrolled.
  Future<String?> getDeviceToken() async {
    return read(key: deviceTokenKey);
  }

  /// Clears the stored device token.
  ///
  /// Call this on enrollment change, logout, or when revoking biometric auth.
  Future<void> clearDeviceToken() async {
    await delete(key: deviceTokenKey);
  }

  // ── App Lock State (Phase 4) ────────────────────────────────────────────────

  /// Sets whether app lock is enabled.
  ///
  /// When enabled, the app requires biometric authentication on launch.
  Future<void> setAppLockEnabled(bool enabled) async {
    await write(key: appLockEnabledKey, value: enabled.toString());
  }

  /// Checks if app lock is enabled.
  ///
  /// Returns `false` if not set (default behavior).
  Future<bool> isAppLockEnabled() async {
    final value = await read(key: appLockEnabledKey);
    return value == 'true';
  }

  // ── Cached User Data ────────────────────────────────────────────────────────

  /// Caches user data for offline mode.
  ///
  /// The user data is stored as JSON and can be retrieved when offline.
  /// [userData] should be a JSON-serializable Map.
  Future<void> setCachedUser(Map<String, dynamic> userData) async {
    await write(key: cachedUserKey, value: jsonEncode(userData));
  }

  /// Retrieves cached user data.
  ///
  /// Returns `null` if no user data is cached.
  Future<Map<String, dynamic>?> getCachedUser() async {
    final stored = await read(key: cachedUserKey);
    if (stored == null || stored.isEmpty) {
      return null;
    }

    try {
      return jsonDecode(stored) as Map<String, dynamic>;
    } catch (e) {
      AppLogger.warning('Failed to parse cached user data', error: e);
      return null;
    }
  }

  /// Clears cached user data.
  Future<void> clearCachedUser() async {
    await delete(key: cachedUserKey);
  }

  // ── Clear All (Preserves Device ID) ─────────────────────────────────────────

  /// Clears all authentication and user data while preserving the device ID.
  ///
  /// Use this on logout to clear sensitive data while maintaining device identity
  /// for analytics and device tracking purposes.
  Future<void> clearAll() async {
    // SECURITY: Clear in-memory cache first to prevent post-logout memory dumps
    // from exposing tokens that are still cached.
    invalidateCache();

    // Preserve device ID before clearing
    final deviceId = await read(key: deviceIdKey);

    // Clear all keys
    await delete(key: accessTokenKey);
    await delete(key: refreshTokenKey);
    await delete(key: userIdKey);
    await delete(key: biometricCredentialsKey);
    await delete(key: deviceTokenKey);
    await delete(key: appLockEnabledKey);
    await delete(key: cachedUserKey);

    // Restore device ID if it existed
    if (deviceId != null && deviceId.isNotEmpty) {
      await write(key: deviceIdKey, value: deviceId);
    }
  }
}
