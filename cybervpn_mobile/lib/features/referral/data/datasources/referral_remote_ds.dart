import 'package:cybervpn_mobile/core/constants/api_constants.dart';
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
  static const _cacheDuration = Duration(minutes: 5);

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
      _setCachedAvailability(false);
      return false;
    } on NetworkException {
      // Network errors -- fail gracefully.
      _setCachedAvailability(false);
      return false;
    } catch (e) {
      // Any unexpected error -- log and fail gracefully.
      AppLogger.error(
        'Unexpected error checking referral availability: $e',
        category: 'ReferralRemoteDataSource',
      );
      _setCachedAvailability(false);
      return false;
    }
  }

  @override
  Future<String> getReferralCode() async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      '$_basePath/code',
    );
    return response.data!['code'] as String;
  }

  @override
  Future<ReferralStats> getReferralStats() async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      '$_basePath/stats',
    );
    final data = response.data!;
    return ReferralStats(
      totalInvited: data['total_invited'] as int,
      paidUsers: data['paid_users'] as int,
      pointsEarned: (data['points_earned'] as num).toDouble(),
      balance: (data['balance'] as num).toDouble(),
    );
  }

  @override
  Future<List<ReferralEntry>> getRecentReferrals({int limit = 10}) async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      '$_basePath/recent',
      queryParameters: {'limit': limit},
    );
    final items = response.data!['referrals'] as List<dynamic>;
    return items.map((item) {
      final map = item as Map<String, dynamic>;
      return ReferralEntry(
        code: map['code'] as String,
        joinDate: DateTime.parse(map['join_date'] as String),
        status: ReferralStatus.values.byName(map['status'] as String),
      );
    }).toList();
  }

  void _setCachedAvailability(bool value) {
    _cachedAvailable = value;
    _cachedAt = DateTime.now();
  }
}
