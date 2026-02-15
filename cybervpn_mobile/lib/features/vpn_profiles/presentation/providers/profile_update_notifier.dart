import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/di/profile_providers.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_notifier.dart';

/// Exponential backoff delays for retry attempts.
const _backoffDelays = [
  Duration(minutes: 1),
  Duration(minutes: 5),
  Duration(minutes: 15),
];

/// Maximum number of retry attempts before giving up.
const _maxRetries = 3;

/// App-scoped notifier that manages automatic subscription updates.
///
/// Checks for due subscription updates on app startup/resume and
/// retries with exponential backoff (1min → 5min → 15min, max 3 attempts).
/// Does NOT interrupt an active VPN connection — updates are deferred
/// until the tunnel is down.
class ProfileUpdateNotifier extends Notifier<ProfileUpdateState> {
  Timer? _retryTimer;
  int _retryCount = 0;

  @override
  ProfileUpdateState build() {
    ref.onDispose(_cancelRetry);
    return const ProfileUpdateState();
  }

  /// Checks for and applies due subscription updates.
  ///
  /// Called on app startup and when the app resumes from background.
  /// Skips silently if the VPN is currently connected or an update
  /// is already in progress.
  Future<void> checkAndUpdate() async {
    if (state.isUpdating) return;

    // Don't update subscriptions while VPN is connected.
    final vpnState = ref.read(vpnConnectionProvider).value;
    if (vpnState != null && vpnState.isConnected) {
      AppLogger.debug('ProfileUpdateNotifier: skipping — VPN connected');
      return;
    }

    state = state.copyWith(isUpdating: true, error: null);

    final result = await ref
        .read(updateSubscriptionsUseCaseProvider)
        .call();

    switch (result) {
      case Success(:final data):
        _retryCount = 0;
        _cancelRetry();
        state = state.copyWith(
          isUpdating: false,
          lastUpdateCount: data,
          lastUpdatedAt: DateTime.now(),
        );
        if (data > 0) {
          AppLogger.info(
            'ProfileUpdateNotifier: updated $data subscription(s)',
          );
        }
      case Failure(:final failure):
        state = state.copyWith(
          isUpdating: false,
          error: failure.toString(),
        );
        _scheduleRetry();
    }
  }

  /// Manually refreshes a single profile's subscription.
  ///
  /// Returns the [Result] so callers can show appropriate UI feedback.
  Future<Result<void>> updateSingle(String profileId) async {
    state = state.copyWith(updatingProfileId: profileId);

    final result = await ref
        .read(vpnProfileRepositoryProvider)
        .updateSubscription(profileId);

    state = state.copyWith(updatingProfileId: null);
    return result;
  }

  /// Schedules a retry with exponential backoff.
  void _scheduleRetry() {
    if (_retryCount >= _maxRetries) {
      AppLogger.warning(
        'ProfileUpdateNotifier: max retries ($_maxRetries) reached',
      );
      return;
    }

    final delay = _backoffDelays[_retryCount];
    _retryCount++;

    AppLogger.debug(
      'ProfileUpdateNotifier: retry $_retryCount/$_maxRetries '
      'in ${delay.inMinutes}min',
    );

    _cancelRetry();
    _retryTimer = Timer(delay, checkAndUpdate);
  }

  void _cancelRetry() {
    _retryTimer?.cancel();
    _retryTimer = null;
  }

  /// Resets the retry counter and cancels any pending retry.
  void resetRetries() {
    _retryCount = 0;
    _cancelRetry();
    state = state.copyWith(error: null);
  }
}

/// Immutable state for [ProfileUpdateNotifier].
class ProfileUpdateState {
  const ProfileUpdateState({
    this.isUpdating = false,
    this.updatingProfileId,
    this.lastUpdateCount,
    this.lastUpdatedAt,
    this.error,
  });

  /// Whether a bulk subscription update is in progress.
  final bool isUpdating;

  /// The profile ID currently being updated individually, or `null`.
  final String? updatingProfileId;

  /// Number of profiles updated in the last successful bulk run.
  final int? lastUpdateCount;

  /// Timestamp of the last successful bulk update.
  final DateTime? lastUpdatedAt;

  /// Human-readable error from the last failed update.
  final String? error;

  ProfileUpdateState copyWith({
    bool? isUpdating,
    String? updatingProfileId,
    int? lastUpdateCount,
    DateTime? lastUpdatedAt,
    String? error,
  }) {
    return ProfileUpdateState(
      isUpdating: isUpdating ?? this.isUpdating,
      updatingProfileId: updatingProfileId,
      lastUpdateCount: lastUpdateCount ?? this.lastUpdateCount,
      lastUpdatedAt: lastUpdatedAt ?? this.lastUpdatedAt,
      error: error,
    );
  }
}

/// App-scoped provider for [ProfileUpdateNotifier].
///
/// Not auto-disposed — subscription updates should persist across
/// screen transitions and be triggered from the lifecycle manager.
final profileUpdateNotifierProvider =
    NotifierProvider<ProfileUpdateNotifier, ProfileUpdateState>(
  ProfileUpdateNotifier.new,
);
