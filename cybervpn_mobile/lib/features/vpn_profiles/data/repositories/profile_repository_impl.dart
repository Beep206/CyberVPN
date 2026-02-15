import 'dart:convert';
import 'dart:math';

import 'package:drift/drift.dart';

import 'package:cybervpn_mobile/core/data/database/app_database.dart';
import 'package:cybervpn_mobile/core/errors/failures.dart' hide Failure;
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/data/datasources/profile_local_ds.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/data/datasources/subscription_fetcher.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/data/mappers/profile_mapper.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/data/security/encrypted_field.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/profile_server.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/vpn_profile.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/repositories/profile_repository.dart';

/// Concrete implementation of [ProfileRepository].
///
/// Coordinates between the local Drift database, the subscription
/// HTTP fetcher, URL encryption, and domain-level mapping.
class ProfileRepositoryImpl implements ProfileRepository {
  ProfileRepositoryImpl({
    required ProfileLocalDataSource localDataSource,
    required SubscriptionFetcher subscriptionFetcher,
    required EncryptedFieldService encryptedField,
  })  : _localDs = localDataSource,
        _fetcher = subscriptionFetcher,
        _encField = encryptedField;

  final ProfileLocalDataSource _localDs;
  final SubscriptionFetcher _fetcher;
  final EncryptedFieldService _encField;

  // ── Reactive Streams ──────────────────────────────────────────────

  @override
  Stream<List<VpnProfile>> watchAll() {
    return _localDs.watchAll().asyncMap((profiles) async {
      final result = <VpnProfile>[];
      for (final profile in profiles) {
        final configs = await _localDs.getConfigsByProfileId(profile.id);
        result.add(ProfileMapper.toDomain(profile, configs));
      }
      return result;
    });
  }

  @override
  Stream<VpnProfile?> watchActiveProfile() {
    return _localDs.watchActiveProfile().asyncMap((profile) async {
      if (profile == null) return null;
      final configs = await _localDs.getConfigsByProfileId(profile.id);
      return ProfileMapper.toDomain(profile, configs);
    });
  }

  // ── Read Operations ───────────────────────────────────────────────

  @override
  Future<Result<VpnProfile>> getById(String id) async {
    try {
      final profile = await _localDs.getById(id);
      if (profile == null) {
        return const Failure(
          CacheFailure(message: 'Profile not found'),
        );
      }
      final configs = await _localDs.getConfigsByProfileId(id);
      return Success(ProfileMapper.toDomain(profile, configs));
    } catch (e) {
      return Failure(CacheFailure(message: 'Failed to get profile: $e'));
    }
  }

  @override
  Future<Result<VpnProfile?>> getBySubscriptionUrl(String url) async {
    try {
      final encrypted = await _encField.encrypt(url);
      final profile = await _localDs.getBySubscriptionUrl(encrypted ?? url);
      if (profile == null) return const Success(null);
      final configs = await _localDs.getConfigsByProfileId(profile.id);
      return Success(ProfileMapper.toDomain(profile, configs));
    } catch (e) {
      return Failure(CacheFailure(message: 'Failed to find profile: $e'));
    }
  }

  // ── Write Operations ──────────────────────────────────────────────

  @override
  Future<Result<VpnProfile>> addRemoteProfile(
    String url, {
    String? name,
  }) async {
    try {
      // Fetch and parse the subscription.
      final fetchResult = await _fetcher.fetch(url);
      if (fetchResult.servers.isEmpty) {
        return const Failure(
          ServerFailure(message: 'No servers found in subscription'),
        );
      }

      final profileId = _generateId();
      final now = DateTime.now();
      final displayName =
          name ?? fetchResult.info.title ?? _extractHostName(url);

      // Encrypt the subscription URL before storing.
      final encryptedUrl = await _encField.encrypt(url);

      final profileCompanion = ProfilesCompanion.insert(
        id: profileId,
        name: displayName,
        type: ProfileType.remote,
        subscriptionUrl: Value(encryptedUrl),
        createdAt: now,
        lastUpdatedAt: Value(now),
        uploadBytes: Value(fetchResult.info.uploadBytes),
        downloadBytes: Value(fetchResult.info.downloadBytes),
        totalBytes: Value(fetchResult.info.totalBytes),
        expiresAt: Value(fetchResult.info.expiresAt),
        updateIntervalMinutes: Value(fetchResult.info.updateIntervalMinutes),
        supportUrl: Value(fetchResult.info.supportUrl),
      );

      await _localDs.insert(profileCompanion);

      // Insert server configs.
      final configCompanions = fetchResult.servers
          .asMap()
          .entries
          .map((e) => ProfileConfigsCompanion.insert(
                id: _generateId(),
                profileId: profileId,
                name: e.value.name,
                serverAddress: e.value.serverAddress,
                port: e.value.port,
                protocol: e.value.protocol,
                configData: jsonEncode(e.value.configData),
                sortOrder: Value(e.key),
                createdAt: now,
              ))
          .toList();

      await _localDs.insertConfigs(configCompanions);

      return getById(profileId);
    } on SubscriptionFetcherException catch (e) {
      return Failure(NetworkFailure(message: e.message));
    } catch (e) {
      return Failure(CacheFailure(message: 'Failed to add profile: $e'));
    }
  }

  @override
  Future<Result<VpnProfile>> addLocalProfile(
    String name,
    List<ProfileServer> servers,
  ) async {
    try {
      final profileId = _generateId();
      final now = DateTime.now();

      final profileCompanion = ProfilesCompanion.insert(
        id: profileId,
        name: name,
        type: ProfileType.local,
        createdAt: now,
      );

      await _localDs.insert(profileCompanion);

      final configCompanions = servers
          .asMap()
          .entries
          .map((e) => ProfileMapper.serverToCompanion(
                e.value.copyWith(
                  id: _generateId(),
                  profileId: profileId,
                  sortOrder: e.key,
                  createdAt: now,
                ),
              ))
          .toList();

      await _localDs.insertConfigs(configCompanions);

      return getById(profileId);
    } catch (e) {
      return Failure(CacheFailure(message: 'Failed to add profile: $e'));
    }
  }

  @override
  Future<Result<void>> setActive(String profileId) async {
    try {
      await _localDs.setActive(profileId);
      return const Success(null);
    } catch (e) {
      return Failure(CacheFailure(message: 'Failed to set active: $e'));
    }
  }

  @override
  Future<Result<void>> update(VpnProfile profile) async {
    try {
      final companion = ProfileMapper.toCompanion(profile);
      await _localDs.update(profile.id, companion);
      return const Success(null);
    } catch (e) {
      return Failure(CacheFailure(message: 'Failed to update profile: $e'));
    }
  }

  @override
  Future<Result<void>> updateSubscription(String profileId) async {
    try {
      final profile = await _localDs.getById(profileId);
      if (profile == null) {
        return const Failure(CacheFailure(message: 'Profile not found'));
      }
      if (profile.type != ProfileType.remote) {
        return const Failure(
          ValidationFailure(message: 'Only remote profiles can be refreshed'),
        );
      }

      // Decrypt the stored subscription URL.
      final decryptedUrl = await _encField.decrypt(profile.subscriptionUrl);
      if (decryptedUrl == null || decryptedUrl.isEmpty) {
        return const Failure(
          CacheFailure(message: 'No subscription URL stored'),
        );
      }

      final fetchResult = await _fetcher.fetch(decryptedUrl);
      final now = DateTime.now();

      // Update profile metadata.
      await _localDs.update(
        profileId,
        ProfilesCompanion(
          lastUpdatedAt: Value(now),
          uploadBytes: Value(fetchResult.info.uploadBytes),
          downloadBytes: Value(fetchResult.info.downloadBytes),
          totalBytes: Value(fetchResult.info.totalBytes),
          expiresAt: Value(fetchResult.info.expiresAt),
          updateIntervalMinutes:
              Value(fetchResult.info.updateIntervalMinutes),
          supportUrl: Value(fetchResult.info.supportUrl),
        ),
      );

      // Replace server configs atomically.
      final configCompanions = fetchResult.servers
          .asMap()
          .entries
          .map((e) => ProfileConfigsCompanion.insert(
                id: _generateId(),
                profileId: profileId,
                name: e.value.name,
                serverAddress: e.value.serverAddress,
                port: e.value.port,
                protocol: e.value.protocol,
                configData: jsonEncode(e.value.configData),
                sortOrder: Value(e.key),
                createdAt: now,
              ))
          .toList();

      await _localDs.replaceConfigs(profileId, configCompanions);

      AppLogger.info(
        'Subscription updated',
        category: 'profile',
        data: {
          'profileId': profileId,
          'serverCount': fetchResult.servers.length,
        },
      );

      return const Success(null);
    } on SubscriptionFetcherException catch (e) {
      return Failure(NetworkFailure(message: e.message));
    } catch (e) {
      return Failure(
        CacheFailure(message: 'Failed to update subscription: $e'),
      );
    }
  }

  @override
  Future<Result<void>> delete(String profileId) async {
    try {
      await _localDs.delete(profileId);
      return const Success(null);
    } catch (e) {
      return Failure(CacheFailure(message: 'Failed to delete profile: $e'));
    }
  }

  @override
  Future<Result<void>> reorder(List<String> profileIds) async {
    try {
      final orders = <String, int>{};
      for (var i = 0; i < profileIds.length; i++) {
        orders[profileIds[i]] = i;
      }
      await _localDs.updateSortOrders(orders);
      return const Success(null);
    } catch (e) {
      return Failure(CacheFailure(message: 'Failed to reorder: $e'));
    }
  }

  @override
  Future<Result<int>> updateAllDueSubscriptions() async {
    try {
      // This is called from watchAll, so we need a snapshot.
      final profiles = await (_localDs.watchAll().first);
      final now = DateTime.now();
      var updatedCount = 0;

      for (final profile in profiles) {
        if (profile.type != ProfileType.remote) continue;
        if (profile.lastUpdatedAt == null) continue;

        final elapsed = now.difference(profile.lastUpdatedAt!);
        final interval = Duration(minutes: profile.updateIntervalMinutes);

        if (elapsed >= interval) {
          final result = await updateSubscription(profile.id);
          if (result.isSuccess) updatedCount++;
        }
      }

      return Success(updatedCount);
    } catch (e) {
      return Failure(
        CacheFailure(message: 'Failed to update subscriptions: $e'),
      );
    }
  }

  @override
  Future<Result<void>> migrateFromLegacy() async {
    try {
      // Legacy migration is a stub — the integration layer (INT-2)
      // will wire this to the actual legacy storage reads.
      AppLogger.info(
        'Legacy migration: no-op (placeholder for INT-2)',
        category: 'profile',
      );
      return const Success(null);
    } catch (e) {
      return Failure(
        CacheFailure(message: 'Failed to migrate legacy data: $e'),
      );
    }
  }

  @override
  Future<Result<int>> count() async {
    try {
      final c = await _localDs.count();
      return Success(c);
    } catch (e) {
      return Failure(CacheFailure(message: 'Failed to count profiles: $e'));
    }
  }

  // ── Helpers ───────────────────────────────────────────────────────

  /// Generates a UUID v4 for new entities.
  String _generateId() {
    final random = Random.secure();
    final bytes = List<int>.generate(16, (_) => random.nextInt(256));
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    final hex =
        bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
    return '${hex.substring(0, 8)}-${hex.substring(8, 12)}-'
        '${hex.substring(12, 16)}-${hex.substring(16, 20)}-'
        '${hex.substring(20)}';
  }

  /// Extracts a human-readable hostname from a URL for display.
  String _extractHostName(String url) {
    final uri = Uri.tryParse(url);
    return uri?.host ?? 'Subscription';
  }
}
