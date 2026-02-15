import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:cybervpn_mobile/features/servers/presentation/providers/server_list_provider.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/di/profile_providers.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/profile_server.dart';

// ---------------------------------------------------------------------------
// Mapper
// ---------------------------------------------------------------------------

/// Converts a [ProfileServer] (from the multi-profile Drift DB) into a
/// [ServerEntity] (the type consumed by the server list UI).
///
/// Fields that have no equivalent in [ProfileServer] (e.g. `countryCode`,
/// `city`, `load`) receive sensible defaults.
ServerEntity profileServerToEntity(ProfileServer ps) {
  return ServerEntity(
    id: ps.id,
    name: ps.name,
    countryCode: '',
    countryName: ps.remark ?? '',
    city: '',
    address: ps.serverAddress,
    port: ps.port,
    protocol: ps.protocol.name,
    isAvailable: true,
    isPremium: false,
    isFavorite: ps.isFavorite,
    ping: ps.latencyMs,
  );
}

// ---------------------------------------------------------------------------
// Profile-Aware Server List Adapter
// ---------------------------------------------------------------------------

/// Provides a profile-aware view of the server list.
///
/// Watches [activeVpnProfileProvider]:
/// - **No active profile** → passes through the API-backed
///   [serverListProvider] unchanged (existing behaviour).
/// - **Active profile** → maps the profile's [ProfileServer] list to
///   [ServerEntity] objects and wraps them in a [ServerListState].
///
/// All derived providers ([filteredServersProvider],
/// [groupedByCountryProvider], etc.) read from this provider so that
/// switching profiles transparently updates the server list UI.
final profileAwareServerListProvider =
    Provider<AsyncValue<ServerListState>>((ref) {
  final activeProfileAsync = ref.watch(activeVpnProfileProvider);

  return activeProfileAsync.when(
    loading: () => const AsyncLoading<ServerListState>(),
    error: AsyncError<ServerListState>.new,
    data: (activeProfile) {
      if (activeProfile == null) {
        // No active profile → delegate to API-backed server list.
        return ref.watch(serverListProvider);
      }

      // Active profile → build state from profile servers.
      final servers = activeProfile.servers
          .map(profileServerToEntity)
          .toList();

      return AsyncData<ServerListState>(
        ServerListState(servers: servers),
      );
    },
  );
});
