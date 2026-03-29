import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:cybervpn_mobile/core/auth/token_refresh_coordinator.dart';
import 'package:cybervpn_mobile/core/device/device_service.dart';
import 'package:cybervpn_mobile/features/auth/data/datasources/auth_local_ds.dart';
import 'package:cybervpn_mobile/features/auth/data/models/token_model.dart';

class MockDio extends Mock implements Dio {}

class MockAuthLocalDataSource extends Mock implements AuthLocalDataSource {}

class MockDeviceService extends Mock implements DeviceService {}

class FakeRequestOptions extends Fake implements RequestOptions {}

void main() {
  late MockDio mockDio;
  late MockAuthLocalDataSource mockLocalDataSource;
  late MockDeviceService mockDeviceService;
  late TokenRefreshCoordinator coordinator;

  setUpAll(() {
    registerFallbackValue(FakeRequestOptions());
    registerFallbackValue(
      const TokenModel(
        accessToken: 'fallback-access',
        refreshToken: 'fallback-refresh',
        expiresIn: 3600,
      ),
    );
  });

  setUp(() {
    mockDio = MockDio();
    mockLocalDataSource = MockAuthLocalDataSource();
    mockDeviceService = MockDeviceService();
    coordinator = TokenRefreshCoordinator(
      dio: mockDio,
      localDataSource: mockLocalDataSource,
      deviceService: mockDeviceService,
    );
  });

  test('successful refresh caches returned token model', () async {
    when(() => mockLocalDataSource.getCachedToken()).thenAnswer(
      (_) async => const TokenModel(
        accessToken: 'old-access',
        refreshToken: 'valid-refresh',
        expiresIn: 3600,
      ),
    );
    when(
      () => mockDeviceService.getDeviceId(),
    ).thenAnswer((_) async => 'device-1');
    when(
      () => mockDio.post<Map<String, dynamic>>(
        any(),
        data: any(named: 'data'),
        options: any(named: 'options'),
      ),
    ).thenAnswer(
      (_) async => Response<Map<String, dynamic>>(
        requestOptions: RequestOptions(path: '/api/v1/auth/refresh'),
        data: const {
          'access_token': 'new-access',
          'refresh_token': 'new-refresh',
          'expires_in': 3600,
        },
      ),
    );
    when(() => mockLocalDataSource.cacheToken(any())).thenAnswer((_) async {});

    final result = await coordinator.refresh(reason: 'test');

    expect(result.accessToken, 'new-access');
    expect(result.refreshToken, 'new-refresh');
    verify(
      () => mockLocalDataSource.cacheToken(
        const TokenModel(
          accessToken: 'new-access',
          refreshToken: 'new-refresh',
          expiresIn: 3600,
        ),
      ),
    ).called(1);
  });

  test('concurrent refresh calls share a single network request', () async {
    when(() => mockLocalDataSource.getCachedToken()).thenAnswer(
      (_) async => const TokenModel(
        accessToken: 'old-access',
        refreshToken: 'valid-refresh',
        expiresIn: 3600,
      ),
    );
    when(
      () => mockDeviceService.getDeviceId(),
    ).thenAnswer((_) async => 'device-1');
    when(
      () => mockDio.post<Map<String, dynamic>>(
        any(),
        data: any(named: 'data'),
        options: any(named: 'options'),
      ),
    ).thenAnswer((_) async {
      await Future<void>.delayed(const Duration(milliseconds: 40));
      return Response<Map<String, dynamic>>(
        requestOptions: RequestOptions(path: '/api/v1/auth/refresh'),
        data: const {
          'access_token': 'new-access',
          'refresh_token': 'new-refresh',
          'expires_in': 3600,
        },
      );
    });
    when(() => mockLocalDataSource.cacheToken(any())).thenAnswer((_) async {});

    final results = await Future.wait([
      coordinator.refresh(reason: 'one'),
      coordinator.refresh(reason: 'two'),
      coordinator.refresh(reason: 'three'),
    ]);

    expect(results.map((token) => token.accessToken).toSet(), {'new-access'});
    verify(
      () => mockDio.post<Map<String, dynamic>>(
        any(),
        data: any(named: 'data'),
        options: any(named: 'options'),
      ),
    ).called(1);
  });

  test('permanent refresh failure clears auth cache', () async {
    when(() => mockLocalDataSource.getCachedToken()).thenAnswer(
      (_) async => const TokenModel(
        accessToken: 'old-access',
        refreshToken: 'valid-refresh',
        expiresIn: 3600,
      ),
    );
    when(
      () => mockDeviceService.getDeviceId(),
    ).thenAnswer((_) async => 'device-1');
    when(
      () => mockDio.post<Map<String, dynamic>>(
        any(),
        data: any(named: 'data'),
        options: any(named: 'options'),
      ),
    ).thenAnswer(
      (_) async => throw DioException(
        requestOptions: RequestOptions(path: '/api/v1/auth/refresh'),
        response: Response(
          requestOptions: RequestOptions(path: '/api/v1/auth/refresh'),
          statusCode: 401,
        ),
        type: DioExceptionType.badResponse,
      ),
    );
    when(() => mockLocalDataSource.clearAuth()).thenAnswer((_) async {});

    TokenRefreshException? thrown;
    try {
      await coordinator.refresh(reason: 'permanent-failure');
    } on TokenRefreshException catch (error) {
      thrown = error;
    }

    expect(thrown, isNotNull);

    verify(() => mockLocalDataSource.clearAuth()).called(1);
  });

  test(
    'missing refresh token throws permanent error without network call',
    () async {
      when(
        () => mockLocalDataSource.getCachedToken(),
      ).thenAnswer((_) async => null);
      when(() => mockLocalDataSource.clearAuth()).thenAnswer((_) async {});

      TokenRefreshException? thrown;
      try {
        await coordinator.refresh(reason: 'missing-token');
      } on TokenRefreshException catch (error) {
        thrown = error;
      }

      expect(thrown, isNotNull);

      verifyNever(
        () => mockDio.post<Map<String, dynamic>>(
          any(),
          data: any(named: 'data'),
          options: any(named: 'options'),
        ),
      );
    },
  );
}
