import 'package:cybervpn_mobile/core/errors/exceptions.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
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
    test('delegates to data source and returns Success(true) on success', () async {
      when(() => mockDataSource.checkAvailability())
          .thenAnswer((_) async => true);

      final result = await repository.isAvailable();

      expect(result, isA<Success<bool>>());
      expect((result as Success<bool>).data, isTrue);
      verify(() => mockDataSource.checkAvailability()).called(1);
    });

    test('delegates to data source and returns Success(false) on 404', () async {
      when(() => mockDataSource.checkAvailability())
          .thenAnswer((_) async => false);

      final result = await repository.isAvailable();

      expect(result, isA<Success<bool>>());
      expect((result as Success<bool>).data, isFalse);
    });

    test('returns Failure on AppException', () async {
      when(() => mockDataSource.checkAvailability())
          .thenThrow(const ServerException(message: 'Server error'));

      final result = await repository.isAvailable();

      expect(result, isA<Failure<bool>>());
    });

    test('caches result and reuses within TTL window', () async {
      when(() => mockDataSource.checkAvailability())
          .thenAnswer((_) async => true);

      // First call hits network.
      await repository.isAvailable();
      verify(() => mockDataSource.checkAvailability()).called(1);

      // Second call within 5 min should use cache.
      await repository.isAvailable();
      verifyNever(() => mockDataSource.checkAvailability());
    });

    test('caches false on exception and reuses within TTL', () async {
      when(() => mockDataSource.checkAvailability())
          .thenThrow(const ServerException(message: 'down'));

      // First call — returns Failure, caches false.
      final first = await repository.isAvailable();
      expect(first, isA<Failure<bool>>());
      verify(() => mockDataSource.checkAvailability()).called(1);

      // Second call — uses cached false, returns Success(false).
      final second = await repository.isAvailable();
      expect(second, isA<Success<bool>>());
      expect((second as Success<bool>).data, isFalse);
      // Still only 1 network call total.
      verifyNever(() => mockDataSource.checkAvailability());
    });
  });

  // ---------------------------------------------------------------------------
  // getReferralCode
  // ---------------------------------------------------------------------------

  group('getReferralCode', () {
    test('returns Success with empty string when feature is unavailable', () async {
      when(() => mockDataSource.checkAvailability())
          .thenAnswer((_) async => false);

      final result = await repository.getReferralCode();

      expect(result, isA<Success<String>>());
      expect((result as Success<String>).data, isEmpty);
      verifyNever(() => mockDataSource.getReferralCode());
    });

    test('returns Success with code from data source when available', () async {
      when(() => mockDataSource.checkAvailability())
          .thenAnswer((_) async => true);
      when(() => mockDataSource.getReferralCode())
          .thenAnswer((_) async => 'ABC123');

      final result = await repository.getReferralCode();

      expect(result, isA<Success<String>>());
      expect((result as Success<String>).data, equals('ABC123'));
      verify(() => mockDataSource.getReferralCode()).called(1);
    });

    test('networkFirst caches after first fetch and falls back to cache on error', () async {
      when(() => mockDataSource.checkAvailability())
          .thenAnswer((_) async => true);
      when(() => mockDataSource.getReferralCode())
          .thenAnswer((_) async => 'CACHED-CODE');

      // First call populates cache.
      final first = await repository.getReferralCode();
      expect((first as Success<String>).data, equals('CACHED-CODE'));

      // Make network call fail — cache fallback should be used.
      when(() => mockDataSource.getReferralCode())
          .thenThrow(const ServerException(message: 'Network error'));

      final second = await repository.getReferralCode();
      expect(second, isA<Success<String>>());
      expect((second as Success<String>).data, equals('CACHED-CODE'));
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

      expect(result, isA<Success<ReferralStats>>());
      final stats = (result as Success<ReferralStats>).data;
      expect(stats.totalInvited, equals(0));
      expect(stats.paidUsers, equals(0));
      expect(stats.pointsEarned, equals(0));
      expect(stats.balance, equals(0));
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

      expect(result, isA<Success<ReferralStats>>());
      final stats = (result as Success<ReferralStats>).data;
      expect(stats.totalInvited, equals(5));
      expect(stats.paidUsers, equals(2));
      expect(stats.pointsEarned, equals(150.0));
      expect(stats.balance, equals(75.0));
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

      expect(result, isA<Success<List<ReferralEntry>>>());
      expect((result as Success<List<ReferralEntry>>).data, isEmpty);
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

      expect(result, isA<Success<List<ReferralEntry>>>());
      final data = (result as Success<List<ReferralEntry>>).data;
      expect(data, hasLength(2));
      expect(data[0].code, equals('REF1'));
      expect(data[1].status, equals(ReferralStatus.completed));
    });

    test('returns Failure when available but data source throws', () async {
      when(() => mockDataSource.checkAvailability())
          .thenAnswer((_) async => true);
      when(() => mockDataSource.getRecentReferrals(limit: 10))
          .thenThrow(const ServerException(message: 'Internal error'));

      final result = await repository.getRecentReferrals();

      expect(result, isA<Failure<List<ReferralEntry>>>());
    });
  });
}
