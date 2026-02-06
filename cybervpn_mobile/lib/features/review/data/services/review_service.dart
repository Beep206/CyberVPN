import 'package:in_app_review/in_app_review.dart';
import 'dart:async';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:cybervpn_mobile/core/utils/app_logger.dart';

/// Service for managing in-app review prompts following platform guidelines.
///
/// Implements rate limiting and condition checking to ensure review prompts
/// are shown at optimal moments:
/// - After 5+ successful VPN connections
/// - After 7+ days of app usage
/// - Not more than once per 90 days
/// - Maximum 3 times per year
///
/// Platform Guidelines:
/// - Apple: https://developer.apple.com/design/human-interface-guidelines/ratings-and-reviews
/// - Google: https://developer.android.com/guide/playcore/in-app-review
class ReviewService {
  final SharedPreferences _prefs;
  final InAppReview _inAppReview;

  // SharedPreferences keys
  static const String _connectionCountKey = 'review_connection_count';
  static const String _firstInstallDateKey = 'review_first_install_date';
  static const String _lastPromptDateKey = 'review_last_prompt_date';
  static const String _yearlyPromptCountKey = 'review_yearly_prompt_count';
  static const String _yearlyPromptYearKey = 'review_yearly_prompt_year';

  // Trigger conditions
  static const int _minConnectionCount = 5;
  static const int _minDaysOfUsage = 7;
  static const int _cooldownDays = 90;
  static const int _maxPromptsPerYear = 3;

  ReviewService({
    required SharedPreferences prefs,
    InAppReview? inAppReview,
  })  : _prefs = prefs,
        _inAppReview = inAppReview ?? InAppReview.instance {
    _ensureFirstInstallDate();
  }

  /// Ensures the first install date is recorded on first run.
  void _ensureFirstInstallDate() {
    if (!_prefs.containsKey(_firstInstallDateKey)) {
      final now = DateTime.now();
      unawaited(_prefs.setString(_firstInstallDateKey, now.toIso8601String()));
      AppLogger.info(
        'First install date recorded: $now',
        category: 'review',
      );
    }
  }

  /// Increments the successful connection counter.
  ///
  /// Should be called after each successful VPN connection (not after errors).
  Future<void> incrementConnectionCount() async {
    final current = _prefs.getInt(_connectionCountKey) ?? 0;
    await _prefs.setInt(_connectionCountKey, current + 1);
    AppLogger.debug(
      'Connection count incremented to ${current + 1}',
      category: 'review',
    );
  }

  /// Checks if all conditions are met to show the review prompt.
  ///
  /// Returns `true` when:
  /// - Connection count >= 5
  /// - Days since install >= 7
  /// - Not prompted in the last 90 days (or never prompted)
  /// - Total prompts this year < 3
  bool shouldShowReview() {
    // Check connection count
    final connectionCount = _prefs.getInt(_connectionCountKey) ?? 0;
    if (connectionCount < _minConnectionCount) {
      AppLogger.debug(
        'Review not shown: connection count $connectionCount < $_minConnectionCount',
        category: 'review',
      );
      return false;
    }

    // Check days since install
    final firstInstallStr = _prefs.getString(_firstInstallDateKey);
    if (firstInstallStr == null) {
      AppLogger.warning(
        'Review not shown: first install date not found',
        category: 'review',
      );
      return false;
    }

    final firstInstallDate = DateTime.parse(firstInstallStr);
    final daysSinceInstall = DateTime.now().difference(firstInstallDate).inDays;
    if (daysSinceInstall < _minDaysOfUsage) {
      AppLogger.debug(
        'Review not shown: days since install $daysSinceInstall < $_minDaysOfUsage',
        category: 'review',
      );
      return false;
    }

    // Check cooldown period
    final lastPromptStr = _prefs.getString(_lastPromptDateKey);
    if (lastPromptStr != null) {
      final lastPromptDate = DateTime.parse(lastPromptStr);
      final daysSinceLastPrompt =
          DateTime.now().difference(lastPromptDate).inDays;
      if (daysSinceLastPrompt < _cooldownDays) {
        AppLogger.debug(
          'Review not shown: last prompt was $daysSinceLastPrompt days ago (cooldown: $_cooldownDays days)',
          category: 'review',
        );
        return false;
      }
    }

    // Check yearly prompt limit
    final currentYear = DateTime.now().year;
    final savedYear = _prefs.getInt(_yearlyPromptYearKey);
    int yearlyCount = 0;

    if (savedYear == currentYear) {
      yearlyCount = _prefs.getInt(_yearlyPromptCountKey) ?? 0;
    } else {
      // New year - reset counter
      unawaited(_prefs.setInt(_yearlyPromptYearKey, currentYear));
      unawaited(_prefs.setInt(_yearlyPromptCountKey, 0));
    }

    if (yearlyCount >= _maxPromptsPerYear) {
      AppLogger.debug(
        'Review not shown: already shown $yearlyCount times this year (max: $_maxPromptsPerYear)',
        category: 'review',
      );
      return false;
    }

    AppLogger.info(
      'Review conditions met: connections=$connectionCount, days=$daysSinceInstall, yearly=$yearlyCount',
      category: 'review',
    );
    return true;
  }

  /// Records that a review prompt was shown.
  ///
  /// Updates the last prompt date and increments the yearly counter.
  /// Should be called after successfully requesting a review.
  Future<void> recordPromptShown() async {
    final now = DateTime.now();
    await _prefs.setString(_lastPromptDateKey, now.toIso8601String());

    final currentYear = now.year;
    final savedYear = _prefs.getInt(_yearlyPromptYearKey);
    int yearlyCount = 0;

    if (savedYear == currentYear) {
      yearlyCount = _prefs.getInt(_yearlyPromptCountKey) ?? 0;
    }

    await _prefs.setInt(_yearlyPromptYearKey, currentYear);
    await _prefs.setInt(_yearlyPromptCountKey, yearlyCount + 1);

    AppLogger.info(
      'Review prompt recorded: date=$now, yearly_count=${yearlyCount + 1}',
      category: 'review',
    );
  }

  /// Requests the native in-app review dialog if conditions are met.
  ///
  /// Returns `true` if the review was requested, `false` if conditions were
  /// not met or the platform does not support in-app review.
  ///
  /// Platform behavior:
  /// - iOS: Shows SKStoreReviewController dialog (limited to 3 times/year by Apple)
  /// - Android: Shows Google Play in-app review dialog
  /// - Other platforms: May not show anything
  Future<bool> requestReview() async {
    if (!shouldShowReview()) {
      return false;
    }

    try {
      final isAvailable = await _inAppReview.isAvailable();
      if (!isAvailable) {
        AppLogger.warning(
          'In-app review not available on this platform',
          category: 'review',
        );
        return false;
      }

      await _inAppReview.requestReview();
      await recordPromptShown();

      AppLogger.info(
        'In-app review requested successfully',
        category: 'review',
      );
      return true;
    } catch (e, st) {
      AppLogger.error(
        'Failed to request in-app review',
        error: e,
        stackTrace: st,
        category: 'review',
      );
      return false;
    }
  }

  /// Opens the app store page for manual review (used for "Rate Us" buttons).
  ///
  /// Unlike [requestReview], this always opens the store and does not count
  /// towards the automated prompt limits.
  Future<void> openStorePage() async {
    try {
      await _inAppReview.openStoreListing();
      AppLogger.info(
        'Opened store page for manual review',
        category: 'review',
      );
    } catch (e, st) {
      AppLogger.error(
        'Failed to open store page',
        error: e,
        stackTrace: st,
        category: 'review',
      );
    }
  }

  // -- Debug/testing helpers ------------------------------------------------

  /// Resets all review-related data (for testing).
  Future<void> reset() async {
    await _prefs.remove(_connectionCountKey);
    await _prefs.remove(_firstInstallDateKey);
    await _prefs.remove(_lastPromptDateKey);
    await _prefs.remove(_yearlyPromptCountKey);
    await _prefs.remove(_yearlyPromptYearKey);
    _ensureFirstInstallDate();
    AppLogger.info('Review service reset', category: 'review');
  }

  /// Gets current review metrics for debugging.
  Map<String, dynamic> getMetrics() {
    final firstInstallStr = _prefs.getString(_firstInstallDateKey);
    final lastPromptStr = _prefs.getString(_lastPromptDateKey);

    return {
      'connectionCount': _prefs.getInt(_connectionCountKey) ?? 0,
      'firstInstallDate': firstInstallStr,
      'daysSinceInstall': firstInstallStr != null
          ? DateTime.now().difference(DateTime.parse(firstInstallStr)).inDays
          : null,
      'lastPromptDate': lastPromptStr,
      'daysSinceLastPrompt': lastPromptStr != null
          ? DateTime.now().difference(DateTime.parse(lastPromptStr)).inDays
          : null,
      'yearlyPromptCount': _prefs.getInt(_yearlyPromptCountKey) ?? 0,
      'yearlyPromptYear': _prefs.getInt(_yearlyPromptYearKey),
      'shouldShowReview': shouldShowReview(),
    };
  }
}
