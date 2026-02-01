import 'package:cybervpn_mobile/core/errors/exceptions.dart';
import 'package:cybervpn_mobile/features/referral/data/datasources/referral_remote_ds.dart';
import 'package:cybervpn_mobile/features/referral/data/repositories/referral_repository_impl.dart';
import 'package:cybervpn_mobile/features/referral/domain/entities/referral.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockReferralRemoteDataSource extends Mock
    implements ReferralRemoteDataSource {}

void main() {
  late MockReferralRemoteDataSource mockDataSource;
  late ReferralRepositoryImpl repository;

  setUp(() {
    mockDataSource = MockReferralRemoteDataSource();
    repository = ReferralRepositoryImpl(remoteDataSource: mockDataSource);
  });

  // ---------------------------------------------------------------------------
  // isAvailable
  // ---------------------------------------------------------------------------

  group('isAvailable', () {
    test('delegates to data source and returns true on success', () async {
      when(() => mockDataSource.checkAvailability())
          .thenAnswer((_) async => true);

      final result = await repository.isAvailable();

      expect(result, isTrue);
      verify(() => mockDataSource.checkAvailability()).called(1);
    });

    test('delegates to data source and returns false on 404', () async {
      when(() => mockDataSource.checkAvailability())
          .thenAnswer((_) async => false);

      final result = await repository.isAvailable();

      expect(result, isFalse);
    });
  });

  // ---------------------------------------------------------------------------
  // getReferralCode
  // ---------------------------------------------------------------------------

  group('getReferralCode', () {
    test('returns empty string when feature is unavailable', () async {
      when(() => mockDataSource.checkAvailability())
          .thenAnswer((_) async => false);

      final result = await repository.getReferralCode();

      expect(result, isEmpty);
      verifyNever(() => mockDataSource.getReferralCode());
    });

    test('returns code from data source when available', () async {
      when(() => mockDataSource.checkAvailability())
          .thenAnswer((_) async => true);
      when(() => mockDataSource.getReferralCode())
          .thenAnswer((_) async => 'ABC123');

      final result = await repository.getReferralCode();

      expect(result, equals('ABC123'));
      verify(() => mockDataSource.getReferralCode()).called(1);
    });
  });

  // ---------------------------------------------------------------------------
  // getStats
  // ---------------------------------------------------------------------------

  group('getStats', () {
    test('returns empty stats when feature is unavailable', () async {
      when(() => mockDataSource.checkAvailability())
          .thenAnswer((_) async => false);

      final result = await repository.getStats();

      expect(result.totalInvited, equals(0));
      expect(result.paidUsers, equals(0));
      expect(result.pointsEarned, equals(0));
      expect(result.balance, equals(0));
      verifyNever(() => mockDataSource.getReferralStats());
    });

    test('returns stats from data source when available', () async {
      when(() => mockDataSource.checkAvailability())
          .thenAnswer((_) async => true);
      when(() => mockDataSource.getReferralStats()).thenAnswer(
        (_) async => const ReferralStats(
          totalInvited: 5,
          paidUsers: 2,
          pointsEarned: 150.0,
          balance: 75.0,
        ),
      );

      final result = await repository.getStats();

      expect(result.totalInvited, equals(5));
      expect(result.paidUsers, equals(2));
      expect(result.pointsEarned, equals(150.0));
      expect(result.balance, equals(75.0));
    });
  });

  // ---------------------------------------------------------------------------
  // getRecentReferrals
  // ---------------------------------------------------------------------------

  group('getRecentReferrals', () {
    test('returns empty list when feature is unavailable', () async {
      when(() => mockDataSource.checkAvailability())
          .thenAnswer((_) async => false);

      final result = await repository.getRecentReferrals();

      expect(result, isEmpty);
      verifyNever(() => mockDataSource.getRecentReferrals(limit: any(named: 'limit')));
    });

    test('returns entries from data source when available', () async {
      final entries = [
        ReferralEntry(
          code: 'REF1',
          joinDate: DateTime(2025, 1, 15),
          status: ReferralStatus.active,
        ),
        ReferralEntry(
          code: 'REF2',
          joinDate: DateTime(2025, 2, 20),
          status: ReferralStatus.completed,
        ),
      ];

      when(() => mockDataSource.checkAvailability())
          .thenAnswer((_) async => true);
      when(() => mockDataSource.getRecentReferrals(limit: 10))
          .thenAnswer((_) async => entries);

      final result = await repository.getRecentReferrals();

      expect(result, hasLength(2));
      expect(result[0].code, equals('REF1'));
      expect(result[1].status, equals(ReferralStatus.completed));
    });
  });
}
