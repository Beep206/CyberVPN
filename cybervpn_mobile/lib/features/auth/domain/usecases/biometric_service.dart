import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:local_auth/local_auth.dart';

import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/core/di/providers.dart'
    show secureStorageProvider;

class BiometricService {
  final LocalAuthentication _localAuth;
  final SecureStorageWrapper _secureStorage;

  // SENSITIVE: Biometric enabled flag is a security setting - must use SecureStorage
  static const String _biometricEnabledKey = 'biometric_enabled';

  // Store enrollment hash to detect changes
  static const String _enrollmentHashKey = 'biometric_enrollment_hash';

  BiometricService({
    LocalAuthentication? localAuth,
    required SecureStorageWrapper secureStorage,
  }) : _localAuth = localAuth ?? LocalAuthentication(),
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

  Future<bool> authenticate({
    String reason = 'Authenticate to continue',
  }) async {
    return _localAuth.authenticate(
      localizedReason: reason,
      options: const AuthenticationOptions(
        biometricOnly: true,
        stickyAuth: true,
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

    // Store current enrollment hash when enabling biometrics
    if (enabled) {
      await _storeEnrollmentHash();
    } else {
      await _secureStorage.delete(key: _enrollmentHashKey);
    }
  }

  // ── Enrollment Change Detection ────────────────────────────────────────────

  /// Generates a hash of the currently enrolled biometrics.
  Future<String> _generateEnrollmentHash() async {
    final types = await getAvailableBiometrics();
    // Sort to ensure consistent ordering
    final sortedTypes = types.map((t) => t.name).toList()..sort();
    return sortedTypes.join(',');
  }

  /// Stores the current enrollment hash.
  Future<void> _storeEnrollmentHash() async {
    final hash = await _generateEnrollmentHash();
    await _secureStorage.write(key: _enrollmentHashKey, value: hash);
  }

  /// Checks if biometric enrollment has changed since biometric login was enabled.
  ///
  /// Returns `true` if:
  /// - Biometric login is enabled
  /// - The current enrollment differs from the stored hash
  ///
  /// Use this to detect when a user adds/removes fingerprints or faces.
  Future<bool> hasEnrollmentChanged() async {
    final isEnabled = await isBiometricEnabled();
    if (!isEnabled) {
      return false;
    }

    final storedHash = await _secureStorage.read(key: _enrollmentHashKey);
    if (storedHash == null) {
      // No stored hash - consider this a change
      return true;
    }

    final currentHash = await _generateEnrollmentHash();
    return storedHash != currentHash;
  }

  /// Updates the stored enrollment hash to match current enrollment.
  ///
  /// Call this after user re-authenticates following an enrollment change.
  Future<void> updateEnrollmentHash() async {
    await _storeEnrollmentHash();
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
final availableBiometricsProvider = FutureProvider<List<BiometricType>>((
  ref,
) async {
  final service = ref.watch(biometricServiceProvider);
  return service.getAvailableBiometrics();
});

/// Provider that checks if biometric login is enabled by the user.
final isBiometricEnabledProvider = FutureProvider<bool>((ref) async {
  final service = ref.watch(biometricServiceProvider);
  return service.isBiometricEnabled();
});

/// Provider that checks if biometric enrollment has changed.
///
/// Returns `true` if user has added/removed biometrics since enabling
/// biometric login. This should trigger credential invalidation.
final hasEnrollmentChangedProvider = FutureProvider<bool>((ref) async {
  final service = ref.watch(biometricServiceProvider);
  return service.hasEnrollmentChanged();
});
