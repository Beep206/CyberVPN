import 'package:cybervpn_mobile/core/errors/exceptions.dart';
import 'package:cybervpn_mobile/core/errors/network_error_handler.dart';
import 'package:cybervpn_mobile/features/referral/data/datasources/referral_remote_ds.dart';
import 'package:cybervpn_mobile/features/referral/domain/entities/referral.dart';
import 'package:cybervpn_mobile/features/referral/domain/repositories/referral_repository.dart';
import 'package:share_plus/share_plus.dart' as share_plus;

/// Implementation of [ReferralRepository] that delegates API calls to
/// [ReferralRemoteDataSource] and applies graceful degradation.
///
/// All data-fetching methods check [isAvailable] first. When the backend
/// referral feature is unavailable (404/501), methods return appropriate
/// empty states instead of throwing.
class ReferralRepositoryImpl
    with NetworkErrorHandler
    implements ReferralRepository {
  final ReferralRemoteDataSource _remoteDataSource;

  ReferralRepositoryImpl({required ReferralRemoteDataSource remoteDataSource})
      : _remoteDataSource = remoteDataSource;

  @override
  Future<bool> isAvailable() => _remoteDataSource.checkAvailability();

  @override
  Future<String> getReferralCode() async {
    if (!await isAvailable()) {
      return '';
    }
    try {
      return await _remoteDataSource.getReferralCode();
    } on AppException catch (e) {
      throw mapExceptionToFailure(e);
    }
  }

  @override
  Future<ReferralStats> getStats() async {
    if (!await isAvailable()) {
      return const ReferralStats(
        totalInvited: 0,
        paidUsers: 0,
        pointsEarned: 0,
        balance: 0,
      );
    }
    try {
      return await _remoteDataSource.getReferralStats();
    } on AppException catch (e) {
      throw mapExceptionToFailure(e);
    }
  }

  @override
  Future<List<ReferralEntry>> getRecentReferrals({int limit = 10}) async {
    if (!await isAvailable()) {
      return const [];
    }
    try {
      return await _remoteDataSource.getRecentReferrals(limit: limit);
    } on AppException catch (e) {
      throw mapExceptionToFailure(e);
    }
  }

  @override
  Future<void> shareReferral(String code) async {
    await share_plus.Share.share(
      'Join CyberVPN with my referral code: $code',
    );
  }
}
