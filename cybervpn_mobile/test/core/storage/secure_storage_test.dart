import 'package:flutter_test/flutter_test.dart';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';

import '../../helpers/fakes/fake_secure_storage.dart';

void main() {
  late FakeSecureStorage storage;

  setUp(() {
    storage = FakeSecureStorage();
  });

  tearDown(() {
    storage.reset();
  });

  group('SecureStorageWrapper', () {
    group('Token Management', () {
      test('setTokens stores both access and refresh tokens', () async {
        await storage.setTokens(
          accessToken: 'access_123',
          refreshToken: 'refresh_456',
        );

        expect(storage.store[SecureStorageWrapper.accessTokenKey], 'access_123');
        expect(storage.store[SecureStorageWrapper.refreshTokenKey], 'refresh_456');
      });

      test('getAccessToken returns stored token', () async {
        storage.seed({SecureStorageWrapper.accessTokenKey: 'my_access_token'});

        final token = await storage.getAccessToken();

        expect(token, 'my_access_token');
      });

      test('getAccessToken returns null when not set', () async {
        final token = await storage.getAccessToken();

        expect(token, isNull);
      });

      test('getRefreshToken returns stored token', () async {
        storage.seed({SecureStorageWrapper.refreshTokenKey: 'my_refresh_token'});

        final token = await storage.getRefreshToken();

        expect(token, 'my_refresh_token');
      });

      test('getRefreshToken returns null when not set', () async {
        final token = await storage.getRefreshToken();

        expect(token, isNull);
      });

      test('setTokens writes both tokens in parallel via Future.wait', () async {
        // Verify both tokens are written (parallel execution)
        await storage.setTokens(
          accessToken: 'at_parallel',
          refreshToken: 'rt_parallel',
        );

        // Both should be present after the call
        expect(await storage.getAccessToken(), 'at_parallel');
        expect(await storage.getRefreshToken(), 'rt_parallel');
      });

      test('setTokens propagates error if one write fails', () async {
        final failingStorage = _FailOnKeyStorage(
          failKey: SecureStorageWrapper.refreshTokenKey,
        );

        expect(
          () => failingStorage.setTokens(
            accessToken: 'access_ok',
            refreshToken: 'refresh_fail',
          ),
          throwsA(isA<Exception>()),
        );
      });

      test('clearTokens removes both tokens', () async {
        await storage.setTokens(
          accessToken: 'access_123',
          refreshToken: 'refresh_456',
        );

        await storage.clearTokens();

        expect(await storage.getAccessToken(), isNull);
        expect(await storage.getRefreshToken(), isNull);
      });
    });

    group('Device ID Management', () {
      test('getOrCreateDeviceId generates UUID on first call', () async {
        final deviceId = await storage.getOrCreateDeviceId();

        expect(deviceId, isNotEmpty);
        expect(deviceId, matches(RegExp(
          r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
        )));
      });

      test('getOrCreateDeviceId returns same ID on subsequent calls', () async {
        final first = await storage.getOrCreateDeviceId();
        final second = await storage.getOrCreateDeviceId();

        expect(first, equals(second));
      });

      test('getOrCreateDeviceId persists to storage', () async {
        final deviceId = await storage.getOrCreateDeviceId();

        expect(storage.store[SecureStorageWrapper.deviceIdKey], deviceId);
      });

      test('getOrCreateDeviceId uses existing ID if present', () async {
        storage.seed({SecureStorageWrapper.deviceIdKey: 'existing-device-id'});

        final deviceId = await storage.getOrCreateDeviceId();

        expect(deviceId, 'existing-device-id');
      });
    });

    group('Device Token (Biometric Re-auth)', () {
      test('setDeviceToken stores token', () async {
        await storage.setDeviceToken('device-token-123');

        expect(
          storage.store[SecureStorageWrapper.deviceTokenKey],
          'device-token-123',
        );
      });

      test('getDeviceToken returns stored token', () async {
        await storage.setDeviceToken('device-token-abc');

        final token = await storage.getDeviceToken();

        expect(token, 'device-token-abc');
      });

      test('getDeviceToken returns null when not set', () async {
        final token = await storage.getDeviceToken();

        expect(token, isNull);
      });

      test('clearDeviceToken removes token', () async {
        await storage.setDeviceToken('device-token-xyz');

        await storage.clearDeviceToken();

        expect(await storage.getDeviceToken(), isNull);
      });
    });

    group('App Lock State', () {
      test('setAppLockEnabled stores true', () async {
        await storage.setAppLockEnabled(true);

        expect(storage.store[SecureStorageWrapper.appLockEnabledKey], 'true');
      });

      test('setAppLockEnabled stores false', () async {
        await storage.setAppLockEnabled(false);

        expect(storage.store[SecureStorageWrapper.appLockEnabledKey], 'false');
      });

      test('isAppLockEnabled returns true when enabled', () async {
        await storage.setAppLockEnabled(true);

        expect(await storage.isAppLockEnabled(), isTrue);
      });

      test('isAppLockEnabled returns false when disabled', () async {
        await storage.setAppLockEnabled(false);

        expect(await storage.isAppLockEnabled(), isFalse);
      });

      test('isAppLockEnabled returns false when not set', () async {
        expect(await storage.isAppLockEnabled(), isFalse);
      });
    });

    group('Cached User', () {
      test('setCachedUser stores user data as JSON', () async {
        await storage.setCachedUser({
          'id': 'user-123',
          'email': 'user@example.com',
          'isPremium': true,
        });

        expect(storage.store[SecureStorageWrapper.cachedUserKey], isNotNull);
        expect(storage.store[SecureStorageWrapper.cachedUserKey], contains('user-123'));
      });

      test('getCachedUser returns stored user data', () async {
        final userData = {
          'id': 'user-456',
          'email': 'test@example.com',
          'username': 'testuser',
          'isPremium': false,
        };
        await storage.setCachedUser(userData);

        final retrieved = await storage.getCachedUser();

        expect(retrieved, isNotNull);
        expect(retrieved!['id'], 'user-456');
        expect(retrieved['email'], 'test@example.com');
        expect(retrieved['username'], 'testuser');
        expect(retrieved['isPremium'], false);
      });

      test('getCachedUser returns null when not set', () async {
        final user = await storage.getCachedUser();

        expect(user, isNull);
      });

      test('getCachedUser returns null for invalid JSON', () async {
        storage.seed({SecureStorageWrapper.cachedUserKey: 'invalid-json'});

        final user = await storage.getCachedUser();

        expect(user, isNull);
      });

      test('clearCachedUser removes user data', () async {
        await storage.setCachedUser({'id': 'user-789'});

        await storage.clearCachedUser();

        expect(await storage.getCachedUser(), isNull);
      });
    });

    group('clearAll', () {
      test('clearAll removes auth data but preserves device ID', () async {
        // Setup: store various data including device ID
        await storage.setTokens(
          accessToken: 'access_token',
          refreshToken: 'refresh_token',
        );
        await storage.write(key: SecureStorageWrapper.userIdKey, value: 'user-123');
        await storage.setDeviceToken('device-token-test');
        await storage.setAppLockEnabled(true);
        await storage.setCachedUser({'id': '123'});
        final deviceId = await storage.getOrCreateDeviceId();

        // Act
        await storage.clearAll();

        // Assert: auth data cleared
        expect(await storage.getAccessToken(), isNull);
        expect(await storage.getRefreshToken(), isNull);
        expect(await storage.read(key: SecureStorageWrapper.userIdKey), isNull);
        expect(await storage.getDeviceToken(), isNull);
        expect(await storage.isAppLockEnabled(), isFalse);
        expect(await storage.getCachedUser(), isNull);

        // Assert: device ID preserved
        expect(await storage.getOrCreateDeviceId(), deviceId);
      });

      test('clearAll works when device ID does not exist', () async {
        await storage.setTokens(
          accessToken: 'access_token',
          refreshToken: 'refresh_token',
        );

        // Should not throw
        await storage.clearAll();

        expect(await storage.getAccessToken(), isNull);
        expect(storage.store[SecureStorageWrapper.deviceIdKey], isNull);
      });
    });

    group('UUID Generation', () {
      test('generates unique UUIDs', () async {
        // Create multiple storage instances to test uniqueness
        final storage1 = FakeSecureStorage();
        final storage2 = FakeSecureStorage();

        final id1 = await storage1.getOrCreateDeviceId();
        final id2 = await storage2.getOrCreateDeviceId();

        expect(id1, isNot(equals(id2)));
      });

      test('generated UUID is version 4', () async {
        final deviceId = await storage.getOrCreateDeviceId();

        // UUID v4 has '4' at position 14 (0-indexed)
        expect(deviceId[14], '4');
      });

      test('generated UUID has correct variant', () async {
        final deviceId = await storage.getOrCreateDeviceId();

        // UUID variant bits at position 19 should be 8, 9, a, or b
        expect(deviceId[19], matches(RegExp(r'[89ab]')));
      });
    });
  });
}

/// A fake storage that throws when writing a specific key.
class _FailOnKeyStorage extends SecureStorageWrapper {
  _FailOnKeyStorage({required this.failKey});
  final String failKey;
  final Map<String, String> _store = {};

  @override
  Future<void> write({required String key, required String value}) async {
    if (key == failKey) throw Exception('Write failed for $key');
    _store[key] = value;
  }

  @override
  Future<String?> read({required String key}) async => _store[key];

  @override
  Future<void> delete({required String key}) async => _store.remove(key);

  @override
  Future<void> deleteAll() async => _store.clear();

  @override
  Future<bool> containsKey({required String key}) async =>
      _store.containsKey(key);
}
