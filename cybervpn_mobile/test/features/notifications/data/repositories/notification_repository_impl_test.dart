import 'dart:async';

import 'package:cybervpn_mobile/core/network/api_client.dart';
import 'package:cybervpn_mobile/features/notifications/data/datasources/fcm_datasource.dart';
import 'package:cybervpn_mobile/features/notifications/data/datasources/notification_local_datasource.dart';
import 'package:cybervpn_mobile/features/notifications/data/repositories/notification_repository_impl.dart';
import 'package:cybervpn_mobile/features/notifications/domain/entities/app_notification.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class _MockFcmDatasource extends Mock implements FcmDatasource {}

class _MockLocalDatasource extends Mock implements NotificationLocalDatasource {}

class _MockApiClient extends Mock implements ApiClient {}

// Use a real AppNotification instance as fallback value since
// AppNotification is a freezed sealed class that cannot be faked.
final _fallbackAppNotification = AppNotification(
  id: 'fallback',
  type: NotificationType.paymentConfirmed,
  title: 'Fallback',
  body: 'Fallback',
  receivedAt: DateTime(2020),
);

void main() {
  setUpAll(() {
    registerFallbackValue(_fallbackAppNotification);
  });

  late _MockFcmDatasource mockFcm;
  late _MockLocalDatasource mockLocal;
  late _MockApiClient mockApi;
  late NotificationRepositoryImpl repository;

  final testNotification = AppNotification(
    id: 'n1',
    type: NotificationType.paymentConfirmed,
    title: 'Payment',
    body: 'Confirmed',
    receivedAt: DateTime(2026, 1, 31),
  );

  setUp(() {
    mockFcm = _MockFcmDatasource();
    mockLocal = _MockLocalDatasource();
    mockApi = _MockApiClient();

    // Default stubs for FCM streams.
    when(() => mockFcm.onForegroundMessage)
        .thenAnswer((_) => const Stream.empty());
    when(() => mockFcm.onBackgroundTap)
        .thenAnswer((_) => const Stream.empty());
    when(() => mockFcm.getInitialNotification())
        .thenAnswer((_) async => null);

    repository = NotificationRepositoryImpl(
      fcmDatasource: mockFcm,
      localDatasource: mockLocal,
      apiClient: mockApi,
    );
  });

  tearDown(() {
    repository.dispose();
  });

  group('getNotifications', () {
    test('delegates to local datasource', () async {
      when(() => mockLocal.getAll())
          .thenAnswer((_) async => [testNotification]);

      final result = await repository.getNotifications();

      expect(result, hasLength(1));
      expect(result.first.id, 'n1');
      verify(() => mockLocal.getAll()).called(1);
    });
  });

  group('markAsRead', () {
    test('delegates to local datasource', () async {
      when(() => mockLocal.markAsRead('n1')).thenAnswer((_) async {});

      await repository.markAsRead('n1');

      verify(() => mockLocal.markAsRead('n1')).called(1);
    });
  });

  group('markAllAsRead', () {
    test('delegates to local datasource', () async {
      when(() => mockLocal.markAllAsRead()).thenAnswer((_) async {});

      await repository.markAllAsRead();

      verify(() => mockLocal.markAllAsRead()).called(1);
    });
  });

  group('deleteNotification', () {
    test('delegates to local datasource', () async {
      when(() => mockLocal.delete('n1')).thenAnswer((_) async {});

      await repository.deleteNotification('n1');

      verify(() => mockLocal.delete('n1')).called(1);
    });
  });

  group('getUnreadCount', () {
    test('delegates to local datasource', () async {
      when(() => mockLocal.getUnreadCount()).thenAnswer((_) async => 5);

      final count = await repository.getUnreadCount();

      expect(count, 5);
    });
  });

  group('registerFcmToken', () {
    test('posts token to API', () async {
      when(() => mockApi.post<Map<String, dynamic>>(
            '/notifications/fcm-token',
            data: {'token': 'abc123'},
          )).thenAnswer((_) async => Response(
            requestOptions: RequestOptions(),
            statusCode: 200,
          ));

      await repository.registerFcmToken('abc123');

      verify(() => mockApi.post<Map<String, dynamic>>(
            '/notifications/fcm-token',
            data: {'token': 'abc123'},
          )).called(1);
    });
  });

  group('init', () {
    test('saves initial notification from terminated state', () async {
      when(() => mockFcm.getInitialNotification())
          .thenAnswer((_) async => testNotification);
      when(() => mockLocal.save(testNotification)).thenAnswer((_) async {});

      await repository.init();

      verify(() => mockLocal.save(testNotification)).called(1);
    });

    test('pipes foreground messages to local storage and stream', () async {
      final controller = StreamController<AppNotification>.broadcast();
      when(() => mockFcm.onForegroundMessage)
          .thenAnswer((_) => controller.stream);
      when(() => mockLocal.save(any())).thenAnswer((_) async {});

      // Re-create repository so it picks up the new stream.
      repository = NotificationRepositoryImpl(
        fcmDatasource: mockFcm,
        localDatasource: mockLocal,
        apiClient: mockApi,
      );

      final received = <AppNotification>[];
      repository.incoming.listen(received.add);

      await repository.init();

      controller.add(testNotification);
      await Future<void>.delayed(Duration.zero);

      expect(received, hasLength(1));
      expect(received.first.id, 'n1');
      verify(() => mockLocal.save(testNotification)).called(1);

      await controller.close();
    });

    test('pipes background tap messages to local storage', () async {
      final controller = StreamController<AppNotification>.broadcast();
      when(() => mockFcm.onBackgroundTap)
          .thenAnswer((_) => controller.stream);
      when(() => mockLocal.save(any())).thenAnswer((_) async {});

      repository = NotificationRepositoryImpl(
        fcmDatasource: mockFcm,
        localDatasource: mockLocal,
        apiClient: mockApi,
      );

      await repository.init();

      controller.add(testNotification);
      await Future<void>.delayed(Duration.zero);

      verify(() => mockLocal.save(testNotification)).called(1);

      await controller.close();
    });
  });
}
