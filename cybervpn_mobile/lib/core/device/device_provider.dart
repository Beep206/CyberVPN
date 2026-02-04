import 'package:riverpod_annotation/riverpod_annotation.dart';

import 'package:cybervpn_mobile/core/device/device_info.dart';
import 'package:cybervpn_mobile/core/device/device_service.dart';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';

part 'device_provider.g.dart';

/// Provider for SecureStorageWrapper.
@riverpod
SecureStorageWrapper secureStorage(Ref ref) {
  return SecureStorageWrapper();
}

/// Provider for DeviceService.
@riverpod
DeviceService deviceService(Ref ref) {
  final storage = ref.watch(secureStorageProvider);
  return DeviceService(storage: storage);
}

/// Provider for current DeviceInfo.
///
/// Fetches device info from DeviceService. Can be refreshed by invalidating.
@riverpod
Future<DeviceInfo> deviceInfo(Ref ref) async {
  final service = ref.watch(deviceServiceProvider);
  return service.getDeviceInfo();
}
