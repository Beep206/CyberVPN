import 'package:cybervpn_mobile/core/data/cache_strategy.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/subscription/data/datasources/subscription_remote_ds.dart'
    show PaginatedPaymentHistory;
import 'package:cybervpn_mobile/features/subscription/domain/entities/plan_entity.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/subscription_entity.dart';

abstract class SubscriptionRepository {
  Future<Result<List<PlanEntity>>> getPlans({
    CacheStrategy strategy = CacheStrategy.cacheFirst,
  });
  Future<Result<SubscriptionEntity?>> getActiveSubscription();
  Future<Result<SubscriptionEntity>> subscribe(String planId, {String? paymentMethod});
  Future<Result<void>> cancelSubscription(String subscriptionId);
  Future<Result<void>> restorePurchases();
  Future<Result<PaginatedPaymentHistory>> getPaymentHistory({
    int offset = 0,
    int limit = 20,
  });

  /// Redeems an invite code to grant subscription benefits.
  /// Returns the newly activated subscription on success.
  Future<Result<SubscriptionEntity>> redeemInviteCode(String code);

  /// Applies a promo code to get a discount on a plan.
  /// Returns the discount amount and final price.
  Future<Result<Map<String, dynamic>>> applyPromoCode(String code, String planId);

  /// Checks trial eligibility for the current user.
  /// Returns: { is_eligible: bool, days_remaining: int?, trial_used: bool }
  Future<Result<Map<String, dynamic>>> getTrialStatus();

  /// Activates a free trial subscription for the user (7 days).
  /// Returns the activated subscription.
  Future<Result<SubscriptionEntity>> activateTrial();
}
