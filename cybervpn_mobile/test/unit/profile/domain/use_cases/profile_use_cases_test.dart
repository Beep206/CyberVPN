import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:cybervpn_mobile/features/profile/domain/entities/device.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/oauth_provider.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/profile.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/setup_2fa_result.dart';
import 'package:cybervpn_mobile/features/profile/domain/use_cases/setup_2fa.dart';
import 'package:cybervpn_mobile/features/profile/domain/use_cases/verify_2fa.dart';
import 'package:cybervpn_mobile/features/profile/domain/use_cases/disable_2fa.dart';
import 'package:cybervpn_mobile/features/profile/domain/use_cases/link_social_account.dart';
import 'package:cybervpn_mobile/features/profile/domain/use_cases/unlink_social_account.dart';
import 'package:cybervpn_mobile/features/profile/domain/use_cases/delete_account.dart';
import 'package:cybervpn_mobile/features/profile/domain/use_cases/get_devices.dart';
import 'package:cybervpn_mobile/features/profile/domain/use_cases/get_profile.dart';
import 'package:cybervpn_mobile/features/profile/domain/use_cases/remove_device.dart';

import '../../../../helpers/mock_repositories.dart';

void main() {
  late MockProfileRepository mockRepository;

  setUpAll(() {
    registerFallbackValue(OAuthProvider.google);
  });

  setUp(() {
    mockRepository = MockProfileRepository();
  });

  // ---------------------------------------------------------------------------
  // Setup2FAUseCase
  // ---------------------------------------------------------------------------
  group('Setup2FAUseCase', () {
    late Setup2FAUseCase useCase;

    setUp(() {
      useCase = Setup2FAUseCase(mockRepository);
    });

    test('returns Setup2FAResult from repository', () async {
      const result = Setup2FAResult(
        secret: 'JBSWY3DPEHPK3PXP',
        qrCodeUri: 'otpauth://totp/CyberVPN:user@example.com?secret=JBSWY3DPEHPK3PXP',
      );
      when(() => mockRepository.setup2FA()).thenAnswer((_) async => result);

      final actual = await useCase();

      expect(actual, equals(result));
      expect(actual.secret, equals('JBSWY3DPEHPK3PXP'));
      verify(() => mockRepository.setup2FA()).called(1);
    });
  });

  // ---------------------------------------------------------------------------
  // Verify2FAUseCase
  // ---------------------------------------------------------------------------
  group('Verify2FAUseCase', () {
    late Verify2FAUseCase useCase;

    setUp(() {
      useCase = Verify2FAUseCase(mockRepository);
    });

    test('returns true when code is valid', () async {
      when(() => mockRepository.verify2FA('123456')).thenAnswer((_) async => true);

      final result = await useCase('123456');

      expect(result, isTrue);
      verify(() => mockRepository.verify2FA('123456')).called(1);
    });

    test('throws ArgumentError when code is empty', () async {
      await expectLater(() => useCase(''), throwsA(isA<ArgumentError>()));
    });

    test('throws ArgumentError when code is not 6 digits', () async {
      await expectLater(() => useCase('12345'), throwsA(isA<ArgumentError>()));
      await expectLater(() => useCase('1234567'), throwsA(isA<ArgumentError>()));
      await expectLater(() => useCase('abcdef'), throwsA(isA<ArgumentError>()));
    });
  });

  // ---------------------------------------------------------------------------
  // Disable2FAUseCase
  // ---------------------------------------------------------------------------
  group('Disable2FAUseCase', () {
    late Disable2FAUseCase useCase;

    setUp(() {
      useCase = Disable2FAUseCase(mockRepository);
    });

    test('calls repository when code is valid', () async {
      when(() => mockRepository.disable2FA('654321')).thenAnswer((_) async {});

      await useCase('654321');

      verify(() => mockRepository.disable2FA('654321')).called(1);
    });

    test('throws ArgumentError when code is empty', () async {
      await expectLater(() => useCase(''), throwsA(isA<ArgumentError>()));
    });

    test('throws ArgumentError when code format is invalid', () async {
      await expectLater(() => useCase('abc123'), throwsA(isA<ArgumentError>()));
    });
  });

  // ---------------------------------------------------------------------------
  // LinkSocialAccountUseCase
  // ---------------------------------------------------------------------------
  group('LinkSocialAccountUseCase', () {
    late LinkSocialAccountUseCase useCase;

    setUp(() {
      useCase = LinkSocialAccountUseCase(mockRepository);
    });

    test('calls repository when provider is not yet linked', () async {
      when(() => mockRepository.linkOAuth(OAuthProvider.github))
          .thenAnswer((_) async {});

      await useCase(
        provider: OAuthProvider.github,
        currentlyLinked: const [OAuthProvider.google],
      );

      verify(() => mockRepository.linkOAuth(OAuthProvider.github)).called(1);
    });

    test('throws StateError when provider is already linked', () async {
      await expectLater(
        () => useCase(
          provider: OAuthProvider.github,
          currentlyLinked: const [OAuthProvider.github, OAuthProvider.google],
        ),
        throwsA(isA<StateError>()),
      );
    });
  });

  // ---------------------------------------------------------------------------
  // UnlinkSocialAccountUseCase
  // ---------------------------------------------------------------------------
  group('UnlinkSocialAccountUseCase', () {
    late UnlinkSocialAccountUseCase useCase;

    setUp(() {
      useCase = UnlinkSocialAccountUseCase(mockRepository);
    });

    test('calls repository when provider is currently linked', () async {
      when(() => mockRepository.unlinkOAuth(OAuthProvider.google))
          .thenAnswer((_) async {});

      await useCase(
        provider: OAuthProvider.google,
        currentlyLinked: const [OAuthProvider.google, OAuthProvider.telegram],
      );

      verify(() => mockRepository.unlinkOAuth(OAuthProvider.google)).called(1);
    });

    test('throws StateError when provider is not linked', () async {
      await expectLater(
        () => useCase(
          provider: OAuthProvider.apple,
          currentlyLinked: const [OAuthProvider.google],
        ),
        throwsA(isA<StateError>()),
      );
    });
  });

  // ---------------------------------------------------------------------------
  // DeleteAccountUseCase
  // ---------------------------------------------------------------------------
  group('DeleteAccountUseCase', () {
    late DeleteAccountUseCase useCase;

    setUp(() {
      useCase = DeleteAccountUseCase(mockRepository);
    });

    test('calls repository when password provided and 2FA disabled', () async {
      when(() => mockRepository.deleteAccount('mypassword'))
          .thenAnswer((_) async {});

      await useCase(password: 'mypassword', is2FAEnabled: false);

      verify(() => mockRepository.deleteAccount('mypassword')).called(1);
    });

    test('calls repository when password and valid TOTP provided with 2FA enabled', () async {
      when(() => mockRepository.deleteAccount('mypassword', totpCode: '123456'))
          .thenAnswer((_) async {});

      await useCase(
        password: 'mypassword',
        is2FAEnabled: true,
        totpCode: '123456',
      );

      verify(() => mockRepository.deleteAccount('mypassword', totpCode: '123456'))
          .called(1);
    });

    test('throws ArgumentError when password is empty', () async {
      await expectLater(
        () => useCase(password: '', is2FAEnabled: false),
        throwsA(isA<ArgumentError>()),
      );
    });

    test('throws ArgumentError when 2FA enabled but no TOTP code', () async {
      await expectLater(
        () => useCase(password: 'mypassword', is2FAEnabled: true),
        throwsA(isA<ArgumentError>()),
      );
    });

    test('throws ArgumentError when 2FA enabled but TOTP code is invalid format', () {
      expect(
        () => useCase(
          password: 'mypassword',
          is2FAEnabled: true,
          totpCode: 'abc',
        ),
        throwsA(isA<ArgumentError>()),
      );
    });
  });

  // ---------------------------------------------------------------------------
  // GetDevicesUseCase
  // ---------------------------------------------------------------------------
  group('GetDevicesUseCase', () {
    late GetDevicesUseCase useCase;

    setUp(() {
      useCase = GetDevicesUseCase(mockRepository);
    });

    test('returns list of devices from repository', () async {
      final devices = [
        const Device(
          id: 'dev-1',
          name: 'iPhone 15',
          platform: 'iOS',
          isCurrent: true,
        ),
        const Device(
          id: 'dev-2',
          name: 'MacBook Pro',
          platform: 'Web',
        ),
      ];
      when(() => mockRepository.getDevices()).thenAnswer((_) async => devices);

      final result = await useCase();

      expect(result, equals(devices));
      expect(result.length, equals(2));
      verify(() => mockRepository.getDevices()).called(1);
    });

    test('returns empty list when no devices', () async {
      when(() => mockRepository.getDevices()).thenAnswer((_) async => []);

      final result = await useCase();

      expect(result, isEmpty);
    });
  });

  // ---------------------------------------------------------------------------
  // RemoveDeviceUseCase
  // ---------------------------------------------------------------------------
  group('RemoveDeviceUseCase', () {
    late RemoveDeviceUseCase useCase;

    setUp(() {
      useCase = RemoveDeviceUseCase(mockRepository);
    });

    test('calls repository when removing a different device', () async {
      when(() => mockRepository.removeDevice('dev-2')).thenAnswer((_) async {});

      await useCase(deviceId: 'dev-2', currentDeviceId: 'dev-1');

      verify(() => mockRepository.removeDevice('dev-2')).called(1);
    });

    test('throws StateError when trying to remove current device', () async {
      await expectLater(
        () => useCase(deviceId: 'dev-1', currentDeviceId: 'dev-1'),
        throwsA(isA<StateError>()),
      );
    });

    test('throws ArgumentError when device ID is empty', () async {
      await expectLater(
        () => useCase(deviceId: '', currentDeviceId: 'dev-1'),
        throwsA(isA<ArgumentError>()),
      );
    });
  });

  // ---------------------------------------------------------------------------
  // GetProfileUseCase
  // ---------------------------------------------------------------------------
  group('GetProfileUseCase', () {
    late GetProfileUseCase useCase;

    setUp(() {
      useCase = GetProfileUseCase(mockRepository);
    });

    test('returns profile from repository', () async {
      const profile = Profile(
        id: 'user-1',
        email: 'test@example.com',
        username: 'testuser',
        is2FAEnabled: true,
        linkedProviders: [OAuthProvider.google],
      );
      when(() => mockRepository.getProfile()).thenAnswer((_) async => profile);

      final result = await useCase();

      expect(result, equals(profile));
      expect(result.is2FAEnabled, isTrue);
      expect(result.linkedProviders, contains(OAuthProvider.google));
      verify(() => mockRepository.getProfile()).called(1);
    });
  });
}
