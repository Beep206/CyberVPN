import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:cybervpn_mobile/core/providers/shared_preferences_provider.dart';
import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:cybervpn_mobile/features/servers/presentation/providers/profile_aware_server_list.dart';

/// Key used for persisting recent server IDs in SharedPreferences.
const _kRecentServerIds = 'recent_server_ids';

/// Maximum number of recent servers to retain.
const _maxRecent = 5;

/// Notifier that manages the list of recently connected server IDs.
///
/// Persists IDs in SharedPreferences. When a server is connected,
/// call [addServer] to push it to the front of the list (deduplicating
/// and capping at [_maxRecent] entries).
class RecentServersNotifier extends Notifier<List<String>> {
  SharedPreferences get _prefs => ref.read(sharedPreferencesProvider);

  @override
  List<String> build() {
    return _prefs.getStringList(_kRecentServerIds) ?? [];
  }

  /// Adds [serverId] to the front of the recent list, removing duplicates
  /// and capping to [_maxRecent] entries.
  Future<void> addServer(String serverId) async {
    final updated = [
      serverId,
      ...state.where((id) => id != serverId),
    ].take(_maxRecent).toList();

    state = updated;
    await _prefs.setStringList(_kRecentServerIds, updated);
  }
}

/// Provider for the list of recently connected server IDs.
final recentServerIdsProvider =
    NotifierProvider<RecentServersNotifier, List<String>>(
  RecentServersNotifier.new,
);

/// Provider that resolves recent server IDs to full [ServerEntity] objects.
///
/// Returns only servers that still exist in the current server list.
final recentServersProvider = Provider<List<ServerEntity>>((ref) {
  final ids = ref.watch(recentServerIdsProvider);
  final allServers = ref.watch(
    profileAwareServerListProvider.select((s) => s.value?.servers ?? []),
  );

  final serverMap = {for (final s in allServers) s.id: s};
  return ids
      .map((id) => serverMap[id])
      .whereType<ServerEntity>()
      .toList();
});
