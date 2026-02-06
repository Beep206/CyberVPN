import 'package:firebase_analytics/firebase_analytics.dart';
import 'dart:async';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:cybervpn_mobile/core/analytics/analytics_service.dart';
import 'package:cybervpn_mobile/core/analytics/firebase_analytics_impl.dart';
import 'package:cybervpn_mobile/core/analytics/noop_analytics.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/core/providers/shared_preferences_provider.dart';

/// Key used to persist the user's analytics consent preference.
const String analyticsConsentKey = 'analytics_consent';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/// Whether Firebase has been successfully initialized in the current process.
bool get _firebaseAvailable => Firebase.apps.isNotEmpty;

/// Completer that resolves when Firebase initialization finishes.
///
/// Analytics calls are gated behind this to prevent race conditions
/// when events are logged before `Firebase.initializeApp()` returns.
final Completer<void> _firebaseReadyCompleter = Completer<void>();

/// Marks Firebase as initialized. Call this from `main()` after
/// `Firebase.initializeApp()` completes.
void markFirebaseReady() {
  if (!_firebaseReadyCompleter.isCompleted) {
    _firebaseReadyCompleter.complete();
  }
}

/// Synchronizes the Firebase Analytics collection-enabled flag with the
/// given [enabled] value.
///
/// When Firebase is not available (e.g. missing platform config) this is a
/// no-op so the app does not crash.
Future<void> _syncAnalyticsCollection(bool enabled) async {
  if (!_firebaseAvailable) return;
  try {
    await FirebaseAnalytics.instance.setAnalyticsCollectionEnabled(enabled);
    AppLogger.info(
      'Firebase Analytics collection ${enabled ? "enabled" : "disabled"}',
      category: 'analytics',
    );
  } catch (e, st) {
    AppLogger.warning(
      'Failed to toggle Firebase Analytics collection',
      error: e,
      stackTrace: st,
      category: 'analytics',
    );
  }
}

// ---------------------------------------------------------------------------
// Analytics consent
// ---------------------------------------------------------------------------

/// Manages the user's analytics consent preference.
///
/// Reads the initial value from [SharedPreferences] and defaults to `false`
/// (opted out) when no preference has been stored. When the consent state
/// changes, the Firebase Analytics collection-enabled flag is updated
/// accordingly to comply with GDPR / privacy requirements.
class AnalyticsConsentNotifier extends Notifier<bool> {
  @override
  bool build() {
    final prefs = ref.watch(sharedPreferencesProvider);
    final consent = prefs.getBool(analyticsConsentKey) ?? false;

    // Ensure the Firebase collection state matches the persisted preference
    // on first build (e.g. app cold start).
    unawaited(_syncAnalyticsCollection(consent));

    return consent;
  }

  /// Updates the consent state, persists it to [SharedPreferences], and
  /// toggles Firebase Analytics data collection.
  Future<void> setConsent(bool value) async {
    final prefs = ref.read(sharedPreferencesProvider);
    await prefs.setBool(analyticsConsentKey, value);
    await _syncAnalyticsCollection(value);
    state = value;
  }
}

/// Provides the current analytics consent state.
///
/// Returns `true` when the user has explicitly opted in to analytics
/// tracking. Defaults to `false` (opted out) when no preference is stored.
final analyticsConsentProvider =
    NotifierProvider<AnalyticsConsentNotifier, bool>(
  AnalyticsConsentNotifier.new,
);

// ---------------------------------------------------------------------------
// Analytics service
// ---------------------------------------------------------------------------

/// Provides the appropriate [AnalyticsService] implementation based on
/// the user's consent state.
///
/// Returns [FirebaseAnalyticsImpl] when consent is granted **and** Firebase
/// is available, or [NoopAnalytics] otherwise.
final analyticsProvider = Provider<AnalyticsService>((ref) {
  final hasConsent = ref.watch(analyticsConsentProvider);
  if (hasConsent && _firebaseAvailable) {
    return FirebaseAnalyticsImpl(readyFuture: _firebaseReadyCompleter.future);
  }
  return const NoopAnalytics();
});
