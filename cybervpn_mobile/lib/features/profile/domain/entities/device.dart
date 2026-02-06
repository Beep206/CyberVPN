import 'package:freezed_annotation/freezed_annotation.dart';

part 'device.freezed.dart';

/// Represents an active device session
///
/// Contains metadata about a logged-in device/session
/// that can be viewed or revoked by the user.
@freezed
sealed class Device with _$Device {
  const factory Device({
    /// Unique identifier for this device session
    required String id,

    /// Human-readable device name (e.g. "iPhone 15 Pro")
    required String name,

    /// Device type or platform (e.g. "iOS", "Android", "Web")
    required String platform,

    /// IP address of the last connection from this device
    String? ipAddress,

    /// When this device session was last active
    DateTime? lastActiveAt,

    /// When this device session was created
    DateTime? createdAt,

    /// Whether this is the current device session
    @Default(false) bool isCurrent,
  }) = _Device;
}
