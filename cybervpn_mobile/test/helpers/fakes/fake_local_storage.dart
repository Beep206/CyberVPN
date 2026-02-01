import 'package:cybervpn_mobile/core/storage/local_storage.dart';

/// In-memory fake implementation of [LocalStorageWrapper] for testing.
///
/// Uses plain maps instead of [SharedPreferences].
class FakeLocalStorage extends LocalStorageWrapper {
  final Map<String, Object> _store = {};

  @override
  Future<void> setString(String key, String value) async {
    _store[key] = value;
  }

  @override
  Future<String?> getString(String key) async {
    return _store[key] as String?;
  }

  @override
  Future<void> setBool(String key, bool value) async {
    _store[key] = value;
  }

  @override
  Future<bool?> getBool(String key) async {
    return _store[key] as bool?;
  }

  @override
  Future<void> setInt(String key, int value) async {
    _store[key] = value;
  }

  @override
  Future<int?> getInt(String key) async {
    return _store[key] as int?;
  }

  @override
  Future<void> remove(String key) async {
    _store.remove(key);
  }

  @override
  Future<void> clear() async {
    _store.clear();
  }

  /// Exposes the internal store for test assertions.
  Map<String, Object> get store => Map.unmodifiable(_store);

  /// Clears all stored data. Alias for [clear].
  void reset() => _store.clear();
}
