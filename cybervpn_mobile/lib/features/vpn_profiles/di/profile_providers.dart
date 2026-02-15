import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/data/database/database_provider.dart';
import 'package:cybervpn_mobile/core/di/providers.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/data/datasources/profile_local_ds.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/data/datasources/subscription_fetcher.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/data/repositories/profile_repository_impl.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/data/security/encrypted_field.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/data/services/legacy_profile_migration.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/vpn_profile.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/repositories/profile_repository.dart'
    as vpn_profiles;
import 'package:cybervpn_mobile/features/vpn_profiles/domain/usecases/add_local_profile.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/usecases/add_remote_profile.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/usecases/delete_profile.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/usecases/migrate_legacy_profiles.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/usecases/switch_active_profile.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/usecases/update_subscriptions.dart';

// ── Data Sources ────────────────────────────────────────────────────

/// Provides the Drift-backed local data source for VPN profiles.
final vpnProfileLocalDataSourceProvider =
    Provider<ProfileLocalDataSource>((ref) {
  return ProfileLocalDataSource(db: ref.watch(appDatabaseProvider));
});

/// Provides the HTTP subscription fetcher.
final subscriptionFetcherProvider = Provider<SubscriptionFetcher>((ref) {
  return SubscriptionFetcher(dio: ref.watch(dioProvider));
});

/// Provides the encrypted field service for subscription URL encryption.
final encryptedFieldServiceProvider = Provider<EncryptedFieldService>((ref) {
  return EncryptedFieldService(secureStorage: ref.watch(secureStorageProvider));
});

// ── Repository ──────────────────────────────────────────────────────

/// Provides the [ProfileRepository] for multi-profile management.
///
/// This is separate from [profileRepositoryProvider] in providers.dart
/// which provides the user-profile (account/2FA) repository.
final vpnProfileRepositoryProvider =
    Provider<vpn_profiles.ProfileRepository>((ref) {
  return ProfileRepositoryImpl(
    localDataSource: ref.watch(vpnProfileLocalDataSourceProvider),
    subscriptionFetcher: ref.watch(subscriptionFetcherProvider),
    encryptedField: ref.watch(encryptedFieldServiceProvider),
  );
});

// ── Use Cases ───────────────────────────────────────────────────────

/// Provides [AddRemoteProfileUseCase].
final addRemoteProfileUseCaseProvider =
    Provider<AddRemoteProfileUseCase>((ref) {
  return AddRemoteProfileUseCase(ref.watch(vpnProfileRepositoryProvider));
});

/// Provides [AddLocalProfileUseCase].
final addLocalProfileUseCaseProvider =
    Provider<AddLocalProfileUseCase>((ref) {
  return AddLocalProfileUseCase(ref.watch(vpnProfileRepositoryProvider));
});

/// Provides [SwitchActiveProfileUseCase].
final switchActiveProfileUseCaseProvider =
    Provider<SwitchActiveProfileUseCase>((ref) {
  return SwitchActiveProfileUseCase(ref.watch(vpnProfileRepositoryProvider));
});

/// Provides [DeleteProfileUseCase].
final deleteProfileUseCaseProvider = Provider<DeleteProfileUseCase>((ref) {
  return DeleteProfileUseCase(ref.watch(vpnProfileRepositoryProvider));
});

/// Provides [UpdateSubscriptionsUseCase].
final updateSubscriptionsUseCaseProvider =
    Provider<UpdateSubscriptionsUseCase>((ref) {
  return UpdateSubscriptionsUseCase(ref.watch(vpnProfileRepositoryProvider));
});

/// Provides [MigrateLegacyProfilesUseCase].
final migrateLegacyProfilesUseCaseProvider =
    Provider<MigrateLegacyProfilesUseCase>((ref) {
  return MigrateLegacyProfilesUseCase(
    ref.watch(vpnProfileRepositoryProvider),
  );
});

// ── App-Scoped Stream Providers ─────────────────────────────────────

/// Watches the full ordered list of VPN profiles.
///
/// App-scoped (no autoDispose) because profile data is used across
/// multiple screens (profile list, connection, server list).
final profileListProvider = StreamProvider<List<VpnProfile>>((ref) {
  return ref.watch(vpnProfileRepositoryProvider).watchAll();
});

/// Watches the currently active VPN profile.
///
/// App-scoped — the active profile drives VPN connection state
/// and server selection across the app.
final activeVpnProfileProvider = StreamProvider<VpnProfile?>((ref) {
  return ref.watch(vpnProfileRepositoryProvider).watchActiveProfile();
});

// ── Legacy Migration ──────────────────────────────────────────────

/// Provides the [LegacyProfileMigrationService].
final legacyProfileMigrationServiceProvider =
    Provider<LegacyProfileMigrationService>((ref) {
  return LegacyProfileMigrationService(
    configImportRepository: ref.watch(configImportRepositoryProvider),
    profileRepository: ref.watch(vpnProfileRepositoryProvider),
    localStorage: ref.watch(localStorageProvider),
  );
});

/// Runs the legacy profile migration exactly once during app startup.
///
/// Returns `true` if migration was performed, `false` if skipped
/// (already complete or no data). Watched by the router during splash
/// to ensure migration completes before entering the main UI.
final profileMigrationProvider = FutureProvider<bool>((ref) {
  final service = ref.watch(legacyProfileMigrationServiceProvider);
  return service.migrate();
});
