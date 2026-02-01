import 'package:cybervpn_mobile/features/onboarding/domain/entities/onboarding_page.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('OnboardingPage', () {
    test('creates with all required fields', () {
      const page = OnboardingPage(
        titleKey: 'onboarding.privacy.title',
        descriptionKey: 'onboarding.privacy.description',
        animationAsset: 'assets/animations/privacy.json',
      );

      expect(page.titleKey, 'onboarding.privacy.title');
      expect(page.descriptionKey, 'onboarding.privacy.description');
      expect(page.animationAsset, 'assets/animations/privacy.json');
      expect(page.actionLabel, isNull);
    });

    test('creates with optional actionLabel', () {
      const page = OnboardingPage(
        titleKey: 'onboarding.getStarted.title',
        descriptionKey: 'onboarding.getStarted.description',
        animationAsset: 'assets/animations/get_started.json',
        actionLabel: 'onboarding.getStarted.action',
      );

      expect(page.actionLabel, 'onboarding.getStarted.action');
    });

    test('copyWith updates specified fields', () {
      const page = OnboardingPage(
        titleKey: 'onboarding.privacy.title',
        descriptionKey: 'onboarding.privacy.description',
        animationAsset: 'assets/animations/privacy.json',
      );

      final updated = page.copyWith(
        actionLabel: 'onboarding.getStarted.action',
      );

      expect(updated.titleKey, 'onboarding.privacy.title');
      expect(updated.descriptionKey, 'onboarding.privacy.description');
      expect(updated.animationAsset, 'assets/animations/privacy.json');
      expect(updated.actionLabel, 'onboarding.getStarted.action');
    });

    test('equality for identical pages', () {
      const page1 = OnboardingPage(
        titleKey: 'onboarding.privacy.title',
        descriptionKey: 'onboarding.privacy.description',
        animationAsset: 'assets/animations/privacy.json',
      );
      const page2 = OnboardingPage(
        titleKey: 'onboarding.privacy.title',
        descriptionKey: 'onboarding.privacy.description',
        animationAsset: 'assets/animations/privacy.json',
      );

      expect(page1, equals(page2));
      expect(page1.hashCode, equals(page2.hashCode));
    });

    test('inequality for different pages', () {
      const page1 = OnboardingPage(
        titleKey: 'onboarding.privacy.title',
        descriptionKey: 'onboarding.privacy.description',
        animationAsset: 'assets/animations/privacy.json',
      );
      const page2 = OnboardingPage(
        titleKey: 'onboarding.connect.title',
        descriptionKey: 'onboarding.connect.description',
        animationAsset: 'assets/animations/connect.json',
      );

      expect(page1, isNot(equals(page2)));
    });

    test('toString returns meaningful representation', () {
      const page = OnboardingPage(
        titleKey: 'onboarding.privacy.title',
        descriptionKey: 'onboarding.privacy.description',
        animationAsset: 'assets/animations/privacy.json',
      );

      expect(page.toString(), contains('OnboardingPage'));
    });
  });
}
