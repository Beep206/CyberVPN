import 'dart:async';

import 'package:cybervpn_mobile/core/errors/network_error_handler.dart';
import 'package:cybervpn_mobile/core/network/api_client.dart';
import 'package:cybervpn_mobile/features/notifications/data/datasources/fcm_datasource.dart';
import 'package:cybervpn_mobile/features/notifications/data/datasources/notification_local_datasource.dart';
import 'package:cybervpn_mobile/features/notifications/domain/entities/app_notification.dart';
import 'package:cybervpn_mobile/features/notifications/domain/repositories/notification_repository.dart';

/// Combines [FcmDatasource] and [NotificationLocalDatasource] to fulfil
/// the [NotificationRepository] contract.
///
/// Incoming FCM messages (foreground and background tap) are automatically
/// persisted to local storage and re-emitted through a broadcast stream so
/// the presentation layer can react immediately.
class NotificationRepositoryImpl with NetworkErrorHandler implements NotificationRepository {
  final FcmDatasource _fcmDatasource;
  final NotificationLocalDatasource _localDatasource;
  final ApiClient _apiClient;

  StreamSubscription<AppNotification>? _foregroundSub;
  StreamSubscription<AppNotification>? _backgroundTapSub;

  final StreamController<AppNotification> _incomingController =
      StreamController<AppNotification>.broadcast();

  /// Stream of newly-received notifications (already persisted locally).
  Stream<AppNotification> get incoming => _incomingController.stream;

  NotificationRepositoryImpl({
    required FcmDatasource fcmDatasource,
    required NotificationLocalDatasource localDatasource,
    required ApiClient apiClient,
  })  : _fcmDatasource = fcmDatasource,
        _localDatasource = localDatasource,
        _apiClient = apiClient;

  /// Sets up FCM listeners and pipes messages to local storage.
  ///
  /// Call once during app initialisation after [FcmDatasource.configure].
  Future<void> init() async {
    _foregroundSub = _fcmDatasource.onForegroundMessage.listen(_handleIncoming);
    _backgroundTapSub = _fcmDatasource.onBackgroundTap.listen(_handleIncoming);

    // Check if the app was launched from a terminated-state notification.
    final initial = await _fcmDatasource.getInitialNotification();
    if (initial != null) {
      await _handleIncoming(initial);
    }
  }

  // ---------------------------------------------------------------------------
  // NotificationRepository interface
  // ---------------------------------------------------------------------------

  @override
  Future<List<AppNotification>> getNotifications() =>
      _localDatasource.getAll();

  @override
  Future<void> markAsRead(String id) => _localDatasource.markAsRead(id);

  @override
  Future<void> markAllAsRead() => _localDatasource.markAllAsRead();

  @override
  Future<void> deleteNotification(String id) => _localDatasource.delete(id);

  @override
  Future<int> getUnreadCount() => _localDatasource.getUnreadCount();

  @override
  Future<void> registerFcmToken(String token) async {
    await _apiClient.post<Map<String, dynamic>>(
      '/notifications/fcm-token',
      data: {'token': token},
    );
  }

  // ---------------------------------------------------------------------------
  // Internal
  // ---------------------------------------------------------------------------

  Future<void> _handleIncoming(AppNotification notification) async {
    await _localDatasource.save(notification);
    if (!_incomingController.isClosed) {
      _incomingController.add(notification);
    }
  }

  /// Releases stream subscriptions and controllers.
  void dispose() {
    unawaited(_foregroundSub?.cancel());
    unawaited(_backgroundTapSub?.cancel());
    unawaited(_incomingController.close());
  }
}
