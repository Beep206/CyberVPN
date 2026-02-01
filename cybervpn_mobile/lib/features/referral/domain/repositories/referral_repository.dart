import 'package:cybervpn_mobile/features/referral/domain/entities/referral.dart';

/// Abstract repository for referral feature operations.
///
/// Implementations must support graceful degradation via [isAvailable],
/// allowing the UI to conditionally render referral features when the
/// backend does not yet support them.
abstract class ReferralRepository {
  /// Checks whether the referral feature is available on the backend.
  ///
  /// Attempts a lightweight API call to the referral endpoint.
  /// Returns `true` on HTTP 200, `false` on 404/501 or any network error.
  /// This enables graceful degradation when the backend has not implemented
  /// the referral system.
  Future<bool> isAvailable();

  /// Retrieves the current user's unique referral code.
  ///
  /// Throws [ServerFailure] if the backend returns an error.
  Future<String> getReferralCode();

  /// Fetches aggregated referral statistics for the current user.
  ///
  /// Throws [ServerFailure] if the backend returns an error.
  Future<ReferralStats> getStats();

  /// Returns the most recent referral entries.
  ///
  /// [limit] controls the maximum number of entries returned (default 10).
  /// Throws [ServerFailure] if the backend returns an error.
  Future<List<ReferralEntry>> getRecentReferrals({int limit = 10});

  /// Shares the referral [code] using the platform share sheet.
  ///
  /// May throw platform-specific errors if sharing is not supported.
  Future<void> shareReferral(String code);
}
