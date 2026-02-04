import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:cybervpn_mobile/core/network/auth_interceptor.dart';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';

class MockSecureStorageWrapper extends Mock implements SecureStorageWrapper {}

class MockDio extends Mock implements Dio {}

class FakeRequestOptions extends Fake implements RequestOptions {}

void main() {
  late MockSecureStorageWrapper mockStorage;
  late MockDio mockDio;
  late AuthInterceptor interceptor;

  setUpAll(() {
    registerFallbackValue(FakeRequestOptions());
  });

  setUp(() {
    mockStorage = MockSecureStorageWrapper();
    mockDio = MockDio();
    interceptor = AuthInterceptor(
      secureStorage: mockStorage,
      dio: mockDio,
    );
  });

  group('AuthInterceptor', () {
    group('onRequest', () {
      test('adds Authorization header when token exists', () async {
        when(() => mockStorage.read(key: any(named: 'key')))
            .thenAnswer((_) async => 'test_access_token');

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
        when(() => mockStorage.read(key: any(named: 'key')))
            .thenAnswer((_) async => null);

        final options = RequestOptions(path: '/test');
        final handler = _MockRequestHandler();

        await interceptor.onRequest(options, handler);

        expect(handler.nextCalled, true);
        expect(handler.lastOptions?.headers['Authorization'], isNull);
      });
    });

    group('onError - concurrent 401 handling', () {
      test('multiple concurrent 401s trigger only ONE refresh call', () async {
        // Setup: access token exists, refresh token exists
        when(() => mockStorage.read(key: 'access_token'))
            .thenAnswer((_) async => 'old_access_token');
        when(() => mockStorage.read(key: 'refresh_token'))
            .thenAnswer((_) async => 'valid_refresh_token');

        // Setup: token refresh succeeds
        when(() => mockDio.post<Map<String, dynamic>>(
              '/mobile/auth/refresh',
              data: any(named: 'data'),
            )).thenAnswer((_) async {
          // Simulate some latency
          await Future<void>.delayed(const Duration(milliseconds: 50));
          return Response(
            requestOptions: RequestOptions(path: '/mobile/auth/refresh'),
            data: {
              'access_token': 'new_access_token',
              'refresh_token': 'new_refresh_token',
            },
          );
        });

        // Setup: retry requests succeed
        when(() => mockDio.fetch<dynamic>(any())).thenAnswer((invocation) async {
          final options = invocation.positionalArguments[0] as RequestOptions;
          return Response(
            requestOptions: options,
            data: {'success': true},
            statusCode: 200,
          );
        });

        // Setup: storage writes succeed
        when(() => mockStorage.write(key: any(named: 'key'), value: any(named: 'value')))
            .thenAnswer((_) async {});

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

        // Verify only ONE refresh call was made
        verify(() => mockDio.post<Map<String, dynamic>>(
              '/mobile/auth/refresh',
              data: any(named: 'data'),
            )).called(1);

        // Verify all requests were eventually resolved (not rejected)
        for (final handler in handlers) {
          expect(handler.resolveCalled, true,
              reason: 'All requests should be resolved after successful refresh');
        }
      });

      test('all queued requests are rejected when refresh fails', () async {
        // Setup: refresh token exists
        when(() => mockStorage.read(key: 'access_token'))
            .thenAnswer((_) async => 'old_access_token');
        when(() => mockStorage.read(key: 'refresh_token'))
            .thenAnswer((_) async => 'valid_refresh_token');

        // Setup: token refresh FAILS
        when(() => mockDio.post<Map<String, dynamic>>(
              '/mobile/auth/refresh',
              data: any(named: 'data'),
            )).thenAnswer((_) async {
          await Future<void>.delayed(const Duration(milliseconds: 50));
          throw DioException(
            requestOptions: RequestOptions(path: '/mobile/auth/refresh'),
            type: DioExceptionType.badResponse,
            response: Response(
              requestOptions: RequestOptions(path: '/mobile/auth/refresh'),
              statusCode: 401,
            ),
          );
        });

        // Setup: storage delete succeeds
        when(() => mockStorage.delete(key: any(named: 'key')))
            .thenAnswer((_) async {});

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
          expect(handler.nextCalled, true,
              reason: 'All requests should be rejected after failed refresh');
          expect(handler.resolveCalled, false);
        }

        // Verify tokens were cleared
        verify(() => mockStorage.delete(key: 'access_token')).called(1);
        verify(() => mockStorage.delete(key: 'refresh_token')).called(1);
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
        verifyNever(() => mockDio.post<Map<String, dynamic>>(
              any(),
              data: any(named: 'data'),
            ));
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
