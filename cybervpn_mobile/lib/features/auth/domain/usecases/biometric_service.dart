import 'package:local_auth/local_auth.dart';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';

class BiometricService {
  final LocalAuthentication _localAuth;
  final SecureStorageWrapper _secureStorage;

  // SENSITIVE: Biometric enabled flag is a security setting - must use SecureStorage
  static const String _biometricEnabledKey = 'biometric_enabled';

  BiometricService({
    LocalAuthentication? localAuth,
    required SecureStorageWrapper secureStorage,
  })  : _localAuth = localAuth ?? LocalAuthentication(),
        _secureStorage = secureStorage;

  Future<bool> isBiometricAvailable() async {
    final canCheck = await _localAuth.canCheckBiometrics;
    final isDeviceSupported = await _localAuth.isDeviceSupported();
    return canCheck && isDeviceSupported;
  }

  Future<bool> authenticate({String reason = 'Authenticate to continue'}) async {
    return _localAuth.authenticate(
      localizedReason: reason,
      options: const AuthenticationOptions(
        stickyAuth: true,
        biometricOnly: true,
      ),
    );
  }

  Future<bool> isBiometricEnabled() async {
    // SENSITIVE: Read biometric setting from SecureStorage
    final value = await _secureStorage.read(key: _biometricEnabledKey);
    return value == 'true';
  }

  Future<void> setBiometricEnabled(bool enabled) async {
    // SENSITIVE: Store biometric setting in SecureStorage (security-related preference)
    await _secureStorage.write(
      key: _biometricEnabledKey,
      value: enabled.toString(),
    );
  }
}
