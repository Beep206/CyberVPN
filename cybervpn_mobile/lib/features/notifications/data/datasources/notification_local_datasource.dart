import 'dart:convert';

import 'package:cybervpn_mobile/core/storage/local_storage.dart';
import 'package:cybervpn_mobile/features/notifications/domain/entities/app_notification.dart';

/// Local datasource that persists [AppNotification]s in SharedPreferences.
///
/// Enforces a maximum capacity of [maxCapacity] notifications (FIFO) and
/// automatically removes entries older than [maxAgeDays] days on every read.
abstract class NotificationLocalDatasource {
  /// Saves a notification. If capacity is exceeded the oldest entry is removed.
  Future<void> save(AppNotification notification);

  /// Returns all stored notifications (newest first), after expiry cleanup.
  Future<List<AppNotification>> getAll();

  /// Deletes a single notification by [id].
  Future<void> delete(String id);

  /// Marks the notification identified by [id] as read.
  Future<void> markAsRead(String id);

  /// Marks every stored notification as read.
  Future<void> markAllAsRead();

  /// Returns the number of unread notifications.
  Future<int> getUnreadCount();

  /// Removes all stored notifications.
  Future<void> clear();
}

/// Default implementation backed by [LocalStorageWrapper].
class NotificationLocalDatasourceImpl implements NotificationLocalDatasource {
  final LocalStorageWrapper _localStorage;

  /// Maximum number of notifications kept in storage.
  static const int maxCapacity = 100;

  /// Notifications older than this many days are automatically purged.
  static const int maxAgeDays = 30;

  static const String _storageKey = 'notifications_data';

  /// Allows injecting a clock for deterministic testing.
  final DateTime Function() _now;

  NotificationLocalDatasourceImpl(
    this._localStorage, {
    DateTime Function()? clock,
  }) : _now = clock ?? DateTime.now;

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------

  @override
  Future<void> save(AppNotification notification) async {
    final list = await _readRaw();

    // Remove duplicates by id.
    list.removeWhere((m) => m['id'] == notification.id);

    // Prepend new entry (newest first).
    list.insert(0, _toMap(notification));

    // FIFO: trim to capacity.
    if (list.length > maxCapacity) {
      list.removeRange(maxCapacity, list.length);
    }

    await _writeRaw(list);
  }

  @override
  Future<List<AppNotification>> getAll() async {
    final list = await _readRaw();

    // Expiry cleanup.
    final cutoff = _now().subtract(const Duration(days: maxAgeDays));
    final cleaned = list.where((m) {
      final ts = m['receivedAt'] as String?;
      if (ts == null) return false;
      try {
        return DateTime.parse(ts).isAfter(cutoff);
      } catch (_) {
        return false;
      }
    }).toList();

    // Persist if we removed expired entries.
    if (cleaned.length != list.length) {
      await _writeRaw(cleaned);
    }

    return cleaned.map(_fromMap).whereType<AppNotification>().toList();
  }

  @override
  Future<void> delete(String id) async {
    final list = await _readRaw();
    list.removeWhere((m) => m['id'] == id);
    await _writeRaw(list);
  }

  @override
  Future<void> markAsRead(String id) async {
    final list = await _readRaw();
    for (final m in list) {
      if (m['id'] == id) {
        m['isRead'] = true;
        break;
      }
    }
    await _writeRaw(list);
  }

  @override
  Future<void> markAllAsRead() async {
    final list = await _readRaw();
    for (final m in list) {
      m['isRead'] = true;
    }
    await _writeRaw(list);
  }

  @override
  Future<int> getUnreadCount() async {
    final list = await _readRaw();
    return list.where((m) => m['isRead'] != true).length;
  }

  @override
  Future<void> clear() async {
    await _localStorage.remove(_storageKey);
  }

  // ---------------------------------------------------------------------------
  // Serialization helpers
  // ---------------------------------------------------------------------------

  Future<List<Map<String, dynamic>>> _readRaw() async {
    final jsonStr = await _localStorage.getString(_storageKey);
    if (jsonStr == null || jsonStr.isEmpty) return [];
    try {
      final decoded = jsonDecode(jsonStr) as List<dynamic>;
      return decoded
          .whereType<Map<String, dynamic>>()
          .map(Map<String, dynamic>.from)
          .toList();
    } catch (_) {
      return [];
    }
  }

  Future<void> _writeRaw(List<Map<String, dynamic>> list) async {
    await _localStorage.setString(_storageKey, jsonEncode(list));
  }

  static Map<String, dynamic> _toMap(AppNotification n) => {
        'id': n.id,
        'type': n.type.name,
        'title': n.title,
        'body': n.body,
        'receivedAt': n.receivedAt.toIso8601String(),
        'isRead': n.isRead,
        'actionRoute': n.actionRoute,
        'data': n.data,
      };

  static AppNotification? _fromMap(Map<String, dynamic> m) {
    try {
      return AppNotification(
        id: m['id'] as String,
        type: _parseType(m['type'] as String?),
        title: m['title'] as String,
        body: m['body'] as String,
        receivedAt: DateTime.parse(m['receivedAt'] as String),
        isRead: m['isRead'] as bool? ?? false,
        actionRoute: m['actionRoute'] as String?,
        data: m['data'] != null
            ? Map<String, dynamic>.from(m['data'] as Map)
            : null,
      );
    } catch (_) {
      return null;
    }
  }

  static NotificationType _parseType(String? value) {
    if (value == null) return NotificationType.promotional;
    for (final t in NotificationType.values) {
      if (t.name == value) return t;
    }
    return NotificationType.promotional;
  }
}
