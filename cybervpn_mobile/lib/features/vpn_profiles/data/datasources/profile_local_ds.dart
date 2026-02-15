import 'package:drift/drift.dart';

import 'package:cybervpn_mobile/core/data/database/app_database.dart';

/// Local data source for VPN profiles backed by the Drift database.
///
/// Provides CRUD operations and reactive streams for profiles and
/// their associated server configurations.
///
/// All write operations are transactional to ensure data consistency —
/// e.g. deleting a profile also removes its configs atomically.
class ProfileLocalDataSource {
  /// Creates a [ProfileLocalDataSource].
  ///
  /// [db] is the Drift [AppDatabase] instance (injected via Riverpod).
  ProfileLocalDataSource({required AppDatabase db}) : _db = db;

  final AppDatabase _db;

  // ── Reactive Streams ──────────────────────────────────────────────

  /// Watches all profiles ordered by [sortOrder].
  ///
  /// Emits a new list whenever any profile row is inserted, updated,
  /// or deleted.
  Stream<List<Profile>> watchAll() {
    return (_db.select(_db.profiles)
          ..orderBy([(t) => OrderingTerm.asc(t.sortOrder)]))
        .watch();
  }

  /// Watches the currently active profile (where `isActive == true`).
  ///
  /// Emits `null` if no profile is active.
  Stream<Profile?> watchActiveProfile() {
    return (_db.select(_db.profiles)
          ..where((t) => t.isActive.equals(true))
          ..limit(1))
        .watchSingleOrNull();
  }

  /// Watches all server configs for a given profile, ordered by [sortOrder].
  Stream<List<ProfileConfig>> watchConfigsByProfileId(String profileId) {
    return (_db.select(_db.profileConfigs)
          ..where((t) => t.profileId.equals(profileId))
          ..orderBy([(t) => OrderingTerm.asc(t.sortOrder)]))
        .watch();
  }

  // ── Read Operations ───────────────────────────────────────────────

  /// Returns a single profile by its [id], or `null` if not found.
  Future<Profile?> getById(String id) {
    return (_db.select(_db.profiles)..where((t) => t.id.equals(id)))
        .getSingleOrNull();
  }

  /// Returns the profile with the given [subscriptionUrl], or `null`.
  ///
  /// Useful for deduplication when adding a subscription by URL.
  Future<Profile?> getBySubscriptionUrl(String subscriptionUrl) {
    return (_db.select(_db.profiles)
          ..where((t) => t.subscriptionUrl.equals(subscriptionUrl)))
        .getSingleOrNull();
  }

  /// Returns the total number of profiles.
  Future<int> count() async {
    final countExpr = _db.profiles.id.count();
    final query = _db.selectOnly(_db.profiles)..addColumns([countExpr]);
    final result = await query.getSingle();
    return result.read(countExpr) ?? 0;
  }

  /// Returns all server configs for a given profile.
  Future<List<ProfileConfig>> getConfigsByProfileId(String profileId) {
    return (_db.select(_db.profileConfigs)
          ..where((t) => t.profileId.equals(profileId))
          ..orderBy([(t) => OrderingTerm.asc(t.sortOrder)]))
        .get();
  }

  // ── Write Operations ──────────────────────────────────────────────

  /// Inserts a new profile.
  ///
  /// Returns the inserted [Profile] data class.
  Future<Profile> insert(ProfilesCompanion profile) {
    return _db.into(_db.profiles).insertReturning(profile);
  }

  /// Inserts multiple server configs in a single transaction.
  Future<void> insertConfigs(List<ProfileConfigsCompanion> configs) {
    return _db.batch((batch) {
      batch.insertAll(_db.profileConfigs, configs);
    });
  }

  /// Updates an existing profile by [id].
  ///
  /// Only the fields present in [companion] are updated.
  /// Returns `true` if a row was updated.
  Future<bool> update(String id, ProfilesCompanion companion) async {
    final count = await (_db.update(_db.profiles)
          ..where((t) => t.id.equals(id)))
        .write(companion);
    return count > 0;
  }

  /// Sets the given profile as active, deactivating all others.
  ///
  /// Runs in a transaction to ensure exactly one profile is active.
  Future<void> setActive(String profileId) {
    return _db.transaction(() async {
      // Deactivate all profiles.
      await _db.update(_db.profiles).write(
            const ProfilesCompanion(isActive: Value(false)),
          );
      // Activate the target profile.
      await (_db.update(_db.profiles)
            ..where((t) => t.id.equals(profileId)))
          .write(const ProfilesCompanion(isActive: Value(true)));
    });
  }

  /// Deletes a profile and all its server configs in a transaction.
  ///
  /// Returns the number of deleted profile rows (0 or 1).
  Future<int> delete(String id) {
    return _db.transaction(() async {
      await (_db.delete(_db.profileConfigs)
            ..where((t) => t.profileId.equals(id)))
          .go();
      return (_db.delete(_db.profiles)..where((t) => t.id.equals(id))).go();
    });
  }

  /// Deletes all server configs for a profile (without deleting the profile).
  ///
  /// Useful before replacing configs during a subscription refresh.
  Future<int> deleteConfigsByProfileId(String profileId) {
    return (_db.delete(_db.profileConfigs)
          ..where((t) => t.profileId.equals(profileId)))
        .go();
  }

  /// Updates sort orders for multiple profiles in a batch.
  ///
  /// [orders] maps profile IDs to their new sort order values.
  Future<void> updateSortOrders(Map<String, int> orders) {
    return _db.batch((batch) {
      for (final entry in orders.entries) {
        batch.update(
          _db.profiles,
          ProfilesCompanion(sortOrder: Value(entry.value)),
          where: ($ProfilesTable t) => t.id.equals(entry.key),
        );
      }
    });
  }

  /// Replaces all configs for a profile in a single transaction.
  ///
  /// Deletes existing configs and inserts the new ones. Used during
  /// subscription refresh to atomically swap server lists.
  Future<void> replaceConfigs(
    String profileId,
    List<ProfileConfigsCompanion> newConfigs,
  ) {
    return _db.transaction(() async {
      await (_db.delete(_db.profileConfigs)
            ..where((t) => t.profileId.equals(profileId)))
          .go();
      await _db.batch((batch) {
        batch.insertAll(_db.profileConfigs, newConfigs);
      });
    });
  }
}
