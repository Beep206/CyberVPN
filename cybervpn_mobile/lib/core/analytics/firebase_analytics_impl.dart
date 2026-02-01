import 'package:firebase_analytics/firebase_analytics.dart';

import 'package:cybervpn_mobile/core/analytics/analytics_service.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

/// Firebase Analytics implementation of [AnalyticsService].
///
/// Delegates all analytics calls to [FirebaseAnalytics]. Errors are
/// caught and logged via [AppLogger] to avoid crashing the app for
/// non-critical analytics failures.
class FirebaseAnalyticsImpl implements AnalyticsService {
  /// Creates a [FirebaseAnalyticsImpl] wrapping the given [analytics] instance.
  FirebaseAnalyticsImpl({FirebaseAnalytics? analytics})
      : _analytics = analytics ?? FirebaseAnalytics.instance;

  final FirebaseAnalytics _analytics;

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
