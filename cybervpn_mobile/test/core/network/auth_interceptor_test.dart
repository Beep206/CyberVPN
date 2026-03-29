import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:cybervpn_mobile/core/auth/token_refresh_coordinator.dart';
import 'package:cybervpn_mobile/core/network/auth_interceptor.dart';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/features/auth/data/models/token_model.dart';

class MockSecureStorageWrapper extends Mock implements SecureStorageWrapper {}

class MockDio extends Mock implements Dio {}

class MockTokenRefreshCoordinator extends Mock
    implements TokenRefreshCoordinator {}

class FakeRequestOptions extends Fake implements RequestOptions {}

void main() {
  late MockSecureStorageWrapper mockStorage;
  late MockDio mockDio;
  late MockTokenRefreshCoordinator mockCoordinator;
  late AuthInterceptor interceptor;

  setUpAll(() {
    registerFallbackValue(FakeRequestOptions());
  });

  setUp(() {
    mockStorage = MockSecureStorageWrapper();
    mockDio = MockDio();
    mockCoordinator = MockTokenRefreshCoordinator();
    interceptor = AuthInterceptor(
      secureStorage: mockStorage,
      dio: mockDio,
      tokenRefreshCoordinator: mockCoordinator,
    );
  });

  group('AuthInterceptor', () {
    group('onRequest', () {
      test('adds Authorization header when token exists', () async {
        when(
          () => mockStorage.read(key: any(named: 'key')),
        ).thenAnswer((_) async => 'test_access_token');

        final options = RequestOptions(path: '/test');
        final handler = _MockRequestHandler();

        await interceptor.onRequest(options, handler);

        expect(handler.nextCalled, true);
        expect(
          handler.lastOptions?.headers['Authorization'],
          'Bearer test_access_token',
        );
      });

      test('does not add Authorization header when token is null', () async {
        when(
          () => mockStorage.read(key: any(named: 'key')),
        ).thenAnswer((_) async => null);

        final options = RequestOptions(path: '/test');
        final handler = _MockRequestHandler();

        await interceptor.onRequest(options, handler);

        expect(handler.nextCalled, true);
        expect(handler.lastOptions?.headers['Authorization'], isNull);
      });
    });

    group('onError - concurrent 401 handling', () {
      test(
        'multiple concurrent 401s are retried after coordinator refreshes',
        () async {
          when(
            () => mockCoordinator.refresh(reason: any(named: 'reason')),
          ).thenAnswer((_) async {
            await Future<void>.delayed(const Duration(milliseconds: 50));
            return const TokenModel(
              accessToken: 'new_access_token',
              refreshToken: 'new_refresh_token',
              expiresIn: 3600,
            );
          });

          // Setup: retry requests succeed
          when(() => mockDio.fetch<dynamic>(any())).thenAnswer((
            invocation,
          ) async {
            final options = invocation.positionalArguments[0] as RequestOptions;
            return Response(
              requestOptions: options,
              data: {'success': true},
              statusCode: 200,
            );
          });

          // Create 3 concurrent 401 errors
          final errors = List.generate(
            3,
            (i) => DioException(
              requestOptions: RequestOptions(path: '/api/request$i'),
              response: Response(
                requestOptions: RequestOptions(path: '/api/request$i'),
                statusCode: 401,
              ),
              type: DioExceptionType.badResponse,
            ),
          );

          final handlers = List.generate(3, (_) => _MockErrorHandler());

          // Fire all 3 errors concurrently
          final futures = <Future<void>>[];
          for (var i = 0; i < 3; i++) {
            futures.add(interceptor.onError(errors[i], handlers[i]));
          }

          await Future.wait(futures);

          verify(
            () => mockCoordinator.refresh(reason: any(named: 'reason')),
          ).called(3);

          // Verify all requests were eventually resolved (not rejected)
          for (final handler in handlers) {
            expect(
              handler.resolveCalled,
              true,
              reason:
                  'All requests should be resolved after successful refresh',
            );
          }
        },
      );

      test('all queued requests are rejected when refresh fails', () async {
        when(
          () => mockCoordinator.refresh(reason: any(named: 'reason')),
        ).thenThrow(const TokenRefreshException(message: 'Refresh failed'));

        // Create 2 concurrent 401 errors
        final errors = List.generate(
          2,
          (i) => DioException(
            requestOptions: RequestOptions(path: '/api/request$i'),
            response: Response(
              requestOptions: RequestOptions(path: '/api/request$i'),
              statusCode: 401,
            ),
            type: DioExceptionType.badResponse,
          ),
        );

        final handlers = List.generate(2, (_) => _MockErrorHandler());

        // Fire all errors concurrently
        final futures = <Future<void>>[];
        for (var i = 0; i < 2; i++) {
          futures.add(interceptor.onError(errors[i], handlers[i]));
        }

        await Future.wait(futures);

        // Verify all requests were rejected (handler.next was called)
        for (final handler in handlers) {
          expect(
            handler.nextCalled,
            true,
            reason: 'All requests should be rejected after failed refresh',
          );
          expect(handler.resolveCalled, false);
        }
      });

      test(
        'refresh-marked requests are passed through without recursion',
        () async {
          final refreshRequestOptions = RequestOptions(
            path: '/mobile/auth/refresh',
            extra: {AuthInterceptor.skipAuthRefreshHandlingKey: true},
          );

          final error = DioException(
            requestOptions: refreshRequestOptions,
            response: Response(
              requestOptions: refreshRequestOptions,
              statusCode: 401,
            ),
            type: DioExceptionType.badResponse,
          );

          final handler = _MockErrorHandler();
          await interceptor.onError(error, handler);

          // Should be passed through, not triggering a new refresh
          expect(handler.nextCalled, true);
          expect(handler.resolveCalled, false);
          verifyNever(
            () => mockCoordinator.refresh(reason: any(named: 'reason')),
          );
        },
      );

      test('already-retried requests are passed through', () async {
        final error = DioException(
          requestOptions: RequestOptions(
            path: '/api/test',
            extra: {AuthInterceptor.hasRetriedAfterRefreshKey: true},
          ),
          response: Response(
            requestOptions: RequestOptions(path: '/api/test'),
            statusCode: 401,
          ),
          type: DioExceptionType.badResponse,
        );

        final handler = _MockErrorHandler();
        await interceptor.onError(error, handler);

        expect(handler.nextCalled, true);
        verifyNever(
          () => mockCoordinator.refresh(reason: any(named: 'reason')),
        );
      });

      test('non-401 errors are passed through immediately', () async {
        final error = DioException(
          requestOptions: RequestOptions(path: '/api/test'),
          response: Response(
            requestOptions: RequestOptions(path: '/api/test'),
            statusCode: 500,
          ),
          type: DioExceptionType.badResponse,
        );

        final handler = _MockErrorHandler();
        await interceptor.onError(error, handler);

        expect(handler.nextCalled, true);
        expect(handler.resolveCalled, false);
        verifyNever(
          () => mockCoordinator.refresh(reason: any(named: 'reason')),
        );
      });
    });
  });
}

/// Mock handler for testing onRequest
class _MockRequestHandler extends RequestInterceptorHandler {
  bool nextCalled = false;
  RequestOptions? lastOptions;

  @override
  void next(RequestOptions requestOptions) {
    nextCalled = true;
    lastOptions = requestOptions;
  }
}

/// Mock handler for testing onError
class _MockErrorHandler extends ErrorInterceptorHandler {
  bool nextCalled = false;
  bool resolveCalled = false;
  DioException? lastError;
  Response<dynamic>? lastResponse;

  @override
  void next(DioException err) {
    nextCalled = true;
    lastError = err;
  }

  @override
  void resolve(Response<dynamic> response) {
    resolveCalled = true;
    lastResponse = response;
  }
}
