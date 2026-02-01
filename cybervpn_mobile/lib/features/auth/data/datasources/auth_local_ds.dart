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
  Future<void> clearAuth();
}

class AuthLocalDataSourceImpl implements AuthLocalDataSource {
  final SecureStorageWrapper _secureStorage;
  final LocalStorageWrapper _localStorage;

  static const String _accessTokenKey = 'access_token';
  static const String _refreshTokenKey = 'refresh_token';
  static const String _userKey = 'cached_user';

  AuthLocalDataSourceImpl({required SecureStorageWrapper secureStorage, required LocalStorageWrapper localStorage})
      : _secureStorage = secureStorage,
        _localStorage = localStorage;

  @override
  Future<void> cacheToken(TokenModel token) async {
    await _secureStorage.write(key: _accessTokenKey, value: token.accessToken);
    await _secureStorage.write(key: _refreshTokenKey, value: token.refreshToken);
  }

  @override
  Future<TokenModel?> getCachedToken() async {
    final accessToken = await _secureStorage.read(key: _accessTokenKey);
    final refreshToken = await _secureStorage.read(key: _refreshTokenKey);
    if (accessToken == null || refreshToken == null) return null;
    return TokenModel(accessToken: accessToken, refreshToken: refreshToken, expiresIn: 0);
  }

  @override
  Future<void> cacheUser(UserModel user) async {
    await _localStorage.setString(_userKey, jsonEncode(user.toJson()));
  }

  @override
  Future<UserModel?> getCachedUser() async {
    final jsonStr = await _localStorage.getString(_userKey);
    if (jsonStr == null) return null;
    return UserModel.fromJson(jsonDecode(jsonStr) as Map<String, dynamic>);
  }

  @override
  Future<void> clearAuth() async {
    await _secureStorage.delete(key: _accessTokenKey);
    await _secureStorage.delete(key: _refreshTokenKey);
    await _localStorage.remove(_userKey);
  }
}
