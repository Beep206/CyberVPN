import 'package:freezed_annotation/freezed_annotation.dart';

part 'device_info.freezed.dart';
part 'device_info.g.dart';

/// Platform identifiers matching backend enum.
enum DevicePlatform {
  @JsonValue('ios')
  ios,
  @JsonValue('android')
  android,
}

/// Device information for mobile authentication requests.
///
/// This model matches the backend Pydantic schema for DeviceInfo.
/// Used in login/register requests to track devices and sessions.
@freezed
abstract class DeviceInfo with _$DeviceInfo {
  const factory DeviceInfo({
    /// Unique device identifier (UUID generated client-side).
    /// Persisted in SecureStorage across app launches.
    @JsonKey(name: 'device_id') required String deviceId,

    /// Mobile platform (ios/android).
    required DevicePlatform platform,

    /// Platform-specific identifier.
    /// - iOS: identifierForVendor
    /// - Android: Android ID
    @JsonKey(name: 'platform_id') required String platformId,

    /// Operating system version (e.g., '17.2', '14.0').
    @JsonKey(name: 'os_version') required String osVersion,

    /// CyberVPN app version (e.g., '1.0.0').
    @JsonKey(name: 'app_version') required String appVersion,

    /// Device model name (e.g., 'iPhone 15 Pro', 'Pixel 8').
    @JsonKey(name: 'device_model') required String deviceModel,

    /// Firebase Cloud Messaging token for push notifications.
    @JsonKey(name: 'push_token') String? pushToken,
  }) = _DeviceInfo;

  factory DeviceInfo.fromJson(Map<String, dynamic> json) =>
      _$DeviceInfoFromJson(json);
}
