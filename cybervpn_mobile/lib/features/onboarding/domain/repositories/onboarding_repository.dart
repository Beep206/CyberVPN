import 'package:cybervpn_mobile/features/onboarding/domain/entities/onboarding_page.dart';

/// Repository interface for managing the onboarding flow.
///
/// Follows the repository pattern from Clean Architecture.
/// The concrete implementation in the data layer handles
/// persistence (SharedPreferences) and provides the hardcoded
/// list of onboarding pages.
abstract class OnboardingRepository {
  /// Checks whether the user has already completed onboarding.
  ///
  /// Returns `true` if onboarding was previously completed,
  /// `false` otherwise (including on first launch).
  Future<bool> hasCompletedOnboarding();

  /// Marks onboarding as completed in persistent storage.
  ///
  /// After this call, [hasCompletedOnboarding] should return `true`.
  Future<void> completeOnboarding();

  /// Returns the ordered list of onboarding pages to display.
  ///
  /// The pages are hardcoded and include: privacy, connect, globe,
  /// and get-started.
  Future<List<OnboardingPage>> getPages();
}
