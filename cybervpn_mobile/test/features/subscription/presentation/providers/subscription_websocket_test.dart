import 'dart:async';

import 'package:cybervpn_mobile/core/data/cache_strategy.dart';
import 'package:cybervpn_mobile/core/network/websocket_client.dart';
import 'package:cybervpn_mobile/core/network/websocket_provider.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/plan_entity.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/subscription_entity.dart';
import 'package:cybervpn_mobile/features/subscription/domain/repositories/subscription_repository.dart';
import 'package:cybervpn_mobile/features/subscription/data/datasources/revenuecat_datasource.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/providers/subscription_provider.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/providers/subscription_state.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

// ---------------------------------------------------------------------------
// Mock SubscriptionRepository
// ---------------------------------------------------------------------------

class MockSubscriptionRepository implements SubscriptionRepository {
  SubscriptionEntity? _subscription;
  List<PlanEntity> _plans = [];
  int getActiveSubscriptionCallCount = 0;

  void seedSubscription(SubscriptionEntity? subscription) {
    _subscription = subscription;
  }

  void seedPlans(List<PlanEntity> plans) {
    _plans = List.from(plans);
  }

  @override
  Future<Result<SubscriptionEntity?>> getActiveSubscription() async {
    getActiveSubscriptionCallCount++;
    return Success(_subscription);
  }

  @override
  Future<Result<List<PlanEntity>>> getPlans({
    CacheStrategy strategy = CacheStrategy.cacheFirst,
  }) async {
    return Success(List.from(_plans));
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

// ---------------------------------------------------------------------------
// Mock RevenueCatDataSource
// ---------------------------------------------------------------------------

class MockRevenueCatDataSource implements RevenueCatDataSource {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

// ---------------------------------------------------------------------------
// Mock WebSocketClient
// ---------------------------------------------------------------------------

class MockWebSocketClient implements WebSocketClient {
  final StreamController<SubscriptionUpdated> _subscriptionController =
      StreamController<SubscriptionUpdated>.broadcast();

  @override
  Stream<SubscriptionUpdated> get subscriptionEvents =>
      _subscriptionController.stream;

  void emitSubscriptionUpdated(SubscriptionUpdated event) {
    _subscriptionController.add(event);
  }

  @override
  Future<void> dispose() async {
    await _subscriptionController.close();
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

// ---------------------------------------------------------------------------
// Test helpers
// ---------------------------------------------------------------------------

SubscriptionEntity _makeSubscription({
  required String id,
  SubscriptionStatus status = SubscriptionStatus.active,
}) {
  return SubscriptionEntity(
    id: id,
    planId: 'plan-1',
    userId: 'user-1',
    status: status,
    startDate: DateTime(2025, 1, 1),
    endDate: DateTime(2025, 12, 31),
    trafficUsedBytes: 1000000,
    trafficLimitBytes: 10000000,
    maxDevices: 5,
  );
}

PlanEntity _makePlan({
  required String id,
  String name = 'Test Plan',
  bool isTrial = false,
}) {
  return PlanEntity(
    id: id,
    name: name,
    description: 'Test plan description',
    price: 9.99,
    currency: 'USD',
    duration: PlanDuration.monthly,
    durationDays: 30,
    maxDevices: 5,
    trafficLimitGb: 100,
    isTrial: isTrial,
  );
}

/// Creates a [ProviderContainer] with all mocks wired up.
ProviderContainer createContainer({
  required MockSubscriptionRepository repo,
  required MockRevenueCatDataSource revenueCat,
  required MockWebSocketClient wsClient,
}) {
  return ProviderContainer(
    overrides: [
      subscriptionRepositoryProvider.overrideWithValue(repo),
      revenueCatDataSourceProvider.overrideWithValue(revenueCat),
      webSocketClientProvider.overrideWithValue(wsClient),
    ],
  );
}

/// Waits for the [subscriptionProvider] to finish loading.
Future<SubscriptionState> waitForState(ProviderContainer container) async {
  final sub = container.listen(subscriptionProvider, (_, _) {});
  await container.read(subscriptionProvider.future);
  sub.close();
  return container.read(subscriptionProvider).requireValue;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  group('SubscriptionProvider - WebSocket Integration', () {
    late MockSubscriptionRepository repo;
    late MockRevenueCatDataSource revenueCat;
    late MockWebSocketClient wsClient;
    late ProviderContainer container;

    setUp(() {
      repo = MockSubscriptionRepository();
      revenueCat = MockRevenueCatDataSource();
      wsClient = MockWebSocketClient();
    });

    tearDown(() {
      container.dispose();
    });

    test('subscription_updated event triggers subscription refresh', () async {
      // Seed initial subscription.
      final initialSubscription = _makeSubscription(
        id: 'sub-1',
        status: SubscriptionStatus.active,
      );
      repo.seedSubscription(initialSubscription);
      repo.seedPlans([_makePlan(id: 'plan-1')]);

      container = createContainer(
        repo: repo,
        revenueCat: revenueCat,
        wsClient: wsClient,
      );

      var state = await waitForState(container);
      expect(state.currentSubscription, isNotNull);
      expect(state.currentSubscription!.id, 'sub-1');
      expect(repo.getActiveSubscriptionCallCount, 1);

      // Update the repository's subscription (simulating backend change).
      final updatedSubscription = _makeSubscription(
        id: 'sub-2',
        status: SubscriptionStatus.active,
      );
      repo.seedSubscription(updatedSubscription);

      // Emit subscription_updated event.
      wsClient.emitSubscriptionUpdated(
        const SubscriptionUpdated(
          subscriptionId: 'sub-2',
          status: 'active',
        ),
      );

      // Give the stream a tick to process.
      await Future<void>.delayed(Duration.zero);

      // Verify subscription was refreshed from backend.
      state = container.read(subscriptionProvider).requireValue;
      expect(state.currentSubscription, isNotNull);
      expect(state.currentSubscription!.id, 'sub-2');
      expect(repo.getActiveSubscriptionCallCount, 2); // Called again
    });

    test('subscription_updated event with expired status refreshes state', () async {
      final activeSubscription = _makeSubscription(
        id: 'sub-1',
        status: SubscriptionStatus.active,
      );
      repo.seedSubscription(activeSubscription);
      repo.seedPlans([_makePlan(id: 'plan-1')]);

      container = createContainer(
        repo: repo,
        revenueCat: revenueCat,
        wsClient: wsClient,
      );

      await waitForState(container);

      // Update subscription to expired.
      final expiredSubscription = _makeSubscription(
        id: 'sub-1',
        status: SubscriptionStatus.expired,
      );
      repo.seedSubscription(expiredSubscription);

      // Emit subscription_updated event with expired status.
      wsClient.emitSubscriptionUpdated(
        const SubscriptionUpdated(
          subscriptionId: 'sub-1',
          status: 'expired',
        ),
      );

      await Future<void>.delayed(Duration.zero);

      final state = container.read(subscriptionProvider).requireValue;
      expect(state.currentSubscription!.status, SubscriptionStatus.expired);
    });

    test('subscription_updated event when subscription is null refreshes correctly', () async {
      // Start with no subscription.
      repo.seedSubscription(null);
      repo.seedPlans([_makePlan(id: 'plan-1', isTrial: true)]);

      container = createContainer(
        repo: repo,
        revenueCat: revenueCat,
        wsClient: wsClient,
      );

      var state = await waitForState(container);
      expect(state.currentSubscription, isNull);
      expect(state.trialEligibility, isTrue);

      // Add a subscription in the repo.
      final newSubscription = _makeSubscription(id: 'sub-1');
      repo.seedSubscription(newSubscription);

      // Emit subscription_updated event.
      wsClient.emitSubscriptionUpdated(
        const SubscriptionUpdated(
          subscriptionId: 'sub-1',
          status: 'active',
        ),
      );

      await Future<void>.delayed(Duration.zero);

      state = container.read(subscriptionProvider).requireValue;
      expect(state.currentSubscription, isNotNull);
      expect(state.currentSubscription!.id, 'sub-1');
      expect(state.trialEligibility, isFalse); // Now has subscription
    });
  });
}
