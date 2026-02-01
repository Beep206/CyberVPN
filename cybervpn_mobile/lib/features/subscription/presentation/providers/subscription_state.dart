import 'package:cybervpn_mobile/features/subscription/domain/entities/plan_entity.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/subscription_entity.dart';

// ---------------------------------------------------------------------------
// Purchase action state
// ---------------------------------------------------------------------------

/// Tracks the state of an in-flight purchase / trial activation.
enum PurchaseState { idle, loading, success, error }

// ---------------------------------------------------------------------------
// Subscription state
// ---------------------------------------------------------------------------

/// Immutable snapshot of everything the subscription UI needs.
///
/// Held inside an [AsyncValue] by the [SubscriptionNotifier] so the
/// outer async wrapper covers the initial load, while [purchaseState]
/// tracks subsequent purchase / restore operations independently.
class SubscriptionState {
  const SubscriptionState({
    this.currentSubscription,
    this.availablePlans = const [],
    this.purchaseState = PurchaseState.idle,
    this.trialEligibility = false,
    this.purchaseError,
  });

  /// The user's active (or most-recent) subscription, if any.
  final SubscriptionEntity? currentSubscription;

  /// Plans available for purchase.
  final List<PlanEntity> availablePlans;

  /// Tracks a purchase / restore / trial-activation operation.
  final PurchaseState purchaseState;

  /// Whether the current user is eligible for a free trial.
  final bool trialEligibility;

  /// Human-readable error from the last failed purchase, if any.
  final String? purchaseError;

  // ---- Derived helpers ----------------------------------------------------

  /// `true` when the user has an active or trial subscription.
  bool get isActive {
    final sub = currentSubscription;
    if (sub == null) return false;
    return sub.status == SubscriptionStatus.active ||
        sub.status == SubscriptionStatus.trial;
  }

  /// Number of full days remaining on the current subscription.
  /// Returns `0` when there is no active subscription.
  int get daysRemaining {
    final sub = currentSubscription;
    if (sub == null) return 0;
    final remaining = sub.endDate.difference(DateTime.now()).inDays;
    return remaining < 0 ? 0 : remaining;
  }

  /// Traffic usage as a ratio in `[0.0, 1.0]`.
  /// Returns `0.0` when there is no subscription or limit is zero
  /// (i.e. unlimited).
  double get trafficUsageRatio {
    final sub = currentSubscription;
    if (sub == null || sub.trafficLimitBytes == 0) return 0.0;
    final ratio = sub.trafficUsedBytes / sub.trafficLimitBytes;
    return ratio.clamp(0.0, 1.0);
  }

  // ---- Copy-with ----------------------------------------------------------

  SubscriptionState copyWith({
    SubscriptionEntity? currentSubscription,
    bool clearSubscription = false,
    List<PlanEntity>? availablePlans,
    PurchaseState? purchaseState,
    bool? trialEligibility,
    String? purchaseError,
    bool clearPurchaseError = false,
  }) {
    return SubscriptionState(
      currentSubscription: clearSubscription
          ? null
          : (currentSubscription ?? this.currentSubscription),
      availablePlans: availablePlans ?? this.availablePlans,
      purchaseState: purchaseState ?? this.purchaseState,
      trialEligibility: trialEligibility ?? this.trialEligibility,
      purchaseError:
          clearPurchaseError ? null : (purchaseError ?? this.purchaseError),
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is SubscriptionState &&
          runtimeType == other.runtimeType &&
          currentSubscription == other.currentSubscription &&
          availablePlans == other.availablePlans &&
          purchaseState == other.purchaseState &&
          trialEligibility == other.trialEligibility &&
          purchaseError == other.purchaseError;

  @override
  int get hashCode => Object.hash(
        currentSubscription,
        availablePlans,
        purchaseState,
        trialEligibility,
        purchaseError,
      );

  @override
  String toString() =>
      'SubscriptionState(active: $isActive, plans: ${availablePlans.length}, '
      'purchase: $purchaseState, trialEligible: $trialEligibility)';
}
