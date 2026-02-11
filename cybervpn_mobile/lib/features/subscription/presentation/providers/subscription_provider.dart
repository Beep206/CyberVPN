import 'dart:async';
import 'dart:ui';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/network/websocket_client.dart';
import 'package:cybervpn_mobile/core/network/websocket_provider.dart';
import 'package:cybervpn_mobile/core/security/app_attestation.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/subscription/data/datasources/revenuecat_datasource.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/plan_entity.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/subscription_entity.dart';
import 'package:cybervpn_mobile/features/subscription/domain/repositories/subscription_repository.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/providers/subscription_state.dart';
import 'package:cybervpn_mobile/core/di/providers.dart'
    show subscriptionRepositoryProvider, revenueCatDataSourceProvider;

// ---------------------------------------------------------------------------
// Subscription notifier
// ---------------------------------------------------------------------------

/// Manages subscription state for the entire app.
///
/// On [build] it loads the current subscription and available plans in
/// parallel. Subsequent mutations (purchase, trial, restore) update the
/// inner [SubscriptionState.purchaseState] so the UI can show inline
/// loading / error indicators without losing the list of plans.
class SubscriptionNotifier extends AsyncNotifier<SubscriptionState> {
  SubscriptionRepository get _repo =>
      ref.read(subscriptionRepositoryProvider);

  RevenueCatDataSource get _revenueCat =>
      ref.read(revenueCatDataSourceProvider);

  StreamSubscription<SubscriptionUpdated>? _webSocketSubscription;

  /// CancelToken for in-flight API requests. Cancelled when provider disposes.
  CancelToken _cancelToken = CancelToken();

  // ---- Lifecycle -----------------------------------------------------------

  @override
  FutureOr<SubscriptionState> build() async {
    // Create a fresh CancelToken for this build cycle.
    _cancelToken = CancelToken();
    ref.onDispose(() => _cancelToken.cancel('Provider disposed'));

    // Fetch plans and active subscription in parallel.
    final results = await Future.wait([
      _repo.getPlans(),
      _repo.getActiveSubscription(),
    ]);

    final plansResult = results[0] as Result<List<PlanEntity>>;
    final subResult = results[1] as Result<SubscriptionEntity?>;

    final plans = plansResult.dataOrNull ?? <PlanEntity>[];
    final subscription = subResult.dataOrNull;

    // Determine trial eligibility: eligible when there is no active
    // subscription and at least one plan is marked as a trial.
    final trialEligible =
        subscription == null && plans.any((p) => p.isTrial);

    // Listen to WebSocket subscription_updated events.
    _listenToWebSocketEvents();

    // Clean up subscription when provider is disposed.
    ref.onDispose(_dispose);

    return SubscriptionState(
      currentSubscription: subscription,
      availablePlans: plans,
      trialEligibility: trialEligible,
    );
  }

  // ---- Public API ----------------------------------------------------------

  /// Reload available plans from the backend.
  Future<void> loadPlans() async {
    final current = state.value;
    if (current == null) return;

    final result = await _repo.getPlans();
    switch (result) {
      case Success(:final data):
        state = AsyncValue.data(current.copyWith(availablePlans: data));
      case Failure(:final failure):
        state = AsyncValue.error(failure, StackTrace.current);
    }
  }

  /// Reload the user's active subscription from the backend.
  Future<void> loadSubscription() async {
    final current = state.value;
    if (current == null) return;

    final result = await _repo.getActiveSubscription();
    switch (result) {
      case Success(:final data):
        state = AsyncValue.data(
          current.copyWith(
            currentSubscription: data,
            clearSubscription: data == null,
            trialEligibility: data == null &&
                current.availablePlans.any((p) => p.isTrial),
          ),
        );
      case Failure(:final failure):
        state = AsyncValue.error(failure, StackTrace.current);
    }
  }

  /// Purchase the given [plan] via the backend.
  ///
  /// Updates [SubscriptionState.purchaseState] throughout the flow so the
  /// UI can react to loading / success / error without a full page reload.
  Future<void> purchase(PlanEntity plan) async {
    final current = state.value;
    if (current == null) return;

    // Signal loading.
    state = AsyncValue.data(
      current.copyWith(
        purchaseState: PurchaseState.loading,
        clearPurchaseError: true,
      ),
    );

    // Perform app attestation before purchase (logging-only mode).
    // This runs inline but never blocks - failures are logged and ignored.
    await _performAttestation(AttestationTrigger.purchase);

    final result = await _repo.subscribe(
      plan.id,
      paymentMethod: plan.storeProductId,
    );

    switch (result) {
      case Success(:final data):
        state = AsyncValue.data(
          current.copyWith(
            currentSubscription: data,
            purchaseState: PurchaseState.success,
            trialEligibility: false,
            clearPurchaseError: true,
          ),
        );
      case Failure(:final failure):
        state = AsyncValue.data(
          current.copyWith(
            purchaseState: PurchaseState.error,
            purchaseError: failure.message,
          ),
        );
    }
  }

  /// Activate a free trial for the user.
  ///
  /// Looks for the first plan flagged [PlanEntity.isTrial] and subscribes
  /// the user to it.
  Future<void> activateTrial() async {
    final current = state.value;
    if (current == null) return;

    final trialPlan = current.availablePlans
        .where((p) => p.isTrial)
        .firstOrNull;

    if (trialPlan == null) {
      state = AsyncValue.data(
        current.copyWith(
          purchaseState: PurchaseState.error,
          purchaseError: 'No trial plan available.',
        ),
      );
      return;
    }

    // Delegate to the standard purchase flow.
    await purchase(trialPlan);
  }

  /// Restore previous purchases via RevenueCat and refresh backend state.
  Future<void> restorePurchases() async {
    final current = state.value;
    if (current == null) return;

    state = AsyncValue.data(
      current.copyWith(
        purchaseState: PurchaseState.loading,
        clearPurchaseError: true,
      ),
    );

    try {
      // Restore through RevenueCat first.
      await _revenueCat.restorePurchases();

      // Then sync with our backend.
      final restoreResult = await _repo.restorePurchases();
      if (restoreResult is Failure<void>) {
        state = AsyncValue.data(
          current.copyWith(
            purchaseState: PurchaseState.error,
            purchaseError: restoreResult.failure.message,
          ),
        );
        return;
      }

      // Reload subscription to reflect restored state.
      final subResult = await _repo.getActiveSubscription();
      final sub = subResult.dataOrNull;

      state = AsyncValue.data(
        current.copyWith(
          currentSubscription: sub,
          clearSubscription: sub == null,
          purchaseState: PurchaseState.success,
          trialEligibility:
              sub == null && current.availablePlans.any((p) => p.isTrial),
          clearPurchaseError: true,
        ),
      );
    } catch (e) {
      state = AsyncValue.data(
        current.copyWith(
          purchaseState: PurchaseState.error,
          purchaseError: e.toString(),
        ),
      );
    }
  }

  /// Reset [purchaseState] back to idle (e.g. after the UI dismisses a
  /// success/error banner).
  void clearPurchaseState() {
    final current = state.value;
    if (current == null) return;
    state = AsyncValue.data(
      current.copyWith(
        purchaseState: PurchaseState.idle,
        clearPurchaseError: true,
      ),
    );
  }

  /// Redeems an invite code to grant subscription benefits.
  ///
  /// Updates [SubscriptionState.purchaseState] throughout the flow so the
  /// UI can react to loading / success / error.
  Future<void> redeemInviteCode(String code) async {
    final current = state.value;
    if (current == null) return;

    // Signal loading.
    state = AsyncValue.data(
      current.copyWith(
        purchaseState: PurchaseState.loading,
        clearPurchaseError: true,
      ),
    );

    // Perform app attestation before redemption (logging-only mode).
    await _performAttestation(AttestationTrigger.purchase);

    final result = await _repo.redeemInviteCode(code);

    switch (result) {
      case Success(:final data):
        state = AsyncValue.data(
          current.copyWith(
            currentSubscription: data,
            purchaseState: PurchaseState.success,
            trialEligibility: false,
            clearPurchaseError: true,
          ),
        );
      case Failure(:final failure):
        state = AsyncValue.data(
          current.copyWith(
            purchaseState: PurchaseState.error,
            purchaseError: failure.message,
          ),
        );
    }
  }

  /// Called when the app returns to the foreground.
  ///
  /// Silently refreshes the subscription so the UI is up-to-date after
  /// the user may have managed their subscription in system settings.
  Future<void> onAppResumed() async {
    await loadSubscription();
  }

  // ---- Private helpers -----------------------------------------------------

  /// Listens to WebSocket subscription_updated events and refreshes
  /// the subscription state in real-time.
  void _listenToWebSocketEvents() {
    try {
      final client = ref.read(webSocketClientProvider);
      _webSocketSubscription = client.subscriptionEvents.listen(
        _onSubscriptionUpdated,
        onError: (Object e) {
          AppLogger.error('WebSocket subscription stream error', error: e);
        },
      );
    } catch (e) {
      AppLogger.error(
        'Failed to listen to WebSocket subscription stream',
        error: e,
      );
    }
  }

  /// Handles incoming subscription_updated WebSocket events.
  ///
  /// Triggers a full subscription refresh from the backend to ensure
  /// the local state is synchronized with the server.
  Future<void> _onSubscriptionUpdated(SubscriptionUpdated event) async {
    AppLogger.info(
      'Received subscription_updated event: subscriptionId=${event.subscriptionId}, status=${event.status}',
    );

    // Trigger a full refresh to get the latest subscription data.
    await loadSubscription();
  }

  /// Disposes resources when the provider is no longer used.
  void _dispose() {
    unawaited(_webSocketSubscription?.cancel());
  }

  // ── App attestation (logging mode) ─────────────────────────────────

  /// Performs app attestation for fraud detection (logging mode only).
  ///
  /// This method completes quickly and never throws. Results are logged
  /// to analytics and Sentry for monitoring. In current logging-only mode,
  /// attestation failures do not block the purchase flow.
  Future<void> _performAttestation(AttestationTrigger trigger) async {
    try {
      final attestationService = ref.read(appAttestationServiceProvider);
      final result = await attestationService.generateToken(trigger: trigger);
      AppLogger.info(
        'Purchase attestation completed: ${result.status.name}',
        category: 'subscription.attestation',
      );
    } catch (e, st) {
      // Log but don't throw - attestation failure should not block purchase
      AppLogger.warning(
        'Purchase attestation failed (non-blocking)',
        error: e,
        stackTrace: st,
        category: 'subscription.attestation',
      );
    }
  }
}

// ---------------------------------------------------------------------------
// Providers
// ---------------------------------------------------------------------------

/// Primary subscription state provider backed by [SubscriptionNotifier].
final subscriptionProvider =
    AsyncNotifierProvider<SubscriptionNotifier, SubscriptionState>(
  SubscriptionNotifier.new,
);

/// The current [SubscriptionStatus], or `null` when no subscription exists.
final subscriptionStatusProvider = Provider<SubscriptionStatus?>((ref) {
  final subState = ref.watch(subscriptionProvider).value;
  return subState?.currentSubscription?.status;
});

/// `true` when the user has an active or trial subscription.
final isSubscriptionActiveProvider = Provider<bool>((ref) {
  final subState = ref.watch(subscriptionProvider).value;
  return subState?.isActive ?? false;
});

/// Full days remaining on the current subscription (0 when none).
final daysRemainingProvider = Provider<int>((ref) {
  final subState = ref.watch(subscriptionProvider).value;
  return subState?.daysRemaining ?? 0;
});

/// Traffic usage ratio `[0.0, 1.0]` for the current subscription.
final trafficUsageProvider = Provider<double>((ref) {
  final subState = ref.watch(subscriptionProvider).value;
  return subState?.trafficUsageRatio ?? 0.0;
});

// ---------------------------------------------------------------------------
// App lifecycle observer (auto-refresh)
// ---------------------------------------------------------------------------

/// A [ProviderObserver]-style helper that refreshes subscription data when
/// the app returns to the foreground.
///
/// Usage: Instantiate in the widget tree (e.g. at the root `MaterialApp`)
/// and forward [AppLifecycleState] changes:
///
/// ```dart
/// class _AppState extends State<App> with WidgetsBindingObserver {
///   @override
///   void didChangeAppLifecycleState(AppLifecycleState state) {
///     if (state == AppLifecycleState.resumed) {
///       ref.read(subscriptionProvider.notifier).onAppResumed();
///     }
///   }
/// }
/// ```
///
/// Alternatively, wrap this in a [ConsumerStatefulWidget] mixin so it is
/// self-contained.
class SubscriptionLifecycleObserver {
  SubscriptionLifecycleObserver(this._ref);

  final Ref _ref;

  /// Call from [WidgetsBindingObserver.didChangeAppLifecycleState].
  void didChangeAppLifecycleState(AppLifecycleState lifecycleState) {
    if (lifecycleState == AppLifecycleState.resumed) {
      unawaited(_ref.read(subscriptionProvider.notifier).onAppResumed());
    }
  }
}
