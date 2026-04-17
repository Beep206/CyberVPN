import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/auth/token_refresh_scheduler.dart';
import 'package:cybervpn_mobile/core/data/database/database_provider.dart';
import 'package:cybervpn_mobile/core/device/device_provider.dart'
    show deviceServiceProvider, secureStorageProvider;
import 'package:cybervpn_mobile/core/di/providers.dart';
import 'package:cybervpn_mobile/core/network/websocket_provider.dart';
import 'package:cybervpn_mobile/core/providers/shared_preferences_provider.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_provider.dart';
import 'package:cybervpn_mobile/features/config_import/presentation/providers/config_import_provider.dart';
import 'package:cybervpn_mobile/features/onboarding/presentation/providers/onboarding_provider.dart';
import 'package:cybervpn_mobile/features/quick_setup/presentation/providers/quick_setup_provider.dart';
import 'package:cybervpn_mobile/features/servers/presentation/providers/recent_servers_provider.dart';
import 'package:cybervpn_mobile/features/servers/presentation/providers/server_list_provider.dart';
import 'package:cybervpn_mobile/features/settings/data/services/app_reset_service.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/other_settings_providers.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/providers/subscription_provider.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_notifier.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/di/profile_providers.dart';

final appResetServiceProvider = Provider<AppResetService>((ref) {
  return AppResetService(
    sharedPreferences: ref.watch(sharedPreferencesProvider),
    secureStorage: ref.watch(secureStorageProvider),
    database: ref.watch(appDatabaseProvider),
    logFileStore: ref.watch(logFileStoreProvider),
  );
});

final appResetControllerProvider =
    AsyncNotifierProvider<AppResetController, void>(
      AppResetController.new,
    );

class AppResetController extends AsyncNotifier<void> {
  @override
  FutureOr<void> build() {}

  Future<void> resetSettings() async {
    state = const AsyncLoading();

    try {
      await ref.read(settingsProvider.notifier).resetAll();
      state = const AsyncData(null);
    } catch (e, st) {
      state = AsyncError(e, st);
      rethrow;
    }
  }

  Future<void> performFullAppReset() async {
    state = const AsyncLoading();

    try {
      await _disconnectVpnIfNeeded();
      ref.read(tokenRefreshSchedulerProvider).cancel();
      await ref.read(webSocketClientProvider).disconnect();
      await _resetRevenueCatUser();

      await ref.read(appResetServiceProvider).performFullReset();
      ref.read(deviceServiceProvider).clearCache();

      _invalidateAfterFullReset();
      state = const AsyncData(null);
    } catch (e, st) {
      AppLogger.error('Full app reset failed', error: e, stackTrace: st);
      state = AsyncError(e, st);
      rethrow;
    }
  }

  Future<void> _disconnectVpnIfNeeded() async {
    final vpnState = ref.read(vpnConnectionProvider).value;
    if (vpnState != null && vpnState.isConnected) {
      await ref.read(vpnConnectionProvider.notifier).disconnect();
    }
  }

  Future<void> _resetRevenueCatUser() async {
    try {
      await ref.read(revenueCatDataSourceProvider).resetUser();
    } catch (error, stackTrace) {
      AppLogger.warning(
        'RevenueCat reset skipped during full app reset',
        error: error,
        stackTrace: stackTrace,
        category: 'subscription.reset',
      );
    }
  }

  void _invalidateAfterFullReset() {
    ref.invalidate(settingsProvider);
    ref.invalidate(configImportProvider);
    ref.invalidate(subscriptionProvider);
    ref.invalidate(profileListProvider);
    ref.invalidate(activeVpnProfileProvider);
    ref.invalidate(serverListProvider);
    ref.invalidate(recentServerIdsProvider);
    ref.invalidate(vpnConnectionProvider);
    ref.invalidate(logFilesProvider);
    ref.invalidate(quickSetupProvider);
    ref.invalidate(onboardingProvider);
    ref.invalidate(shouldShowOnboardingProvider);
    ref.invalidate(authProvider);
  }
}
