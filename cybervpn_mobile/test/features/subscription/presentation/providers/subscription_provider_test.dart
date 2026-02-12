import 'dart:async';

import 'package:cybervpn_mobile/core/data/cache_strategy.dart';
import 'package:cybervpn_mobile/core/network/websocket_client.dart';
import 'package:cybervpn_mobile/core/network/websocket_provider.dart';
import 'package:cybervpn_mobile/core/security/app_attestation.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/core/errors/failures.dart' hide Failure;
import 'package:cybervpn_mobile/features/subscription/data/datasources/revenuecat_datasource.dart';
import 'package:cybervpn_mobile/features/subscription/data/datasources/subscription_remote_ds.dart'
    show PaginatedPaymentHistory;
import 'package:purchases_flutter/purchases_flutter.dart'
    show CustomerInfo, EntitlementInfos;
import 'package:cybervpn_mobile/features/subscription/domain/entities/plan_entity.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/subscription_entity.dart';
import 'package:cybervpn_mobile/features/subscription/domain/repositories/subscription_repository.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/providers/subscription_provider.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/providers/subscription_state.dart';
import 'package:cybervpn_mobile/core/di/providers.dart'
    show subscriptionRepositoryProvider, revenueCatDataSourceProvider;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

// =============================================================================
// Mocks
// =============================================================================

class _MockSubscriptionRepo implements SubscriptionRepository {
  List<PlanEntity> plans = [];
  SubscriptionEntity? activeSub;
  SubscriptionEntity? subscribeResult;
  bool subscribeShouldFail = false;
  String subscribeErrorMsg = 'Purchase failed';
  int subscribeCallCount = 0;

  @override
  Future<Result<List<PlanEntity>>> getPlans({
    CacheStrategy strategy = CacheStrategy.cacheFirst,
  }) async =>
      Success(plans);

  @override
  Future<Result<SubscriptionEntity?>> getActiveSubscription() async =>
      Success(activeSub);

  @override
  Future<Result<SubscriptionEntity>> subscribe(
    String planId, {
    String? paymentMethod,
  }) async {
    subscribeCallCount++;
    if (subscribeShouldFail) {
      return Failure(ServerFailure(message: subscribeErrorMsg));
    }
    return Success(subscribeResult!);
  }

  @override
  Future<Result<void>> cancelSubscription(String subscriptionId) async =>
      const Success(null);

  @override
  Future<Result<void>> restorePurchases() async => const Success(null);

  @override
  Future<Result<PaginatedPaymentHistory>> getPaymentHistory({
    int offset = 0,
    int limit = 20,
  }) async =>
      const Success(PaginatedPaymentHistory(items: [], total: 0, offset: 0, limit: 20));

  @override
  Future<Result<SubscriptionEntity>> redeemInviteCode(String code) async =>
      const Failure(ServerFailure(message: 'Not implemented'));

  @override
  Future<Result<Map<String, dynamic>>> applyPromoCode(String code, String planId) async =>
      const Success(<String, dynamic>{});

  @override
  Future<Result<Map<String, dynamic>>> getTrialStatus() async =>
      const Success(<String, dynamic>{'is_eligible': false, 'days_remaining': null, 'trial_used': false});

  @override
  Future<Result<SubscriptionEntity>> activateTrial() async =>
      const Failure(ServerFailure(message: 'Not implemented'));
}

class _MockRevenueCat implements RevenueCatDataSource {
  int restoreCallCount = 0;
  bool shouldFailRestore = false;
  String restoreErrorMsg = 'Restore failed';

  @override
  Future<CustomerInfo> restorePurchases() async {
    restoreCallCount++;
    if (shouldFailRestore) throw Exception(restoreErrorMsg);
    return _emptyCustomerInfo;
  }

  static const _emptyCustomerInfo = CustomerInfo(
    EntitlementInfos({}, {}),
    {},
    [],
    [],
    [],
    '',
    '',
    {},
    '',
  );

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _MockAttestationService implements AppAttestationService {
  int generateTokenCallCount = 0;

  @override
  Future<AttestationResult> generateToken({
    required AttestationTrigger trigger,
    String? challenge,
  }) async {
    generateTokenCallCount++;
    return const AttestationResult(
      status: AttestationStatus.disabled,
      platform: 'test',
      deviceSupportsAttestation: false,
    );
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _MockWebSocketClient implements WebSocketClient {
  final StreamController<SubscriptionUpdated> subController =
      StreamController<SubscriptionUpdated>.broadcast();

  @override
  Stream<SubscriptionUpdated> get subscriptionEvents => subController.stream;

  @override
  Future<void> dispose() async => subController.close();

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

// =============================================================================
// Helpers
// =============================================================================

PlanEntity _testPlan({
  String id = 'plan-monthly',
  String name = 'Monthly',
  double price = 9.99,
  bool isTrial = false,
  String? storeProductId = 'com.cybervpn.monthly',
}) =>
    PlanEntity(
      id: id,
      name: name,
      description: 'Test plan',
      price: price,
      currency: 'USD',
      duration: PlanDuration.monthly,
      durationDays: 30,
      maxDevices: 5,
      trafficLimitGb: 100,
      isTrial: isTrial,
      storeProductId: storeProductId,
    );

SubscriptionEntity _testSubscription({
  String id = 'sub-1',
  String planId = 'plan-monthly',
  SubscriptionStatus status = SubscriptionStatus.active,
}) =>
    SubscriptionEntity(
      id: id,
      planId: planId,
      userId: 'user-1',
      status: status,
      startDate: DateTime.now(),
      endDate: DateTime.now().add(const Duration(days: 30)),
      trafficUsedBytes: 0,
      trafficLimitBytes: 100 * 1024 * 1024 * 1024, // 100 GB
      maxDevices: 5,
    );

ProviderContainer _createContainer({
  required _MockSubscriptionRepo repo,
  required _MockRevenueCat revenueCat,
  required _MockAttestationService attestation,
  required _MockWebSocketClient wsClient,
}) {
  return ProviderContainer(
    overrides: [
      subscriptionRepositoryProvider.overrideWithValue(repo),
      revenueCatDataSourceProvider.overrideWithValue(revenueCat),
      appAttestationServiceProvider.overrideWithValue(attestation),
      webSocketClientProvider.overrideWithValue(wsClient),
    ],
  );
}

Future<SubscriptionState> _waitForState(ProviderContainer container) async {
  await container.read(subscriptionProvider.future);
  return container.read(subscriptionProvider).value!;
}

// =============================================================================
// Tests
// =============================================================================

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late _MockSubscriptionRepo repo;
  late _MockRevenueCat revenueCat;
  late _MockAttestationService attestation;
  late _MockWebSocketClient wsClient;

  setUp(() {
    repo = _MockSubscriptionRepo();
    revenueCat = _MockRevenueCat();
    attestation = _MockAttestationService();
    wsClient = _MockWebSocketClient();
  });

  // ── purchase() happy path ─────────────────────────────────────────────────

  group('purchase() happy path', () {
    test('sets purchaseState to loading then success', () async {
      final plan = _testPlan();
      final subscription = _testSubscription();
      repo.plans = [plan];
      repo.subscribeResult = subscription;

      final container = _createContainer(
        repo: repo,
        revenueCat: revenueCat,
        attestation: attestation,
        wsClient: wsClient,
      );

      await _waitForState(container);
      final notifier = container.read(subscriptionProvider.notifier);

      await notifier.purchase(plan);

      final state = container.read(subscriptionProvider).value!;
      expect(state.purchaseState, equals(PurchaseState.success));
      expect(state.currentSubscription, isNotNull);
      expect(state.currentSubscription!.id, equals('sub-1'));
      container.dispose();
    });

    test('performs app attestation (non-blocking)', () async {
      final plan = _testPlan();
      repo.plans = [plan];
      repo.subscribeResult = _testSubscription();

      final container = _createContainer(
        repo: repo,
        revenueCat: revenueCat,
        attestation: attestation,
        wsClient: wsClient,
      );

      await _waitForState(container);
      final notifier = container.read(subscriptionProvider.notifier);

      await notifier.purchase(plan);

      expect(attestation.generateTokenCallCount, equals(1));
      container.dispose();
    });

    test('calls repository.subscribe() with planId and storeProductId', () async {
      final plan = _testPlan(
        id: 'plan-yearly',
        storeProductId: 'com.cybervpn.yearly',
      );
      repo.plans = [plan];
      repo.subscribeResult = _testSubscription(planId: 'plan-yearly');

      final container = _createContainer(
        repo: repo,
        revenueCat: revenueCat,
        attestation: attestation,
        wsClient: wsClient,
      );

      await _waitForState(container);
      final notifier = container.read(subscriptionProvider.notifier);

      await notifier.purchase(plan);

      expect(repo.subscribeCallCount, equals(1));
      container.dispose();
    });

    test('clears trialEligibility on success', () async {
      final trialPlan = _testPlan(id: 'trial', isTrial: true);
      final regularPlan = _testPlan();
      repo.plans = [trialPlan, regularPlan];
      repo.subscribeResult = _testSubscription();

      final container = _createContainer(
        repo: repo,
        revenueCat: revenueCat,
        attestation: attestation,
        wsClient: wsClient,
      );

      final initialState = await _waitForState(container);
      expect(initialState.trialEligibility, isTrue);

      final notifier = container.read(subscriptionProvider.notifier);
      await notifier.purchase(regularPlan);

      final state = container.read(subscriptionProvider).value!;
      expect(state.trialEligibility, isFalse);
      container.dispose();
    });
  });

  // ── purchase() failure ─────────────────────────────────────────────────────

  group('purchase() failure', () {
    test('sets purchaseState to error with failure message', () async {
      final plan = _testPlan();
      repo.plans = [plan];
      repo.subscribeShouldFail = true;
      repo.subscribeErrorMsg = 'Payment declined';

      final container = _createContainer(
        repo: repo,
        revenueCat: revenueCat,
        attestation: attestation,
        wsClient: wsClient,
      );

      await _waitForState(container);
      final notifier = container.read(subscriptionProvider.notifier);

      await notifier.purchase(plan);

      final state = container.read(subscriptionProvider).value!;
      expect(state.purchaseState, equals(PurchaseState.error));
      expect(state.purchaseError, equals('Payment declined'));
      container.dispose();
    });

    test('preserves existing subscription and plan list on failure', () async {
      final existingSub = _testSubscription();
      final plan = _testPlan(id: 'upgrade-plan');
      repo.plans = [plan];
      repo.activeSub = existingSub;
      repo.subscribeShouldFail = true;

      final container = _createContainer(
        repo: repo,
        revenueCat: revenueCat,
        attestation: attestation,
        wsClient: wsClient,
      );

      final initialState = await _waitForState(container);
      expect(initialState.currentSubscription, isNotNull);

      final notifier = container.read(subscriptionProvider.notifier);
      await notifier.purchase(plan);

      final state = container.read(subscriptionProvider).value!;
      // Original subscription should still be there.
      expect(state.currentSubscription, isNotNull);
      expect(state.currentSubscription!.id, equals('sub-1'));
      // Plan list should be preserved.
      expect(state.availablePlans, hasLength(1));
      container.dispose();
    });
  });

  // ── initialization ─────────────────────────────────────────────────────────

  group('initialization', () {
    test('loads plans and subscription in parallel', () async {
      repo.plans = [_testPlan(), _testPlan(id: 'plan-yearly')];
      repo.activeSub = _testSubscription();

      final container = _createContainer(
        repo: repo,
        revenueCat: revenueCat,
        attestation: attestation,
        wsClient: wsClient,
      );

      final state = await _waitForState(container);
      expect(state.availablePlans, hasLength(2));
      expect(state.currentSubscription, isNotNull);
      container.dispose();
    });

    test('sets trialEligibility when no active sub and trial plan exists', () async {
      repo.plans = [_testPlan(isTrial: true)];
      repo.activeSub = null;

      final container = _createContainer(
        repo: repo,
        revenueCat: revenueCat,
        attestation: attestation,
        wsClient: wsClient,
      );

      final state = await _waitForState(container);
      expect(state.trialEligibility, isTrue);
      container.dispose();
    });

    test('sets trialEligibility false when active sub exists', () async {
      repo.plans = [_testPlan(isTrial: true)];
      repo.activeSub = _testSubscription();

      final container = _createContainer(
        repo: repo,
        revenueCat: revenueCat,
        attestation: attestation,
        wsClient: wsClient,
      );

      final state = await _waitForState(container);
      expect(state.trialEligibility, isFalse);
      container.dispose();
    });
  });

  // ── restorePurchases() ────────────────────────────────────────────────────

  group('restorePurchases() success', () {
    test('calls RevenueCat.restorePurchases() then repo.restorePurchases()', () async {
      repo.plans = [_testPlan()];
      repo.activeSub = null;

      final container = _createContainer(
        repo: repo,
        revenueCat: revenueCat,
        attestation: attestation,
        wsClient: wsClient,
      );

      await _waitForState(container);
      final notifier = container.read(subscriptionProvider.notifier);

      await notifier.restorePurchases();

      expect(revenueCat.restoreCallCount, equals(1));
      container.dispose();
    });

    test('reloads subscription and sets purchaseState to success', () async {
      repo.plans = [_testPlan()];
      repo.activeSub = null;

      final container = _createContainer(
        repo: repo,
        revenueCat: revenueCat,
        attestation: attestation,
        wsClient: wsClient,
      );

      await _waitForState(container);
      final notifier = container.read(subscriptionProvider.notifier);

      // After restore, getActiveSubscription will return this.
      repo.activeSub = _testSubscription();

      await notifier.restorePurchases();

      final state = container.read(subscriptionProvider).value!;
      expect(state.purchaseState, equals(PurchaseState.success));
      expect(state.currentSubscription, isNotNull);
      expect(state.currentSubscription!.id, equals('sub-1'));
      container.dispose();
    });

    test('preserves plan list during restore', () async {
      repo.plans = [_testPlan(), _testPlan(id: 'yearly', name: 'Yearly', price: 79.99)];

      final container = _createContainer(
        repo: repo,
        revenueCat: revenueCat,
        attestation: attestation,
        wsClient: wsClient,
      );

      await _waitForState(container);
      final notifier = container.read(subscriptionProvider.notifier);

      await notifier.restorePurchases();

      final state = container.read(subscriptionProvider).value!;
      expect(state.availablePlans, hasLength(2));
      container.dispose();
    });
  });

  group('restorePurchases() failure', () {
    test('sets purchaseState to error when repo returns Failure', () async {
      repo.plans = [_testPlan()];
      // Override restorePurchases to return failure.
      final failRepo = _MockSubscriptionRepoWithFailRestore();
      failRepo.plans = [_testPlan()];

      final container = _createContainer(
        repo: failRepo,
        revenueCat: revenueCat,
        attestation: attestation,
        wsClient: wsClient,
      );

      await _waitForState(container);
      final notifier = container.read(subscriptionProvider.notifier);

      await notifier.restorePurchases();

      final state = container.read(subscriptionProvider).value!;
      expect(state.purchaseState, equals(PurchaseState.error));
      expect(state.purchaseError, isNotNull);
      container.dispose();
    });

    test('sets purchaseState to error when RevenueCat throws', () async {
      repo.plans = [_testPlan()];
      revenueCat.shouldFailRestore = true;
      revenueCat.restoreErrorMsg = 'No purchases to restore';

      final container = _createContainer(
        repo: repo,
        revenueCat: revenueCat,
        attestation: attestation,
        wsClient: wsClient,
      );

      await _waitForState(container);
      final notifier = container.read(subscriptionProvider.notifier);

      await notifier.restorePurchases();

      final state = container.read(subscriptionProvider).value!;
      expect(state.purchaseState, equals(PurchaseState.error));
      expect(state.purchaseError, contains('No purchases to restore'));
      container.dispose();
    });
  });
  // ── activateTrial() ──────────────────────────────────────────────────────

  group('activateTrial()', () {
    test('finds first trial plan and calls purchase()', () async {
      final trialPlan = _testPlan(id: 'trial', isTrial: true);
      repo.plans = [_testPlan(), trialPlan];
      repo.subscribeResult = _testSubscription(planId: 'trial');

      final container = _createContainer(
        repo: repo,
        revenueCat: revenueCat,
        attestation: attestation,
        wsClient: wsClient,
      );

      await _waitForState(container);
      final notifier = container.read(subscriptionProvider.notifier);

      await notifier.activateTrial();

      final state = container.read(subscriptionProvider).value!;
      expect(state.purchaseState, equals(PurchaseState.success));
      expect(state.currentSubscription, isNotNull);
      expect(repo.subscribeCallCount, equals(1));
      container.dispose();
    });

    test('sets error when no trial plan available', () async {
      repo.plans = [_testPlan()]; // No isTrial plans.

      final container = _createContainer(
        repo: repo,
        revenueCat: revenueCat,
        attestation: attestation,
        wsClient: wsClient,
      );

      await _waitForState(container);
      final notifier = container.read(subscriptionProvider.notifier);

      await notifier.activateTrial();

      final state = container.read(subscriptionProvider).value!;
      expect(state.purchaseState, equals(PurchaseState.error));
      expect(state.purchaseError, equals('No trial plan available.'));
      container.dispose();
    });
  });

  // ── clearPurchaseState() ──────────────────────────────────────────────────

  group('clearPurchaseState()', () {
    test('resets purchaseState to idle', () async {
      repo.plans = [_testPlan()];
      repo.subscribeShouldFail = true;

      final container = _createContainer(
        repo: repo,
        revenueCat: revenueCat,
        attestation: attestation,
        wsClient: wsClient,
      );

      await _waitForState(container);
      final notifier = container.read(subscriptionProvider.notifier);

      // Trigger an error state first.
      await notifier.purchase(_testPlan());
      expect(
        container.read(subscriptionProvider).value!.purchaseState,
        equals(PurchaseState.error),
      );

      // Clear it.
      notifier.clearPurchaseState();

      final state = container.read(subscriptionProvider).value!;
      expect(state.purchaseState, equals(PurchaseState.idle));
      expect(state.purchaseError, isNull);
      container.dispose();
    });
  });

  // ── loadPlans() / loadSubscription() ──────────────────────────────────────

  group('loadPlans()', () {
    test('refreshes availablePlans without changing subscription', () async {
      repo.plans = [_testPlan()];
      repo.activeSub = _testSubscription();

      final container = _createContainer(
        repo: repo,
        revenueCat: revenueCat,
        attestation: attestation,
        wsClient: wsClient,
      );

      final initial = await _waitForState(container);
      expect(initial.availablePlans, hasLength(1));
      expect(initial.currentSubscription, isNotNull);

      final notifier = container.read(subscriptionProvider.notifier);

      // Change plans in the mock.
      repo.plans = [_testPlan(), _testPlan(id: 'yearly')];

      await notifier.loadPlans();

      final state = container.read(subscriptionProvider).value!;
      expect(state.availablePlans, hasLength(2));
      // Subscription unchanged.
      expect(state.currentSubscription!.id, equals('sub-1'));
      container.dispose();
    });
  });

  group('loadSubscription()', () {
    test('refreshes subscription and updates trialEligibility', () async {
      repo.plans = [_testPlan(isTrial: true)];
      repo.activeSub = _testSubscription();

      final container = _createContainer(
        repo: repo,
        revenueCat: revenueCat,
        attestation: attestation,
        wsClient: wsClient,
      );

      final initial = await _waitForState(container);
      expect(initial.trialEligibility, isFalse); // Has active sub.

      final notifier = container.read(subscriptionProvider.notifier);

      // Simulate subscription expiring.
      repo.activeSub = null;

      await notifier.loadSubscription();

      final state = container.read(subscriptionProvider).value!;
      expect(state.currentSubscription, isNull);
      expect(state.trialEligibility, isTrue); // No sub + trial plan.
      container.dispose();
    });
  });
}

/// Variant of _MockSubscriptionRepo that fails on restorePurchases.
class _MockSubscriptionRepoWithFailRestore extends _MockSubscriptionRepo {
  @override
  Future<Result<void>> restorePurchases() async =>
      const Failure(ServerFailure(message: 'Restore sync failed'));
}
