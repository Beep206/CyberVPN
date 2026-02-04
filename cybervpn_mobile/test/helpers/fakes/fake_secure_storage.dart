import 'package:cybervpn_mobile/core/storage/secure_storage.dart';

/// In-memory fake implementation of [SecureStorageWrapper] for testing.
///
/// Stores key-value pairs in a plain [Map] instead of actual secure storage.
/// All high-level convenience methods from [SecureStorageWrapper] work correctly
/// because they delegate to the overridden [read], [write], [delete] methods.
class FakeSecureStorage extends SecureStorageWrapper {
  FakeSecureStorage() : super();

  final Map<String, String> _store = {};

  @override
  Future<void> write({required String key, required String value}) async {
    _store[key] = value;
  }

  @override
  Future<String?> read({required String key}) async {
    return _store[key];
  }

  @override
  Future<void> delete({required String key}) async {
    _store.remove(key);
  }

  @override
  Future<void> deleteAll() async {
    _store.clear();
  }

  @override
  Future<bool> containsKey({required String key}) async {
    return _store.containsKey(key);
  }

  /// Exposes the internal store for test assertions.
  Map<String, String> get store => Map.unmodifiable(_store);

  /// Clears all stored data. Alias for [deleteAll].
  void reset() => _store.clear();

  /// Pre-populates storage with test data.
  void seed(Map<String, String> data) {
    _store.addAll(data);
  }
}
