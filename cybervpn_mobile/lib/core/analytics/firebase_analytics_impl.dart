import 'dart:async';

import 'package:firebase_analytics/firebase_analytics.dart';

import 'package:cybervpn_mobile/core/analytics/analytics_service.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

/// Firebase Analytics implementation of [AnalyticsService].
///
/// Delegates all analytics calls to [FirebaseAnalytics]. Each call awaits
/// the [readyFuture] before accessing the Firebase instance, preventing
/// crashes if analytics events are logged before `Firebase.initializeApp()`
/// completes.
class FirebaseAnalyticsImpl implements AnalyticsService {
  /// Creates a [FirebaseAnalyticsImpl].
  ///
  /// [readyFuture] gates all analytics calls until Firebase is initialized.
  /// When `null`, calls proceed immediately (assume Firebase is ready).
  FirebaseAnalyticsImpl({FirebaseAnalytics? analytics, Future<void>? readyFuture})
      : _analytics = analytics ?? FirebaseAnalytics.instance,
        _readyFuture = readyFuture ?? Future<void>.value();

  final FirebaseAnalytics _analytics;
  final Future<void> _readyFuture;

  /// Exposes the underlying [FirebaseAnalytics] instance.
  ///
  /// Useful for obtaining the [FirebaseAnalyticsObserver] for navigation
  /// tracking with GoRouter.
  FirebaseAnalytics get instance => _analytics;

  @override
  Future<void> logEvent(
    String name, {
    Map<String, dynamic>? parameters,
  }) async {
    try {
      await _readyFuture;
      // Firebase expects Map<String, Object>; filter out null values
      // and cast to the expected type.
      final Map<String, Object>? safeParams = parameters != null
          ? {
              for (final entry in parameters.entries)
                if (entry.value != null) entry.key: entry.value as Object,
            }
          : null;
      await _analytics.logEvent(
        name: name,
        parameters: safeParams,
      );
    } catch (e, st) {
      AppLogger.warning('Analytics logEvent failed', error: e, stackTrace: st);
    }
  }

  @override
  Future<void> setUserId(String? userId) async {
    try {
      await _readyFuture;
      await _analytics.setUserId(id: userId);
    } catch (e, st) {
      AppLogger.warning('Analytics setUserId failed', error: e, stackTrace: st);
    }
  }

  @override
  Future<void> setUserProperty({
    required String name,
    required String value,
  }) async {
    try {
      await _readyFuture;
      await _analytics.setUserProperty(name: name, value: value);
    } catch (e, st) {
      AppLogger.warning(
        'Analytics setUserProperty failed',
        error: e,
        stackTrace: st,
      );
    }
  }

  @override
  Future<void> logScreenView(
    String screenName, {
    String? screenClass,
  }) async {
    try {
      await _readyFuture;
      await _analytics.logScreenView(
        screenName: screenName,
        screenClass: screenClass,
      );
    } catch (e, st) {
      AppLogger.warning(
        'Analytics logScreenView failed',
        error: e,
        stackTrace: st,
      );
    }
  }
}
