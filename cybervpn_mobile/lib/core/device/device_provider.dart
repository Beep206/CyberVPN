import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/device/device_info.dart';
import 'package:cybervpn_mobile/core/device/device_service.dart';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';

/// Provider for [SecureStorageWrapper].
final secureStorageProvider = Provider<SecureStorageWrapper>((ref) {
  return SecureStorageWrapper();
});

/// Provider for [DeviceService].
final deviceServiceProvider = Provider<DeviceService>((ref) {
  final storage = ref.watch(secureStorageProvider);
  return DeviceService(storage: storage);
});

/// Provider for current [DeviceInfo].
///
/// Fetches device info from DeviceService. Can be refreshed by invalidating.
final deviceInfoProvider = FutureProvider<DeviceInfo>((ref) async {
  final service = ref.watch(deviceServiceProvider);
  return service.getDeviceInfo();
});
