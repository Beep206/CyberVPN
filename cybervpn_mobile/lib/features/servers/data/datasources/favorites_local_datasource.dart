import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

/// Local datasource for persisting favorite server IDs with ordering.
///
/// Uses [SharedPreferences] (not secure storage) because favorite server IDs
/// are not sensitive data. Data survives logout since SharedPreferences is
/// not cleared on logout.
class FavoritesLocalDatasource {
  FavoritesLocalDatasource(this._prefs);

  final SharedPreferences _prefs;

  static const String _key = 'favorite_server_ids';

  /// Maximum number of favorites a user can have.
  static const int maxFavorites = 10;

  /// Returns the ordered list of favorite server IDs.
  Future<List<String>> getFavoriteIds() async {
    final raw = _prefs.getString(_key);
    if (raw == null || raw.isEmpty) return [];

    try {
      final decoded = jsonDecode(raw);
      if (decoded is List) {
        return decoded.cast<String>();
      }
      return [];
    } catch (_) {
      return [];
    }
  }

  /// Persists the full ordered list of favorite server IDs.
  Future<void> saveFavoriteIds(List<String> ids) async {
    await _prefs.setString(_key, jsonEncode(ids));
  }

  /// Adds a server ID to favorites. Returns `true` if added, `false` if
  /// the limit ([maxFavorites]) has been reached or the ID is already present.
  Future<bool> addFavorite(String id) async {
    final ids = await getFavoriteIds();

    if (ids.contains(id)) return false;

    if (ids.length >= maxFavorites) return false;

    ids.add(id);
    await saveFavoriteIds(ids);
    return true;
  }

  /// Removes a server ID from favorites. Returns `true` if it was present.
  Future<bool> removeFavorite(String id) async {
    final ids = await getFavoriteIds();
    final removed = ids.remove(id);
    if (removed) {
      await saveFavoriteIds(ids);
    }
    return removed;
  }

  /// Reorders favorites by moving the item at [oldIndex] to [newIndex].
  Future<void> reorderFavorites(int oldIndex, int newIndex) async {
    final ids = await getFavoriteIds();

    if (oldIndex < 0 ||
        oldIndex >= ids.length ||
        newIndex < 0 ||
        newIndex >= ids.length) {
      return;
    }

    // Standard reorder logic matching ReorderableListView semantics:
    // If moving down, the newIndex needs adjustment because removal shifts items.
    final adjustedNewIndex =
        newIndex > oldIndex ? newIndex - 1 : newIndex;

    final item = ids.removeAt(oldIndex);
    ids.insert(adjustedNewIndex, item);
    await saveFavoriteIds(ids);
  }
}
