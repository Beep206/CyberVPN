import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/referral/domain/entities/referral.dart';
import 'package:cybervpn_mobile/features/referral/domain/repositories/referral_repository.dart';
import 'package:cybervpn_mobile/features/referral/presentation/providers/referral_provider.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

class MockReferralRepository extends Mock implements ReferralRepository {}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/// Creates a [ProviderContainer] with a mocked [ReferralRepository].
ProviderContainer createContainer(MockReferralRepository mockRepo) {
  final container = ProviderContainer(
    overrides: [
      referralRepositoryProvider.overrideWithValue(mockRepo),
    ],
  );
  addTearDown(container.dispose);
  return container;
}

const _emptyStats = ReferralStats(
  totalInvited: 0,
  paidUsers: 0,
  pointsEarned: 0,
  balance: 0,
);

const _sampleStats = ReferralStats(
  totalInvited: 10,
  paidUsers: 3,
  pointsEarned: 250.0,
  balance: 120.5,
);

final _sampleReferrals = [
  ReferralEntry(
    code: 'REF001',
    joinDate: DateTime(2025, 6, 1),
    status: ReferralStatus.active,
  ),
  ReferralEntry(
    code: 'REF002',
    joinDate: DateTime(2025, 7, 15),
    status: ReferralStatus.completed,
  ),
];

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  late MockReferralRepository mockRepo;

  setUp(() {
    mockRepo = MockReferralRepository();
  });

  // ---- ReferralState -------------------------------------------------------

  group('ReferralState', () {
    test('default constructor has isAvailable=false and empty data', () {
      const state = ReferralState();

      expect(state.isAvailable, isFalse);
      expect(state.referralCode, isNull);
      expect(state.stats, isNull);
      expect(state.recentReferrals, isEmpty);
    });

    test('copyWith updates specified fields', () {
      const original = ReferralState(
        isAvailable: true,
        referralCode: 'ABC',
        stats: _sampleStats,
      );

      final copied = original.copyWith(
        referralCode: () => 'XYZ',
        recentReferrals: _sampleReferrals,
      );

      expect(copied.isAvailable, isTrue);
      expect(copied.referralCode, equals('XYZ'));
      expect(copied.stats, equals(_sampleStats));
      expect(copied.recentReferrals, hasLength(2));
    });

    test('equality works correctly', () {
      const a = ReferralState(isAvailable: true, referralCode: 'A');
      const b = ReferralState(isAvailable: true, referralCode: 'A');
      const c = ReferralState(isAvailable: false, referralCode: 'A');

      expect(a, equals(b));
      expect(a, isNot(equals(c)));
    });
  });

  // ---- ReferralNotifier build (unavailable) --------------------------------

  group('ReferralNotifier build - unavailable', () {
    test('returns state with isAvailable=false when backend unavailable',
        () async {
      when(() => mockRepo.isAvailable()).thenAnswer((_) async => const Success(false));

      final container = createContainer(mockRepo);

      // Wait for the async build to complete.
      final state = await container.read(referralProvider.future);

      expect(state.isAvailable, isFalse);
      expect(state.referralCode, isNull);
      expect(state.stats, isNull);
      expect(state.recentReferrals, isEmpty);

      verify(() => mockRepo.isAvailable()).called(1);
      verifyNever(() => mockRepo.getReferralCode());
      verifyNever(() => mockRepo.getStats());
      verifyNever(() => mockRepo.getRecentReferrals());
    });
  });

  // ---- ReferralNotifier build (available) ----------------------------------

  group('ReferralNotifier build - available', () {
    test('loads code, stats, and recent referrals when available', () async {
      when(() => mockRepo.isAvailable()).thenAnswer((_) async => const Success(true));
      when(() => mockRepo.getReferralCode())
          .thenAnswer((_) async => const Success('CYBER123'));
      when(() => mockRepo.getStats()).thenAnswer((_) async => const Success(_sampleStats));
      when(() => mockRepo.getRecentReferrals())
          .thenAnswer((_) async => Success(_sampleReferrals));

      final container = createContainer(mockRepo);
      final state = await container.read(referralProvider.future);

      expect(state.isAvailable, isTrue);
      expect(state.referralCode, equals('CYBER123'));
      expect(state.stats, equals(_sampleStats));
      expect(state.recentReferrals, hasLength(2));
    });

    test('sets referralCode to null when code is empty string', () async {
      when(() => mockRepo.isAvailable()).thenAnswer((_) async => const Success(true));
      when(() => mockRepo.getReferralCode()).thenAnswer((_) async => const Success(''));
      when(() => mockRepo.getStats()).thenAnswer((_) async => const Success(_emptyStats));
      when(() => mockRepo.getRecentReferrals())
          .thenAnswer((_) async => const Success(<ReferralEntry>[]));

      final container = createContainer(mockRepo);
      final state = await container.read(referralProvider.future);

      expect(state.isAvailable, isTrue);
      expect(state.referralCode, isNull);
    });
  });

  // ---- checkAvailability ---------------------------------------------------

  group('checkAvailability', () {
    test('transitions to unavailable state', () async {
      // Build initially as available.
      when(() => mockRepo.isAvailable()).thenAnswer((_) async => const Success(true));
      when(() => mockRepo.getReferralCode())
          .thenAnswer((_) async => const Success('CODE1'));
      when(() => mockRepo.getStats()).thenAnswer((_) async => const Success(_sampleStats));
      when(() => mockRepo.getRecentReferrals())
          .thenAnswer((_) async => Success(_sampleReferrals));

      final container = createContainer(mockRepo);
      await container.read(referralProvider.future);

      // Now backend becomes unavailable.
      when(() => mockRepo.isAvailable()).thenAnswer((_) async => const Success(false));

      await container.read(referralProvider.notifier).checkAvailability();
      final state = container.read(referralProvider).value;

      expect(state?.isAvailable, isFalse);
      expect(state?.referralCode, isNull);
      expect(state?.stats, isNull);
      expect(state?.recentReferrals, isEmpty);
    });
  });

  // ---- refreshStats --------------------------------------------------------

  group('refreshStats', () {
    test('updates stats and referrals when available', () async {
      when(() => mockRepo.isAvailable()).thenAnswer((_) async => const Success(true));
      when(() => mockRepo.getReferralCode())
          .thenAnswer((_) async => const Success('CODE1'));
      when(() => mockRepo.getStats()).thenAnswer((_) async => const Success(_emptyStats));
      when(() => mockRepo.getRecentReferrals())
          .thenAnswer((_) async => const Success(<ReferralEntry>[]));

      final container = createContainer(mockRepo);
      await container.read(referralProvider.future);

      // Setup new data for refresh.
      when(() => mockRepo.getStats()).thenAnswer((_) async => const Success(_sampleStats));
      when(() => mockRepo.getRecentReferrals())
          .thenAnswer((_) async => Success(_sampleReferrals));

      await container.read(referralProvider.notifier).refreshStats();
      final state = container.read(referralProvider).value;

      expect(state?.stats, equals(_sampleStats));
      expect(state?.recentReferrals, hasLength(2));
    });

    test('is a no-op when feature is unavailable', () async {
      when(() => mockRepo.isAvailable()).thenAnswer((_) async => const Success(false));

      final container = createContainer(mockRepo);
      await container.read(referralProvider.future);

      // Clear interaction counts.
      clearInteractions(mockRepo);

      await container.read(referralProvider.notifier).refreshStats();

      verifyNever(() => mockRepo.getStats());
      verifyNever(() => mockRepo.getRecentReferrals());
    });
  });

  // ---- shareReferralCode ---------------------------------------------------

  group('shareReferralCode', () {
    test('calls repository shareReferral with code', () async {
      when(() => mockRepo.isAvailable()).thenAnswer((_) async => const Success(true));
      when(() => mockRepo.getReferralCode())
          .thenAnswer((_) async => const Success('SHARE_ME'));
      when(() => mockRepo.getStats()).thenAnswer((_) async => const Success(_sampleStats));
      when(() => mockRepo.getRecentReferrals())
          .thenAnswer((_) async => const Success(<ReferralEntry>[]));
      when(() => mockRepo.shareReferral(any()))
          .thenAnswer((_) async => const Success<void>(null));

      final container = createContainer(mockRepo);
      await container.read(referralProvider.future);

      await container.read(referralProvider.notifier).shareReferralCode();

      verify(() => mockRepo.shareReferral('SHARE_ME')).called(1);
    });

    test('is a no-op when referral code is null', () async {
      when(() => mockRepo.isAvailable()).thenAnswer((_) async => const Success(true));
      when(() => mockRepo.getReferralCode()).thenAnswer((_) async => const Success(''));
      when(() => mockRepo.getStats()).thenAnswer((_) async => const Success(_emptyStats));
      when(() => mockRepo.getRecentReferrals())
          .thenAnswer((_) async => const Success(<ReferralEntry>[]));

      final container = createContainer(mockRepo);
      await container.read(referralProvider.future);

      await container.read(referralProvider.notifier).shareReferralCode();

      verifyNever(() => mockRepo.shareReferral(any()));
    });
  });

  // ---- Derived providers ---------------------------------------------------

  group('isReferralAvailableProvider', () {
    test('returns true when referral feature is available', () async {
      when(() => mockRepo.isAvailable()).thenAnswer((_) async => const Success(true));
      when(() => mockRepo.getReferralCode())
          .thenAnswer((_) async => const Success('CODE'));
      when(() => mockRepo.getStats()).thenAnswer((_) async => const Success(_sampleStats));
      when(() => mockRepo.getRecentReferrals())
          .thenAnswer((_) async => const Success(<ReferralEntry>[]));

      final container = createContainer(mockRepo);
      await container.read(referralProvider.future);

      final available = container.read(isReferralAvailableProvider);
      expect(available, isTrue);
    });

    test('returns false when referral feature is unavailable', () async {
      when(() => mockRepo.isAvailable()).thenAnswer((_) async => const Success(false));

      final container = createContainer(mockRepo);
      await container.read(referralProvider.future);

      final available = container.read(isReferralAvailableProvider);
      expect(available, isFalse);
    });
  });
}
