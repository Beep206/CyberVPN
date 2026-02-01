import 'package:flutter_test/flutter_test.dart';
import 'package:in_app_review/in_app_review.dart';
import 'package:mocktail/mocktail.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:cybervpn_mobile/features/review/data/services/review_service.dart';

class MockInAppReview extends Mock implements InAppReview {}

void main() {
  late ReviewService reviewService;
  late SharedPreferences prefs;
  late MockInAppReview mockInAppReview;

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    prefs = await SharedPreferences.getInstance();
    mockInAppReview = MockInAppReview();
    reviewService = ReviewService(
      prefs: prefs,
      inAppReview: mockInAppReview,
    );
  });

  group('ReviewService', () {
    group('incrementConnectionCount', () {
      test('increments connection count from 0 to 1', () async {
        await reviewService.incrementConnectionCount();
        expect(prefs.getInt('review_connection_count'), 1);
      });

      test('increments connection count from existing value', () async {
        await prefs.setInt('review_connection_count', 3);
        await reviewService.incrementConnectionCount();
        expect(prefs.getInt('review_connection_count'), 4);
      });

      test('multiple increments work correctly', () async {
        for (int i = 0; i < 5; i++) {
          await reviewService.incrementConnectionCount();
        }
        expect(prefs.getInt('review_connection_count'), 5);
      });
    });

    group('shouldShowReview', () {
      test('returns false when connection count is less than 5', () async {
        await prefs.setInt('review_connection_count', 4);
        await prefs.setString(
          'review_first_install_date',
          DateTime.now().subtract(const Duration(days: 30)).toIso8601String(),
        );
        expect(reviewService.shouldShowReview(), false);
      });

      test('returns false when days since install is less than 7', () async {
        await prefs.setInt('review_connection_count', 10);
        await prefs.setString(
          'review_first_install_date',
          DateTime.now().subtract(const Duration(days: 6)).toIso8601String(),
        );
        expect(reviewService.shouldShowReview(), false);
      });

      test('returns false when prompted within 90 days', () async {
        await prefs.setInt('review_connection_count', 10);
        await prefs.setString(
          'review_first_install_date',
          DateTime.now().subtract(const Duration(days: 100)).toIso8601String(),
        );
        await prefs.setString(
          'review_last_prompt_date',
          DateTime.now().subtract(const Duration(days: 50)).toIso8601String(),
        );
        expect(reviewService.shouldShowReview(), false);
      });

      test('returns false when already shown 3 times this year', () async {
        final currentYear = DateTime.now().year;
        await prefs.setInt('review_connection_count', 10);
        await prefs.setString(
          'review_first_install_date',
          DateTime.now().subtract(const Duration(days: 100)).toIso8601String(),
        );
        await prefs.setInt('review_yearly_prompt_year', currentYear);
        await prefs.setInt('review_yearly_prompt_count', 3);
        expect(reviewService.shouldShowReview(), false);
      });

      test('returns true when all conditions are met', () async {
        await prefs.setInt('review_connection_count', 5);
        await prefs.setString(
          'review_first_install_date',
          DateTime.now().subtract(const Duration(days: 7)).toIso8601String(),
        );
        expect(reviewService.shouldShowReview(), true);
      });

      test('returns true when 90-day cooldown has passed', () async {
        await prefs.setInt('review_connection_count', 10);
        await prefs.setString(
          'review_first_install_date',
          DateTime.now().subtract(const Duration(days: 200)).toIso8601String(),
        );
        await prefs.setString(
          'review_last_prompt_date',
          DateTime.now().subtract(const Duration(days: 91)).toIso8601String(),
        );
        expect(reviewService.shouldShowReview(), true);
      });

      test('resets yearly counter on new year', () async {
        final lastYear = DateTime.now().year - 1;
        await prefs.setInt('review_connection_count', 10);
        await prefs.setString(
          'review_first_install_date',
          DateTime.now().subtract(const Duration(days: 365)).toIso8601String(),
        );
        await prefs.setInt('review_yearly_prompt_year', lastYear);
        await prefs.setInt('review_yearly_prompt_count', 3);

        // shouldShowReview will reset the counter for the new year
        expect(reviewService.shouldShowReview(), true);
      });
    });

    group('recordPromptShown', () {
      test('updates last prompt date', () async {
        final beforeRecord = DateTime.now();
        await reviewService.recordPromptShown();
        final afterRecord = DateTime.now();

        final savedDateStr = prefs.getString('review_last_prompt_date');
        expect(savedDateStr, isNotNull);

        final savedDate = DateTime.parse(savedDateStr!);
        expect(
          savedDate.isAfter(beforeRecord.subtract(const Duration(seconds: 1))),
          true,
        );
        expect(savedDate.isBefore(afterRecord.add(const Duration(seconds: 1))),
            true);
      });

      test('increments yearly prompt count', () async {
        final currentYear = DateTime.now().year;
        await prefs.setInt('review_yearly_prompt_year', currentYear);
        await prefs.setInt('review_yearly_prompt_count', 1);

        await reviewService.recordPromptShown();

        expect(prefs.getInt('review_yearly_prompt_count'), 2);
        expect(prefs.getInt('review_yearly_prompt_year'), currentYear);
      });

      test('initializes yearly counter for new year', () async {
        final lastYear = DateTime.now().year - 1;
        await prefs.setInt('review_yearly_prompt_year', lastYear);
        await prefs.setInt('review_yearly_prompt_count', 3);

        await reviewService.recordPromptShown();

        expect(prefs.getInt('review_yearly_prompt_count'), 1);
        expect(prefs.getInt('review_yearly_prompt_year'), DateTime.now().year);
      });
    });

    group('requestReview', () {
      test('returns false when conditions not met', () async {
        await prefs.setInt('review_connection_count', 2); // Less than 5
        final result = await reviewService.requestReview();
        expect(result, false);
        verifyNever(() => mockInAppReview.isAvailable());
      });

      test('returns false when in-app review not available', () async {
        await prefs.setInt('review_connection_count', 5);
        await prefs.setString(
          'review_first_install_date',
          DateTime.now().subtract(const Duration(days: 7)).toIso8601String(),
        );
        when(() => mockInAppReview.isAvailable())
            .thenAnswer((_) async => false);

        final result = await reviewService.requestReview();
        expect(result, false);
        verify(() => mockInAppReview.isAvailable()).called(1);
        verifyNever(() => mockInAppReview.requestReview());
      });

      test('requests review and records prompt when conditions met', () async {
        await prefs.setInt('review_connection_count', 5);
        await prefs.setString(
          'review_first_install_date',
          DateTime.now().subtract(const Duration(days: 7)).toIso8601String(),
        );
        when(() => mockInAppReview.isAvailable()).thenAnswer((_) async => true);
        when(() => mockInAppReview.requestReview()).thenAnswer((_) async {});

        final result = await reviewService.requestReview();

        expect(result, true);
        verify(() => mockInAppReview.isAvailable()).called(1);
        verify(() => mockInAppReview.requestReview()).called(1);
        expect(prefs.getString('review_last_prompt_date'), isNotNull);
        expect(prefs.getInt('review_yearly_prompt_count'), 1);
      });

      test('returns false and logs error when requestReview throws', () async {
        await prefs.setInt('review_connection_count', 5);
        await prefs.setString(
          'review_first_install_date',
          DateTime.now().subtract(const Duration(days: 7)).toIso8601String(),
        );
        when(() => mockInAppReview.isAvailable()).thenAnswer((_) async => true);
        when(() => mockInAppReview.requestReview())
            .thenThrow(Exception('Platform error'));

        final result = await reviewService.requestReview();

        expect(result, false);
        verify(() => mockInAppReview.requestReview()).called(1);
        // Should NOT record the prompt when it fails
        expect(prefs.getString('review_last_prompt_date'), isNull);
      });
    });

    group('openStorePage', () {
      test('opens store listing successfully', () async {
        when(() => mockInAppReview.openStoreListing())
            .thenAnswer((_) async {});

        await reviewService.openStorePage();

        verify(() => mockInAppReview.openStoreListing()).called(1);
      });

      test('handles errors when opening store page', () async {
        when(() => mockInAppReview.openStoreListing())
            .thenThrow(Exception('Store not available'));

        // Should not throw
        await reviewService.openStorePage();

        verify(() => mockInAppReview.openStoreListing()).called(1);
      });
    });

    group('reset', () {
      test('clears all review data and re-initializes first install date',
          () async {
        await prefs.setInt('review_connection_count', 10);
        await prefs.setString('review_last_prompt_date',
            DateTime.now().toIso8601String());
        await prefs.setInt('review_yearly_prompt_count', 2);
        await prefs.setInt('review_yearly_prompt_year', 2024);

        await reviewService.reset();

        expect(prefs.getInt('review_connection_count'), isNull);
        expect(prefs.getString('review_last_prompt_date'), isNull);
        expect(prefs.getInt('review_yearly_prompt_count'), isNull);
        expect(prefs.getInt('review_yearly_prompt_year'), isNull);
        // First install date should be re-created
        expect(prefs.getString('review_first_install_date'), isNotNull);
      });
    });

    group('getMetrics', () {
      test('returns correct metrics', () async {
        final installDate =
            DateTime.now().subtract(const Duration(days: 10));
        final lastPromptDate =
            DateTime.now().subtract(const Duration(days: 95)); // > 90 days cooldown

        await prefs.setInt('review_connection_count', 7);
        await prefs.setString(
            'review_first_install_date', installDate.toIso8601String());
        await prefs.setString(
            'review_last_prompt_date', lastPromptDate.toIso8601String());
        await prefs.setInt('review_yearly_prompt_count', 1);
        await prefs.setInt('review_yearly_prompt_year', DateTime.now().year);

        final metrics = reviewService.getMetrics();

        expect(metrics['connectionCount'], 7);
        expect(metrics['daysSinceInstall'], 10);
        expect(metrics['daysSinceLastPrompt'], 95);
        expect(metrics['yearlyPromptCount'], 1);
        expect(metrics['yearlyPromptYear'], DateTime.now().year);
        expect(metrics['shouldShowReview'], true);
      });
    });
  });
}
