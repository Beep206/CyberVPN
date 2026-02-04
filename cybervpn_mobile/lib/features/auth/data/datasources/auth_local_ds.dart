import 'dart:convert';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/core/storage/local_storage.dart';
import 'package:cybervpn_mobile/features/auth/data/models/user_model.dart';
import 'package:cybervpn_mobile/features/auth/data/models/token_model.dart';

abstract class AuthLocalDataSource {
  Future<void> cacheToken(TokenModel token);
  Future<TokenModel?> getCachedToken();
  Future<void> cacheUser(UserModel user);
  Future<UserModel?> getCachedUser();
  Future<void> cacheSubscription(Map<String, dynamic> subscription);
  Future<Map<String, dynamic>?> getCachedSubscription();
  Future<DateTime?> getLastUpdated();
  Future<void> clearAuth();
}

class AuthLocalDataSourceImpl implements AuthLocalDataSource {
  final SecureStorageWrapper _secureStorage;
  final LocalStorageWrapper _localStorage;

  // SENSITIVE: JWT access token - must use SecureStorage for encryption at rest
  static const String _accessTokenKey = 'access_token';

  // SENSITIVE: JWT refresh token - must use SecureStorage for encryption at rest
  static const String _refreshTokenKey = 'refresh_token';

  // NON-SENSITIVE: User profile JSON (email, username, avatar) - public data
  static const String _userKey = 'cached_user';

  // NON-SENSITIVE: Subscription info JSON - public data
  static const String _subscriptionKey = 'cached_subscription';

  // NON-SENSITIVE: Timestamp of last cache update
  static const String _lastUpdatedKey = 'cache_last_updated';

  AuthLocalDataSourceImpl({required SecureStorageWrapper secureStorage, required LocalStorageWrapper localStorage})
      : _secureStorage = secureStorage,
        _localStorage = localStorage;

  @override
  Future<void> cacheToken(TokenModel token) async {
    // SENSITIVE: Store JWT tokens in SecureStorage for encryption at rest
    await _secureStorage.write(key: _accessTokenKey, value: token.accessToken);
    await _secureStorage.write(key: _refreshTokenKey, value: token.refreshToken);
  }

  @override
  Future<TokenModel?> getCachedToken() async {
    // SENSITIVE: Read JWT tokens from SecureStorage
    final accessToken = await _secureStorage.read(key: _accessTokenKey);
    final refreshToken = await _secureStorage.read(key: _refreshTokenKey);
    if (accessToken == null || refreshToken == null) return null;
    return TokenModel(accessToken: accessToken, refreshToken: refreshToken, expiresIn: 0);
  }

  @override
  Future<void> cacheUser(UserModel user) async {
    // NON-SENSITIVE: User profile is public data - SharedPreferences is sufficient
    await _localStorage.setString(_userKey, jsonEncode(user.toJson()));
    // Update timestamp when caching user
    await _updateLastUpdated();
  }

  @override
  Future<UserModel?> getCachedUser() async {
    // NON-SENSITIVE: Read user profile from SharedPreferences
    final jsonStr = await _localStorage.getString(_userKey);
    if (jsonStr == null) return null;
    return UserModel.fromJson(jsonDecode(jsonStr) as Map<String, dynamic>);
  }

  @override
  Future<void> cacheSubscription(Map<String, dynamic> subscription) async {
    // NON-SENSITIVE: Subscription info is public data - SharedPreferences is sufficient
    await _localStorage.setString(_subscriptionKey, jsonEncode(subscription));
    // Update timestamp when caching subscription
    await _updateLastUpdated();
  }

  @override
  Future<Map<String, dynamic>?> getCachedSubscription() async {
    // NON-SENSITIVE: Read subscription from SharedPreferences
    final jsonStr = await _localStorage.getString(_subscriptionKey);
    if (jsonStr == null) return null;
    return jsonDecode(jsonStr) as Map<String, dynamic>;
  }

  @override
  Future<DateTime?> getLastUpdated() async {
    final timestamp = await _localStorage.getString(_lastUpdatedKey);
    if (timestamp == null) return null;
    return DateTime.tryParse(timestamp);
  }

  Future<void> _updateLastUpdated() async {
    await _localStorage.setString(
      _lastUpdatedKey,
      DateTime.now().toIso8601String(),
    );
  }

  @override
  Future<void> clearAuth() async {
    await _secureStorage.delete(key: _accessTokenKey);
    await _secureStorage.delete(key: _refreshTokenKey);
    await _localStorage.remove(_userKey);
    await _localStorage.remove(_subscriptionKey);
    await _localStorage.remove(_lastUpdatedKey);
  }
}
