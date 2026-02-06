import 'package:cybervpn_mobile/core/errors/exceptions.dart';
import 'package:cybervpn_mobile/core/errors/failures.dart' hide Failure;
import 'package:cybervpn_mobile/core/errors/network_error_handler.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/referral/data/datasources/referral_remote_ds.dart';
import 'package:cybervpn_mobile/features/referral/domain/entities/referral.dart';
import 'package:cybervpn_mobile/features/referral/domain/repositories/referral_repository.dart';
import 'package:share_plus/share_plus.dart' as share_plus;

/// Implementation of [ReferralRepository] that delegates API calls to
/// [ReferralRemoteDataSource] and applies graceful degradation.
///
/// All data-fetching methods check [isAvailable] first. When the backend
/// referral feature is unavailable (404/501), methods return appropriate
/// empty states wrapped in [Success] instead of returning [Failure].
///
/// All methods return [Result<T>] instead of throwing, enabling callers
/// to handle success and failure explicitly via pattern matching.
class ReferralRepositoryImpl
    with NetworkErrorHandler
    implements ReferralRepository {
  final ReferralRemoteDataSource _remoteDataSource;

  ReferralRepositoryImpl({required ReferralRemoteDataSource remoteDataSource})
      : _remoteDataSource = remoteDataSource;

  @override
  Future<Result<bool>> isAvailable() async {
    try {
      return Success(await _remoteDataSource.checkAvailability());
    } on AppException catch (e) {
      return Failure(mapExceptionToFailure(e));
    }
  }

  @override
  Future<Result<String>> getReferralCode() async {
    final isAvail = (await isAvailable()).dataOrNull ?? false;
    if (!isAvail) return const Success('');
    try {
      return Success(await _remoteDataSource.getReferralCode());
    } on AppException catch (e) {
      return Failure(mapExceptionToFailure(e));
    }
  }

  @override
  Future<Result<ReferralStats>> getStats() async {
    final isAvail = (await isAvailable()).dataOrNull ?? false;
    if (!isAvail) {
      return const Success(ReferralStats(
        totalInvited: 0,
        paidUsers: 0,
        pointsEarned: 0,
        balance: 0,
      ));
    }
    try {
      return Success(await _remoteDataSource.getReferralStats());
    } on AppException catch (e) {
      return Failure(mapExceptionToFailure(e));
    }
  }

  @override
  Future<Result<List<ReferralEntry>>> getRecentReferrals({
    int limit = 10,
  }) async {
    final isAvail = (await isAvailable()).dataOrNull ?? false;
    if (!isAvail) return const Success([]);
    try {
      return Success(
        await _remoteDataSource.getRecentReferrals(limit: limit),
      );
    } on AppException catch (e) {
      return Failure(mapExceptionToFailure(e));
    }
  }

  @override
  Future<Result<void>> shareReferral(String code) async {
    try {
      await share_plus.SharePlus.instance.share(
        share_plus.ShareParams(
          text: 'Join CyberVPN with my referral code: $code',
        ),
      );
      return const Success(null);
    } catch (e) {
      return Failure(
        UnknownFailure(message: 'Failed to share referral: $e'),
      );
    }
  }
}
