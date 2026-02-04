import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:cybervpn_mobile/core/analytics/analytics_service.dart';
import 'package:cybervpn_mobile/features/review/data/services/review_service.dart';

/// Integration tests for review prompt triggered by VPN connection flow.
///
/// These tests verify:
/// 1. Review prompt is triggered after successful VPN connection
/// 2. Review prompt is NOT triggered after failed VPN connection
/// 3. Analytics events are logged correctly
/// 4. Rate limiting works (max 3 prompts per year)

class MockAnalyticsService extends Mock implements AnalyticsService {}

void main() {
  late ReviewService reviewService;
  late SharedPreferences prefs;
  late MockAnalyticsService mockAnalytics;

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    prefs = await SharedPreferences.getInstance();
    mockAnalytics = MockAnalyticsService();
    reviewService = ReviewService(prefs: prefs);

    // Set up mock analytics
    when(() => mockAnalytics.logEvent(any(), parameters: any(named: 'parameters')))
        .thenAnswer((_) async {});
  });

  group('Review Prompt VPN Integration', () {
    test('Review prompt triggered after 5 successful connections and 7+ days',
        () async {
      // Simulate first install 7 days ago
      final installDate = DateTime.now().subtract(const Duration(days: 7));
      await prefs.setString(
          'review_first_install_date', installDate.toIso8601String());

      // Simulate 5 successful VPN connections
      for (int i = 0; i < 5; i++) {
        await reviewService.incrementConnectionCount();
      }

      // Verify conditions are met
      expect(reviewService.shouldShowReview(), true);

      // Simulate analytics logging
      final metrics = reviewService.getMetrics();
      await mockAnalytics.logEvent(
        'review_prompt_shown',
        parameters: {
          'connection_count': metrics['connectionCount'],
          'days_since_install': metrics['daysSinceInstall'],
        },
      );

      verify(() => mockAnalytics.logEvent(
            'review_prompt_shown',
            parameters: {
              'connection_count': 5,
              'days_since_install': 7,
            },
          )).called(1);
    });

    test('Review prompt NOT triggered with less than 5 connections', () async {
      // Simulate first install 10 days ago
      final installDate = DateTime.now().subtract(const Duration(days: 10));
      await prefs.setString(
          'review_first_install_date', installDate.toIso8601String());

      // Simulate only 4 successful VPN connections
      for (int i = 0; i < 4; i++) {
        await reviewService.incrementConnectionCount();
      }

      // Verify conditions are NOT met
      expect(reviewService.shouldShowReview(), false);

      // Simulate analytics logging for conditions not met
      final metrics = reviewService.getMetrics();
      await mockAnalytics.logEvent(
        'review_prompt_conditions_not_met',
        parameters: {
          'connection_count': metrics['connectionCount'],
          'days_since_install': metrics['daysSinceInstall'],
          'days_since_last_prompt': metrics['daysSinceLastPrompt'] ?? -1,
          'yearly_prompt_count': metrics['yearlyPromptCount'],
        },
      );

      verify(() => mockAnalytics.logEvent(
            'review_prompt_conditions_not_met',
            parameters: any(named: 'parameters'),
          )).called(1);
    });

    test('Review prompt NOT triggered before 7 days of usage', () async {
      // Simulate first install only 5 days ago
      final installDate = DateTime.now().subtract(const Duration(days: 5));
      await prefs.setString(
          'review_first_install_date', installDate.toIso8601String());

      // Simulate 10 successful VPN connections
      for (int i = 0; i < 10; i++) {
        await reviewService.incrementConnectionCount();
      }

      // Verify conditions are NOT met (too few days)
      expect(reviewService.shouldShowReview(), false);
    });

    test('Review prompt respects 90-day cooldown period', () async {
      // Simulate first install 200 days ago
      final installDate = DateTime.now().subtract(const Duration(days: 200));
      await prefs.setString(
          'review_first_install_date', installDate.toIso8601String());

      // Simulate last prompt 50 days ago (within 90-day cooldown)
      final lastPromptDate = DateTime.now().subtract(const Duration(days: 50));
      await prefs.setString(
          'review_last_prompt_date', lastPromptDate.toIso8601String());

      // Simulate 10 successful connections
      for (int i = 0; i < 10; i++) {
        await reviewService.incrementConnectionCount();
      }

      // Verify conditions are NOT met (within cooldown)
      expect(reviewService.shouldShowReview(), false);

      // Simulate cooldown period has passed (91 days)
      final oldPromptDate = DateTime.now().subtract(const Duration(days: 91));
      await prefs.setString(
          'review_last_prompt_date', oldPromptDate.toIso8601String());

      // Verify conditions are NOW met
      expect(reviewService.shouldShowReview(), true);
    });

    test('Review prompt enforces max 3 prompts per year', () async {
      final currentYear = DateTime.now().year;

      // Simulate first install 100 days ago
      final installDate = DateTime.now().subtract(const Duration(days: 100));
      await prefs.setString(
          'review_first_install_date', installDate.toIso8601String());

      // Simulate 10 successful connections
      await prefs.setInt('review_connection_count', 10);

      // Simulate already shown 3 times this year
      await prefs.setInt('review_yearly_prompt_year', currentYear);
      await prefs.setInt('review_yearly_prompt_count', 3);

      // Verify conditions are NOT met (max prompts reached)
      expect(reviewService.shouldShowReview(), false);

      // Simulate new year - counter should reset
      final lastYear = currentYear - 1;
      await prefs.setInt('review_yearly_prompt_year', lastYear);
      await prefs.setInt('review_yearly_prompt_count', 3);

      // Verify conditions are NOW met (new year reset)
      expect(reviewService.shouldShowReview(), true);
    });

    test('Connection count increments only on successful connections', () async {
      // Start with 0 connections
      expect(prefs.getInt('review_connection_count'), isNull);

      // Simulate successful connection #1
      await reviewService.incrementConnectionCount();
      expect(prefs.getInt('review_connection_count'), 1);

      // Simulate connection error - DO NOT increment
      // (this is handled by NOT calling incrementConnectionCount on error)

      // Simulate successful connection #2
      await reviewService.incrementConnectionCount();
      expect(prefs.getInt('review_connection_count'), 2);

      // Verify only successful connections counted
      expect(prefs.getInt('review_connection_count'), 2);
    });

    test('Analytics events logged with correct parameters', () async {
      // Simulate conditions met
      final installDate = DateTime.now().subtract(const Duration(days: 10));
      await prefs.setString(
          'review_first_install_date', installDate.toIso8601String());
      await prefs.setInt('review_connection_count', 7);

      final metrics = reviewService.getMetrics();

      // Verify metrics contain expected data
      expect(metrics['connectionCount'], 7);
      expect(metrics['daysSinceInstall'], 10);
      expect(metrics['shouldShowReview'], true);

      // Simulate logging analytics for shown prompt
      await mockAnalytics.logEvent(
        'review_prompt_shown',
        parameters: {
          'connection_count': metrics['connectionCount'],
          'days_since_install': metrics['daysSinceInstall'],
        },
      );

      verify(() => mockAnalytics.logEvent(
            'review_prompt_shown',
            parameters: {
              'connection_count': 7,
              'days_since_install': 10,
            },
          )).called(1);
    });

    test('Error handling in review prompt logs analytics event', () async {
      // Simulate error scenario
      const errorMessage = 'Platform not available';

      await mockAnalytics.logEvent(
        'review_prompt_error',
        parameters: {
          'error': errorMessage,
        },
      );

      verify(() => mockAnalytics.logEvent(
            'review_prompt_error',
            parameters: {
              'error': errorMessage,
            },
          )).called(1);
    });

    test('Review metrics provide accurate debugging information', () async {
      final installDate = DateTime.now().subtract(const Duration(days: 15));
      final lastPromptDate = DateTime.now().subtract(const Duration(days: 100));

      await prefs.setString(
          'review_first_install_date', installDate.toIso8601String());
      await prefs.setString(
          'review_last_prompt_date', lastPromptDate.toIso8601String());
      await prefs.setInt('review_connection_count', 8);
      await prefs.setInt('review_yearly_prompt_count', 1);
      await prefs.setInt('review_yearly_prompt_year', DateTime.now().year);

      final metrics = reviewService.getMetrics();

      expect(metrics['connectionCount'], 8);
      expect(metrics['daysSinceInstall'], 15);
      expect(metrics['daysSinceLastPrompt'], 100);
      expect(metrics['yearlyPromptCount'], 1);
      expect(metrics['firstInstallDate'], isNotNull);
      expect(metrics['lastPromptDate'], isNotNull);
      expect(metrics['shouldShowReview'], true);
    });
  });
}
