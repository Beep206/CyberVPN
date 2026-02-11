import 'package:cybervpn_mobile/core/data/cache_strategy.dart';
import 'package:cybervpn_mobile/core/errors/exceptions.dart';
import 'package:cybervpn_mobile/core/errors/failures.dart' hide Failure;
import 'package:cybervpn_mobile/core/errors/network_error_handler.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/partner/data/datasources/partner_remote_ds.dart';
import 'package:cybervpn_mobile/features/partner/domain/entities/partner.dart';
import 'package:cybervpn_mobile/features/partner/domain/repositories/partner_repository.dart';
import 'package:share_plus/share_plus.dart' as share_plus;

/// Implementation of [PartnerRepository] that delegates API calls to
/// [PartnerRemoteDataSource] and applies graceful degradation.
///
/// Uses [CachedRepository] with [CacheStrategy.networkFirst] for read
/// methods so cached data is available when the network is down.
///
/// All data-fetching methods check [isAvailable] first. When the backend
/// partner feature is unavailable (404/501), methods return appropriate
/// empty states wrapped in [Success] instead of returning [Failure].
class PartnerRepositoryImpl
    with NetworkErrorHandler, CachedRepository
    implements PartnerRepository {
  final PartnerRemoteDataSource _remoteDataSource;

  // In-memory caches for networkFirst fallback.
  PartnerInfo? _cachedInfo;
  List<PartnerCode>? _cachedCodes;
  bool? _cachedIsPartner;

  // TTL cache for availability to avoid redundant network calls.
  bool? _availabilityCache;
  DateTime? _availabilityCacheTime;
  static const _availabilityTtl = Duration(minutes: 5);

  PartnerRepositoryImpl({required PartnerRemoteDataSource remoteDataSource})
      : _remoteDataSource = remoteDataSource;

  @override
  Future<Result<bool>> isAvailable() async {
    if (_availabilityCache != null && _availabilityCacheTime != null) {
      if (DateTime.now().difference(_availabilityCacheTime!) <
          _availabilityTtl) {
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
  Future<Result<bool>> isPartner({
    CacheStrategy strategy = CacheStrategy.networkFirst,
  }) async {
    final isAvail = (await isAvailable()).dataOrNull ?? false;
    if (!isAvail) return const Success(false);
    return executeWithStrategy<bool>(
      strategy: strategy,
      fetchFromNetwork: _remoteDataSource.isPartner,
      readFromCache: () async => _cachedIsPartner,
      writeToCache: (isPartner) async => _cachedIsPartner = isPartner,
    );
  }

  @override
  Future<Result<PartnerInfo>> getPartnerInfo({
    CacheStrategy strategy = CacheStrategy.networkFirst,
  }) async {
    final isAvail = (await isAvailable()).dataOrNull ?? false;
    if (!isAvail) {
      return Failure(
        UnknownFailure(message: 'Partner feature not available'),
      );
    }
    return executeWithStrategy<PartnerInfo>(
      strategy: strategy,
      fetchFromNetwork: _remoteDataSource.getPartnerInfo,
      readFromCache: () async => _cachedInfo,
      writeToCache: (info) async => _cachedInfo = info,
    );
  }

  @override
  Future<Result<List<PartnerCode>>> getPartnerCodes({
    CacheStrategy strategy = CacheStrategy.networkFirst,
  }) async {
    final isAvail = (await isAvailable()).dataOrNull ?? false;
    if (!isAvail) return const Success([]);
    return executeWithStrategy<List<PartnerCode>>(
      strategy: strategy,
      fetchFromNetwork: _remoteDataSource.getPartnerCodes,
      readFromCache: () async => _cachedCodes,
      writeToCache: (codes) async => _cachedCodes = codes,
    );
  }

  @override
  Future<Result<PartnerCode>> createPartnerCode({
    required double markup,
    String? description,
  }) async {
    final isAvail = (await isAvailable()).dataOrNull ?? false;
    if (!isAvail) {
      return Failure(
        UnknownFailure(message: 'Partner feature not available'),
      );
    }
    try {
      final code = await _remoteDataSource.createPartnerCode(
        markup: markup,
        description: description,
      );
      // Invalidate cached codes so next fetch gets updated list.
      _cachedCodes = null;
      return Success(code);
    } on AppException catch (e) {
      return Failure(mapExceptionToFailure(e));
    }
  }

  @override
  Future<Result<PartnerCode>> updateCodeMarkup({
    required String code,
    required double markup,
  }) async {
    final isAvail = (await isAvailable()).dataOrNull ?? false;
    if (!isAvail) {
      return Failure(
        UnknownFailure(message: 'Partner feature not available'),
      );
    }
    try {
      final updated = await _remoteDataSource.updateCodeMarkup(
        code: code,
        markup: markup,
      );
      // Invalidate cached codes so next fetch gets updated list.
      _cachedCodes = null;
      return Success(updated);
    } on AppException catch (e) {
      return Failure(mapExceptionToFailure(e));
    }
  }

  @override
  Future<Result<PartnerCode>> toggleCodeStatus({
    required String code,
    required bool isActive,
  }) async {
    final isAvail = (await isAvailable()).dataOrNull ?? false;
    if (!isAvail) {
      return Failure(
        UnknownFailure(message: 'Partner feature not available'),
      );
    }
    try {
      final updated = await _remoteDataSource.toggleCodeStatus(
        code: code,
        isActive: isActive,
      );
      // Invalidate cached codes so next fetch gets updated list.
      _cachedCodes = null;
      return Success(updated);
    } on AppException catch (e) {
      return Failure(mapExceptionToFailure(e));
    }
  }

  @override
  Future<Result<List<Earnings>>> getEarnings({int limit = 50}) async {
    final isAvail = (await isAvailable()).dataOrNull ?? false;
    if (!isAvail) return const Success([]);
    try {
      return Success(await _remoteDataSource.getEarnings(limit: limit));
    } on AppException catch (e) {
      return Failure(mapExceptionToFailure(e));
    }
  }

  @override
  Future<Result<BindCodeResult>> bindPartnerCode(String code) async {
    final isAvail = (await isAvailable()).dataOrNull ?? false;
    if (!isAvail) {
      return Failure(
        UnknownFailure(message: 'Partner feature not available'),
      );
    }
    try {
      final result = await _remoteDataSource.bindPartnerCode(code);
      // Invalidate caches as user may now be a partner.
      _cachedIsPartner = null;
      _cachedInfo = null;
      return Success(result);
    } on AppException catch (e) {
      return Failure(mapExceptionToFailure(e));
    }
  }

  @override
  Future<Result<void>> sharePartnerCode(String code) async {
    try {
      await share_plus.SharePlus.instance.share(
        share_plus.ShareParams(
          text: 'Join CyberVPN as my client with partner code: $code',
        ),
      );
      return const Success(null);
    } catch (e) {
      return Failure(
        UnknownFailure(message: 'Failed to share partner code: $e'),
      );
    }
  }
}
