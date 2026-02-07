import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_v2ray_plus/flutter_v2ray.dart';

import 'package:cybervpn_mobile/core/utils/app_logger.dart';

// ---------------------------------------------------------------------------
// PermissionRequestState
// ---------------------------------------------------------------------------

/// Immutable state for the permission request flow.
///
/// Tracks the status of VPN permission request, including whether it has
/// been granted and whether the request is currently in progress.
class PermissionRequestState {
  const PermissionRequestState({
    this.vpnPermissionGranted = false,
    this.isRequestingVpnPermission = false,
    this.hasRequestedAnyPermission = false,
    this.isComplete = false,
  });

  /// Whether VPN permission has been granted by the user.
  final bool vpnPermissionGranted;

  /// Whether a VPN permission request is currently in progress.
  final bool isRequestingVpnPermission;

  /// Whether any permission has been requested (even if denied).
  final bool hasRequestedAnyPermission;

  /// Whether the user has completed the permission flow and can continue.
  final bool isComplete;

  /// Whether all permissions have been granted.
  bool get allPermissionsGranted => vpnPermissionGranted;

  /// Whether the request button should be enabled.
  bool get canRequestPermissions =>
      !isRequestingVpnPermission && !isComplete;

  PermissionRequestState copyWith({
    bool? vpnPermissionGranted,
    bool? isRequestingVpnPermission,
    bool? hasRequestedAnyPermission,
    bool? isComplete,
  }) {
    return PermissionRequestState(
      vpnPermissionGranted: vpnPermissionGranted ?? this.vpnPermissionGranted,
      isRequestingVpnPermission:
          isRequestingVpnPermission ?? this.isRequestingVpnPermission,
      hasRequestedAnyPermission:
          hasRequestedAnyPermission ?? this.hasRequestedAnyPermission,
      isComplete: isComplete ?? this.isComplete,
    );
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is PermissionRequestState &&
        other.vpnPermissionGranted == vpnPermissionGranted &&
        other.isRequestingVpnPermission == isRequestingVpnPermission &&
        other.hasRequestedAnyPermission == hasRequestedAnyPermission &&
        other.isComplete == isComplete;
  }

  @override
  int get hashCode => Object.hash(
        vpnPermissionGranted,
        isRequestingVpnPermission,
        hasRequestedAnyPermission,
        isComplete,
      );

  @override
  String toString() =>
      'PermissionRequestState(vpn: $vpnPermissionGranted, '
      'complete: $isComplete)';
}

// ---------------------------------------------------------------------------
// PermissionRequestNotifier
// ---------------------------------------------------------------------------

/// Manages the permission request flow state.
///
/// Handles requesting VPN permission, updating the UI state to reflect
/// progress and results.
class PermissionRequestNotifier extends AsyncNotifier<PermissionRequestState> {
  late final FlutterV2ray _v2ray;

  @override
  Future<PermissionRequestState> build() async {
    _v2ray = FlutterV2ray();
    return const PermissionRequestState();
  }

  // ── Permission Requests ─────────────────────────────────────────────────

  /// Requests all required permissions.
  ///
  /// Only VPN permission is required during onboarding.
  /// Updates state after the request regardless of grant status.
  Future<void> requestAllPermissions() async {
    try {
      await _requestVpnPermission();

      // Mark as complete after requesting permission
      final current = state.value;
      if (current == null) return;

      state = AsyncData(
        current.copyWith(
          isComplete: true,
          hasRequestedAnyPermission: true,
        ),
      );

      AppLogger.info('Permission request flow completed');
    } catch (e, st) {
      AppLogger.error(
        'Failed to request permissions',
        error: e,
        stackTrace: st,
      );
      state = AsyncError(e, st);
    }
  }

  /// Requests VPN permission from the system.
  ///
  /// Updates state to show the request is in progress, then requests
  /// permission via flutter_v2ray_plus. Updates state with the result.
  Future<void> _requestVpnPermission() async {
    try {
      final current = state.value;
      if (current == null) return;

      // Mark as requesting
      state = AsyncData(current.copyWith(isRequestingVpnPermission: true));

      AppLogger.info('Requesting VPN permission');

      // Request permission via flutter_v2ray_plus
      final granted = await _v2ray.requestPermission();

      AppLogger.info('VPN permission ${granted ? 'granted' : 'denied'}');

      // Update state with result
      final updated = state.value;
      if (updated == null) return;

      state = AsyncData(
        updated.copyWith(
          vpnPermissionGranted: granted,
          isRequestingVpnPermission: false,
          hasRequestedAnyPermission: true,
        ),
      );
    } catch (e, st) {
      AppLogger.error(
        'Failed to request VPN permission',
        error: e,
        stackTrace: st,
      );

      // Mark request as complete even on error
      final current = state.value;
      if (current != null) {
        state = AsyncData(
          current.copyWith(
            isRequestingVpnPermission: false,
            hasRequestedAnyPermission: true,
          ),
        );
      }
    }
  }

  // ── Completion ──────────────────────────────────────────────────────────

  /// Marks the permission flow as complete.
  ///
  /// Called when the user is ready to proceed to the next screen.
  Future<void> complete() async {
    final current = state.value;
    if (current == null) return;

    state = AsyncData(current.copyWith(isComplete: true));
    AppLogger.info('Permission request flow marked as complete');
  }
}

// ---------------------------------------------------------------------------
// Main provider
// ---------------------------------------------------------------------------

/// Provides the [PermissionRequestNotifier] managing [PermissionRequestState].
final permissionRequestProvider =
    AsyncNotifierProvider<PermissionRequestNotifier, PermissionRequestState>(
  PermissionRequestNotifier.new,
);
