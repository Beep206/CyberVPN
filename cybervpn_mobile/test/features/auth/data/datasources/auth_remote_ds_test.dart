import 'package:cybervpn_mobile/core/constants/api_constants.dart';
import 'package:cybervpn_mobile/core/device/device_info.dart';
import 'package:cybervpn_mobile/core/network/api_client.dart';
import 'package:cybervpn_mobile/features/auth/data/datasources/auth_remote_ds.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockApiClient extends Mock implements ApiClient {}

void main() {
  late MockApiClient mockApiClient;
  late AuthRemoteDataSourceImpl dataSource;

  const testDevice = DeviceInfo(
    deviceId: '123e4567-e89b-12d3-a456-426614174000',
    platform: DevicePlatform.ios,
    platformId: 'ios-platform-id',
    osVersion: '17.4',
    appVersion: '1.2.3',
    deviceModel: 'iPhone 15 Pro',
  );

  setUp(() {
    mockApiClient = MockApiClient();
    dataSource = AuthRemoteDataSourceImpl(mockApiClient);
  });

  RequestOptions requestOptions() => RequestOptions(path: '');

  group('AuthRemoteDataSourceImpl', () {
    test('login normalizes snake_case mobile auth response', () async {
      when(
        () => mockApiClient.post<Map<String, dynamic>>(
          ApiConstants.login,
          data: any<dynamic>(named: 'data'),
          options: any<Options?>(named: 'options'),
        ),
      ).thenAnswer(
        (_) async => Response(
          data: {
            'tokens': {
              'access_token': 'access-token',
              'refresh_token': 'refresh-token',
              'expires_in': 900,
              'token_type': 'Bearer',
            },
            'user': {
              'id': 'user-1',
              'email': 'user@example.com',
              'username': 'mobile_user',
              'telegram_id': 123456789,
              'is_email_verified': true,
              'created_at': '2026-04-21T06:00:00Z',
              'last_login_at': '2026-04-21T06:05:00Z',
            },
          },
          statusCode: 200,
          requestOptions: requestOptions(),
        ),
      );

      final result = await dataSource.login(
        email: 'user@example.com',
        password: 'Password123!',
        device: testDevice,
      );

      expect(result.$1.email, 'user@example.com');
      expect(result.$1.telegramId, '123456789');
      expect(result.$1.isEmailVerified, isTrue);
      expect(result.$2.accessToken, 'access-token');
      expect(result.$2.refreshToken, 'refresh-token');
    });

    test('refreshToken normalizes snake_case token response', () async {
      when(
        () => mockApiClient.post<Map<String, dynamic>>(
          ApiConstants.refresh,
          data: {'refresh_token': 'refresh-token', 'device_id': 'device-1'},
          options: any<Options?>(named: 'options'),
        ),
      ).thenAnswer(
        (_) async => Response(
          data: {
            'access_token': 'new-access',
            'refresh_token': 'new-refresh',
            'expires_in': 900,
            'token_type': 'Bearer',
          },
          statusCode: 200,
          requestOptions: requestOptions(),
        ),
      );

      final token = await dataSource.refreshToken(
        refreshToken: 'refresh-token',
        deviceId: 'device-1',
      );

      expect(token.accessToken, 'new-access');
      expect(token.refreshToken, 'new-refresh');
      expect(token.tokenType, 'Bearer');
    });

    test('getCurrentUser normalizes snake_case profile response', () async {
      when(
        () => mockApiClient.get<Map<String, dynamic>>(
          ApiConstants.me,
          queryParameters: any<Map<String, dynamic>?>(named: 'queryParameters'),
          options: any<Options?>(named: 'options'),
        ),
      ).thenAnswer(
        (_) async => Response(
          data: {
            'id': 'user-2',
            'email': 'current@example.com',
            'username': 'current_user',
            'telegram_id': 987654321,
            'is_email_verified': true,
            'last_login_at': '2026-04-21T06:05:00Z',
          },
          statusCode: 200,
          requestOptions: requestOptions(),
        ),
      );

      final user = await dataSource.getCurrentUser();

      expect(user.id, 'user-2');
      expect(user.telegramId, '987654321');
      expect(user.isEmailVerified, isTrue);
    });
  });
}
