import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/di/providers.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/domain/repositories/settings_repository.dart';

// ---------------------------------------------------------------------------
// SettingsNotifier
// ---------------------------------------------------------------------------

/// Manages the application settings state with automatic persistence.
///
/// Loads the initial [AppSettings] from [SettingsRepository] during [build]
/// and persists every mutation back to the repository.
class SettingsNotifier extends AsyncNotifier<AppSettings> {
  late final SettingsRepository _repository;

  /// Stores the last failed operation for retry.
  Future<void> Function()? _lastFailedOperation;

  @override
  Future<AppSettings> build() async {
    _repository = ref.watch(settingsRepositoryProvider);
    return _repository.getSettings();
  }

  // ── Appearance ────────────────────────────────────────────────────────────

  /// Update the application theme mode.
  Future<void> updateThemeMode(AppThemeMode mode) async {
    await _updateSetting(
      (settings) => settings.copyWith(themeMode: mode),
      'updateThemeMode',
    );
  }

  /// Update the application brightness setting.
  Future<void> updateBrightness(AppBrightness brightness) async {
    await _updateSetting(
      (settings) => settings.copyWith(brightness: brightness),
      'updateBrightness',
    );
  }

  /// Update the dynamic color preference.
  Future<void> updateDynamicColor(bool enabled) async {
    await _updateSetting(
      (settings) => settings.copyWith(dynamicColor: enabled),
      'updateDynamicColor',
    );
  }

  // ── Locale ────────────────────────────────────────────────────────────────

  /// Update the application locale.
  Future<void> updateLocale(String locale) async {
    await _updateSetting(
      (settings) => settings.copyWith(locale: locale),
      'updateLocale',
    );
  }

  // ── Connection / VPN ──────────────────────────────────────────────────────

  /// Update the preferred VPN protocol.
  Future<void> updateProtocol(PreferredProtocol protocol) async {
    await _updateSetting(
      (settings) => settings.copyWith(preferredProtocol: protocol),
      'updateProtocol',
    );
  }

  /// Toggle auto-connect on launch.
  Future<void> toggleAutoConnect() async {
    await _updateSetting(
      (settings) =>
          settings.copyWith(autoConnectOnLaunch: !settings.autoConnectOnLaunch),
      'toggleAutoConnect',
    );
  }

  /// Toggle auto-connect on untrusted WiFi.
  Future<void> toggleAutoConnectUntrustedWifi() async {
    await _updateSetting(
      (settings) => settings.copyWith(
        autoConnectUntrustedWifi: !settings.autoConnectUntrustedWifi,
      ),
      'toggleAutoConnectUntrustedWifi',
    );
  }

  /// Toggle the VPN kill switch.
  Future<void> toggleKillSwitch() async {
    await _updateSetting(
      (settings) => settings.copyWith(killSwitch: !settings.killSwitch),
      'toggleKillSwitch',
    );
  }

  /// Toggle split tunneling.
  Future<void> toggleSplitTunneling() async {
    await _updateSetting(
      (settings) =>
          settings.copyWith(splitTunneling: !settings.splitTunneling),
      'toggleSplitTunneling',
    );
  }

  // ── MTU ──────────────────────────────────────────────────────────────────

  /// Update the MTU mode and optional manual value.
  Future<void> updateMtu({
    required MtuMode mode,
    int? mtuValue,
  }) async {
    await _updateSetting(
      (settings) => settings.copyWith(
        mtuMode: mode,
        mtuValue: mtuValue ?? settings.mtuValue,
      ),
      'updateMtu',
    );
  }

  // ── DNS ───────────────────────────────────────────────────────────────────

  /// Update the DNS provider and optional custom DNS address.
  Future<void> updateDns({
    required DnsProvider provider,
    String? customDns,
  }) async {
    await _updateSetting(
      (settings) => settings.copyWith(
        dnsProvider: provider,
        customDns: customDns,
      ),
      'updateDns',
    );
  }

  // ── Notifications ─────────────────────────────────────────────────────────

  /// Toggle a specific notification type.
  ///
  /// [type] selects which notification toggle to flip:
  /// `connection`, `expiry`, `promotional`, or `referral`.
  Future<void> toggleNotification(NotificationType type) async {
    await _updateSetting(
      (settings) => switch (type) {
        NotificationType.connection => settings.copyWith(
            notificationConnection: !settings.notificationConnection,
          ),
        NotificationType.expiry => settings.copyWith(
            notificationExpiry: !settings.notificationExpiry,
          ),
        NotificationType.promotional => settings.copyWith(
            notificationPromotional: !settings.notificationPromotional,
          ),
        NotificationType.referral => settings.copyWith(
            notificationReferral: !settings.notificationReferral,
          ),
        NotificationType.vpnSpeed => settings.copyWith(
            notificationVpnSpeed: !settings.notificationVpnSpeed,
          ),
      },
      'toggleNotification($type)',
    );
  }

  // ── Privacy ──────────────────────────────────────────────────────────────

  /// Toggle clipboard auto-detect for VPN config import.
  Future<void> toggleClipboardAutoDetect() async {
    await _updateSetting(
      (settings) => settings.copyWith(
        clipboardAutoDetect: !settings.clipboardAutoDetect,
      ),
      'toggleClipboardAutoDetect',
    );
  }

  // ── Diagnostics ──────────────────────────────────────────────────────────

  /// Update the application log level.
  Future<void> updateLogLevel(LogLevel level) async {
    await _updateSetting(
      (settings) => settings.copyWith(logLevel: level),
      'updateLogLevel',
    );
  }

  // ── Reset ─────────────────────────────────────────────────────────────────

  /// Reset all settings to their default values.
  Future<void> resetAll() async {
    final previousState = state;

    try {
      state = const AsyncLoading<AppSettings>();
      await _repository.resetSettings();
      final defaults = await _repository.getSettings();
      state = AsyncData(defaults);
      _lastFailedOperation = null;
      AppLogger.info('Settings reset to defaults');
    } catch (e, st) {
      AppLogger.error('Failed to reset settings', error: e, stackTrace: st);
      // Rollback to previous state on failure.
      state = previousState;
      _lastFailedOperation = resetAll;
      rethrow;
    }
  }

  // ── Error Recovery ────────────────────────────────────────────────────────

  /// Retry the last operation that failed.
  ///
  /// Returns `true` if a retry was attempted, `false` if there was nothing
  /// to retry.
  Future<bool> retryLastOperation() async {
    final operation = _lastFailedOperation;
    if (operation == null) return false;

    try {
      await operation();
      return true;
    } catch (_) {
      return false;
    }
  }

  /// Validate consistency between in-memory state and the repository.
  ///
  /// Reloads settings from the repository and replaces the current state
  /// if they differ. Useful after app restart or suspected corruption.
  Future<void> validateConsistency() async {
    try {
      final persisted = await _repository.getSettings();
      final current = state.value;

      if (current != persisted) {
        AppLogger.info('Settings consistency mismatch detected, reconciling');
        state = AsyncData(persisted);
      }
    } catch (e, st) {
      AppLogger.error(
        'Failed to validate settings consistency',
        error: e,
        stackTrace: st,
      );
    }
  }

  // ── Private helpers ───────────────────────────────────────────────────────

  /// Applies [updater] to the current settings using optimistic update.
  ///
  /// Immediately updates the UI state, then persists to the repository.
  /// On failure, rolls back to the previous state and stores the operation
  /// for retry via [retryLastOperation].
  Future<void> _updateSetting(
    AppSettings Function(AppSettings current) updater,
    String operationName,
  ) async {
    final current = state.value;
    if (current == null) return;

    final updated = updater(current);

    // Optimistic update: show the new state immediately.
    state = AsyncData(updated);

    try {
      await _repository.updateSettings(updated);
      _lastFailedOperation = null;
      AppLogger.debug('Settings updated: $operationName');
    } catch (e, st) {
      AppLogger.error(
        'Failed to persist setting: $operationName',
        error: e,
        stackTrace: st,
      );
      // Rollback to previous state on persistence failure.
      state = AsyncData(current);
      _lastFailedOperation = () => _updateSetting(updater, operationName);
      rethrow;
    }
  }
}

// ---------------------------------------------------------------------------
// Notification type enum for toggleNotification()
// ---------------------------------------------------------------------------

/// Identifies which notification toggle to flip.
enum NotificationType {
  connection,
  expiry,
  promotional,
  referral,
  vpnSpeed,
}

// ---------------------------------------------------------------------------
// Main provider
// ---------------------------------------------------------------------------

/// Provides the [SettingsNotifier] managing [AppSettings] state.
final settingsProvider =
    AsyncNotifierProvider<SettingsNotifier, AppSettings>(
  SettingsNotifier.new,
);

// ---------------------------------------------------------------------------
// Derived providers
// ---------------------------------------------------------------------------

/// The current locale string from settings.
///
/// UI components that only need the locale can watch this provider
/// instead of the full [settingsProvider] to minimize rebuilds.
final currentLocaleProvider = Provider<String>((ref) {
  final asyncSettings = ref.watch(settingsProvider);
  return asyncSettings.value?.locale ?? 'en';
});

/// A subset of VPN-related settings for connection screens.
///
/// Groups protocol, auto-connect, kill-switch, and DNS into a single
/// object so VPN UI components can watch one provider for all connection
/// preferences.
final vpnSettingsProvider = Provider<VpnSettings>((ref) {
  final asyncSettings = ref.watch(settingsProvider);
  final settings = asyncSettings.value;

  if (settings == null) return const VpnSettings();

  return VpnSettings(
    preferredProtocol: settings.preferredProtocol,
    autoConnectOnLaunch: settings.autoConnectOnLaunch,
    autoConnectUntrustedWifi: settings.autoConnectUntrustedWifi,
    killSwitch: settings.killSwitch,
    splitTunneling: settings.splitTunneling,
    dnsProvider: settings.dnsProvider,
    customDns: settings.customDns,
    mtuMode: settings.mtuMode,
    mtuValue: settings.mtuValue,
  );
});

// ---------------------------------------------------------------------------
// VpnSettings value object
// ---------------------------------------------------------------------------

/// Immutable subset of [AppSettings] containing only VPN-related preferences.
class VpnSettings {
  const VpnSettings({
    this.preferredProtocol = PreferredProtocol.auto,
    this.autoConnectOnLaunch = false,
    this.autoConnectUntrustedWifi = false,
    this.killSwitch = false,
    this.splitTunneling = false,
    this.dnsProvider = DnsProvider.system,
    this.customDns,
    this.mtuMode = MtuMode.auto,
    this.mtuValue = 1400,
  });

  final PreferredProtocol preferredProtocol;
  final bool autoConnectOnLaunch;
  final bool autoConnectUntrustedWifi;
  final bool killSwitch;
  final bool splitTunneling;
  final DnsProvider dnsProvider;
  final String? customDns;
  final MtuMode mtuMode;
  final int mtuValue;

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is VpnSettings &&
        other.preferredProtocol == preferredProtocol &&
        other.autoConnectOnLaunch == autoConnectOnLaunch &&
        other.autoConnectUntrustedWifi == autoConnectUntrustedWifi &&
        other.killSwitch == killSwitch &&
        other.splitTunneling == splitTunneling &&
        other.dnsProvider == dnsProvider &&
        other.customDns == customDns &&
        other.mtuMode == mtuMode &&
        other.mtuValue == mtuValue;
  }

  @override
  int get hashCode => Object.hash(
        preferredProtocol,
        autoConnectOnLaunch,
        autoConnectUntrustedWifi,
        killSwitch,
        splitTunneling,
        dnsProvider,
        customDns,
        mtuMode,
        mtuValue,
      );

  @override
  String toString() =>
      'VpnSettings(protocol: $preferredProtocol, autoConnect: $autoConnectOnLaunch, '
      'autoConnectWifi: $autoConnectUntrustedWifi, killSwitch: $killSwitch, '
      'splitTunneling: $splitTunneling, dns: $dnsProvider, customDns: $customDns, '
      'mtuMode: $mtuMode, mtuValue: $mtuValue)';
}
