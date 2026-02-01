import 'package:cybervpn_mobile/features/onboarding/domain/entities/onboarding_page.dart';

/// Returns the default list of onboarding pages shown on first launch.
///
/// The pages are ordered as: privacy, connect, globe, get-started.
/// Only the final page (get-started) includes an [OnboardingPage.actionLabel].
List<OnboardingPage> getDefaultOnboardingPages() {
  return const [
    OnboardingPage(
      titleKey: 'onboarding.privacy.title',
      descriptionKey: 'onboarding.privacy.description',
      animationAsset: 'assets/animations/privacy.json',
    ),
    OnboardingPage(
      titleKey: 'onboarding.connect.title',
      descriptionKey: 'onboarding.connect.description',
      animationAsset: 'assets/animations/connect.json',
    ),
    OnboardingPage(
      titleKey: 'onboarding.globe.title',
      descriptionKey: 'onboarding.globe.description',
      animationAsset: 'assets/animations/globe.json',
    ),
    OnboardingPage(
      titleKey: 'onboarding.getStarted.title',
      descriptionKey: 'onboarding.getStarted.description',
      animationAsset: 'assets/animations/get_started.json',
      actionLabel: 'onboarding.getStarted.action',
    ),
  ];
}
