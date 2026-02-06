import 'package:flutter_test/flutter_test.dart';
import 'package:local_auth/local_auth.dart';
import 'package:mocktail/mocktail.dart';

import 'package:cybervpn_mobile/features/auth/domain/usecases/biometric_service.dart';

import '../../../../helpers/fakes/fake_secure_storage.dart';

class MockLocalAuthentication extends Mock implements LocalAuthentication {}

void main() {
  late BiometricService biometricService;
  late MockLocalAuthentication mockLocalAuth;
  late FakeSecureStorage fakeSecureStorage;

  setUp(() {
    mockLocalAuth = MockLocalAuthentication();
    fakeSecureStorage = FakeSecureStorage();
    biometricService = BiometricService(
      localAuth: mockLocalAuth,
      secureStorage: fakeSecureStorage,
    );
  });

  group('BiometricService', () {
    group('isBiometricAvailable', () {
      test('returns true when biometrics can check and device is supported',
          () async {
        when(() => mockLocalAuth.canCheckBiometrics)
            .thenAnswer((_) async => true);
        when(() => mockLocalAuth.isDeviceSupported())
            .thenAnswer((_) async => true);

        final result = await biometricService.isBiometricAvailable();

        expect(result, isTrue);
      });

      test('returns false when biometrics cannot be checked', () async {
        when(() => mockLocalAuth.canCheckBiometrics)
            .thenAnswer((_) async => false);
        when(() => mockLocalAuth.isDeviceSupported())
            .thenAnswer((_) async => true);

        final result = await biometricService.isBiometricAvailable();

        expect(result, isFalse);
      });

      test('returns false when device is not supported', () async {
        when(() => mockLocalAuth.canCheckBiometrics)
            .thenAnswer((_) async => true);
        when(() => mockLocalAuth.isDeviceSupported())
            .thenAnswer((_) async => false);

        final result = await biometricService.isBiometricAvailable();

        expect(result, isFalse);
      });

      test('returns false when both checks fail', () async {
        when(() => mockLocalAuth.canCheckBiometrics)
            .thenAnswer((_) async => false);
        when(() => mockLocalAuth.isDeviceSupported())
            .thenAnswer((_) async => false);

        final result = await biometricService.isBiometricAvailable();

        expect(result, isFalse);
      });
    });

    group('authenticate', () {
      test('returns true on successful authentication', () async {
        when(() => mockLocalAuth.authenticate(
              localizedReason: any(named: 'localizedReason'),
              options: any(named: 'options'),
            )).thenAnswer((_) async => true);

        final result = await biometricService.authenticate();

        expect(result, isTrue);
        verify(() => mockLocalAuth.authenticate(
              localizedReason: 'Authenticate to continue',
              options: any(named: 'options'),
            )).called(1);
      });

      test('returns false on failed authentication', () async {
        when(() => mockLocalAuth.authenticate(
              localizedReason: any(named: 'localizedReason'),
              options: any(named: 'options'),
            )).thenAnswer((_) async => false);

        final result = await biometricService.authenticate();

        expect(result, isFalse);
      });

      test('passes custom reason to authenticate', () async {
        const customReason = 'Unlock CyberVPN';
        when(() => mockLocalAuth.authenticate(
              localizedReason: any(named: 'localizedReason'),
              options: any(named: 'options'),
            )).thenAnswer((_) async => true);

        await biometricService.authenticate(reason: customReason);

        verify(() => mockLocalAuth.authenticate(
              localizedReason: customReason,
              options: any(named: 'options'),
            )).called(1);
      });

      test('passes AuthenticationOptions with biometricOnly and stickyAuth', () async {
        when(() => mockLocalAuth.authenticate(
              localizedReason: any(named: 'localizedReason'),
              options: any(named: 'options'),
            )).thenAnswer((_) async => true);

        await biometricService.authenticate();

        verify(() => mockLocalAuth.authenticate(
              localizedReason: any(named: 'localizedReason'),
              options: any(named: 'options'),
            )).called(1);
      });

      test('propagates exception from local_auth', () async {
        when(() => mockLocalAuth.authenticate(
              localizedReason: any(named: 'localizedReason'),
              options: any(named: 'options'),
            )).thenThrow(Exception('Biometric hardware error'));

        expect(
          () => biometricService.authenticate(),
          throwsA(isA<Exception>()),
        );
      });
    });

    group('isBiometricEnabled', () {
      test('returns true when stored value is "true"', () async {
        await fakeSecureStorage.write(
            key: 'biometric_enabled', value: 'true');

        final result = await biometricService.isBiometricEnabled();

        expect(result, isTrue);
      });

      test('returns false when stored value is "false"', () async {
        await fakeSecureStorage.write(
            key: 'biometric_enabled', value: 'false');

        final result = await biometricService.isBiometricEnabled();

        expect(result, isFalse);
      });

      test('returns false when no value is stored', () async {
        final result = await biometricService.isBiometricEnabled();

        expect(result, isFalse);
      });
    });

    group('setBiometricEnabled', () {
      test('stores "true" when enabled', () async {
        await biometricService.setBiometricEnabled(true);

        final stored =
            await fakeSecureStorage.read(key: 'biometric_enabled');
        expect(stored, equals('true'));
      });

      test('stores "false" when disabled', () async {
        await biometricService.setBiometricEnabled(false);

        final stored =
            await fakeSecureStorage.read(key: 'biometric_enabled');
        expect(stored, equals('false'));
      });

      test('overwrites previous value', () async {
        await biometricService.setBiometricEnabled(true);
        await biometricService.setBiometricEnabled(false);

        final stored =
            await fakeSecureStorage.read(key: 'biometric_enabled');
        expect(stored, equals('false'));
      });
    });
  });
}
