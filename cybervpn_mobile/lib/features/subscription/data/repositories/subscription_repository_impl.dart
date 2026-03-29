import 'dart:async';

import 'package:cybervpn_mobile/core/data/cache_strategy.dart';
import 'package:cybervpn_mobile/core/constants/cache_constants.dart';
import 'package:cybervpn_mobile/core/errors/exceptions.dart';
import 'package:cybervpn_mobile/core/errors/failures.dart' hide Failure;
import 'package:cybervpn_mobile/core/errors/network_error_handler.dart';
// NetworkInfo import kept for DI parameter type compatibility.
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/subscription/data/datasources/subscription_local_ds.dart';
import 'package:cybervpn_mobile/features/subscription/data/datasources/subscription_remote_ds.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/plan_entity.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/subscription_entity.dart';
import 'package:cybervpn_mobile/features/subscription/domain/repositories/subscription_repository.dart';

class SubscriptionRepositoryImpl
    with NetworkErrorHandler, CachedRepository
    implements SubscriptionRepository {
  final SubscriptionRemoteDataSource _remoteDataSource;
  final SubscriptionLocalDataSource? _localDataSource;

  // In-memory caches for cacheFirst strategy.
  List<PlanEntity>? _cachedPlans;
  DateTime? _cachedPlansAt;
  SubscriptionEntity? _cachedSubscription;
  bool _hasSubscriptionCache = false;
  DateTime? _cachedSubscriptionAt;

  static const _memoryCacheTtl = CacheConstants.subscriptionCacheTtl;

  SubscriptionRepositoryImpl({
    required SubscriptionRemoteDataSource remoteDataSource,
    SubscriptionLocalDataSource? localDataSource,
    // Kept for DI compatibility; not used directly.
    Object? networkInfo,
  }) : _remoteDataSource = remoteDataSource,
       _localDataSource = localDataSource;

  @override
  Future<Result<List<PlanEntity>>> getPlans({
    CacheStrategy strategy = CacheStrategy.cacheFirst,
  }) async {
    switch (strategy) {
      case CacheStrategy.cacheFirst:
        return _getPlansCacheFirst();
      case CacheStrategy.networkFirst:
        return _getPlansNetworkFirst();
      case CacheStrategy.cacheOnly:
        return _getPlansCacheOnly();
      case CacheStrategy.networkOnly:
        return _getPlansNetworkOnly();
      case CacheStrategy.staleWhileRevalidate:
        return _getPlansStaleWhileRevalidate();
    }
  }

  @override
  Future<Result<SubscriptionEntity?>> getActiveSubscription() async {
    final memoryFresh = _readFreshSubscriptionMemory();
    if (memoryFresh.hit) {
      return Success(memoryFresh.value);
    }

    try {
      final persistedFresh = await _readFreshSubscriptionCache();
      if (persistedFresh.hit) {
        _writeSubscriptionMemory(persistedFresh.value);
        return Success(persistedFresh.value);
      }
    } catch (e) {
      AppLogger.debug('Persistent subscription cache read failed', error: e);
    }

    final staleSubscription = await _readStaleSubscriptionFallback();

    try {
      final sub = await _remoteDataSource.fetchActiveSubscription();
      await _writeSubscriptionCache(sub);
      return Success(sub);
    } on AppException catch (e) {
      if (staleSubscription.hit) {
        AppLogger.warning(
          'Returning stale subscription cache after network failure',
          category: 'subscription.cache',
          error: e,
        );
        return Success(staleSubscription.value);
      }
      return Failure(mapExceptionToFailure(e));
    } catch (e) {
      if (staleSubscription.hit) {
        AppLogger.warning(
          'Returning stale subscription cache after unexpected fetch failure',
          category: 'subscription.cache',
          error: e,
        );
        return Success(staleSubscription.value);
      }
      return Failure(UnknownFailure(message: e.toString()));
    }
  }

  @override
  Future<Result<SubscriptionEntity>> subscribe(
    String planId, {
    String? paymentMethod,
  }) async {
    try {
      final subscription = await _remoteDataSource.createSubscription(
        planId,
        paymentMethod: paymentMethod,
      );
      // Invalidate caches on mutation.
      await _invalidateAllCaches();
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
      await _invalidateAllCaches();
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

  @override
  Future<Result<PaginatedPaymentHistory>> getPaymentHistory({
    int offset = 0,
    int limit = 20,
  }) async {
    try {
      final history = await _remoteDataSource.fetchPaymentHistory(
        offset: offset,
        limit: limit,
      );
      return Success(history);
    } on AppException catch (e) {
      return Failure(mapExceptionToFailure(e));
    } catch (e) {
      return Failure(UnknownFailure(message: e.toString()));
    }
  }

  @override
  Future<Result<SubscriptionEntity>> redeemInviteCode(String code) async {
    try {
      final subscription = await _remoteDataSource.redeemInviteCode(code);
      // Invalidate caches on mutation.
      await _invalidateAllCaches();
      return Success(subscription);
    } on AppException catch (e) {
      return Failure(mapExceptionToFailure(e));
    } catch (e) {
      return Failure(UnknownFailure(message: e.toString()));
    }
  }

  @override
  Future<Result<Map<String, dynamic>>> applyPromoCode(
    String code,
    String planId,
  ) async {
    try {
      final result = await _remoteDataSource.applyPromoCode(code, planId);
      return Success(result);
    } on AppException catch (e) {
      return Failure(mapExceptionToFailure(e));
    } catch (e) {
      return Failure(UnknownFailure(message: e.toString()));
    }
  }

  @override
  Future<Result<Map<String, dynamic>>> getTrialStatus() async {
    try {
      final result = await _remoteDataSource.getTrialStatus();
      return Success(result);
    } on AppException catch (e) {
      return Failure(mapExceptionToFailure(e));
    } catch (e) {
      return Failure(UnknownFailure(message: e.toString()));
    }
  }

  @override
  Future<Result<SubscriptionEntity>> activateTrial() async {
    try {
      final subscription = await _remoteDataSource.activateTrial();

      // Clear cached subscription since trial activation creates a new subscription
      await _invalidateAllCaches();

      return Success(subscription);
    } on AppException catch (e) {
      return Failure(mapExceptionToFailure(e));
    } catch (e) {
      return Failure(UnknownFailure(message: e.toString()));
    }
  }

  Future<Result<List<PlanEntity>>> _getPlansCacheFirst() async {
    final memoryFresh = _readFreshPlansMemory();
    if (memoryFresh != null) {
      return Success(memoryFresh);
    }

    try {
      final persistedFresh = await _localDataSource?.getCachedPlans();
      if (persistedFresh != null) {
        _writePlansMemory(persistedFresh);
        return Success(persistedFresh);
      }
    } catch (e) {
      AppLogger.debug('Persistent plan cache read failed', error: e);
    }

    final stalePlans = await _readStalePlansFallback();

    try {
      final data = await _remoteDataSource.fetchPlans();
      await _writePlansCache(data);
      return Success(data);
    } on AppException catch (e) {
      if (stalePlans != null) {
        AppLogger.warning(
          'Returning stale plans cache after network failure',
          category: 'subscription.cache',
          error: e,
        );
        return Success(stalePlans);
      }
      return Failure(mapExceptionToFailure(e));
    } catch (e) {
      if (stalePlans != null) {
        AppLogger.warning(
          'Returning stale plans cache after unexpected fetch failure',
          category: 'subscription.cache',
          error: e,
        );
        return Success(stalePlans);
      }
      return Failure(UnknownFailure(message: e.toString()));
    }
  }

  Future<Result<List<PlanEntity>>> _getPlansNetworkFirst() async {
    try {
      final data = await _remoteDataSource.fetchPlans();
      await _writePlansCache(data);
      return Success(data);
    } on AppException catch (e) {
      final fallback = await _readAnyPlansCache();
      if (fallback != null) {
        AppLogger.warning(
          'Network-first plans fetch failed, using cache fallback',
          category: 'subscription.cache',
          error: e,
        );
        return Success(fallback);
      }
      return Failure(mapExceptionToFailure(e));
    } catch (e) {
      final fallback = await _readAnyPlansCache();
      if (fallback != null) {
        AppLogger.warning(
          'Network-first plans fetch failed unexpectedly, using cache fallback',
          category: 'subscription.cache',
          error: e,
        );
        return Success(fallback);
      }
      return Failure(UnknownFailure(message: e.toString()));
    }
  }

  Future<Result<List<PlanEntity>>> _getPlansCacheOnly() async {
    final cached = await _readAnyPlansCache();
    if (cached != null) {
      return Success(cached);
    }
    return const Failure(CacheFailure(message: 'No cached plans available'));
  }

  Future<Result<List<PlanEntity>>> _getPlansNetworkOnly() async {
    try {
      final data = await _remoteDataSource.fetchPlans();
      await _writePlansCache(data);
      return Success(data);
    } on AppException catch (e) {
      return Failure(mapExceptionToFailure(e));
    } catch (e) {
      return Failure(UnknownFailure(message: e.toString()));
    }
  }

  Future<Result<List<PlanEntity>>> _getPlansStaleWhileRevalidate() async {
    final cached = await _readAnyPlansCache();
    if (cached != null) {
      unawaited(_refreshPlansInBackground());
      return Success(cached);
    }

    return _getPlansNetworkOnly();
  }

  List<PlanEntity>? _readFreshPlansMemory() {
    if (_cachedPlans == null || !_isMemoryCacheFresh(_cachedPlansAt)) {
      return null;
    }
    return _cachedPlans;
  }

  Future<List<PlanEntity>?> _readAnyPlansCache() async {
    final memoryFresh = _readFreshPlansMemory();
    if (memoryFresh != null) {
      return memoryFresh;
    }

    if (_cachedPlans != null) {
      return _cachedPlans;
    }

    try {
      final persisted = await _localDataSource?.getCachedPlans(
        allowExpired: true,
      );
      if (persisted != null) {
        _writePlansMemory(persisted);
      }
      return persisted;
    } catch (e) {
      AppLogger.debug('Failed to read any plans cache', error: e);
      return null;
    }
  }

  Future<List<PlanEntity>?> _readStalePlansFallback() async {
    if (_cachedPlans != null) {
      return _cachedPlans;
    }

    try {
      final persisted = await _localDataSource?.getCachedPlans(
        allowExpired: true,
      );
      if (persisted != null) {
        _writePlansMemory(persisted);
      }
      return persisted;
    } catch (e) {
      AppLogger.debug('Failed to read stale plans cache', error: e);
      return null;
    }
  }

  ({bool hit, SubscriptionEntity? value}) _readFreshSubscriptionMemory() {
    if (!_hasSubscriptionCache || !_isMemoryCacheFresh(_cachedSubscriptionAt)) {
      return (hit: false, value: null);
    }
    return (hit: true, value: _cachedSubscription);
  }

  Future<({bool hit, SubscriptionEntity? value})>
  _readFreshSubscriptionCache() async {
    try {
      final localDataSource = _localDataSource;
      if (localDataSource != null &&
          await localDataSource.hasSubscriptionCache()) {
        final persisted = await localDataSource.getCachedSubscription();
        return (hit: true, value: persisted);
      }
    } catch (e) {
      AppLogger.debug('Failed to read fresh subscription cache', error: e);
    }
    return (hit: false, value: null);
  }

  Future<({bool hit, SubscriptionEntity? value})>
  _readStaleSubscriptionFallback() async {
    if (_hasSubscriptionCache) {
      return (hit: true, value: _cachedSubscription);
    }

    try {
      final localDataSource = _localDataSource;
      if (localDataSource != null &&
          await localDataSource.hasSubscriptionCache(allowExpired: true)) {
        final persisted = await localDataSource.getCachedSubscription(
          allowExpired: true,
        );
        _writeSubscriptionMemory(persisted);
        return (hit: true, value: persisted);
      }
    } catch (e) {
      AppLogger.debug('Failed to read stale subscription cache', error: e);
    }

    return (hit: false, value: null);
  }

  Future<void> _writePlansCache(List<PlanEntity> plans) async {
    _writePlansMemory(plans);
    try {
      await _localDataSource?.cachePlans(plans);
    } catch (e) {
      AppLogger.debug('Persistent plan cache write failed', error: e);
    }
  }

  Future<void> _writeSubscriptionCache(SubscriptionEntity? subscription) async {
    _writeSubscriptionMemory(subscription);
    try {
      await _localDataSource?.cacheSubscription(subscription);
    } catch (e) {
      AppLogger.debug('Persistent subscription cache write failed', error: e);
    }
  }

  void _writePlansMemory(List<PlanEntity> plans) {
    _cachedPlans = plans;
    _cachedPlansAt = DateTime.now();
  }

  void _writeSubscriptionMemory(SubscriptionEntity? subscription) {
    _cachedSubscription = subscription;
    _hasSubscriptionCache = true;
    _cachedSubscriptionAt = DateTime.now();
  }

  Future<void> _refreshPlansInBackground() async {
    try {
      final data = await _remoteDataSource.fetchPlans();
      await _writePlansCache(data);
      AppLogger.debug(
        'Subscription plans cache revalidated',
        category: 'subscription.cache',
      );
    } catch (e) {
      AppLogger.debug(
        'Subscription plans revalidation failed',
        error: e,
        category: 'subscription.cache',
      );
    }
  }

  bool _isMemoryCacheFresh(DateTime? cachedAt) {
    if (cachedAt == null) return false;
    return DateTime.now().difference(cachedAt) < _memoryCacheTtl;
  }

  Future<void> _invalidateAllCaches() async {
    _cachedPlans = null;
    _cachedPlansAt = null;
    _cachedSubscription = null;
    _cachedSubscriptionAt = null;
    _hasSubscriptionCache = false;
    try {
      await _localDataSource?.clearCache();
    } catch (e) {
      AppLogger.debug(
        'Persistent cache clear failed',
        error: e,
        category: 'subscription.cache',
      );
    }
  }
}
