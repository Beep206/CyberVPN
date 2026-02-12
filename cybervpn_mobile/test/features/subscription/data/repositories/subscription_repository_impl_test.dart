import 'package:cybervpn_mobile/core/data/cache_strategy.dart';
import 'package:cybervpn_mobile/core/errors/exceptions.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/subscription/data/datasources/subscription_local_ds.dart';
import 'package:cybervpn_mobile/features/subscription/data/datasources/subscription_remote_ds.dart';
import 'package:cybervpn_mobile/features/subscription/data/repositories/subscription_repository_impl.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/plan_entity.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/subscription_entity.dart';
import 'package:flutter_test/flutter_test.dart';

// =============================================================================
// Mocks
// =============================================================================

class _MockRemoteDataSource implements SubscriptionRemoteDataSource {
  List<PlanEntity> plans = [];
  SubscriptionEntity? activeSub;
  SubscriptionEntity? createResult;
  int fetchPlansCallCount = 0;
  int fetchSubCallCount = 0;
  bool shouldFail = false;
  String errorMsg = 'Server error';

  @override
  Future<List<PlanEntity>> fetchPlans() async {
    fetchPlansCallCount++;
    if (shouldFail) throw ServerException(message: errorMsg);
    return plans;
  }

  @override
  Future<SubscriptionEntity?> fetchActiveSubscription() async {
    fetchSubCallCount++;
    if (shouldFail) throw ServerException(message: errorMsg);
    return activeSub;
  }

  @override
  Future<SubscriptionEntity> createSubscription(
    String planId, {
    String? paymentMethod,
  }) async {
    if (shouldFail) throw ServerException(message: errorMsg);
    return createResult!;
  }

  @override
  Future<void> cancelSubscription(String subscriptionId) async {
    if (shouldFail) throw ServerException(message: errorMsg);
  }
}

class _MockLocalDataSource implements SubscriptionLocalDataSource {
  List<PlanEntity>? cachedPlans;
  SubscriptionEntity? cachedSubscription;
  bool _hasSubCache = false;
  int cachePlansCallCount = 0;
  int getCachedPlansCallCount = 0;
  int cacheSubCallCount = 0;
  int getCachedSubCallCount = 0;
  int clearCacheCallCount = 0;

  @override
  Future<void> cachePlans(List<PlanEntity> plans) async {
    cachePlansCallCount++;
    cachedPlans = plans;
  }

  @override
  Future<List<PlanEntity>?> getCachedPlans() async {
    getCachedPlansCallCount++;
    return cachedPlans;
  }

  @override
  Future<void> cacheSubscription(SubscriptionEntity? subscription) async {
    cacheSubCallCount++;
    cachedSubscription = subscription;
    _hasSubCache = true;
  }

  @override
  Future<SubscriptionEntity?> getCachedSubscription() async {
    getCachedSubCallCount++;
    return cachedSubscription;
  }

  @override
  Future<bool> hasSubscriptionCache() async => _hasSubCache;

  @override
  Future<void> clearCache() async {
    clearCacheCallCount++;
    cachedPlans = null;
    cachedSubscription = null;
    _hasSubCache = false;
  }
}

// =============================================================================
// Helpers
// =============================================================================

PlanEntity _testPlan({String id = 'plan-1', double price = 9.99}) => PlanEntity(
      id: id,
      name: 'Test Plan',
      description: 'Test',
      price: price,
      currency: 'USD',
      duration: PlanDuration.monthly,
      durationDays: 30,
      maxDevices: 5,
      trafficLimitGb: 100,
    );

SubscriptionEntity _testSub({
  String id = 'sub-1',
  SubscriptionStatus status = SubscriptionStatus.active,
}) =>
    SubscriptionEntity(
      id: id,
      planId: 'plan-1',
      userId: 'user-1',
      status: status,
      startDate: DateTime.now(),
      endDate: DateTime.now().add(const Duration(days: 30)),
      trafficUsedBytes: 0,
      trafficLimitBytes: 100 * 1024 * 1024 * 1024,
      maxDevices: 5,
    );

// =============================================================================
// Tests
// =============================================================================

void main() {
  late _MockRemoteDataSource ds;
  late SubscriptionRepositoryImpl repo;

  setUp(() {
    ds = _MockRemoteDataSource();
    repo = SubscriptionRepositoryImpl(remoteDataSource: ds);
  });

  // ── getPlans caching ──────────────────────────────────────────────────────

  group('getPlans()', () {
    test('cacheFirst returns cached on 2nd call', () async {
      ds.plans = [_testPlan()];

      final first = await repo.getPlans();
      expect((first as Success).data, hasLength(1));
      expect(ds.fetchPlansCallCount, equals(1));

      // Second call should use cache.
      final second = await repo.getPlans();
      expect((second as Success).data, hasLength(1));
      expect(ds.fetchPlansCallCount, equals(1)); // NOT increased.
    });

    test('networkOnly always fetches from network', () async {
      ds.plans = [_testPlan()];

      await repo.getPlans(); // populate cache
      expect(ds.fetchPlansCallCount, equals(1));

      await repo.getPlans(strategy: CacheStrategy.networkOnly);
      expect(ds.fetchPlansCallCount, equals(2));
    });

    test('returns Failure on exception', () async {
      ds.shouldFail = true;
      final result = await repo.getPlans();
      expect(result, isA<Failure<List<PlanEntity>>>());
    });
  });

  // ── getActiveSubscription caching ─────────────────────────────────────────

  group('getActiveSubscription()', () {
    test('caches nullable result with _hasSubscriptionCache flag', () async {
      ds.activeSub = null; // No active subscription.

      final first = await repo.getActiveSubscription();
      expect((first as Success).data, isNull);
      expect(ds.fetchSubCallCount, equals(1));

      // Second call should use cache even though value is null.
      final second = await repo.getActiveSubscription();
      expect((second as Success).data, isNull);
      expect(ds.fetchSubCallCount, equals(1)); // NOT increased.
    });

    test('caches non-null subscription', () async {
      ds.activeSub = _testSub();

      final first = await repo.getActiveSubscription();
      expect((first as Success).data, isNotNull);
      expect(ds.fetchSubCallCount, equals(1));

      final second = await repo.getActiveSubscription();
      expect((second as Success<SubscriptionEntity?>).data!.id, equals('sub-1'));
      expect(ds.fetchSubCallCount, equals(1));
    });
  });

  // ── subscribe invalidates cache ───────────────────────────────────────────

  group('subscribe()', () {
    test('invalidates subscription cache on success', () async {
      ds.activeSub = _testSub();
      ds.createResult = _testSub(id: 'sub-2');

      // Populate cache.
      await repo.getActiveSubscription();
      expect(ds.fetchSubCallCount, equals(1));

      // Subscribe invalidates cache.
      final result = await repo.subscribe('plan-1');
      expect(result, isA<Success<SubscriptionEntity>>());

      // Next getActiveSubscription should hit network again.
      await repo.getActiveSubscription();
      expect(ds.fetchSubCallCount, equals(2));
    });

    test('returns Failure on exception', () async {
      ds.shouldFail = true;
      final result = await repo.subscribe('plan-1');
      expect(result, isA<Failure<SubscriptionEntity>>());
    });
  });

  // ── cancelSubscription invalidates cache ──────────────────────────────────

  group('cancelSubscription()', () {
    test('invalidates subscription cache on success', () async {
      ds.activeSub = _testSub();

      // Populate cache.
      await repo.getActiveSubscription();
      expect(ds.fetchSubCallCount, equals(1));

      // Cancel invalidates cache.
      final result = await repo.cancelSubscription('sub-1');
      expect(result, isA<Success<void>>());

      // Next getActiveSubscription should hit network.
      await repo.getActiveSubscription();
      expect(ds.fetchSubCallCount, equals(2));
    });
  });

  // ── restorePurchases placeholder ──────────────────────────────────────────

  group('restorePurchases()', () {
    test('returns Success (placeholder)', () async {
      final result = await repo.restorePurchases();
      expect(result, isA<Success<void>>());
    });
  });

  // ── persistent cache integration ────────────────────────────────────────

  group('persistent cache', () {
    late _MockLocalDataSource localDs;
    late SubscriptionRepositoryImpl repoWithLocal;

    setUp(() {
      localDs = _MockLocalDataSource();
      repoWithLocal = SubscriptionRepositoryImpl(
        remoteDataSource: ds,
        localDataSource: localDs,
      );
    });

    test('getPlans writes to persistent cache on network fetch', () async {
      ds.plans = [_testPlan()];

      await repoWithLocal.getPlans();

      expect(localDs.cachePlansCallCount, equals(1));
      expect(localDs.cachedPlans, hasLength(1));
    });

    test('getPlans reads from persistent cache on new repo instance', () async {
      // Simulate persisted cache from a prior session.
      localDs.cachedPlans = [_testPlan()];

      final result = await repoWithLocal.getPlans();

      expect((result as Success).data, hasLength(1));
      // Network was NOT called because persistent cache returned data.
      expect(ds.fetchPlansCallCount, equals(0));
      expect(localDs.getCachedPlansCallCount, equals(1));
    });

    test('getActiveSubscription writes to persistent cache', () async {
      ds.activeSub = _testSub();

      await repoWithLocal.getActiveSubscription();

      expect(localDs.cacheSubCallCount, equals(1));
      expect(localDs.cachedSubscription, isNotNull);
    });

    test('getActiveSubscription reads from persistent cache on new instance', () async {
      // Simulate persisted cache.
      localDs.cachedSubscription = _testSub(id: 'persisted-sub');
      localDs._hasSubCache = true;

      final result = await repoWithLocal.getActiveSubscription();

      expect((result as Success<SubscriptionEntity?>).data!.id, equals('persisted-sub'));
      // Network was NOT called.
      expect(ds.fetchSubCallCount, equals(0));
    });

    test('subscribe clears persistent cache', () async {
      ds.createResult = _testSub(id: 'sub-new');
      localDs._hasSubCache = true;

      await repoWithLocal.subscribe('plan-1');

      expect(localDs.clearCacheCallCount, equals(1));
    });

    test('cancelSubscription clears persistent cache', () async {
      localDs._hasSubCache = true;

      await repoWithLocal.cancelSubscription('sub-1');

      expect(localDs.clearCacheCallCount, equals(1));
    });
  });
}
