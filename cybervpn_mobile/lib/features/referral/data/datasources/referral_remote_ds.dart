import 'package:cybervpn_mobile/core/constants/api_constants.dart';
import 'package:cybervpn_mobile/core/constants/cache_constants.dart';
import 'package:cybervpn_mobile/core/errors/exceptions.dart';
import 'package:cybervpn_mobile/core/network/api_client.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/referral/domain/entities/referral.dart';

/// Abstract data source for referral-related API calls.
abstract class ReferralRemoteDataSource {
  /// Checks whether the referral feature is supported by the backend.
  ///
  /// Returns `true` on HTTP 200, `false` on 404/501 or any network error.
  Future<bool> checkAvailability();

  /// Fetches the current user's referral code.
  Future<String> getReferralCode();

  /// Fetches aggregated referral statistics for the current user.
  Future<ReferralStats> getReferralStats();

  /// Fetches the most recent referral entries.
  Future<List<ReferralEntry>> getRecentReferrals({int limit = 10});
}

/// Implementation of [ReferralRemoteDataSource] using [ApiClient].
///
/// Caches the availability check result in-memory for the session to avoid
/// repeated network calls to an endpoint that may not exist yet.
class ReferralRemoteDataSourceImpl implements ReferralRemoteDataSource {
  final ApiClient _apiClient;

  /// In-memory cached availability result.
  bool? _cachedAvailable;
  DateTime? _cachedAt;

  /// Duration to cache the availability result.
  /// See [CacheConstants.referralCacheTtl] for the centralized value.
  static const _cacheDuration = CacheConstants.referralCacheTtl;

  /// Base path for all referral endpoints.
  static const _basePath = '${ApiConstants.apiPrefix}/referral';

  ReferralRemoteDataSourceImpl(this._apiClient);

  @override
  Future<bool> checkAvailability() async {
    // Return cached result if still valid.
    if (_cachedAvailable != null && _cachedAt != null) {
      final elapsed = DateTime.now().difference(_cachedAt!);
      if (elapsed < _cacheDuration) return _cachedAvailable!;
    }

    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        '$_basePath/status',
      );
      final available = response.statusCode == 200;
      _setCachedAvailability(available);
      return available;
    } on ServerException catch (e) {
      // 404 or 501 means the feature is not available.
      if (e.code == 404 || e.code == 501) {
        _setCachedAvailability(false);
        return false;
      }
      AppLogger.warning(
        'Referral availability check failed: ${e.message}',
        category: 'ReferralRemoteDataSource',
      );
      return _cachedAvailable ?? false;
    } on NetworkException {
      return _cachedAvailable ?? false;
    } catch (e) {
      // Any unexpected error -- log and fail gracefully.
      AppLogger.error(
        'Unexpected error checking referral availability: $e',
        category: 'ReferralRemoteDataSource',
      );
      return _cachedAvailable ?? false;
    }
  }

  @override
  Future<String> getReferralCode() async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      '$_basePath/code',
    );
    final data = response.data ?? const <String, dynamic>{};
    return (data['referral_code'] ?? data['code']) as String;
  }

  @override
  Future<ReferralStats> getReferralStats() async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      '$_basePath/stats',
    );
    final data = response.data ?? const <String, dynamic>{};
    return ReferralStats(
      totalInvited:
          (data['total_referrals'] ?? data['total_invited'] ?? 0) as int,
      paidUsers: (data['paid_users'] ?? 0) as int,
      pointsEarned:
          ((data['total_earned'] ?? data['points_earned'] ?? 0) as num)
              .toDouble(),
      balance: ((data['balance'] ?? data['total_earned'] ?? 0) as num)
          .toDouble(),
    );
  }

  @override
  Future<List<ReferralEntry>> getRecentReferrals({int limit = 10}) async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      '$_basePath/recent',
      queryParameters: {'limit': limit},
    );
    final Object? data = response.data;
    final List<dynamic> items;
    if (data is List<dynamic>) {
      items = data;
    } else if (data is Map<String, dynamic> &&
        data['referrals'] is List<dynamic>) {
      items = data['referrals'] as List<dynamic>;
    } else {
      items = const <dynamic>[];
    }

    return items.map((item) {
      final map = item as Map<String, dynamic>;
      final statusValue = map['status'] as String?;
      final backendCreatedAt = map['created_at'] as String?;
      final legacyJoinDate = map['join_date'] as String?;
      return ReferralEntry(
        code: (map['code'] ?? map['referred_user_id'] ?? '') as String,
        joinDate: DateTime.parse(
          backendCreatedAt ??
              legacyJoinDate ??
              DateTime.now().toIso8601String(),
        ),
        status: switch (statusValue) {
          'active' => ReferralStatus.active,
          'pending' => ReferralStatus.pending,
          'completed' => ReferralStatus.completed,
          _ => ReferralStatus.completed,
        },
      );
    }).toList();
  }

  void _setCachedAvailability(bool value) {
    _cachedAvailable = value;
    _cachedAt = DateTime.now();
  }
}
