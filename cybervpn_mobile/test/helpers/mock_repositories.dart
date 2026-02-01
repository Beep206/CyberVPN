import 'package:mocktail/mocktail.dart';

import 'package:cybervpn_mobile/features/auth/domain/repositories/auth_repository.dart';
import 'package:cybervpn_mobile/features/servers/domain/repositories/server_repository.dart';
import 'package:cybervpn_mobile/features/subscription/domain/repositories/subscription_repository.dart';
import 'package:cybervpn_mobile/features/vpn/domain/repositories/vpn_repository.dart';
import 'package:cybervpn_mobile/features/config_import/domain/repositories/config_import_repository.dart';
import 'package:cybervpn_mobile/features/onboarding/domain/repositories/onboarding_repository.dart';
import 'package:cybervpn_mobile/features/profile/domain/repositories/profile_repository.dart';

/// Mocktail mock for [AuthRepository].
class MockAuthRepository extends Mock implements AuthRepository {}

/// Mocktail mock for [ServerRepository].
class MockServerRepository extends Mock implements ServerRepository {}

/// Mocktail mock for [SubscriptionRepository].
class MockSubscriptionRepository extends Mock implements SubscriptionRepository {}

/// Mocktail mock for [VpnRepository].
class MockVpnRepository extends Mock implements VpnRepository {}

/// Mocktail mock for [ConfigImportRepository].
class MockConfigImportRepository extends Mock implements ConfigImportRepository {}

/// Mocktail mock for [OnboardingRepository].
class MockOnboardingRepository extends Mock implements OnboardingRepository {}

/// Mocktail mock for [ProfileRepository].
class MockProfileRepository extends Mock implements ProfileRepository {}
