import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/di/providers.dart';
import 'package:cybervpn_mobile/core/errors/failures.dart' show CacheFailure;
import 'package:cybervpn_mobile/core/services/push_notification_service.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/config_import/presentation/providers/config_import_provider.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/domain/services/ping_policy_runtime.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_notifier.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/di/profile_providers.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/vpn_profile.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/services/subscription_policy_runtime.dart';

/// Exponential backoff delays for retry attempts.
const _backoffDelays = [
  Duration(minutes: 1),
  Duration(minutes: 5),
  Duration(minutes: 15),
];

/// Maximum number of retry attempts before giving up.
const _maxRetries = 3;

/// Minimum interval between lifecycle-driven refresh runs.
const _lifecycleDebounce = Duration(seconds: 10);

/// Limit parallel TCP pings to a small batch size to avoid bursts.
const _pingBatchSize = 6;

/// Source that triggered lifecycle subscription policies.
enum SubscriptionLifecycleTrigger { startup, resume }

/// App-scoped notifier that manages subscription policy automation.
///
/// Handles:
/// - due remote subscription refreshes
/// - due imported source refreshes
/// - ping-on-open latency caching
/// - optional local update notifications
class ProfileUpdateNotifier extends Notifier<ProfileUpdateState> {
  Timer? _retryTimer;
  int _retryCount = 0;
  DateTime? _lastLifecycleRunAt;

  @override
  ProfileUpdateState build() {
    ref.onDispose(_cancelRetry);
    return const ProfileUpdateState();
  }

  /// Legacy compatibility entrypoint: refreshes due subscription sources.
  Future<void> checkAndUpdate() async {
    await _runLifecyclePolicies(
      trigger: SubscriptionLifecycleTrigger.resume,
      allowPing: false,
    );
  }

  /// Applies on-open subscription policies on app startup/resume.
  Future<void> handleAppOpen({
    required SubscriptionLifecycleTrigger trigger,
  }) async {
    await _runLifecyclePolicies(trigger: trigger, allowPing: true);
  }

  /// Manually refreshes a single profile's subscription.
  ///
  /// Returns the [Result] so callers can show appropriate UI feedback.
  Future<Result<void>> updateSingle(String profileId) async {
    state = state.copyWith(updatingProfileId: profileId);

    final result = await ref
        .read(vpnProfileRepositoryProvider)
        .updateSubscription(profileId);

    if (!ref.mounted) {
      return result;
    }

    state = state.copyWith(updatingProfileId: null);
    return result;
  }

  /// Refreshes the provided remote profile ids immediately, ignoring due checks.
  ///
  /// Intended for manual "refresh all" actions from settings surfaces.
  Future<Result<int>> refreshProfilesNow(Iterable<String> profileIds) async {
    final ids = profileIds
        .map((id) => id.trim())
        .where((id) => id.isNotEmpty)
        .toSet()
        .toList(growable: false);

    if (ids.isEmpty) {
      return const Success(0);
    }

    state = state.copyWith(isUpdating: true, error: null);

    var updatedCount = 0;
    AppFailure? lastFailure;

    for (final profileId in ids) {
      final result = await ref
          .read(vpnProfileRepositoryProvider)
          .updateSubscription(profileId);

      switch (result) {
        case Success():
          updatedCount++;
        case Failure(:final failure):
          lastFailure = failure;
          AppLogger.warning(
            'ProfileUpdateNotifier: failed to refresh $profileId',
            error: failure,
          );
      }
    }

    if (!ref.mounted) {
      return Success(updatedCount);
    }

    state = state.copyWith(
      isUpdating: false,
      lastUpdateCount: updatedCount,
      lastImportRefreshCount: 0,
      lastPingedProfileCount: 0,
      lastUpdatedAt: DateTime.now(),
      error: lastFailure?.toString(),
    );

    if (updatedCount == 0 && lastFailure != null) {
      return const Failure(
        CacheFailure(message: 'Failed to refresh subscription profiles'),
      );
    }

    return Success(updatedCount);
  }

  Future<void> _runLifecyclePolicies({
    required SubscriptionLifecycleTrigger trigger,
    required bool allowPing,
  }) async {
    if (state.isUpdating) {
      return;
    }

    final now = DateTime.now();
    if (_lastLifecycleRunAt != null &&
        now.difference(_lastLifecycleRunAt!) < _lifecycleDebounce) {
      AppLogger.debug(
        'ProfileUpdateNotifier: lifecycle run debounced',
        category: 'subscription.policy',
      );
      return;
    }

    final policy = await _readPolicy();
    final shouldRefresh = policy.autoUpdateEnabled && policy.autoUpdateOnOpen;
    final shouldPing = allowPing && policy.pingOnOpenEnabled;
    if (!shouldRefresh && !shouldPing) {
      return;
    }

    final vpnState = ref.read(vpnConnectionProvider).value;
    if (vpnState != null && vpnState.isConnected) {
      AppLogger.debug(
        'ProfileUpdateNotifier: skipping lifecycle policy while VPN connected',
        category: 'subscription.policy',
      );
      return;
    }

    _lastLifecycleRunAt = now;
    state = state.copyWith(isUpdating: true, error: null);

    try {
      var updatedProfiles = 0;
      var refreshedImports = 0;
      var pingedProfiles = 0;

      if (shouldRefresh) {
        updatedProfiles = await _refreshDueRemoteProfiles(policy);
        refreshedImports = await _refreshDueImportedSources(policy);
      }

      if (shouldPing) {
        pingedProfiles = await _refreshRemoteProfileLatencies();
      }

      if (!ref.mounted) {
        return;
      }

      _retryCount = 0;
      _cancelRetry();
      state = state.copyWith(
        isUpdating: false,
        lastUpdateCount: updatedProfiles,
        lastImportRefreshCount: refreshedImports,
        lastPingedProfileCount: pingedProfiles,
        lastUpdatedAt: DateTime.now(),
        lastLifecycleTrigger: trigger,
        error: null,
      );

      AppLogger.info(
        'ProfileUpdateNotifier: lifecycle policies applied',
        category: 'subscription.policy',
        data: {
          'trigger': trigger.name,
          'updatedProfiles': updatedProfiles,
          'refreshedImports': refreshedImports,
          'pingedProfiles': pingedProfiles,
          'userAgent': policy.effectiveUserAgent,
          'sortMode': policy.sortMode.name,
          'connectStrategy': policy.connectStrategy.name,
          'collapseSubscriptions': policy.collapseSubscriptions,
          'preventDuplicateImports': policy.preventDuplicateImports,
          'noFilter': policy.noFilter,
        },
      );

      if (policy.updateNotificationsEnabled &&
          (updatedProfiles > 0 || refreshedImports > 0)) {
        await _showUpdateNotification(
          updatedProfiles: updatedProfiles,
          refreshedImports: refreshedImports,
        );
      }
    } catch (e, st) {
      AppLogger.error(
        'ProfileUpdateNotifier: lifecycle policy run failed',
        error: e,
        stackTrace: st,
        category: 'subscription.policy',
      );
      if (!ref.mounted) {
        return;
      }
      state = state.copyWith(isUpdating: false, error: e.toString());
      _scheduleRetry();
    }
  }

  Future<int> _refreshDueRemoteProfiles(SubscriptionPolicyState policy) async {
    final profiles = await ref.read(profileListProvider.future);
    final dueProfiles = profiles
        .whereType<RemoteVpnProfile>()
        .where(
          (profile) => ref
              .read(subscriptionPolicyRuntimeProvider)
              .isRefreshDue(
                lastUpdated: profile.lastUpdatedAt,
                policy: policy,
              ),
        )
        .toList(growable: false);

    if (dueProfiles.isEmpty) {
      return 0;
    }

    var updatedCount = 0;
    for (final profile in dueProfiles) {
      final result = await ref
          .read(vpnProfileRepositoryProvider)
          .updateSubscription(profile.id);
      if (result.isSuccess) {
        updatedCount++;
        continue;
      }

      AppLogger.warning(
        'ProfileUpdateNotifier: failed lifecycle refresh for ${profile.id}',
        error: result.failureOrNull,
        category: 'subscription.policy',
      );
    }

    return updatedCount;
  }

  Future<int> _refreshDueImportedSources(SubscriptionPolicyState policy) async {
    await ref.read(configImportProvider.future);
    final metadata = ref.read(subscriptionUrlMetadataProvider);
    final dueUrls = metadata
        .where(
          (entry) => ref
              .read(subscriptionPolicyRuntimeProvider)
              .isRefreshDue(lastUpdated: entry.lastUpdated, policy: policy),
        )
        .map((entry) => entry.url)
        .toList(growable: false);

    if (dueUrls.isEmpty) {
      return 0;
    }

    var refreshedCount = 0;
    final notifier = ref.read(configImportProvider.notifier);
    for (final url in dueUrls) {
      if (await notifier.refreshSubscriptionUrl(url)) {
        refreshedCount++;
      }
    }
    return refreshedCount;
  }

  Future<int> _refreshRemoteProfileLatencies() async {
    final profiles = await ref.read(profileListProvider.future);
    final remoteProfiles = profiles
        .whereType<RemoteVpnProfile>()
        .where((profile) => profile.servers.isNotEmpty)
        .toList(growable: false);
    if (remoteProfiles.isEmpty) {
      return 0;
    }

    final settings = await ref
        .read(settingsProvider.future)
        .catchError((Object _, StackTrace _) => const AppSettings());
    final pingPolicy = ref.read(pingPolicyRuntimeProvider);
    final pingService = ref.read(pingServiceProvider);
    final vpnEngine = ref.read(vpnEngineDatasourceProvider);
    var pingedProfiles = 0;

    for (final profile in remoteProfiles) {
      final latencies = <String, int?>{};
      for (var i = 0; i < profile.servers.length; i += _pingBatchSize) {
        final end = i + _pingBatchSize < profile.servers.length
            ? i + _pingBatchSize
            : profile.servers.length;
        final batch = profile.servers.sublist(i, end);
        final batchResults = await Future.wait(
          batch.map((server) async {
            try {
              final hasConfigData = server.configData.trim().isNotEmpty;
              final plan = pingPolicy.resolveProfilePlan(
                settings.pingMode,
                hasConfigData: hasConfigData,
              );
              if (plan.isFallback) {
                AppLogger.info(
                  'Subscription ping fell back to TCP',
                  category: 'subscription.policy',
                  data: {
                    'profileId': profile.id,
                    'serverId': server.id,
                    'requestedMode': plan.requestedMode.name,
                    'effectiveTransport': plan.effectiveTransport.name,
                    'reason': plan.fallbackReason,
                  },
                );
              }

              final latency = await () async {
                switch (plan.effectiveTransport) {
                  case PingTransport.tcp:
                    return pingService.pingServer(
                      server.serverAddress,
                      server.port,
                    );
                  case PingTransport.proxyGet:
                  case PingTransport.proxyHead:
                    final delay = await vpnEngine.getServerDelay(
                      server.configData,
                      url: settings.pingTestUrl,
                      httpMethod:
                          plan.effectiveTransport == PingTransport.proxyGet
                          ? 'GET'
                          : 'HEAD',
                    );
                    return delay >= 0 ? delay : null;
                }
              }();
              return MapEntry(server.id, latency);
            } catch (error, stackTrace) {
              AppLogger.warning(
                'Profile latency probe failed',
                category: 'subscription.policy',
                error: error,
                stackTrace: stackTrace,
                data: {'profileId': profile.id, 'serverId': server.id},
              );
              return MapEntry(server.id, null);
            }
          }),
        );
        for (final entry in batchResults) {
          latencies[entry.key] = entry.value;
        }
      }

      final updateResult = await ref
          .read(vpnProfileRepositoryProvider)
          .updateProfileServerLatencies(profile.id, latencies);
      if (updateResult.isSuccess) {
        pingedProfiles++;
      }
    }

    return pingedProfiles;
  }

  Future<SubscriptionPolicyState> _readPolicy() async {
    try {
      final settings = await ref.read(settingsProvider.future);
      return ref.read(subscriptionPolicyRuntimeProvider).resolve(settings);
    } catch (e, st) {
      AppLogger.warning(
        'ProfileUpdateNotifier: failed to read settings, using defaults',
        error: e,
        stackTrace: st,
        category: 'subscription.policy',
      );
      return const SubscriptionPolicyState();
    }
  }

  Future<void> _showUpdateNotification({
    required int updatedProfiles,
    required int refreshedImports,
  }) async {
    final id = DateTime.now().millisecondsSinceEpoch.remainder(1 << 31);
    await PushNotificationService.instance.showLocalNotification(
      id: id,
      title: 'Subscriptions updated',
      body:
          '$updatedProfiles provider profile(s), $refreshedImports imported source(s).',
      payload: '/settings/vpn/subscriptions',
    );
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
    this.lastImportRefreshCount,
    this.lastPingedProfileCount,
    this.lastUpdatedAt,
    this.lastLifecycleTrigger,
    this.error,
  });

  /// Whether a bulk subscription update is in progress.
  final bool isUpdating;

  /// The profile ID currently being updated individually, or `null`.
  final String? updatingProfileId;

  /// Number of provider profiles updated in the last successful bulk run.
  final int? lastUpdateCount;

  /// Number of imported subscription sources refreshed in the last run.
  final int? lastImportRefreshCount;

  /// Number of remote profiles whose latency cache was refreshed.
  final int? lastPingedProfileCount;

  /// Timestamp of the last successful bulk update.
  final DateTime? lastUpdatedAt;

  /// Which lifecycle trigger last drove an automatic run.
  final SubscriptionLifecycleTrigger? lastLifecycleTrigger;

  /// Human-readable error from the last failed update.
  final String? error;

  ProfileUpdateState copyWith({
    bool? isUpdating,
    String? updatingProfileId,
    int? lastUpdateCount,
    int? lastImportRefreshCount,
    int? lastPingedProfileCount,
    DateTime? lastUpdatedAt,
    SubscriptionLifecycleTrigger? lastLifecycleTrigger,
    String? error,
  }) {
    return ProfileUpdateState(
      isUpdating: isUpdating ?? this.isUpdating,
      updatingProfileId: updatingProfileId,
      lastUpdateCount: lastUpdateCount ?? this.lastUpdateCount,
      lastImportRefreshCount:
          lastImportRefreshCount ?? this.lastImportRefreshCount,
      lastPingedProfileCount:
          lastPingedProfileCount ?? this.lastPingedProfileCount,
      lastUpdatedAt: lastUpdatedAt ?? this.lastUpdatedAt,
      lastLifecycleTrigger: lastLifecycleTrigger ?? this.lastLifecycleTrigger,
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
