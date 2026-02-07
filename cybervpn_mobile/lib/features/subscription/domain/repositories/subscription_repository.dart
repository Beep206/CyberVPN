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
}
