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
/// **DO NOT USE** [LocalStorageWrapper] (SharedPreferences) for credentials!
/// See [STORAGE_GUIDELINES.md] for data classification rules.
class SecureStorageWrapper {
  final FlutterSecureStorage _storage;

  SecureStorageWrapper({FlutterSecureStorage? storage})
      : _storage = storage ??
            const FlutterSecureStorage(
              aOptions: AndroidOptions(encryptedSharedPreferences: true),
              iOptions: IOSOptions(
                accessibility: KeychainAccessibility.first_unlock,
              ),
            );

  Future<void> write({required String key, required String value}) async =>
      _storage.write(key: key, value: value);

  Future<String?> read({required String key}) async =>
      _storage.read(key: key);

  Future<void> delete({required String key}) async =>
      _storage.delete(key: key);

  Future<void> deleteAll() async => _storage.deleteAll();

  Future<bool> containsKey({required String key}) async =>
      _storage.containsKey(key: key);

  // ── Common Secure Storage Keys ────────────────────────────────────────────

  // SENSITIVE: JWT access token - must use SecureStorage for encryption at rest
  static const String accessTokenKey = 'access_token';

  // SENSITIVE: JWT refresh token - must use SecureStorage for encryption at rest
  static const String refreshTokenKey = 'refresh_token';

  // NON-SENSITIVE: User ID is just an identifier, but stored here for consistency
  static const String userIdKey = 'user_id';
}
