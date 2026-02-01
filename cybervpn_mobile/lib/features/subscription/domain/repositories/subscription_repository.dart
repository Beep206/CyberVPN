import 'package:cybervpn_mobile/core/errors/failures.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/plan_entity.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/subscription_entity.dart';

abstract class SubscriptionRepository {
  Future<List<PlanEntity>> getPlans();
  Future<SubscriptionEntity?> getActiveSubscription();
  Future<SubscriptionEntity> subscribe(String planId, {String? paymentMethod});
  Future<void> cancelSubscription(String subscriptionId);
  Future<void> restorePurchases();
}
