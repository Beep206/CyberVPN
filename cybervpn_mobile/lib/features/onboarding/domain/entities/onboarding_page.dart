import 'package:freezed_annotation/freezed_annotation.dart';

part 'onboarding_page.freezed.dart';

/// A single page displayed during the onboarding flow.
///
/// Each page contains localisation keys for title and description, a path to
/// a Lottie animation asset, and an optional call-to-action label.
@freezed
sealed class OnboardingPage with _$OnboardingPage {
  const factory OnboardingPage({
    /// Localisation key for the page title (e.g. 'onboarding.privacy.title').
    required String titleKey,

    /// Localisation key for the page description.
    required String descriptionKey,

    /// Path to the Lottie animation asset (e.g. 'assets/animations/privacy.json').
    required String animationAsset,

    /// Optional CTA button label localisation key.
    /// Typically only set on the final onboarding page.
    String? actionLabel,
  }) = _OnboardingPage;
}
