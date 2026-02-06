import 'package:cybervpn_mobile/core/data/cache_strategy.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/referral/domain/entities/referral.dart';

/// Abstract repository for referral feature operations.
///
/// Implementations must support graceful degradation via [isAvailable],
/// allowing the UI to conditionally render referral features when the
/// backend does not yet support them.
///
/// All methods return [Result<T>] to provide type-safe error handling
/// without relying on exceptions for control flow.
abstract class ReferralRepository {
  /// Checks whether the referral feature is available on the backend.
  Future<Result<bool>> isAvailable();

  /// Retrieves the current user's unique referral code.
  ///
  /// Returns [Success('')]  if the referral feature is unavailable.
  Future<Result<String>> getReferralCode({
    CacheStrategy strategy = CacheStrategy.networkFirst,
  });

  /// Fetches aggregated referral statistics for the current user.
  ///
  /// Returns empty stats if the referral feature is unavailable.
  Future<Result<ReferralStats>> getStats({
    CacheStrategy strategy = CacheStrategy.networkFirst,
  });

  /// Returns the most recent referral entries.
  ///
  /// [limit] controls the maximum number of entries returned (default 10).
  /// Returns an empty list if the referral feature is unavailable.
  /// Returns [Failure] if the backend returns an unexpected error.
  Future<Result<List<ReferralEntry>>> getRecentReferrals({int limit = 10});

  /// Shares the referral [code] using the platform share sheet.
  ///
  /// Returns [Failure] if platform sharing is not supported or fails.
  Future<Result<void>> shareReferral(String code);
}
