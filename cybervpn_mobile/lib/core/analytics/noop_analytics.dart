import 'package:cybervpn_mobile/core/analytics/analytics_service.dart';

/// No-operation implementation of [AnalyticsService].
///
/// Used when the user has opted out of analytics tracking or when
/// analytics consent has not yet been granted. All methods return
/// immediately without performing any work or side effects.
class NoopAnalytics implements AnalyticsService {
  /// Creates a [NoopAnalytics] instance.
  const NoopAnalytics();

  @override
  Future<void> logEvent(String name, {Map<String, dynamic>? parameters}) async {
    // Intentionally empty: analytics disabled.
  }

  @override
  Future<void> setUserId(String? userId) async {
    // Intentionally empty: analytics disabled.
  }

  @override
  Future<void> setUserProperty({required String name, required String value}) async {
    // Intentionally empty: analytics disabled.
  }

  @override
  Future<void> logScreenView(String screenName, {String? screenClass}) async {
    // Intentionally empty: analytics disabled.
  }
}
