import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:cybervpn_mobile/core/config/environment_config.dart';
import 'package:cybervpn_mobile/core/network/api_client.dart';
import 'package:cybervpn_mobile/core/network/auth_interceptor.dart';
import 'package:cybervpn_mobile/core/network/network_info.dart';
import 'package:cybervpn_mobile/core/security/device_integrity.dart';
import 'package:cybervpn_mobile/core/services/fcm_token_service.dart';
import 'package:cybervpn_mobile/core/storage/local_storage.dart';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';

// Data sources
import 'package:cybervpn_mobile/features/auth/data/datasources/auth_remote_ds.dart';
import 'package:cybervpn_mobile/features/auth/data/datasources/auth_local_ds.dart';
import 'package:cybervpn_mobile/features/servers/data/datasources/server_remote_ds.dart';
import 'package:cybervpn_mobile/features/servers/data/datasources/server_local_ds.dart';
import 'package:cybervpn_mobile/features/subscription/data/datasources/subscription_remote_ds.dart';
import 'package:cybervpn_mobile/features/referral/data/datasources/referral_remote_ds.dart';
import 'package:cybervpn_mobile/features/vpn/data/datasources/vpn_engine_datasource.dart';

// Repository implementations
import 'package:cybervpn_mobile/features/auth/data/repositories/auth_repository_impl.dart';
import 'package:cybervpn_mobile/features/onboarding/data/repositories/onboarding_repository_impl.dart';
import 'package:cybervpn_mobile/features/onboarding/domain/repositories/onboarding_repository.dart';
import 'package:cybervpn_mobile/features/servers/data/repositories/server_repository_impl.dart';
import 'package:cybervpn_mobile/features/settings/data/repositories/settings_repository_impl.dart';
import 'package:cybervpn_mobile/features/settings/domain/repositories/settings_repository.dart';
import 'package:cybervpn_mobile/features/subscription/data/repositories/subscription_repository_impl.dart';
import 'package:cybervpn_mobile/features/referral/data/repositories/referral_repository_impl.dart';
import 'package:cybervpn_mobile/features/referral/domain/repositories/referral_repository.dart';
import 'package:cybervpn_mobile/features/vpn/data/repositories/vpn_repository_impl.dart';

// Import provider symbols from presentation providers so overrides
// reference the same provider instances used throughout the app.
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_provider.dart'
    show authRepositoryProvider;
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_provider.dart'
    show vpnRepositoryProvider, secureStorageProvider, networkInfoProvider;
import 'package:cybervpn_mobile/features/servers/presentation/providers/server_list_provider.dart'
    show serverRepositoryProvider, sharedPreferencesProvider;
import 'package:cybervpn_mobile/features/subscription/presentation/providers/subscription_provider.dart'
    show subscriptionRepositoryProvider;
import 'package:cybervpn_mobile/app/theme/theme_provider.dart'
    show themePrefsProvider;

// ---------------------------------------------------------------------------
// Settings repository provider
// ---------------------------------------------------------------------------

/// Provides the [SettingsRepository] backed by [SharedPreferences].
///
/// Overridden with a concrete [SettingsRepositoryImpl] in [buildProviderOverrides].
final settingsRepositoryProvider = Provider<SettingsRepository>((ref) {
  throw UnimplementedError(
    'settingsRepositoryProvider must be overridden in the root ProviderScope',
  );
});

// ---------------------------------------------------------------------------
// Onboarding repository provider
// ---------------------------------------------------------------------------

/// Provides the [OnboardingRepository] backed by [SharedPreferences].
///
/// Overridden with a concrete [OnboardingRepositoryImpl] in [buildProviderOverrides].
final onboardingRepositoryProvider = Provider<OnboardingRepository>((ref) {
  throw UnimplementedError(
    'onboardingRepositoryProvider must be overridden in the root ProviderScope',
  );
});

// ---------------------------------------------------------------------------
// Referral repository provider
// ---------------------------------------------------------------------------

/// Provides the [ReferralRepository] backed by [ReferralRemoteDataSource].
///
/// Overridden with a concrete [ReferralRepositoryImpl] in [buildProviderOverrides].
final referralRepositoryProvider = Provider<ReferralRepository>((ref) {
  throw UnimplementedError(
    'referralRepositoryProvider must be overridden in the root ProviderScope',
  );
});

// ---------------------------------------------------------------------------
// Infrastructure providers (leaf dependencies)
// ---------------------------------------------------------------------------

/// Provides the [DeviceIntegrityChecker] for root/jailbreak detection.
///
/// Overridden with a concrete instance in [buildProviderOverrides].
final deviceIntegrityCheckerProvider = Provider<DeviceIntegrityChecker>((ref) {
  throw UnimplementedError(
    'deviceIntegrityCheckerProvider must be overridden in the root ProviderScope',
  );
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
  return LocalStorageWrapper();
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
final referralRemoteDataSourceProvider =
    Provider<ReferralRemoteDataSource>((ref) {
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
// ignore: strict_raw_type
List buildProviderOverrides(SharedPreferences prefs) {
  // We create concrete instances here that require synchronous access to
  // pre-initialized resources (SharedPreferences).
  final secureStorage = SecureStorageWrapper();
  final localStorage = LocalStorageWrapper();
  final networkInfo = NetworkInfo();
  final deviceIntegrityChecker = DeviceIntegrityChecker(prefs);
  final dio = Dio();
  final apiClient = ApiClient(dio: dio, baseUrl: EnvironmentConfig.baseUrl);

  // Add auth interceptor for automatic token management.
  apiClient.addInterceptor(
    AuthInterceptor(secureStorage: secureStorage, dio: dio),
  );

  // FCM token service for push notification registration
  final fcmTokenService = FcmTokenService(apiClient: apiClient);

  // Data sources
  final authRemoteDs = AuthRemoteDataSourceImpl(apiClient);
  final authLocalDs = AuthLocalDataSourceImpl(
    secureStorage: secureStorage,
    localStorage: localStorage,
  );
  final serverRemoteDs = ServerRemoteDataSourceImpl(apiClient);
  final serverLocalDs = ServerLocalDataSourceImpl(localStorage);
  final subscriptionRemoteDs = SubscriptionRemoteDataSourceImpl(apiClient);
  final referralRemoteDs = ReferralRemoteDataSourceImpl(apiClient);
  final vpnEngine = VpnEngineDatasource();

  // Repositories
  final authRepo = AuthRepositoryImpl(
    remoteDataSource: authRemoteDs,
    localDataSource: authLocalDs,
    networkInfo: networkInfo,
  );

  final vpnRepo = VpnRepositoryImpl(
    engine: vpnEngine,
    localStorage: localStorage,
    secureStorage: secureStorage,
  );

  final serverRepo = ServerRepositoryImpl(
    remoteDataSource: serverRemoteDs,
    localDataSource: serverLocalDs,
    networkInfo: networkInfo,
  );

  final subscriptionRepo = SubscriptionRepositoryImpl(
    remoteDataSource: subscriptionRemoteDs,
    networkInfo: networkInfo,
  );

  final settingsRepo = SettingsRepositoryImpl(sharedPreferences: prefs);
  final referralRepo = ReferralRepositoryImpl(
    remoteDataSource: referralRemoteDs,
  );
  final onboardingRepo = OnboardingRepositoryImpl(sharedPreferences: prefs);

  return [
    // Infrastructure
    sharedPreferencesProvider.overrideWithValue(prefs),
    themePrefsProvider.overrideWithValue(prefs),
    secureStorageProvider.overrideWithValue(secureStorage),
    localStorageProvider.overrideWithValue(localStorage),
    networkInfoProvider.overrideWithValue(networkInfo),
    deviceIntegrityCheckerProvider.overrideWithValue(deviceIntegrityChecker),
    dioProvider.overrideWithValue(dio),
    apiClientProvider.overrideWithValue(apiClient),
    fcmTokenServiceProvider.overrideWithValue(fcmTokenService),

    // Repositories
    authRepositoryProvider.overrideWithValue(authRepo),
    vpnRepositoryProvider.overrideWithValue(vpnRepo),
    serverRepositoryProvider.overrideWithValue(serverRepo),
    subscriptionRepositoryProvider.overrideWithValue(subscriptionRepo),
    settingsRepositoryProvider.overrideWithValue(settingsRepo),
    onboardingRepositoryProvider.overrideWithValue(onboardingRepo),
    referralRepositoryProvider.overrideWithValue(referralRepo),
  ];
}
