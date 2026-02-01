import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_v2ray_plus/flutter_v2ray.dart';

import 'package:cybervpn_mobile/core/utils/app_logger.dart';

// ---------------------------------------------------------------------------
// PermissionRequestState
// ---------------------------------------------------------------------------

/// Immutable state for the permission request flow.
///
/// Tracks the status of VPN and notification permission requests,
/// including whether they have been granted and whether requests are
/// currently in progress.
class PermissionRequestState {
  const PermissionRequestState({
    this.vpnPermissionGranted = false,
    this.notificationPermissionGranted = false,
    this.isRequestingVpnPermission = false,
    this.isRequestingNotificationPermission = false,
    this.hasRequestedAnyPermission = false,
    this.isComplete = false,
  });

  /// Whether VPN permission has been granted by the user.
  final bool vpnPermissionGranted;

  /// Whether notification permission has been granted by the user.
  final bool notificationPermissionGranted;

  /// Whether a VPN permission request is currently in progress.
  final bool isRequestingVpnPermission;

  /// Whether a notification permission request is currently in progress.
  final bool isRequestingNotificationPermission;

  /// Whether any permission has been requested (even if denied).
  final bool hasRequestedAnyPermission;

  /// Whether the user has completed the permission flow and can continue.
  final bool isComplete;

  /// Whether all permissions have been granted.
  bool get allPermissionsGranted =>
      vpnPermissionGranted && notificationPermissionGranted;

  /// Whether the request button should be enabled.
  bool get canRequestPermissions =>
      !isRequestingVpnPermission &&
      !isRequestingNotificationPermission &&
      !isComplete;

  PermissionRequestState copyWith({
    bool? vpnPermissionGranted,
    bool? notificationPermissionGranted,
    bool? isRequestingVpnPermission,
    bool? isRequestingNotificationPermission,
    bool? hasRequestedAnyPermission,
    bool? isComplete,
  }) {
    return PermissionRequestState(
      vpnPermissionGranted: vpnPermissionGranted ?? this.vpnPermissionGranted,
      notificationPermissionGranted:
          notificationPermissionGranted ?? this.notificationPermissionGranted,
      isRequestingVpnPermission:
          isRequestingVpnPermission ?? this.isRequestingVpnPermission,
      isRequestingNotificationPermission: isRequestingNotificationPermission ??
          this.isRequestingNotificationPermission,
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
        other.notificationPermissionGranted == notificationPermissionGranted &&
        other.isRequestingVpnPermission == isRequestingVpnPermission &&
        other.isRequestingNotificationPermission ==
            isRequestingNotificationPermission &&
        other.hasRequestedAnyPermission == hasRequestedAnyPermission &&
        other.isComplete == isComplete;
  }

  @override
  int get hashCode => Object.hash(
        vpnPermissionGranted,
        notificationPermissionGranted,
        isRequestingVpnPermission,
        isRequestingNotificationPermission,
        hasRequestedAnyPermission,
        isComplete,
      );

  @override
  String toString() =>
      'PermissionRequestState(vpn: $vpnPermissionGranted, '
      'notification: $notificationPermissionGranted, '
      'complete: $isComplete)';
}

// ---------------------------------------------------------------------------
// PermissionRequestNotifier
// ---------------------------------------------------------------------------

/// Manages the permission request flow state.
///
/// Handles requesting VPN and notification permissions sequentially,
/// updating the UI state to reflect progress and results.
class PermissionRequestNotifier extends AsyncNotifier<PermissionRequestState> {
  late final FlutterV2ray _v2ray;

  @override
  Future<PermissionRequestState> build() async {
    _v2ray = FlutterV2ray();
    return const PermissionRequestState();
  }

  // ── Permission Requests ─────────────────────────────────────────────────

  /// Requests all required permissions sequentially.
  ///
  /// First requests VPN permission, then notification permission.
  /// Updates state after each request regardless of grant status.
  Future<void> requestAllPermissions() async {
    try {
      await _requestVpnPermission();
      await _requestNotificationPermission();

      // Mark as complete after requesting all permissions
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

  /// Requests notification permission from the system.
  ///
  /// Uses Firebase Messaging to request notification permissions.
  /// Handles iOS 16+/Android 13+ permission requirements.
  Future<void> _requestNotificationPermission() async {
    try {
      final current = state.value;
      if (current == null) return;

      // Mark as requesting
      state = AsyncData(
        current.copyWith(isRequestingNotificationPermission: true),
      );

      AppLogger.info('Requesting notification permission');

      // Request permission via Firebase Messaging
      final settings = await FirebaseMessaging.instance.requestPermission(
        alert: true,
        badge: true,
        sound: true,
        provisional: false,
      );

      final granted = settings.authorizationStatus == AuthorizationStatus.authorized ||
          settings.authorizationStatus == AuthorizationStatus.provisional;

      AppLogger.info(
        'Notification permission ${granted ? 'granted' : 'denied'} '
        '(status: ${settings.authorizationStatus})',
      );

      // Update state with result
      final updated = state.value;
      if (updated == null) return;

      state = AsyncData(
        updated.copyWith(
          notificationPermissionGranted: granted,
          isRequestingNotificationPermission: false,
          hasRequestedAnyPermission: true,
        ),
      );
    } catch (e, st) {
      AppLogger.error(
        'Failed to request notification permission',
        error: e,
        stackTrace: st,
      );

      // Mark request as complete even on error
      final current = state.value;
      if (current != null) {
        state = AsyncData(
          current.copyWith(
            isRequestingNotificationPermission: false,
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
