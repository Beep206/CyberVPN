import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:cybervpn_mobile/core/storage/local_storage.dart';
import 'package:cybervpn_mobile/features/subscription/data/datasources/subscription_local_ds.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/plan_entity.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/subscription_entity.dart';

PlanEntity _testPlan() => const PlanEntity(
  id: 'plan-1',
  name: 'Test Plan',
  description: 'desc',
  price: 9.99,
  currency: 'USD',
  duration: PlanDuration.monthly,
  durationDays: 30,
  maxDevices: 5,
  trafficLimitGb: 100,
);

SubscriptionEntity _testSubscription() => SubscriptionEntity(
  id: 'sub-1',
  planId: 'plan-1',
  userId: 'user-1',
  status: SubscriptionStatus.active,
  startDate: DateTime.utc(2026, 1, 1),
  endDate: DateTime.utc(2026, 2, 1),
  trafficUsedBytes: 0,
  trafficLimitBytes: 100,
  maxDevices: 5,
);

void main() {
  late SharedPreferences prefs;
  late SubscriptionLocalDataSourceImpl dataSource;

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    prefs = await SharedPreferences.getInstance();
    dataSource = SubscriptionLocalDataSourceImpl(
      LocalStorageWrapper(prefs: prefs),
    );
  });

  test('returns fresh cached plans', () async {
    await dataSource.cachePlans([_testPlan()]);

    final result = await dataSource.getCachedPlans();

    expect(result, hasLength(1));
    expect(result?.first.id, 'plan-1');
  });

  test('returns expired plans only when allowExpired is true', () async {
    await dataSource.cachePlans([_testPlan()]);
    await prefs.setString(
      'plans_cache_timestamp',
      DateTime.now().subtract(const Duration(hours: 2)).toIso8601String(),
    );

    expect(await dataSource.getCachedPlans(), isNull);
    expect(await dataSource.getCachedPlans(allowExpired: true), hasLength(1));
  });

  test('returns expired subscription only when allowExpired is true', () async {
    await dataSource.cacheSubscription(_testSubscription());
    await prefs.setString(
      'subscription_cache_timestamp',
      DateTime.now().subtract(const Duration(hours: 2)).toIso8601String(),
    );

    expect(await dataSource.hasSubscriptionCache(), isFalse);
    expect(await dataSource.hasSubscriptionCache(allowExpired: true), isTrue);
    expect(await dataSource.getCachedSubscription(), isNull);
    expect(
      await dataSource.getCachedSubscription(allowExpired: true),
      isNotNull,
    );
  });

  test('cache version mismatch clears legacy cache entries', () async {
    await prefs.setInt('subscription_cache_version', 1);
    await prefs.setString('cached_plans', '[{"id":"legacy"}]');

    final result = await dataSource.getCachedPlans(allowExpired: true);

    expect(result, isNull);
    expect(prefs.getInt('subscription_cache_version'), 2);
    expect(prefs.getString('cached_plans'), isNull);
  });
}
