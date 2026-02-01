import 'package:cybervpn_mobile/features/onboarding/domain/constants/onboarding_pages.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('getDefaultOnboardingPages', () {
    test('returns exactly 4 pages', () {
      final pages = getDefaultOnboardingPages();
      expect(pages, hasLength(4));
    });

    test('first page is privacy', () {
      final pages = getDefaultOnboardingPages();
      expect(pages[0].titleKey, 'onboarding.privacy.title');
      expect(pages[0].descriptionKey, 'onboarding.privacy.description');
      expect(pages[0].animationAsset, 'assets/animations/privacy.json');
      expect(pages[0].actionLabel, isNull);
    });

    test('second page is connect', () {
      final pages = getDefaultOnboardingPages();
      expect(pages[1].titleKey, 'onboarding.connect.title');
      expect(pages[1].descriptionKey, 'onboarding.connect.description');
      expect(pages[1].animationAsset, 'assets/animations/connect.json');
      expect(pages[1].actionLabel, isNull);
    });

    test('third page is globe', () {
      final pages = getDefaultOnboardingPages();
      expect(pages[2].titleKey, 'onboarding.globe.title');
      expect(pages[2].descriptionKey, 'onboarding.globe.description');
      expect(pages[2].animationAsset, 'assets/animations/globe.json');
      expect(pages[2].actionLabel, isNull);
    });

    test('fourth page is get-started with actionLabel', () {
      final pages = getDefaultOnboardingPages();
      expect(pages[3].titleKey, 'onboarding.getStarted.title');
      expect(pages[3].descriptionKey, 'onboarding.getStarted.description');
      expect(pages[3].animationAsset, 'assets/animations/get_started.json');
      expect(pages[3].actionLabel, 'onboarding.getStarted.action');
    });

    test('only the last page has a non-null actionLabel', () {
      final pages = getDefaultOnboardingPages();
      for (var i = 0; i < pages.length - 1; i++) {
        expect(pages[i].actionLabel, isNull,
            reason: 'Page $i should not have an actionLabel');
      }
      expect(pages.last.actionLabel, isNotNull);
    });
  });
}
