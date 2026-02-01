import 'package:freezed_annotation/freezed_annotation.dart';

part 'referral.freezed.dart';

/// Status of a referral entry.
enum ReferralStatus {
  /// Invited user has not yet subscribed.
  pending,

  /// Invited user is active but not yet paid.
  active,

  /// Invited user has completed a paid subscription.
  completed,
}

/// Aggregated referral statistics for the current user.
@freezed
abstract class ReferralStats with _$ReferralStats {
  const factory ReferralStats({
    /// Total number of users invited via referral.
    required int totalInvited,

    /// Number of invited users who became paying customers.
    required int paidUsers,

    /// Total referral points accumulated.
    required double pointsEarned,

    /// Current redeemable referral balance.
    required double balance,
  }) = _ReferralStats;
}

/// A single referral entry representing an invited user.
@freezed
abstract class ReferralEntry with _$ReferralEntry {
  const factory ReferralEntry({
    /// Unique referral code used for this invitation.
    required String code,

    /// Date when the referred user joined.
    required DateTime joinDate,

    /// Current status of this referral.
    required ReferralStatus status,
  }) = _ReferralEntry;
}
