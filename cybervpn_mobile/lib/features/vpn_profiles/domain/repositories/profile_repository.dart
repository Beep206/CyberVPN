import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/profile_server.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/vpn_profile.dart';

/// Abstract interface for managing VPN profiles.
///
/// Implementations handle persistence (Drift), network fetching
/// (subscription URLs), and ordering. All fallible operations return
/// [Result] to avoid exception-based control flow.
abstract class ProfileRepository {
  /// Emits the full ordered list of profiles whenever any profile changes.
  Stream<List<VpnProfile>> watchAll();

  /// Emits the currently-active profile, or `null` when none is active.
  Stream<VpnProfile?> watchActiveProfile();

  /// Fetches a single profile by its [id].
  Future<Result<VpnProfile>> getById(String id);

  /// Finds a remote profile matching the given subscription [url].
  Future<Result<VpnProfile?>> getBySubscriptionUrl(String url);

  /// Creates a new remote profile by fetching the subscription at [url].
  Future<Result<VpnProfile>> addRemoteProfile(String url, {String? name});

  /// Creates a new local profile from a list of [servers].
  Future<Result<VpnProfile>> addLocalProfile(
    String name,
    List<ProfileServer> servers,
  );

  /// Sets the profile with [profileId] as active, deactivating any other.
  Future<Result<void>> setActive(String profileId);

  /// Persists changes to an existing [profile].
  Future<Result<void>> update(VpnProfile profile);

  /// Re-fetches the subscription for the profile with [profileId] and
  /// updates its server list and metadata.
  Future<Result<void>> updateSubscription(String profileId);

  /// Deletes the profile with [profileId] and all associated servers.
  Future<Result<void>> delete(String profileId);

  /// Reorders profiles to match [profileIds] order.
  Future<Result<void>> reorder(List<String> profileIds);

  /// Refreshes all remote profiles whose update interval has elapsed.
  ///
  /// Returns the number of profiles that were updated.
  Future<Result<int>> updateAllDueSubscriptions();

  /// Migrates data from the legacy single-config storage into the
  /// multi-profile system.
  Future<Result<void>> migrateFromLegacy();

  /// Returns the total number of stored profiles.
  Future<Result<int>> count();
}
