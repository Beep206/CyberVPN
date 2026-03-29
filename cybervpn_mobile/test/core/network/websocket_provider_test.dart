import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:cybervpn_mobile/core/errors/exceptions.dart';
import 'package:cybervpn_mobile/core/network/api_client.dart';
import 'package:cybervpn_mobile/core/network/websocket_provider.dart';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';

class MockApiClient extends Mock implements ApiClient {}

class MockSecureStorageWrapper extends Mock implements SecureStorageWrapper {}

void main() {
  late MockApiClient mockApiClient;
  late MockSecureStorageWrapper mockSecureStorage;

  setUp(() {
    mockApiClient = MockApiClient();
    mockSecureStorage = MockSecureStorageWrapper();
  });

  test('returns websocket ticket on success', () async {
    when(
      () => mockSecureStorage.getAccessToken(),
    ).thenAnswer((_) async => 'access-token');
    when(() => mockApiClient.post<Map<String, dynamic>>(any())).thenAnswer(
      (_) async => Response<Map<String, dynamic>>(
        requestOptions: RequestOptions(path: '/api/v1/ws/ticket'),
        data: {'ticket': 'ws-ticket'},
      ),
    );

    final ticket = await requestWebSocketTicket(
      mockApiClient,
      mockSecureStorage,
    );

    expect(ticket, 'ws-ticket');
  });

  test('returns null when no access token is available', () async {
    when(
      () => mockSecureStorage.getAccessToken(),
    ).thenAnswer((_) async => null);

    final ticket = await requestWebSocketTicket(
      mockApiClient,
      mockSecureStorage,
    );

    expect(ticket, isNull);
    verifyNever(() => mockApiClient.post<Map<String, dynamic>>(any()));
  });

  test('returns null when auth is no longer valid', () async {
    when(
      () => mockSecureStorage.getAccessToken(),
    ).thenAnswer((_) async => 'access-token');
    when(
      () => mockApiClient.post<Map<String, dynamic>>(any()),
    ).thenThrow(const AuthException(message: 'Unauthorized', code: 401));

    final ticket = await requestWebSocketTicket(
      mockApiClient,
      mockSecureStorage,
    );

    expect(ticket, isNull);
  });

  test('rethrows transient ticket request failures', () async {
    when(
      () => mockSecureStorage.getAccessToken(),
    ).thenAnswer((_) async => 'access-token');
    when(
      () => mockApiClient.post<Map<String, dynamic>>(any()),
    ).thenThrow(const NetworkException(message: 'No internet connection'));

    await expectLater(
      requestWebSocketTicket(mockApiClient, mockSecureStorage),
      throwsA(isA<NetworkException>()),
    );
  });
}
