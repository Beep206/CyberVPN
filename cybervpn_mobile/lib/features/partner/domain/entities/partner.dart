import 'package:freezed_annotation/freezed_annotation.dart';

part 'partner.freezed.dart';

/// Partner tier levels.
enum PartnerTier {
  /// Entry-level partner tier.
  bronze,

  /// Mid-level partner tier with higher commission.
  silver,

  /// Premium partner tier with highest commission.
  gold,
}

/// Aggregated partner statistics for the current user.
@freezed
sealed class PartnerInfo with _$PartnerInfo {
  const factory PartnerInfo({
    /// Partner tier level.
    required PartnerTier tier,

    /// Total number of clients using partner codes.
    required int clientCount,

    /// Total earnings accumulated (in dollars).
    required double totalEarnings,

    /// Current available balance (in dollars).
    required double availableBalance,

    /// Commission rate based on tier (percentage).
    required double commissionRate,

    /// Date when the user became a partner.
    required DateTime partnerSince,
  }) = _PartnerInfo;
}

/// A single partner code with associated metadata.
@freezed
sealed class PartnerCode with _$PartnerCode {
  const factory PartnerCode({
    /// Unique partner code identifier.
    required String code,

    /// Markup percentage for this code.
    required double markup,

    /// Whether this code is currently active.
    required bool isActive,

    /// Number of clients using this code.
    required int clientCount,

    /// Date when this code was created.
    required DateTime createdAt,

    /// Optional description/label for the code.
    String? description,
  }) = _PartnerCode;
}

/// Earnings record for a specific period.
@freezed
sealed class Earnings with _$Earnings {
  const factory Earnings({
    /// Earnings amount (in dollars).
    required double amount,

    /// Period label (e.g., "January 2024", "Week 3").
    required String period,

    /// Date for this earnings record.
    required DateTime date,

    /// Number of transactions contributing to this amount.
    required int transactionCount,
  }) = _Earnings;
}

/// Status for non-partners who want to bind a code.
enum BindCodeStatus {
  /// User is not a partner yet.
  notPartner,

  /// Bind code request is pending approval.
  pending,

  /// Bind code request was rejected.
  rejected,
}

/// Response from binding a partner code.
@freezed
sealed class BindCodeResult with _$BindCodeResult {
  const factory BindCodeResult({
    /// Whether the bind was successful.
    required bool success,

    /// Status message.
    required String message,

    /// New status after binding.
    BindCodeStatus? newStatus,
  }) = _BindCodeResult;
}
