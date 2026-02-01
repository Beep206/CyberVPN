/// Analytics abstraction layer for the CyberVPN application.
///
/// Provides a platform-agnostic interface for analytics tracking.
/// Concrete implementations include [FirebaseAnalyticsImpl] for production
/// analytics and [NoopAnalytics] for users who opt out of tracking.
abstract class AnalyticsService {
  /// Logs a custom analytics event.
  ///
  /// [name] is the event name (e.g. `vpn_connected`, `plan_selected`).
  /// [parameters] is an optional map of key-value pairs attached to the event.
  Future<void> logEvent(String name, {Map<String, dynamic>? parameters});

  /// Sets the user identifier for analytics attribution.
  ///
  /// Pass `null` to clear the user ID (e.g. on logout).
  Future<void> setUserId(String? userId);

  /// Sets a user-scoped property for segmentation.
  ///
  /// [name] is the property key and [value] is the property value.
  Future<void> setUserProperty({required String name, required String value});

  /// Logs a screen view event.
  ///
  /// [screenName] is the display name of the screen.
  /// [screenClass] is the optional class name of the screen widget.
  Future<void> logScreenView(String screenName, {String? screenClass});
}
