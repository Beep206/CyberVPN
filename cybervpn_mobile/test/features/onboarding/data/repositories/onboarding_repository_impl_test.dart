import 'package:cybervpn_mobile/features/onboarding/data/repositories/onboarding_repository_impl.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:shared_preferences/shared_preferences.dart';

class MockSharedPreferences extends Mock implements SharedPreferences {}

void main() {
  late MockSharedPreferences mockPrefs;
  late OnboardingRepositoryImpl repository;

  setUp(() {
    mockPrefs = MockSharedPreferences();
    repository = OnboardingRepositoryImpl(sharedPreferences: mockPrefs);
  });

  group('hasCompletedOnboarding', () {
    test('returns false when key does not exist', () async {
      when(() => mockPrefs.getBool('onboarding_complete')).thenReturn(null);

      final result = await repository.hasCompletedOnboarding();

      expect(result, isFalse);
      verify(() => mockPrefs.getBool('onboarding_complete')).called(1);
    });

    test('returns false when key is false', () async {
      when(() => mockPrefs.getBool('onboarding_complete')).thenReturn(false);

      final result = await repository.hasCompletedOnboarding();

      expect(result, isFalse);
    });

    test('returns true when key is true', () async {
      when(() => mockPrefs.getBool('onboarding_complete')).thenReturn(true);

      final result = await repository.hasCompletedOnboarding();

      expect(result, isTrue);
    });
  });

  group('completeOnboarding', () {
    test('writes true to SharedPreferences', () async {
      when(() => mockPrefs.setBool('onboarding_complete', true))
          .thenAnswer((_) async => true);

      await repository.completeOnboarding();

      verify(() => mockPrefs.setBool('onboarding_complete', true)).called(1);
    });

    test('after completion, hasCompletedOnboarding returns true', () async {
      when(() => mockPrefs.setBool('onboarding_complete', true))
          .thenAnswer((_) async => true);
      when(() => mockPrefs.getBool('onboarding_complete')).thenReturn(true);

      await repository.completeOnboarding();
      final result = await repository.hasCompletedOnboarding();

      expect(result, isTrue);
    });
  });

  group('getPages', () {
    test('returns exactly 4 onboarding pages', () async {
      final pages = await repository.getPages();

      expect(pages, hasLength(4));
    });

    test('all pages have non-empty title, description, and asset', () async {
      final pages = await repository.getPages();

      for (final page in pages) {
        expect(page.titleKey, isNotEmpty);
        expect(page.descriptionKey, isNotEmpty);
        expect(page.animationAsset, isNotEmpty);
      }
    });

    test('only the last page has an actionLabel', () async {
      final pages = await repository.getPages();

      for (var i = 0; i < pages.length - 1; i++) {
        expect(pages[i].actionLabel, isNull,
            reason: 'Page $i should not have an actionLabel');
      }
      expect(pages.last.actionLabel, isNotNull,
          reason: 'Last page should have an actionLabel');
    });

    test('pages follow expected order', () async {
      final pages = await repository.getPages();

      expect(pages[0].titleKey, contains('privacy'));
      expect(pages[1].titleKey, contains('connect'));
      expect(pages[2].titleKey, contains('globe'));
      expect(pages[3].titleKey, contains('getStarted'));
    });
  });
}
