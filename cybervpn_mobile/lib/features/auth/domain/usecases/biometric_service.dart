import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:local_auth/local_auth.dart';

import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_provider.dart'
    show secureStorageProvider;

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

  /// Returns the list of available biometric types on the device.
  ///
  /// Common types: [BiometricType.fingerprint], [BiometricType.face],
  /// [BiometricType.iris], [BiometricType.strong], [BiometricType.weak].
  Future<List<BiometricType>> getAvailableBiometrics() async {
    if (!await isBiometricAvailable()) {
      return [];
    }
    return _localAuth.getAvailableBiometrics();
  }

  /// Returns `true` if fingerprint authentication is available.
  Future<bool> hasFingerprintAuth() async {
    final types = await getAvailableBiometrics();
    return types.contains(BiometricType.fingerprint) ||
        types.contains(BiometricType.strong);
  }

  /// Returns `true` if face authentication is available.
  Future<bool> hasFaceAuth() async {
    final types = await getAvailableBiometrics();
    return types.contains(BiometricType.face);
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

// ---------------------------------------------------------------------------
// Riverpod Provider
// ---------------------------------------------------------------------------

/// Provider for [BiometricService].
///
/// Provides biometric authentication capabilities using the device's
/// fingerprint sensor, Face ID, or other biometric hardware.
final biometricServiceProvider = Provider<BiometricService>((ref) {
  final secureStorage = ref.watch(secureStorageProvider);
  return BiometricService(secureStorage: secureStorage);
});

/// Provider that checks if biometrics are available on this device.
final isBiometricAvailableProvider = FutureProvider<bool>((ref) async {
  final service = ref.watch(biometricServiceProvider);
  return service.isBiometricAvailable();
});

/// Provider that returns available biometric types.
final availableBiometricsProvider =
    FutureProvider<List<BiometricType>>((ref) async {
  final service = ref.watch(biometricServiceProvider);
  return service.getAvailableBiometrics();
});

/// Provider that checks if biometric login is enabled by the user.
final isBiometricEnabledProvider = FutureProvider<bool>((ref) async {
  final service = ref.watch(biometricServiceProvider);
  return service.isBiometricEnabled();
});
