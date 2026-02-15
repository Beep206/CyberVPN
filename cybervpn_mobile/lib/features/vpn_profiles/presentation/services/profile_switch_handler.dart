import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_provider.dart';

/// Handles the VPN disconnect-before-profile-switch flow.
///
/// When the user switches to a different VPN profile while connected,
/// this handler:
/// 1. Shows a confirmation dialog explaining the VPN will disconnect.
/// 2. On confirmation, disconnects the VPN with a 10-second timeout.
/// 3. Returns whether the switch should proceed.
///
/// Usage from a notifier or widget:
/// ```dart
/// if (await ProfileSwitchHandler.ensureDisconnected(context: ctx, ref: ref)) {
///   await switchActiveProfileUseCase.call(targetId);
/// }
/// ```
class ProfileSwitchHandler {
  ProfileSwitchHandler._();

  /// Maximum time to wait for VPN disconnect before forcing the switch.
  static const _disconnectTimeout = Duration(seconds: 10);

  /// Ensures the VPN is disconnected before a profile switch.
  ///
  /// Returns `true` if the caller should proceed with the switch, `false`
  /// if the user cancelled.
  ///
  /// When the VPN is already disconnected, returns `true` immediately.
  /// When connected, shows a confirmation dialog and handles disconnect.
  static Future<bool> ensureDisconnected({
    required BuildContext context,
    required WidgetRef ref,
  }) async {
    final vpnState = ref.read(vpnConnectionProvider).value;

    // Already disconnected or in an error state — safe to switch.
    if (vpnState == null ||
        vpnState is VpnDisconnected ||
        vpnState is VpnError ||
        vpnState is VpnForceDisconnected) {
      return true;
    }

    // VPN is active (connected, connecting, reconnecting, or disconnecting).
    // Show confirmation dialog.
    final confirmed = await _showConfirmationDialog(context);
    if (confirmed != true) return false;

    // User confirmed — disconnect with timeout.
    return _disconnectWithTimeout(ref);
  }

  /// Shows the disconnect confirmation dialog.
  ///
  /// Returns `true` if the user chose to disconnect, `false` or `null` if
  /// they cancelled.
  static Future<bool?> _showConfirmationDialog(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(l10n.disconnect),
        content: Text(l10n.profileSwitchDisconnect),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: Text(l10n.cancel),
          ),
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: Text(l10n.disconnect),
          ),
        ],
      ),
    );
  }

  /// Disconnects the VPN and waits for the disconnected state.
  ///
  /// Returns `true` when the VPN reaches [VpnDisconnected] (or an error/
  /// force-disconnect state) within [_disconnectTimeout]. On timeout,
  /// logs a warning and returns `true` to allow the forced switch.
  static Future<bool> _disconnectWithTimeout(WidgetRef ref) async {
    try {
      // Initiate the disconnect.
      final notifier = ref.read(vpnConnectionProvider.notifier);
      unawaited(notifier.disconnect());

      // Wait for the VPN state to settle.
      final completer = Completer<bool>();
      ProviderSubscription<AsyncValue<VpnConnectionState>>? subscription;

      subscription = ref.listenManual(
        vpnConnectionProvider,
        (previous, next) {
          final state = next.value;
          if (state is VpnDisconnected ||
              state is VpnError ||
              state is VpnForceDisconnected) {
            if (!completer.isCompleted) {
              completer.complete(true);
            }
            subscription?.close();
          }
        },
      );

      // Check if already disconnected synchronously.
      final current = ref.read(vpnConnectionProvider).value;
      if (current is VpnDisconnected ||
          current is VpnError ||
          current is VpnForceDisconnected) {
        subscription.close();
        return true;
      }

      // Wait with timeout.
      final result = await completer.future.timeout(
        _disconnectTimeout,
        onTimeout: () {
          AppLogger.warning(
            'VPN disconnect timed out after ${_disconnectTimeout.inSeconds}s, '
            'forcing profile switch',
            category: 'vpn_profiles',
          );
          subscription?.close();
          return true; // Force switch on timeout.
        },
      );

      return result;
    } catch (e, st) {
      AppLogger.error(
        'Error during VPN disconnect for profile switch',
        error: e,
        stackTrace: st,
        category: 'vpn_profiles',
      );
      // Allow switch even on error — the disconnect was best-effort.
      return true;
    }
  }
}
