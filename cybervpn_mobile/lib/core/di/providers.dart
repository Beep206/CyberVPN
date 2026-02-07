import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/misc.dart' show Override;
import 'package:shared_preferences/shared_preferences.dart';

import 'package:cybervpn_mobile/core/config/environment_config.dart';
import 'package:cybervpn_mobile/core/network/api_client.dart';
import 'package:cybervpn_mobile/core/network/auth_interceptor.dart';
import 'package:cybervpn_mobile/core/network/retry_interceptor.dart';
import 'package:cybervpn_mobile/core/storage/local_storage.dart';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/core/types/result.dart';

// Data sources (lazy - created on first access via ref.watch)
import 'package:cybervpn_mobile/features/auth/data/datasources/auth_remote_ds.dart';
import 'package:cybervpn_mobile/features/auth/data/datasources/auth_local_ds.dart';
import 'package:cybervpn_mobile/features/servers/data/datasources/server_remote_ds.dart';
import 'package:cybervpn_mobile/features/servers/data/datasources/server_local_ds.dart';
import 'package:cybervpn_mobile/features/subscription/data/datasources/subscription_remote_ds.dart';
import 'package:cybervpn_mobile/features/subscription/data/datasources/subscription_local_ds.dart';
import 'package:cybervpn_mobile/features/referral/data/datasources/referral_remote_ds.dart';
import 'package:cybervpn_mobile/features/vpn/data/datasources/vpn_engine_datasource.dart';
import 'package:cybervpn_mobile/features/profile/data/datasources/profile_remote_ds.dart';
import 'package:cybervpn_mobile/features/profile/data/repositories/profile_repository_impl.dart';
import 'package:cybervpn_mobile/features/profile/domain/repositories/profile_repository.dart';
import 'package:cybervpn_mobile/features/profile/domain/usecases/get_profile.dart';
import 'package:cybervpn_mobile/features/profile/domain/usecases/setup_2fa.dart';
import 'package:cybervpn_mobile/features/profile/domain/usecases/verify_2fa.dart';
import 'package:cybervpn_mobile/features/profile/domain/usecases/disable_2fa.dart';
import 'package:cybervpn_mobile/features/profile/domain/usecases/get_devices.dart';
import 'package:cybervpn_mobile/features/profile/domain/usecases/remove_device.dart';
import 'package:cybervpn_mobile/features/profile/domain/usecases/register_device.dart';
import 'package:cybervpn_mobile/features/profile/domain/services/device_registration_service.dart';
import 'package:cybervpn_mobile/features/profile/domain/usecases/link_social_account.dart'
    show LinkSocialAccountUseCase, CompleteSocialAccountLinkUseCase;
import 'package:cybervpn_mobile/features/profile/domain/usecases/unlink_social_account.dart';
import 'package:cybervpn_mobile/features/notifications/data/datasources/fcm_datasource.dart';
import 'package:cybervpn_mobile/features/notifications/data/datasources/notification_local_datasource.dart';
import 'package:cybervpn_mobile/features/notifications/data/repositories/notification_repository_impl.dart';
import 'package:cybervpn_mobile/features/notifications/domain/repositories/notification_repository.dart';
import 'package:cybervpn_mobile/features/config_import/data/parsers/subscription_url_parser.dart';
import 'package:cybervpn_mobile/features/config_import/data/repositories/config_import_repository_impl.dart';
import 'package:cybervpn_mobile/features/config_import/domain/repositories/config_import_repository.dart';

// Repository implementations (lazy - created on first access via ref.watch)
import 'package:cybervpn_mobile/features/auth/data/repositories/auth_repository_impl.dart';
import 'package:cybervpn_mobile/features/auth/domain/repositories/auth_repository.dart';
import 'package:cybervpn_mobile/features/auth/domain/usecases/login.dart';
import 'package:cybervpn_mobile/features/auth/domain/usecases/register.dart';
import 'package:cybervpn_mobile/features/onboarding/data/repositories/onboarding_repository_impl.dart';
import 'package:cybervpn_mobile/features/onboarding/domain/repositories/onboarding_repository.dart';
import 'package:cybervpn_mobile/features/settings/data/repositories/settings_repository_impl.dart';
import 'package:cybervpn_mobile/features/settings/domain/repositories/settings_repository.dart';
import 'package:cybervpn_mobile/features/referral/data/repositories/referral_repository_impl.dart';
import 'package:cybervpn_mobile/features/referral/domain/repositories/referral_repository.dart';
import 'package:cybervpn_mobile/features/servers/data/repositories/server_repository_impl.dart';
import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:cybervpn_mobile/features/servers/domain/repositories/server_repository.dart';
import 'package:cybervpn_mobile/features/servers/data/datasources/ping_service.dart';
import 'package:cybervpn_mobile/features/servers/data/datasources/favorites_local_datasource.dart';
import 'package:cybervpn_mobile/features/subscription/data/repositories/subscription_repository_impl.dart';
import 'package:cybervpn_mobile/features/subscription/domain/repositories/subscription_repository.dart';
import 'package:cybervpn_mobile/features/subscription/data/datasources/revenuecat_datasource.dart';
import 'package:cybervpn_mobile/features/vpn/data/repositories/vpn_repository_impl.dart';
import 'package:cybervpn_mobile/features/vpn/domain/repositories/vpn_repository.dart';
import 'package:cybervpn_mobile/features/vpn/domain/usecases/connect_vpn.dart';
import 'package:cybervpn_mobile/features/vpn/domain/usecases/disconnect_vpn.dart';
import 'package:cybervpn_mobile/features/vpn/domain/usecases/auto_reconnect.dart';
import 'package:cybervpn_mobile/features/vpn/data/datasources/kill_switch_service.dart';
import 'package:cybervpn_mobile/core/network/network_info.dart';

import 'package:cybervpn_mobile/core/device/device_provider.dart'
    show secureStorageProvider;
// Re-export so downstream files can access it via core/di/providers.dart.
export 'package:cybervpn_mobile/core/device/device_provider.dart'
    show secureStorageProvider;
import 'package:cybervpn_mobile/core/providers/shared_preferences_provider.dart';

// ═══════════════════════════════════════════════════════════════════════════
// Provider Scoping Audit (last updated: 2026-02-07)
// ═══════════════════════════════════════════════════════════════════════════
//
// GLOBAL (app-lifetime, no autoDispose) — this file:
//   All providers below are stateless infrastructure, repositories, and
//   use cases. They are cheap to keep alive and used across many screens.
//
// APP-SCOPED notifiers (no autoDispose) — feature providers:
//   authProvider           — session lifecycle, must survive navigation
//   settingsProvider       — app preferences, always needed
//   subscriptionProvider   — status checked by many screens
//   serverListProvider     — server list reused across tabs
//   profileProvider        — used by VPN connection + multiple screens
//   configImportProvider   — clipboard observer is always active
//   onboardingProvider     — checked by router guards
//   quickSetupProvider     — checked by router guards
//   notificationProvider   — background listener in app lifecycle
//
// SCREEN-SCOPED (autoDispose) — feature providers:
//   diagnosticsProvider    — only on diagnostics screens
//   referralProvider       — only on referral dashboard
//   permissionRequestProvider — only during onboarding flow
//   telegramAuthProvider   — only on login/register screens
//   biometricLoginProvider — only on login screen
//
// ═══════════════════════════════════════════════════════════════════════════

// ---------------------------------------------------------------------------
// Settings repository provider
// ---------------------------------------------------------------------------

/// Provides the [SettingsRepository] backed by [SharedPreferences].
final settingsRepositoryProvider = Provider<SettingsRepository>((ref) {
  return SettingsRepositoryImpl(
    sharedPreferences: ref.watch(sharedPreferencesProvider),
  );
});

// ---------------------------------------------------------------------------
// Onboarding repository provider
// ---------------------------------------------------------------------------

/// Provides the [OnboardingRepository] backed by [SharedPreferences].
final onboardingRepositoryProvider = Provider<OnboardingRepository>((ref) {
  return OnboardingRepositoryImpl(
    sharedPreferences: ref.watch(sharedPreferencesProvider),
  );
});

// ---------------------------------------------------------------------------
// Referral repository provider
// ---------------------------------------------------------------------------

/// Provides the [ReferralRepository] backed by [ReferralRemoteDataSource].
final referralRepositoryProvider = Provider<ReferralRepository>((ref) {
  return ReferralRepositoryImpl(
    remoteDataSource: ref.watch(referralRemoteDataSourceProvider),
  );
});

// ---------------------------------------------------------------------------
// Profile repository & use-case providers
// ---------------------------------------------------------------------------

/// Provides the [ProfileRepository] lazily via ref.watch.
final profileRepositoryProvider = Provider<ProfileRepository>((ref) {
  return ProfileRepositoryImpl(
    remoteDataSource: ProfileRemoteDataSourceImpl(ref.watch(apiClientProvider)),
    networkInfo: ref.watch(networkInfoProvider),
  );
});

/// Provides the [GetProfileUseCase].
final getProfileUseCaseProvider = Provider<GetProfileUseCase>((ref) {
  return GetProfileUseCase(ref.watch(profileRepositoryProvider));
});

/// Provides the [Setup2FAUseCase].
final setup2FAUseCaseProvider = Provider<Setup2FAUseCase>((ref) {
  return Setup2FAUseCase(ref.watch(profileRepositoryProvider));
});

/// Provides the [Verify2FAUseCase].
final verify2FAUseCaseProvider = Provider<Verify2FAUseCase>((ref) {
  return Verify2FAUseCase(ref.watch(profileRepositoryProvider));
});

/// Provides the [Disable2FAUseCase].
final disable2FAUseCaseProvider = Provider<Disable2FAUseCase>((ref) {
  return Disable2FAUseCase(ref.watch(profileRepositoryProvider));
});

/// Provides the [GetDevicesUseCase].
final getDevicesUseCaseProvider = Provider<GetDevicesUseCase>((ref) {
  return GetDevicesUseCase(ref.watch(profileRepositoryProvider));
});

/// Provides the [RemoveDeviceUseCase].
final removeDeviceUseCaseProvider = Provider<RemoveDeviceUseCase>((ref) {
  return RemoveDeviceUseCase(ref.watch(profileRepositoryProvider));
});

/// Provides the [RegisterDeviceUseCase].
final registerDeviceUseCaseProvider = Provider<RegisterDeviceUseCase>((ref) {
  return RegisterDeviceUseCase(ref.watch(profileRepositoryProvider));
});

/// Provides the [DeviceRegistrationService].
final deviceRegistrationServiceProvider = Provider<DeviceRegistrationService>((
  ref,
) {
  return DeviceRegistrationService(
    registerDevice: ref.watch(registerDeviceUseCaseProvider),
    storage: ref.watch(secureStorageProvider),
  );
});

/// Provides the [LinkSocialAccountUseCase].
final linkSocialAccountUseCaseProvider = Provider<LinkSocialAccountUseCase>((
  ref,
) {
  return LinkSocialAccountUseCase(ref.watch(profileRepositoryProvider));
});

/// Provides the [CompleteSocialAccountLinkUseCase].
final completeSocialAccountLinkUseCaseProvider =
    Provider<CompleteSocialAccountLinkUseCase>((ref) {
      return CompleteSocialAccountLinkUseCase(
        ref.watch(profileRepositoryProvider),
      );
    });

/// Provides the [UnlinkSocialAccountUseCase].
final unlinkSocialAccountUseCaseProvider = Provider<UnlinkSocialAccountUseCase>(
  (ref) {
    return UnlinkSocialAccountUseCase(ref.watch(profileRepositoryProvider));
  },
);

// ---------------------------------------------------------------------------
// Notification repository & datasource providers
// ---------------------------------------------------------------------------

/// Provides the [FcmDatasource] singleton (lazily created).
///
/// Override in tests to inject a mock.
final fcmDatasourceProvider = Provider<FcmDatasource>((ref) {
  return FcmDatasourceImpl();
});

/// Provides the [NotificationRepositoryImpl] lazily via ref.watch.
final notificationRepositoryImplProvider = Provider<NotificationRepositoryImpl>(
  (ref) {
    return NotificationRepositoryImpl(
      fcmDatasource: ref.watch(fcmDatasourceProvider),
      localDatasource: NotificationLocalDatasourceImpl(
        ref.watch(localStorageProvider),
      ),
      apiClient: ref.watch(apiClientProvider),
    );
  },
);

/// Provides the [NotificationRepository] implementation via the impl provider.
final notificationRepositoryProvider = Provider<NotificationRepository>((ref) {
  return ref.watch(notificationRepositoryImplProvider);
});

// ---------------------------------------------------------------------------
// Config import repository provider
// ---------------------------------------------------------------------------

/// Provides the [ConfigImportRepository] lazily via ref.watch.
final configImportRepositoryProvider = Provider<ConfigImportRepository>((ref) {
  return ConfigImportRepositoryImpl(
    sharedPreferences: ref.watch(sharedPreferencesProvider),
    subscriptionUrlParser: SubscriptionUrlParser(dio: ref.watch(dioProvider)),
  );
});

// ---------------------------------------------------------------------------
// VPN repository & related providers
// ---------------------------------------------------------------------------

/// Provides the [VpnRepository] implementation lazily via ref.watch.
final vpnRepositoryProvider = Provider<VpnRepository>((ref) {
  return VpnRepositoryImpl(
    engine: ref.watch(vpnEngineDatasourceProvider),
    localStorage: ref.watch(localStorageProvider),
    secureStorage: ref.watch(secureStorageProvider),
  );
});

/// Provides the [ConnectVpnUseCase].
final connectVpnUseCaseProvider = Provider<ConnectVpnUseCase>((ref) {
  return ConnectVpnUseCase(ref.watch(vpnRepositoryProvider));
});

/// Provides the [DisconnectVpnUseCase].
final disconnectVpnUseCaseProvider = Provider<DisconnectVpnUseCase>((ref) {
  return DisconnectVpnUseCase(ref.watch(vpnRepositoryProvider));
});

/// Provides the [AutoReconnectService].
final autoReconnectServiceProvider = Provider<AutoReconnectService>((ref) {
  return AutoReconnectService(
    repository: ref.watch(vpnRepositoryProvider),
    networkInfo: ref.watch(networkInfoProvider),
  );
});

/// Provides the [KillSwitchService].
final killSwitchServiceProvider = Provider<KillSwitchService>((ref) {
  return KillSwitchService();
});

/// Holds the currently active DNS server list resolved from user settings.
///
/// Consumed by lower-level config generators and the VPN engine layer.
/// `null` means use platform / system DNS defaults.
final activeDnsServersProvider =
    NotifierProvider<ActiveDnsServersNotifier, List<String>?>(
      ActiveDnsServersNotifier.new,
    );

/// Notifier for active DNS servers state.
class ActiveDnsServersNotifier extends Notifier<List<String>?> {
  @override
  List<String>? build() => null;

  void set(List<String>? servers) {
    state = servers;
  }
}

// ---------------------------------------------------------------------------
// Subscription repository & related providers
//
// Scoping: Subscription providers are global because subscription state
// affects multiple features (VPN connection eligibility, server list filtering
// for premium servers, profile display). If subscription state were scoped
// to the subscription feature only, other features would need to duplicate
// the data source or introduce cross-feature dependencies.
// ---------------------------------------------------------------------------

/// Provides the [SubscriptionLocalDataSource] for persistent caching.
final subscriptionLocalDataSourceProvider =
    Provider<SubscriptionLocalDataSource>((ref) {
      return SubscriptionLocalDataSourceImpl(ref.watch(localStorageProvider));
    });

/// Provides the [SubscriptionRepository] lazily via ref.watch.
final subscriptionRepositoryProvider = Provider<SubscriptionRepository>((ref) {
  return SubscriptionRepositoryImpl(
    remoteDataSource: ref.watch(subscriptionRemoteDataSourceProvider),
    localDataSource: ref.watch(subscriptionLocalDataSourceProvider),
  );
});

/// Provides the [RevenueCatDataSource] singleton.
///
/// Override in tests to inject a mock.
final revenueCatDataSourceProvider = Provider<RevenueCatDataSource>((ref) {
  return RevenueCatDataSource();
});

// ---------------------------------------------------------------------------
// Auth repository provider
// ---------------------------------------------------------------------------

/// Provides the [AuthRepository] implementation lazily via ref.watch.
final authRepositoryProvider = Provider<AuthRepository>((ref) {
  return AuthRepositoryImpl(
    remoteDataSource: ref.watch(authRemoteDataSourceProvider),
    localDataSource: ref.watch(authLocalDataSourceProvider),
    networkInfo: ref.watch(networkInfoProvider),
  );
});

/// Provides the [LoginUseCase] with input validation.
final loginUseCaseProvider = Provider<LoginUseCase>((ref) {
  return LoginUseCase(ref.watch(authRepositoryProvider));
});

/// Provides the [RegisterUseCase] with input validation.
final registerUseCaseProvider = Provider<RegisterUseCase>((ref) {
  return RegisterUseCase(ref.watch(authRepositoryProvider));
});

// ---------------------------------------------------------------------------
// Server repository & related providers
//
// Scoping: Server providers are global because server data (list, favorites,
// ping results) is shared across multiple features (connection, settings,
// quick-connect). The serverDetailProvider uses .family to allow parameterized
// access by server ID without global state pollution.
// ---------------------------------------------------------------------------

/// Provides details for a specific server by ID.
///
/// Uses the `.family` modifier so each server ID gets its own cached provider
/// instance, avoiding unnecessary rebuilds across the server list.
final serverDetailProvider = FutureProvider.family<ServerEntity?, String>((
  ref,
  serverId,
) async {
  final repo = ref.watch(serverRepositoryProvider);
  final result = await repo.getServerById(serverId);
  return switch (result) {
    Success(:final data) => data,
    Failure() => null,
  };
});

/// Provides the [ServerRepository] lazily via ref.watch.
final serverRepositoryProvider = Provider<ServerRepository>((ref) {
  return ServerRepositoryImpl(
    remoteDataSource: ref.watch(serverRemoteDataSourceProvider),
    localDataSource: ref.watch(serverLocalDataSourceProvider),
  );
});

/// Singleton [PingService] instance.
final pingServiceProvider = Provider<PingService>((ref) {
  final service = PingService();
  ref.onDispose(service.dispose);
  return service;
});

/// Provider for [FavoritesLocalDatasource].
///
/// Requires [SharedPreferences] to be available. Use
/// [sharedPreferencesProvider] to supply the instance.
final favoritesLocalDatasourceProvider = Provider<FavoritesLocalDatasource>((
  ref,
) {
  final prefs = ref.watch(sharedPreferencesProvider);
  return FavoritesLocalDatasource(prefs);
});

// ---------------------------------------------------------------------------
// Infrastructure providers (leaf dependencies)
// ---------------------------------------------------------------------------

/// Provides [NetworkInfo] for connectivity checks.
final networkInfoProvider = Provider<NetworkInfo>((ref) {
  return NetworkInfo();
});

/// Provides the [Dio] HTTP client instance.
final dioProvider = Provider<Dio>((ref) {
  return Dio();
});

/// Provides the [ApiClient] configured with the environment base URL.
final apiClientProvider = Provider<ApiClient>((ref) {
  final dio = ref.watch(dioProvider);
  return ApiClient(dio: dio, baseUrl: EnvironmentConfig.baseUrl);
});

/// Provides the [LocalStorageWrapper] backed by [SharedPreferences].
///
/// The [SharedPreferences] instance is obtained from [sharedPreferencesProvider]
/// which must be overridden with a pre-initialized instance in the root
/// [ProviderScope].
final localStorageProvider = Provider<LocalStorageWrapper>((ref) {
  return LocalStorageWrapper(prefs: ref.watch(sharedPreferencesProvider));
});

/// Provides the [VpnEngineDatasource] singleton.
final vpnEngineDatasourceProvider = Provider<VpnEngineDatasource>((ref) {
  final engine = VpnEngineDatasource();
  ref.onDispose(engine.dispose);
  return engine;
});

// ---------------------------------------------------------------------------
// Data source providers
// ---------------------------------------------------------------------------

/// Provides the [AuthRemoteDataSource] backed by the [ApiClient].
final authRemoteDataSourceProvider = Provider<AuthRemoteDataSource>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return AuthRemoteDataSourceImpl(apiClient);
});

/// Provides the [AuthLocalDataSource] backed by secure + local storage.
final authLocalDataSourceProvider = Provider<AuthLocalDataSource>((ref) {
  final secureStorage = ref.watch(secureStorageProvider);
  final localStorage = ref.watch(localStorageProvider);
  return AuthLocalDataSourceImpl(
    secureStorage: secureStorage,
    localStorage: localStorage,
  );
});

/// Provides the [ServerRemoteDataSource] backed by the [ApiClient].
final serverRemoteDataSourceProvider = Provider<ServerRemoteDataSource>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return ServerRemoteDataSourceImpl(apiClient);
});

/// Provides the [ServerLocalDataSource] backed by [LocalStorageWrapper].
final serverLocalDataSourceProvider = Provider<ServerLocalDataSource>((ref) {
  final localStorage = ref.watch(localStorageProvider);
  return ServerLocalDataSourceImpl(localStorage);
});

/// Provides the [SubscriptionRemoteDataSource] backed by the [ApiClient].
final subscriptionRemoteDataSourceProvider =
    Provider<SubscriptionRemoteDataSource>((ref) {
      final apiClient = ref.watch(apiClientProvider);
      return SubscriptionRemoteDataSourceImpl(apiClient);
    });

/// Provides the [ReferralRemoteDataSource] backed by the [ApiClient].
final referralRemoteDataSourceProvider = Provider<ReferralRemoteDataSource>((
  ref,
) {
  final apiClient = ref.watch(apiClientProvider);
  return ReferralRemoteDataSourceImpl(apiClient);
});

// ---------------------------------------------------------------------------
// Utility: build the list of ProviderScope overrides for main.dart
// ---------------------------------------------------------------------------

/// Builds the list of provider overrides for the root [ProviderScope].
///
/// [prefs] must be an already-initialized [SharedPreferences] instance
/// obtained via `await SharedPreferences.getInstance()` before `runApp`.
///
/// Only infrastructure providers that require async init or synchronous
/// access to pre-initialized resources are eagerly created here.
/// Data sources, repositories, and services are lazily initialized via
/// [ref.watch] chains when first accessed.
Future<List<Override>> buildProviderOverrides(SharedPreferences prefs) async {
  // --- Eager: requires async pre-warming ---
  final secureStorage = SecureStorageWrapper();
  await secureStorage.prewarmCache();

  // --- Eager: requires pre-initialized SharedPreferences ---
  final dio = Dio(BaseOptions(
    connectTimeout: const Duration(seconds: 10),
    receiveTimeout: const Duration(seconds: 15),
    sendTimeout: const Duration(seconds: 10),
  ));
  final apiClient = ApiClient(dio: dio, baseUrl: EnvironmentConfig.baseUrl);
  // Interceptor order is intentional:
  // 1. Auth: attaches/refreshes JWT on every request.
  // 2. Retry: retries on transient failures (after auth is attached).
  // If retry triggers a new request, Auth re-evaluates the token.
  apiClient.addInterceptor(
    AuthInterceptor(secureStorage: secureStorage, dio: dio),
  );
  apiClient.addInterceptor(RetryInterceptor(dio: dio, maxRetries: 3));

  return [
    // Eager infrastructure (async-init or sync-critical)
    sharedPreferencesProvider.overrideWithValue(prefs),
    secureStorageProvider.overrideWithValue(secureStorage),
    dioProvider.overrideWithValue(dio),
    apiClientProvider.overrideWithValue(apiClient),
  ];
}
