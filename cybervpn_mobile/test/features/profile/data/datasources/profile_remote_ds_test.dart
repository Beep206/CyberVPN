import 'package:cybervpn_mobile/core/constants/api_constants.dart';
import 'package:cybervpn_mobile/core/network/api_client.dart';
import 'package:cybervpn_mobile/features/profile/data/datasources/profile_remote_ds.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/oauth_provider.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockApiClient extends Mock implements ApiClient {}

void main() {
  late MockApiClient mockApiClient;
  late ProfileRemoteDataSourceImpl dataSource;

  setUp(() {
    mockApiClient = MockApiClient();
    dataSource = ProfileRemoteDataSourceImpl(mockApiClient);
  });

  RequestOptions _requestOptions() => RequestOptions(path: '');

  // ---------------------------------------------------------------------------
  // getProfile
  // ---------------------------------------------------------------------------
  group('getProfile', () {
    test('calls GET /auth/me and maps response to Profile', () async {
      when(() => mockApiClient.get(
            ApiConstants.me,
            queryParameters: any(named: 'queryParameters'),
            options: any(named: 'options'),
          )).thenAnswer((_) async => Response(
            data: {
              'id': 'user-1',
              'email': 'test@example.com',
              'username': 'testuser',
              'avatar_url': null,
              'telegram_id': null,
              'is_email_verified': true,
              'is_2fa_enabled': false,
              'linked_providers': ['github', 'google'],
              'created_at': '2025-01-01T00:00:00Z',
              'last_login_at': '2025-06-15T12:00:00Z',
            },
            statusCode: 200,
            requestOptions: _requestOptions(),
          ));

      final profile = await dataSource.getProfile();

      expect(profile.id, 'user-1');
      expect(profile.email, 'test@example.com');
      expect(profile.username, 'testuser');
      expect(profile.isEmailVerified, isTrue);
      expect(profile.is2FAEnabled, isFalse);
      expect(profile.linkedProviders, [OAuthProvider.github, OAuthProvider.google]);
      verify(() => mockApiClient.get(
            ApiConstants.me,
            queryParameters: any(named: 'queryParameters'),
            options: any(named: 'options'),
          )).called(1);
    });

    test('handles missing optional fields gracefully', () async {
      when(() => mockApiClient.get(
            ApiConstants.me,
            queryParameters: any(named: 'queryParameters'),
            options: any(named: 'options'),
          )).thenAnswer((_) async => Response(
            data: {
              'id': 'user-2',
              'email': 'minimal@example.com',
            },
            statusCode: 200,
            requestOptions: _requestOptions(),
          ));

      final profile = await dataSource.getProfile();

      expect(profile.id, 'user-2');
      expect(profile.email, 'minimal@example.com');
      expect(profile.username, isNull);
      expect(profile.is2FAEnabled, isFalse);
      expect(profile.linkedProviders, isEmpty);
    });
  });

  // ---------------------------------------------------------------------------
  // setup2FA
  // ---------------------------------------------------------------------------
  group('setup2FA', () {
    test('calls POST /2fa/setup and returns Setup2FAResult', () async {
      when(() => mockApiClient.post(
            ApiConstants.setup2fa,
            data: any(named: 'data'),
            options: any(named: 'options'),
          )).thenAnswer((_) async => Response(
            data: {
              'secret': 'JBSWY3DPEHPK3PXP',
              'qr_code_uri': 'otpauth://totp/CyberVPN:test@example.com?secret=JBSWY3DPEHPK3PXP',
            },
            statusCode: 200,
            requestOptions: _requestOptions(),
          ));

      final result = await dataSource.setup2FA();

      expect(result.secret, 'JBSWY3DPEHPK3PXP');
      expect(result.qrCodeUri, contains('otpauth://'));
    });
  });

  // ---------------------------------------------------------------------------
  // verify2FA
  // ---------------------------------------------------------------------------
  group('verify2FA', () {
    test('calls POST /2fa/verify with code and returns boolean', () async {
      when(() => mockApiClient.post(
            ApiConstants.verify2fa,
            data: {'code': '123456'},
            options: any(named: 'options'),
          )).thenAnswer((_) async => Response(
            data: {'verified': true},
            statusCode: 200,
            requestOptions: _requestOptions(),
          ));

      final result = await dataSource.verify2FA('123456');

      expect(result, isTrue);
    });

    test('returns false when verified field is missing', () async {
      when(() => mockApiClient.post(
            ApiConstants.verify2fa,
            data: {'code': '000000'},
            options: any(named: 'options'),
          )).thenAnswer((_) async => Response(
            data: <String, dynamic>{},
            statusCode: 200,
            requestOptions: _requestOptions(),
          ));

      final result = await dataSource.verify2FA('000000');

      expect(result, isFalse);
    });
  });

  // ---------------------------------------------------------------------------
  // validate2FA
  // ---------------------------------------------------------------------------
  group('validate2FA', () {
    test('calls POST /2fa/validate with code and returns boolean', () async {
      when(() => mockApiClient.post(
            ApiConstants.validate2fa,
            data: {'code': '654321'},
            options: any(named: 'options'),
          )).thenAnswer((_) async => Response(
            data: {'valid': true},
            statusCode: 200,
            requestOptions: _requestOptions(),
          ));

      final result = await dataSource.validate2FA('654321');

      expect(result, isTrue);
    });
  });

  // ---------------------------------------------------------------------------
  // disable2FA
  // ---------------------------------------------------------------------------
  group('disable2FA', () {
    test('calls POST /2fa/disable with code', () async {
      when(() => mockApiClient.post(
            ApiConstants.disable2fa,
            data: {'code': '111111'},
            options: any(named: 'options'),
          )).thenAnswer((_) async => Response(
            data: null,
            statusCode: 200,
            requestOptions: _requestOptions(),
          ));

      await dataSource.disable2FA('111111');

      verify(() => mockApiClient.post(
            ApiConstants.disable2fa,
            data: {'code': '111111'},
            options: any(named: 'options'),
          )).called(1);
    });
  });

  // ---------------------------------------------------------------------------
  // unlinkOAuth
  // ---------------------------------------------------------------------------
  group('unlinkOAuth', () {
    test('calls DELETE /oauth/{provider}', () async {
      when(() => mockApiClient.delete(
            '${ApiConstants.oauthUnlink}google',
            options: any(named: 'options'),
          )).thenAnswer((_) async => Response(
            data: null,
            statusCode: 200,
            requestOptions: _requestOptions(),
          ));

      await dataSource.unlinkOAuth(OAuthProvider.google);

      verify(() => mockApiClient.delete(
            '${ApiConstants.oauthUnlink}google',
            options: any(named: 'options'),
          )).called(1);
    });
  });

  // ---------------------------------------------------------------------------
  // getDevices
  // ---------------------------------------------------------------------------
  group('getDevices', () {
    test('calls GET /auth/me/devices and maps response to Device list', () async {
      when(() => mockApiClient.get(
            '${ApiConstants.me}/devices',
            queryParameters: any(named: 'queryParameters'),
            options: any(named: 'options'),
          )).thenAnswer((_) async => Response(
            data: [
              {
                'id': 'dev-1',
                'name': 'iPhone 15',
                'platform': 'iOS',
                'ip_address': '192.168.1.1',
                'last_active_at': '2025-06-15T12:00:00Z',
                'created_at': '2025-01-01T00:00:00Z',
                'is_current': true,
              },
              {
                'id': 'dev-2',
                'name': 'Pixel 9',
                'platform': 'Android',
                'is_current': false,
              },
            ],
            statusCode: 200,
            requestOptions: _requestOptions(),
          ));

      final devices = await dataSource.getDevices();

      expect(devices, hasLength(2));
      expect(devices[0].id, 'dev-1');
      expect(devices[0].name, 'iPhone 15');
      expect(devices[0].isCurrent, isTrue);
      expect(devices[1].ipAddress, isNull);
    });
  });

  // ---------------------------------------------------------------------------
  // removeDevice
  // ---------------------------------------------------------------------------
  group('removeDevice', () {
    test('calls DELETE /auth/me/devices/{id}', () async {
      when(() => mockApiClient.delete(
            '${ApiConstants.me}/devices/dev-1',
            options: any(named: 'options'),
          )).thenAnswer((_) async => Response(
            data: null,
            statusCode: 200,
            requestOptions: _requestOptions(),
          ));

      await dataSource.removeDevice('dev-1');

      verify(() => mockApiClient.delete(
            '${ApiConstants.me}/devices/dev-1',
            options: any(named: 'options'),
          )).called(1);
    });
  });

  // ---------------------------------------------------------------------------
  // deleteAccount
  // ---------------------------------------------------------------------------
  group('deleteAccount', () {
    test('calls POST /auth/me/delete with password', () async {
      when(() => mockApiClient.post(
            '${ApiConstants.deleteAccount}/delete',
            data: {'password': 'secret123'},
            options: any(named: 'options'),
          )).thenAnswer((_) async => Response(
            data: null,
            statusCode: 200,
            requestOptions: _requestOptions(),
          ));

      await dataSource.deleteAccount('secret123');

      verify(() => mockApiClient.post(
            '${ApiConstants.deleteAccount}/delete',
            data: {'password': 'secret123'},
            options: any(named: 'options'),
          )).called(1);
    });

    test('includes totp_code when provided', () async {
      when(() => mockApiClient.post(
            '${ApiConstants.deleteAccount}/delete',
            data: {'password': 'secret123', 'totp_code': '123456'},
            options: any(named: 'options'),
          )).thenAnswer((_) async => Response(
            data: null,
            statusCode: 200,
            requestOptions: _requestOptions(),
          ));

      await dataSource.deleteAccount('secret123', totpCode: '123456');

      verify(() => mockApiClient.post(
            '${ApiConstants.deleteAccount}/delete',
            data: {'password': 'secret123', 'totp_code': '123456'},
            options: any(named: 'options'),
          )).called(1);
    });
  });
}
