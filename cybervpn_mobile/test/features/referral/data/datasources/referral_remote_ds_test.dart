import 'package:cybervpn_mobile/core/errors/exceptions.dart';
import 'package:cybervpn_mobile/core/network/api_client.dart';
import 'package:cybervpn_mobile/features/referral/data/datasources/referral_remote_ds.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockApiClient extends Mock implements ApiClient {}

void main() {
  late MockApiClient mockApiClient;
  late ReferralRemoteDataSourceImpl dataSource;

  setUp(() {
    mockApiClient = MockApiClient();
    dataSource = ReferralRemoteDataSourceImpl(mockApiClient);
  });

  void stubGetSuccess({Map<String, dynamic>? data}) {
    when(() => mockApiClient.get<Map<String, dynamic>>(
          any(),
          queryParameters: any(named: 'queryParameters'),
          options: any(named: 'options'),
        )).thenAnswer((_) async => Response<Map<String, dynamic>>(
          data: data ?? {'status': 'ok'},
          statusCode: 200,
          requestOptions: RequestOptions(path: ''),
        ));
  }

  // ---------------------------------------------------------------------------
  // checkAvailability
  // ---------------------------------------------------------------------------

  group('checkAvailability', () {
    test('returns true on HTTP 200', () async {
      stubGetSuccess();

      final result = await dataSource.checkAvailability();

      expect(result, isTrue);
    });

    test('returns false on ServerException with 404', () async {
      when(() => mockApiClient.get<Map<String, dynamic>>(
            any(),
            queryParameters: any(named: 'queryParameters'),
            options: any(named: 'options'),
          )).thenThrow(
              const ServerException(message: 'Not Found', code: 404));

      final result = await dataSource.checkAvailability();

      expect(result, isFalse);
    });

    test('returns false on ServerException with 501', () async {
      when(() => mockApiClient.get<Map<String, dynamic>>(
            any(),
            queryParameters: any(named: 'queryParameters'),
            options: any(named: 'options'),
          )).thenThrow(const ServerException(
              message: 'Not Implemented', code: 501));

      final result = await dataSource.checkAvailability();

      expect(result, isFalse);
    });

    test('returns false on NetworkException', () async {
      when(() => mockApiClient.get<Map<String, dynamic>>(
            any(),
            queryParameters: any(named: 'queryParameters'),
            options: any(named: 'options'),
          )).thenThrow(
              const NetworkException(message: 'No internet connection'));

      final result = await dataSource.checkAvailability();

      expect(result, isFalse);
    });

    test('returns false on unexpected exception', () async {
      when(() => mockApiClient.get<Map<String, dynamic>>(
            any(),
            queryParameters: any(named: 'queryParameters'),
            options: any(named: 'options'),
          )).thenThrow(Exception('Unexpected'));

      final result = await dataSource.checkAvailability();

      expect(result, isFalse);
    });

    test('caches result and does not make repeated API calls', () async {
      stubGetSuccess();

      // First call hits the API.
      await dataSource.checkAvailability();
      // Second call should use cached value.
      final result = await dataSource.checkAvailability();

      expect(result, isTrue);
      verify(() => mockApiClient.get<Map<String, dynamic>>(
            any(),
            queryParameters: any(named: 'queryParameters'),
            options: any(named: 'options'),
          )).called(1);
    });
  });

  // ---------------------------------------------------------------------------
  // getReferralCode
  // ---------------------------------------------------------------------------

  group('getReferralCode', () {
    test('returns code from API response', () async {
      stubGetSuccess(data: {'code': 'ABC123'});

      final result = await dataSource.getReferralCode();

      expect(result, equals('ABC123'));
    });
  });

  // ---------------------------------------------------------------------------
  // getReferralStats
  // ---------------------------------------------------------------------------

  group('getReferralStats', () {
    test('returns parsed stats from API response', () async {
      stubGetSuccess(data: {
        'total_invited': 10,
        'paid_users': 3,
        'points_earned': 250.5,
        'balance': 100.0,
      });

      final result = await dataSource.getReferralStats();

      expect(result.totalInvited, equals(10));
      expect(result.paidUsers, equals(3));
      expect(result.pointsEarned, equals(250.5));
      expect(result.balance, equals(100.0));
    });
  });

  // ---------------------------------------------------------------------------
  // getRecentReferrals
  // ---------------------------------------------------------------------------

  group('getRecentReferrals', () {
    test('returns parsed entries from API response', () async {
      stubGetSuccess(data: {
        'referrals': [
          {
            'code': 'REF1',
            'join_date': '2025-01-15T00:00:00.000',
            'status': 'active',
          },
          {
            'code': 'REF2',
            'join_date': '2025-02-20T00:00:00.000',
            'status': 'completed',
          },
        ],
      });

      final result = await dataSource.getRecentReferrals();

      expect(result, hasLength(2));
      expect(result[0].code, equals('REF1'));
      expect(result[1].code, equals('REF2'));
    });
  });
}
