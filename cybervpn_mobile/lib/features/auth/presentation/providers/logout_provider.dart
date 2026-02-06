import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/device/device_provider.dart'
    show deviceServiceProvider, secureStorageProvider;
import 'package:cybervpn_mobile/core/network/api_client.dart';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_provider.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_provider.dart';

// ---------------------------------------------------------------------------
// API Client provider (used only for logout endpoint)
// ---------------------------------------------------------------------------

/// Provides the shared [ApiClient] instance.
///
/// Override this in tests to inject a mock API client.
final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient();
});

// ---------------------------------------------------------------------------
// Logout Notifier
// ---------------------------------------------------------------------------

/// Handles the full logout flow:
/// 1. Disconnect VPN if connected
/// 2. Call the server-side logout endpoint (best-effort)
/// 3. Clear auth tokens from secure storage
/// 4. Invalidate auth provider so the router redirect guard kicks in
class LogoutNotifier extends AsyncNotifier<void> {
  @override
  FutureOr<void> build() {
    // No-op initial build; logout is triggered explicitly.
  }

  /// Execute the full logout sequence.
  ///
  /// Even if the API call fails (e.g. device is offline), local state is
  /// always cleared so the user can log out regardless of network conditions.
  Future<void> logout() async {
    state = const AsyncLoading();

    try {
      // Step 1: Disconnect VPN if currently connected.
      await _disconnectVpnIfNeeded();

      // Step 2: Call server-side logout (best-effort).
      await _callLogoutApi();
    } catch (e) {
      // Log but do not abort -- we always clear local state.
      AppLogger.warning('Non-critical logout step failed', error: e);
    }

    try {
      // Step 3: Clear auth tokens from secure storage.
      await _clearAuthTokens();

      // Step 4: Invalidate auth provider so the redirect guard navigates
      // to the login screen automatically.
      ref.invalidate(authProvider);

      state = const AsyncData(null);
    } catch (e, st) {
      AppLogger.error('Failed to clear local auth state', error: e, stackTrace: st);
      // Even on error, try to invalidate auth so the user isn't stuck.
      ref.invalidate(authProvider);
      state = AsyncError(e, st);
    }
  }

  // ── Private helpers ─────────────────────────────────────────────────────

  /// Checks the VPN connection state and disconnects if active.
  Future<void> _disconnectVpnIfNeeded() async {
    try {
      final vpnState = ref.read(vpnConnectionProvider).value;
      if (vpnState != null && vpnState.isConnected) {
        AppLogger.info('VPN is connected, disconnecting before logout');
        await ref.read(vpnConnectionProvider.notifier).disconnect();
      }
    } catch (e) {
      AppLogger.warning('Failed to disconnect VPN during logout', error: e);
      // Non-fatal: proceed with logout even if VPN disconnect fails.
    }
  }

  /// Calls POST /api/v1/mobile/auth/logout on the server.
  ///
  /// Sends refresh_token and device_id to revoke the session on server.
  /// Errors are caught and logged but never prevent local logout.
  Future<void> _callLogoutApi() async {
    try {
      final storage = ref.read(secureStorageProvider);
      final deviceService = ref.read(deviceServiceProvider);

      final refreshToken = await storage.getRefreshToken();
      final deviceId = await deviceService.getDeviceId();

      if (refreshToken == null || refreshToken.isEmpty) {
        AppLogger.info('No refresh token found, skipping server logout');
        return;
      }

      final apiClient = ref.read(apiClientProvider);
      await apiClient.post<dynamic>(
        '/mobile/auth/logout',
        data: {
          'refresh_token': refreshToken,
          'device_id': deviceId,
        },
      );
      AppLogger.info('Server logout successful');
    } catch (e) {
      // Offline logout is perfectly fine -- the server session will expire
      // naturally. Log for diagnostics only.
      AppLogger.info('Server logout call failed (offline logout OK)', error: e);
    }
  }

  /// Clears only auth-related keys from secure storage.
  ///
  /// Deliberately does NOT clear SharedPreferences (locale, theme, etc.)
  /// so user preferences survive across sessions.
  Future<void> _clearAuthTokens() async {
    final storage = ref.read(secureStorageProvider);
    await Future.wait<void>([
      storage.delete(key: SecureStorageWrapper.accessTokenKey),
      storage.delete(key: SecureStorageWrapper.refreshTokenKey),
      storage.delete(key: 'cached_user'),
    ]);
  }
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

/// Provider for the [LogoutNotifier].
final logoutProvider = AsyncNotifierProvider<LogoutNotifier, void>(
  LogoutNotifier.new,
);
