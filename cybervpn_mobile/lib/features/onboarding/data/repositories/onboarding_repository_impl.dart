import 'package:shared_preferences/shared_preferences.dart';

import 'package:cybervpn_mobile/features/onboarding/domain/constants/onboarding_pages.dart';
import 'package:cybervpn_mobile/features/onboarding/domain/entities/onboarding_page.dart';
import 'package:cybervpn_mobile/features/onboarding/domain/repositories/onboarding_repository.dart';

/// Concrete implementation of [OnboardingRepository] backed by [SharedPreferences].
///
/// Persists the onboarding completion flag under the key [_kOnboardingComplete]
/// and returns the hardcoded list of onboarding pages from
/// [getDefaultOnboardingPages].
class OnboardingRepositoryImpl implements OnboardingRepository {
  final SharedPreferences _prefs;

  OnboardingRepositoryImpl({required SharedPreferences sharedPreferences})
      : _prefs = sharedPreferences;

  // ---------------------------------------------------------------------------
  // SharedPreferences key constants
  // ---------------------------------------------------------------------------

  static const _kOnboardingComplete = 'onboarding_complete';

  // ---------------------------------------------------------------------------
  // OnboardingRepository implementation
  // ---------------------------------------------------------------------------

  @override
  Future<bool> hasCompletedOnboarding() async {
    return _prefs.getBool(_kOnboardingComplete) ?? false;
  }

  @override
  Future<void> completeOnboarding() async {
    await _prefs.setBool(_kOnboardingComplete, true);
  }

  @override
  Future<List<OnboardingPage>> getPages() async {
    return getDefaultOnboardingPages();
  }
}
