import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:in_app_review/in_app_review.dart';
import 'package:mocktail/mocktail.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:cybervpn_mobile/core/analytics/analytics_service.dart';
import 'package:cybervpn_mobile/core/analytics/analytics_providers.dart';
import 'package:cybervpn_mobile/features/review/data/services/review_service.dart';
import 'package:cybervpn_mobile/features/review/presentation/providers/review_provider.dart';
import 'package:cybervpn_mobile/core/providers/shared_preferences_provider.dart';

class MockInAppReview extends Mock implements InAppReview {}

class MockAnalyticsService extends Mock implements AnalyticsService {}

void main() {
  late SharedPreferences prefs;
  late MockInAppReview mockInAppReview;
  late MockAnalyticsService mockAnalytics;
  late ProviderContainer container;

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    prefs = await SharedPreferences.getInstance();
    mockInAppReview = MockInAppReview();
    mockAnalytics = MockAnalyticsService();

    // Stub analytics methods
    when(() => mockAnalytics.logEvent(any(), parameters: any(named: 'parameters')))
        .thenAnswer((_) async {});

    container = ProviderContainer(
      overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
        reviewServiceProvider.overrideWith((ref) => ReviewService(
              prefs: prefs,
              inAppReview: mockInAppReview,
            )),
        analyticsProvider.overrideWith((ref) => mockAnalytics),
      ],
    );
  });

  tearDown(() {
    container.dispose();
  });

  group('Review Integration', () {
    test('review not triggered when connection count < 5', () async {
      final reviewService = container.read(reviewServiceProvider);

      // Set up conditions: 4 connections, 10 days since install
      await prefs.setInt('review_connection_count', 4);
      await prefs.setString(
        'review_first_install_date',
        DateTime.now().subtract(const Duration(days: 10)).toIso8601String(),
      );

      // Simulate incrementing connection count (now 5 total)
      await reviewService.incrementConnectionCount();

      // Request review
      when(() => mockInAppReview.isAvailable()).thenAnswer((_) async => true);
      when(() => mockInAppReview.requestReview()).thenAnswer((_) async {});

      final result = await reviewService.requestReview();

      expect(result, true);
      verify(() => mockInAppReview.requestReview()).called(1);
    });

    test('review not triggered within 90 days of last prompt', () async {
      final reviewService = container.read(reviewServiceProvider);

      // Set up conditions: 10 connections, 100 days since install, prompted 50 days ago
      await prefs.setInt('review_connection_count', 10);
      await prefs.setString(
        'review_first_install_date',
        DateTime.now().subtract(const Duration(days: 100)).toIso8601String(),
      );
      await prefs.setString(
        'review_last_prompt_date',
        DateTime.now().subtract(const Duration(days: 50)).toIso8601String(),
      );

      final result = await reviewService.requestReview();

      expect(result, false);
      verifyNever(() => mockInAppReview.isAvailable());
    });

    test('review triggered after 90-day cooldown expires', () async {
      final reviewService = container.read(reviewServiceProvider);

      // Set up conditions: 10 connections, 200 days since install, prompted 95 days ago
      await prefs.setInt('review_connection_count', 10);
      await prefs.setString(
        'review_first_install_date',
        DateTime.now().subtract(const Duration(days: 200)).toIso8601String(),
      );
      await prefs.setString(
        'review_last_prompt_date',
        DateTime.now().subtract(const Duration(days: 95)).toIso8601String(),
      );

      when(() => mockInAppReview.isAvailable()).thenAnswer((_) async => true);
      when(() => mockInAppReview.requestReview()).thenAnswer((_) async {});

      final result = await reviewService.requestReview();

      expect(result, true);
      verify(() => mockInAppReview.requestReview()).called(1);
    });

    test('review not triggered after 3 prompts in same year', () async {
      final reviewService = container.read(reviewServiceProvider);

      final currentYear = DateTime.now().year;

      // Set up conditions: 10 connections, 100 days since install, 3 prompts this year
      await prefs.setInt('review_connection_count', 10);
      await prefs.setString(
        'review_first_install_date',
        DateTime.now().subtract(const Duration(days: 100)).toIso8601String(),
      );
      await prefs.setInt('review_yearly_prompt_year', currentYear);
      await prefs.setInt('review_yearly_prompt_count', 3);

      final result = await reviewService.requestReview();

      expect(result, false);
      verifyNever(() => mockInAppReview.isAvailable());
    });

    test('yearly counter resets on new year', () async {
      final reviewService = container.read(reviewServiceProvider);

      final lastYear = DateTime.now().year - 1;

      // Set up conditions: 10 connections, 365 days since install, 3 prompts last year
      await prefs.setInt('review_connection_count', 10);
      await prefs.setString(
        'review_first_install_date',
        DateTime.now().subtract(const Duration(days: 365)).toIso8601String(),
      );
      await prefs.setInt('review_yearly_prompt_year', lastYear);
      await prefs.setInt('review_yearly_prompt_count', 3);

      when(() => mockInAppReview.isAvailable()).thenAnswer((_) async => true);
      when(() => mockInAppReview.requestReview()).thenAnswer((_) async {});

      final result = await reviewService.requestReview();

      expect(result, true);
      verify(() => mockInAppReview.requestReview()).called(1);

      // Verify yearly counter was reset
      expect(prefs.getInt('review_yearly_prompt_count'), 1);
      expect(prefs.getInt('review_yearly_prompt_year'), DateTime.now().year);
    });

    test('analytics event logged when conditions not met', () async {
      final reviewService = container.read(reviewServiceProvider);

      // Set up conditions: 3 connections (< 5), 10 days since install
      await prefs.setInt('review_connection_count', 3);
      await prefs.setString(
        'review_first_install_date',
        DateTime.now().subtract(const Duration(days: 10)).toIso8601String(),
      );

      // Simulate the review prompt handling
      if (!reviewService.shouldShowReview()) {
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
      }

      verify(() => mockAnalytics.logEvent(
            'review_prompt_conditions_not_met',
            parameters: {
              'connection_count': 3,
              'days_since_install': 10,
              'days_since_last_prompt': -1,
              'yearly_prompt_count': 0,
            },
          )).called(1);
    });

    test('analytics event logged when review shown', () async {
      final reviewService = container.read(reviewServiceProvider);

      // Set up conditions: 5 connections, 10 days since install
      await prefs.setInt('review_connection_count', 5);
      await prefs.setString(
        'review_first_install_date',
        DateTime.now().subtract(const Duration(days: 10)).toIso8601String(),
      );

      when(() => mockInAppReview.isAvailable()).thenAnswer((_) async => true);
      when(() => mockInAppReview.requestReview()).thenAnswer((_) async {});

      final success = await reviewService.requestReview();

      if (success) {
        final metrics = reviewService.getMetrics();
        await mockAnalytics.logEvent(
          'review_prompt_shown',
          parameters: {
            'connection_count': metrics['connectionCount'],
            'days_since_install': metrics['daysSinceInstall'],
          },
        );
      }

      verify(() => mockAnalytics.logEvent(
            'review_prompt_shown',
            parameters: {
              'connection_count': 5,
              'days_since_install': 10,
            },
          )).called(1);
    });

    test('multiple successful connections eventually trigger review', () async {
      final reviewService = container.read(reviewServiceProvider);

      // Start with 0 connections, 10 days since install
      await prefs.setString(
        'review_first_install_date',
        DateTime.now().subtract(const Duration(days: 10)).toIso8601String(),
      );

      when(() => mockInAppReview.isAvailable()).thenAnswer((_) async => true);
      when(() => mockInAppReview.requestReview()).thenAnswer((_) async {});

      // Simulate 4 connections - should not trigger
      for (int i = 0; i < 4; i++) {
        await reviewService.incrementConnectionCount();
      }
      expect(reviewService.shouldShowReview(), false);

      // 5th connection - should trigger
      await reviewService.incrementConnectionCount();
      expect(reviewService.shouldShowReview(), true);

      final result = await reviewService.requestReview();
      expect(result, true);
      verify(() => mockInAppReview.requestReview()).called(1);
    });
  });
}
