import 'package:cybervpn_mobile/core/data/cache_strategy.dart';
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
/// Uses [CachedRepository] with [CacheStrategy.networkFirst] for read
/// methods so cached data is available when the network is down.
///
/// All data-fetching methods check [isAvailable] first. When the backend
/// referral feature is unavailable (404/501), methods return appropriate
/// empty states wrapped in [Success] instead of returning [Failure].
class ReferralRepositoryImpl
    with NetworkErrorHandler, CachedRepository
    implements ReferralRepository {
  final ReferralRemoteDataSource _remoteDataSource;

  // In-memory caches for networkFirst fallback.
  ReferralStats? _cachedStats;
  String? _cachedCode;

  // TTL cache for availability to avoid redundant network calls.
  bool? _availabilityCache;
  DateTime? _availabilityCacheTime;
  static const _availabilityTtl = Duration(minutes: 5);

  ReferralRepositoryImpl({required ReferralRemoteDataSource remoteDataSource})
      : _remoteDataSource = remoteDataSource;

  @override
  Future<Result<bool>> isAvailable() async {
    if (_availabilityCache != null && _availabilityCacheTime != null) {
      if (DateTime.now().difference(_availabilityCacheTime!) < _availabilityTtl) {
        return Success(_availabilityCache!);
      }
    }
    try {
      final result = await _remoteDataSource.checkAvailability();
      _availabilityCache = result;
      _availabilityCacheTime = DateTime.now();
      return Success(result);
    } on AppException catch (e) {
      _availabilityCache = false;
      _availabilityCacheTime = DateTime.now();
      return Failure(mapExceptionToFailure(e));
    }
  }

  @override
  Future<Result<String>> getReferralCode({
    CacheStrategy strategy = CacheStrategy.networkFirst,
  }) async {
    final isAvail = (await isAvailable()).dataOrNull ?? false;
    if (!isAvail) return const Success('');
    return executeWithStrategy<String>(
      strategy: strategy,
      fetchFromNetwork: _remoteDataSource.getReferralCode,
      readFromCache: () async => _cachedCode,
      writeToCache: (code) async => _cachedCode = code,
    );
  }

  @override
  Future<Result<ReferralStats>> getStats({
    CacheStrategy strategy = CacheStrategy.networkFirst,
  }) async {
    final isAvail = (await isAvailable()).dataOrNull ?? false;
    if (!isAvail) {
      return const Success(ReferralStats(
        totalInvited: 0,
        paidUsers: 0,
        pointsEarned: 0,
        balance: 0,
      ));
    }
    return executeWithStrategy<ReferralStats>(
      strategy: strategy,
      fetchFromNetwork: _remoteDataSource.getReferralStats,
      readFromCache: () async => _cachedStats,
      writeToCache: (stats) async => _cachedStats = stats,
    );
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
