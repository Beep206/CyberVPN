import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/device.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/oauth_provider.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/profile.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/setup_2fa_result.dart';
import 'package:cybervpn_mobile/features/profile/domain/repositories/profile_repository.dart';
import 'package:cybervpn_mobile/features/profile/presentation/providers/profile_provider.dart';
import 'package:cybervpn_mobile/core/di/providers.dart'
    show profileRepositoryProvider;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

class MockProfileRepository extends Mock implements ProfileRepository {}

// ---------------------------------------------------------------------------
// Test data
// ---------------------------------------------------------------------------

const tProfile = Profile(
  id: 'user-1',
  email: 'test@example.com',
  username: 'testuser',
  is2FAEnabled: false,
  linkedProviders: [],
);

const tProfileWith2FA = Profile(
  id: 'user-1',
  email: 'test@example.com',
  username: 'testuser',
  is2FAEnabled: true,
  linkedProviders: [],
);

const tProfileWithTelegram = Profile(
  id: 'user-1',
  email: 'test@example.com',
  username: 'testuser',
  is2FAEnabled: false,
  linkedProviders: [OAuthProvider.telegram],
);

final tDevices = [
  const Device(id: 'dev-1', name: 'iPhone 15', platform: 'iOS', isCurrent: true),
  const Device(id: 'dev-2', name: 'Pixel 8', platform: 'Android'),
];

const tSetup2FAResult = Setup2FAResult(
  secret: 'JBSWY3DPEHPK3PXP',
  qrCodeUri: 'otpauth://totp/CyberVPN:test@example.com?secret=JBSWY3DPEHPK3PXP',
);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/// Creates a [ProviderContainer] with the mock repository injected.
ProviderContainer createContainer(MockProfileRepository mockRepo) {
  return ProviderContainer(
    overrides: [
      profileRepositoryProvider.overrideWithValue(mockRepo),
    ],
  );
}

/// Waits for the [profileProvider] to settle into a data or error state.
Future<void> waitForProvider(ProviderContainer container) async {
  // Trigger the build by reading the provider.
  container.read(profileProvider);
  // Allow microtasks to complete.
  await Future<void>.delayed(Duration.zero);
  await Future<void>.delayed(Duration.zero);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  late MockProfileRepository mockRepo;

  setUp(() {
    mockRepo = MockProfileRepository();
  });

  // ---------------------------------------------------------------------------
  // ProfileState
  // ---------------------------------------------------------------------------
  group('ProfileState', () {
    test('defaults have correct values', () {
      const state = ProfileState();
      expect(state.profile, isNull);
      expect(state.devices, isEmpty);
      expect(state.is2FAEnabled, isFalse);
      expect(state.linkedProviders, isEmpty);
      expect(state.linkedAccountsCount, 0);
    });

    test('is2FAEnabled delegates to profile', () {
      const state = ProfileState(profile: tProfileWith2FA);
      expect(state.is2FAEnabled, isTrue);
    });

    test('linkedProviders delegates to profile', () {
      const state = ProfileState(profile: tProfileWithTelegram);
      expect(state.linkedProviders, [OAuthProvider.telegram]);
      expect(state.linkedAccountsCount, 1);
    });

    test('copyWith replaces profile', () {
      final state = ProfileState(profile: tProfile, devices: tDevices);
      final updated = state.copyWith(profile: () => tProfileWith2FA);
      expect(updated.is2FAEnabled, isTrue);
      expect(updated.devices, tDevices);
    });

    test('copyWith replaces devices', () {
      final state = ProfileState(profile: tProfile, devices: tDevices);
      final updated = state.copyWith(devices: []);
      expect(updated.devices, isEmpty);
      expect(updated.profile, tProfile);
    });
  });

  // ---------------------------------------------------------------------------
  // ProfileNotifier - build
  // ---------------------------------------------------------------------------
  group('ProfileNotifier build', () {
    test('loads profile and devices on initialization', () async {
      when(() => mockRepo.getProfile()).thenAnswer((_) async => const Success(tProfile));
      when(() => mockRepo.getDevices()).thenAnswer((_) async => Success(tDevices));

      final container = createContainer(mockRepo);
      await waitForProvider(container);

      final result = container.read(profileProvider);
      expect(result.value, isNotNull);
      expect(result.value!.profile, tProfile);
      expect(result.value!.devices, tDevices);

      verify(() => mockRepo.getProfile()).called(1);
      verify(() => mockRepo.getDevices()).called(1);

      container.dispose();
    });

    test('sets error state when getProfile fails', () async {
      when(() => mockRepo.getProfile()).thenThrow(Exception('network error'));
      when(() => mockRepo.getDevices()).thenAnswer((_) async => const Success(<Device>[]));

      final container = createContainer(mockRepo);
      await waitForProvider(container);

      final result = container.read(profileProvider);
      expect(result.hasError, isTrue);

      container.dispose();
    });
  });

  // ---------------------------------------------------------------------------
  // ProfileNotifier - setup2FA
  // ---------------------------------------------------------------------------
  group('ProfileNotifier setup2FA', () {
    test('calls use case and returns result', () async {
      when(() => mockRepo.getProfile()).thenAnswer((_) async => const Success(tProfile));
      when(() => mockRepo.getDevices()).thenAnswer((_) async => Success(tDevices));
      when(() => mockRepo.setup2FA()).thenAnswer((_) async => const Success(tSetup2FAResult));

      final container = createContainer(mockRepo);
      await waitForProvider(container);

      final notifier = container.read(profileProvider.notifier);
      final result = await notifier.setup2FA();

      expect(result.secret, tSetup2FAResult.secret);
      expect(result.qrCodeUri, tSetup2FAResult.qrCodeUri);
      verify(() => mockRepo.setup2FA()).called(1);

      container.dispose();
    });
  });

  // ---------------------------------------------------------------------------
  // ProfileNotifier - verify2FA
  // ---------------------------------------------------------------------------
  group('ProfileNotifier verify2FA', () {
    test('updates state when verification succeeds', () async {
      when(() => mockRepo.getProfile())
          .thenAnswer((_) async => const Success(tProfile));
      when(() => mockRepo.getDevices()).thenAnswer((_) async => Success(tDevices));
      when(() => mockRepo.verify2FA('123456')).thenAnswer((_) async => const Success(true));

      final container = createContainer(mockRepo);
      await waitForProvider(container);

      // After verify, getProfile is called again to refresh state.
      when(() => mockRepo.getProfile())
          .thenAnswer((_) async => const Success(tProfileWith2FA));

      final notifier = container.read(profileProvider.notifier);
      final success = await notifier.verify2FA('123456');

      expect(success, isTrue);
      // Profile should now show 2FA enabled.
      expect(container.read(profileProvider).value?.is2FAEnabled, isTrue);
      verify(() => mockRepo.verify2FA('123456')).called(1);

      container.dispose();
    });
  });

  // ---------------------------------------------------------------------------
  // ProfileNotifier - disable2FA
  // ---------------------------------------------------------------------------
  group('ProfileNotifier disable2FA', () {
    test('updates state when disable succeeds', () async {
      when(() => mockRepo.getProfile())
          .thenAnswer((_) async => const Success(tProfileWith2FA));
      when(() => mockRepo.getDevices()).thenAnswer((_) async => Success(tDevices));
      when(() => mockRepo.disable2FA('654321'))
          .thenAnswer((_) async => const Success<void>(null));

      final container = createContainer(mockRepo);
      await waitForProvider(container);

      expect(container.read(profileProvider).value?.is2FAEnabled, isTrue);

      // After disable, getProfile returns profile without 2FA.
      when(() => mockRepo.getProfile()).thenAnswer((_) async => const Success(tProfile));

      final notifier = container.read(profileProvider.notifier);
      await notifier.disable2FA('654321');

      expect(container.read(profileProvider).value?.is2FAEnabled, isFalse);
      verify(() => mockRepo.disable2FA('654321')).called(1);

      container.dispose();
    });
  });

  // ---------------------------------------------------------------------------
  // ProfileNotifier - OAuth linking / unlinkAccount
  // ---------------------------------------------------------------------------
  group('ProfileNotifier OAuth linking', () {
    test('getTelegramAuthUrl returns authorization URL', () async {
      when(() => mockRepo.getProfile()).thenAnswer((_) async => const Success(tProfile));
      when(() => mockRepo.getDevices()).thenAnswer((_) async => Success(tDevices));
      when(() => mockRepo.getOAuthAuthorizationUrl(OAuthProvider.telegram))
          .thenAnswer((_) async => const Success('https://auth.example.com/telegram'));

      final container = createContainer(mockRepo);
      await waitForProvider(container);

      final notifier = container.read(profileProvider.notifier);
      final url = await notifier.getTelegramAuthUrl();

      expect(url, 'https://auth.example.com/telegram');
      verify(() => mockRepo.getOAuthAuthorizationUrl(OAuthProvider.telegram)).called(1);

      container.dispose();
    });

    test('unlinkAccount removes provider and refreshes profile', () async {
      when(() => mockRepo.getProfile())
          .thenAnswer((_) async => const Success(tProfileWithTelegram));
      when(() => mockRepo.getDevices()).thenAnswer((_) async => Success(tDevices));
      when(() => mockRepo.unlinkOAuth(OAuthProvider.telegram))
          .thenAnswer((_) async => const Success<void>(null));

      final container = createContainer(mockRepo);
      await waitForProvider(container);

      expect(
        container.read(profileProvider).value?.linkedProviders,
        contains(OAuthProvider.telegram),
      );

      // After unlink, getProfile returns profile without telegram.
      when(() => mockRepo.getProfile()).thenAnswer((_) async => const Success(tProfile));

      final notifier = container.read(profileProvider.notifier);
      await notifier.unlinkAccount(OAuthProvider.telegram);

      final linked = container.read(profileProvider).value?.linkedProviders;
      expect(linked, isNot(contains(OAuthProvider.telegram)));
      verify(() => mockRepo.unlinkOAuth(OAuthProvider.telegram)).called(1);

      container.dispose();
    });
  });

  // ---------------------------------------------------------------------------
  // ProfileNotifier - refreshProfile
  // ---------------------------------------------------------------------------
  group('ProfileNotifier refreshProfile', () {
    test('refreshes profile and devices', () async {
      when(() => mockRepo.getProfile()).thenAnswer((_) async => const Success(tProfile));
      when(() => mockRepo.getDevices()).thenAnswer((_) async => const Success(<Device>[]));

      final container = createContainer(mockRepo);
      await waitForProvider(container);

      expect(container.read(profileProvider).value?.devices, isEmpty);

      // On refresh, return updated data.
      when(() => mockRepo.getProfile())
          .thenAnswer((_) async => const Success(tProfileWith2FA));
      when(() => mockRepo.getDevices()).thenAnswer((_) async => Success(tDevices));

      final notifier = container.read(profileProvider.notifier);
      await notifier.refreshProfile();

      final updated = container.read(profileProvider).value;
      expect(updated?.is2FAEnabled, isTrue);
      expect(updated?.devices, tDevices);

      container.dispose();
    });

    test('sets error state on refresh failure', () async {
      when(() => mockRepo.getProfile()).thenAnswer((_) async => const Success(tProfile));
      when(() => mockRepo.getDevices()).thenAnswer((_) async => const Success(<Device>[]));

      final container = createContainer(mockRepo);
      await waitForProvider(container);

      when(() => mockRepo.getProfile()).thenThrow(Exception('server down'));

      final notifier = container.read(profileProvider.notifier);
      await notifier.refreshProfile();

      expect(container.read(profileProvider).hasError, isTrue);

      container.dispose();
    });
  });

  // ---------------------------------------------------------------------------
  // Derived providers
  // ---------------------------------------------------------------------------
  group('Derived providers', () {
    test('is2FAEnabledProvider returns correct value', () async {
      when(() => mockRepo.getProfile())
          .thenAnswer((_) async => const Success(tProfileWith2FA));
      when(() => mockRepo.getDevices()).thenAnswer((_) async => const Success(<Device>[]));

      final container = createContainer(mockRepo);
      await waitForProvider(container);

      expect(container.read(is2FAEnabledProvider), isTrue);

      container.dispose();
    });

    test('linkedAccountsProvider returns correct list', () async {
      when(() => mockRepo.getProfile())
          .thenAnswer((_) async => const Success(tProfileWithTelegram));
      when(() => mockRepo.getDevices()).thenAnswer((_) async => const Success(<Device>[]));

      final container = createContainer(mockRepo);
      await waitForProvider(container);

      expect(
        container.read(linkedAccountsProvider),
        [OAuthProvider.telegram],
      );
      expect(container.read(linkedAccountsCountProvider), 1);

      container.dispose();
    });

    test('devicesListProvider returns device list', () async {
      when(() => mockRepo.getProfile()).thenAnswer((_) async => const Success(tProfile));
      when(() => mockRepo.getDevices()).thenAnswer((_) async => Success(tDevices));

      final container = createContainer(mockRepo);
      await waitForProvider(container);

      expect(container.read(devicesListProvider), tDevices);

      container.dispose();
    });

    test('userProfileProvider returns profile', () async {
      when(() => mockRepo.getProfile()).thenAnswer((_) async => const Success(tProfile));
      when(() => mockRepo.getDevices()).thenAnswer((_) async => const Success(<Device>[]));

      final container = createContainer(mockRepo);
      await waitForProvider(container);

      expect(container.read(userProfileProvider), tProfile);

      container.dispose();
    });

    test('derived providers return defaults when state not loaded', () {
      // Container without overrides will have the provider in loading state
      // because the repository throws UnimplementedError.
      // Instead, test with a fresh container that has mock returning delayed.
      when(() => mockRepo.getProfile())
          .thenAnswer((_) => Future.delayed(const Duration(seconds: 10), () => const Success(tProfile)));
      when(() => mockRepo.getDevices())
          .thenAnswer((_) => Future.delayed(const Duration(seconds: 10), () => const Success(<Device>[])));

      final container = createContainer(mockRepo);
      // Read immediately before async completes.
      container.read(profileProvider);

      expect(container.read(is2FAEnabledProvider), isFalse);
      expect(container.read(linkedAccountsProvider), isEmpty);
      expect(container.read(linkedAccountsCountProvider), 0);
      expect(container.read(devicesListProvider), isEmpty);
      expect(container.read(userProfileProvider), isNull);

      container.dispose();
    });
  });
}
