import 'package:freezed_annotation/freezed_annotation.dart';

part 'subscription_info.freezed.dart';

@freezed
sealed class SubscriptionInfo with _$SubscriptionInfo {
  const SubscriptionInfo._();

  const factory SubscriptionInfo({
    String? title,
    @Default(0) int uploadBytes,
    @Default(0) int downloadBytes,
    @Default(0) int totalBytes,
    DateTime? expiresAt,
    @Default(60) int updateIntervalMinutes,
    String? supportUrl,
  }) = _SubscriptionInfo;

  /// Total bytes consumed (upload + download).
  int get consumedBytes => uploadBytes + downloadBytes;

  /// Ratio of consumed traffic to total allowance (0.0–1.0).
  ///
  /// Returns 0.0 when [totalBytes] is zero (unlimited plan).
  double get usageRatio =>
      totalBytes > 0 ? (consumedBytes / totalBytes).clamp(0.0, 1.0) : 0.0;

  /// Whether the subscription has expired.
  bool get isExpired =>
      expiresAt != null && expiresAt!.isBefore(DateTime.now());

  /// Time remaining until expiry. Returns [Duration.zero] when already
  /// expired or when [expiresAt] is `null` (no expiry set).
  Duration get remaining {
    if (expiresAt == null) return Duration.zero;
    final diff = expiresAt!.difference(DateTime.now());
    return diff.isNegative ? Duration.zero : diff;
  }
}
