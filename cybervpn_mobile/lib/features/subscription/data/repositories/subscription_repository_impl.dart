import 'package:cybervpn_mobile/core/data/cache_strategy.dart';
import 'package:cybervpn_mobile/core/errors/exceptions.dart';
import 'package:cybervpn_mobile/core/errors/failures.dart' hide Failure;
import 'package:cybervpn_mobile/core/errors/network_error_handler.dart';
// NetworkInfo import kept for DI parameter type compatibility.
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/subscription/data/datasources/subscription_remote_ds.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/plan_entity.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/subscription_entity.dart';
import 'package:cybervpn_mobile/features/subscription/domain/repositories/subscription_repository.dart';

class SubscriptionRepositoryImpl with NetworkErrorHandler, CachedRepository implements SubscriptionRepository {
  final SubscriptionRemoteDataSource _remoteDataSource;

  // In-memory caches for cacheFirst strategy.
  List<PlanEntity>? _cachedPlans;
  SubscriptionEntity? _cachedSubscription;
  bool _hasSubscriptionCache = false;

  SubscriptionRepositoryImpl({
    required SubscriptionRemoteDataSource remoteDataSource,
    // Kept for DI compatibility; not used directly.
    Object? networkInfo,
  }) : _remoteDataSource = remoteDataSource;

  @override
  Future<Result<List<PlanEntity>>> getPlans({
    CacheStrategy strategy = CacheStrategy.cacheFirst,
  }) async {
    return executeWithStrategy<List<PlanEntity>>(
      strategy: strategy,
      fetchFromNetwork: _remoteDataSource.fetchPlans,
      readFromCache: () async => _cachedPlans,
      writeToCache: (plans) async => _cachedPlans = plans,
    );
  }

  @override
  Future<Result<SubscriptionEntity?>> getActiveSubscription() async {
    // Manual cacheFirst: nullable T is incompatible with CachedRepository
    // (which uses null to signal cache miss).
    if (_hasSubscriptionCache) {
      return Success(_cachedSubscription);
    }
    try {
      final sub = await _remoteDataSource.fetchActiveSubscription();
      _cachedSubscription = sub;
      _hasSubscriptionCache = true;
      return Success(sub);
    } on AppException catch (e) {
      return Failure(mapExceptionToFailure(e));
    } catch (e) {
      return Failure(UnknownFailure(message: e.toString()));
    }
  }

  @override
  Future<Result<SubscriptionEntity>> subscribe(String planId, {String? paymentMethod}) async {
    try {
      final subscription = await _remoteDataSource.createSubscription(planId, paymentMethod: paymentMethod);
      // Invalidate caches on mutation.
      _cachedSubscription = null;
      _hasSubscriptionCache = false;
      return Success(subscription);
    } on AppException catch (e) {
      return Failure(mapExceptionToFailure(e));
    } catch (e) {
      return Failure(UnknownFailure(message: e.toString()));
    }
  }

  @override
  Future<Result<void>> cancelSubscription(String subscriptionId) async {
    try {
      await _remoteDataSource.cancelSubscription(subscriptionId);
      // Invalidate caches on mutation.
      _cachedSubscription = null;
      _hasSubscriptionCache = false;
      return const Success(null);
    } on AppException catch (e) {
      return Failure(mapExceptionToFailure(e));
    } catch (e) {
      return Failure(UnknownFailure(message: e.toString()));
    }
  }

  @override
  Future<Result<void>> restorePurchases() async {
    // RevenueCat handles restore; this is a placeholder
    return const Success(null);
  }
}
