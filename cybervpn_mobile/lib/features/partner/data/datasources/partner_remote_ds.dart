import 'package:cybervpn_mobile/core/constants/api_constants.dart';
import 'package:cybervpn_mobile/core/constants/cache_constants.dart';
import 'package:cybervpn_mobile/core/errors/exceptions.dart';
import 'package:cybervpn_mobile/core/network/api_client.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/partner/domain/entities/partner.dart';

/// Abstract data source for partner-related API calls.
abstract class PartnerRemoteDataSource {
  /// Checks whether the partner feature is supported by the backend.
  ///
  /// Returns `true` on HTTP 200, `false` on 404/501 or any network error.
  Future<bool> checkAvailability();

  /// Checks if the current user is a partner.
  Future<bool> isPartner();

  /// Fetches the current user's partner information.
  Future<PartnerInfo> getPartnerInfo();

  /// Fetches all partner codes for the current user.
  Future<List<PartnerCode>> getPartnerCodes();

  /// Creates a new partner code.
  Future<PartnerCode> createPartnerCode({
    required double markup,
    String? description,
  });

  /// Updates the markup for an existing partner code.
  Future<PartnerCode> updateCodeMarkup({
    required String code,
    required double markup,
  });

  /// Toggles the active status of a partner code.
  Future<PartnerCode> toggleCodeStatus({
    required String code,
    required bool isActive,
  });

  /// Fetches earnings history for the current partner.
  Future<List<Earnings>> getEarnings({int limit = 50});

  /// Binds a partner code to become a partner.
  Future<BindCodeResult> bindPartnerCode(String code);
}

/// Implementation of [PartnerRemoteDataSource] using [ApiClient].
///
/// Caches the availability check result in-memory for the session to avoid
/// repeated network calls to an endpoint that may not exist yet.
class PartnerRemoteDataSourceImpl implements PartnerRemoteDataSource {
  final ApiClient _apiClient;

  /// In-memory cached availability result.
  bool? _cachedAvailable;
  DateTime? _cachedAt;

  /// Duration to cache the availability result.
  static const _cacheDuration = CacheConstants.referralCacheTtl;

  /// Base path for all partner endpoints.
  static const _basePath = '${ApiConstants.apiPrefix}/partner';

  PartnerRemoteDataSourceImpl(this._apiClient);

  @override
  Future<bool> checkAvailability() async {
    // Return cached result if still valid.
    if (_cachedAvailable != null && _cachedAt != null) {
      final elapsed = DateTime.now().difference(_cachedAt!);
      if (elapsed < _cacheDuration) return _cachedAvailable!;
    }

    try {
      // Backend doesn't have /status endpoint. Use /dashboard for availability check.
      final response = await _apiClient.get<Map<String, dynamic>>(
        '$_basePath/dashboard',
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
        'Partner availability check failed: ${e.message}',
        category: 'PartnerRemoteDataSource',
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
        'Unexpected error checking partner availability: $e',
        category: 'PartnerRemoteDataSource',
      );
      _setCachedAvailability(false);
      return false;
    }
  }

  @override
  Future<bool> isPartner() async {
    // Backend doesn't have /is-partner endpoint.
    // Check if user has partner dashboard access instead.
    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        '$_basePath/dashboard',
      );
      // If dashboard is accessible (200 OK), user is a partner
      return response.statusCode == 200;
    } catch (e) {
      // If dashboard access fails, user is not a partner
      return false;
    }
  }

  @override
  Future<PartnerInfo> getPartnerInfo() async {
    // Backend doesn't have /info endpoint. Use /dashboard instead.
    final response = await _apiClient.get<Map<String, dynamic>>(
      '$_basePath/dashboard',
    );
    final data = response.data!;
    // Backend returns: {total_clients, total_earned, current_tier, codes}
    // Map to PartnerInfo domain entity
    final tierData = data['current_tier'] as Map<String, dynamic>?;
    return PartnerInfo(
      tier: tierData != null
          ? PartnerTier.values.byName(tierData['name'] as String)
          : PartnerTier.bronze,
      clientCount: data['total_clients'] as int,
      totalEarnings: (data['total_earned'] as num).toDouble(),
      availableBalance: (data['total_earned'] as num).toDouble(), // TODO: Backend doesn't separate balance
      commissionRate: 0.0, // TODO: Backend doesn't provide this in dashboard
      partnerSince: DateTime.now(), // TODO: Backend doesn't provide this
    );
  }

  @override
  Future<List<PartnerCode>> getPartnerCodes() async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      '$_basePath/codes',
    );
    // Backend returns list directly (not wrapped in 'codes')
    // Schema: [{id, code, markup_pct, is_active, created_at}]
    final items = response.data as List<dynamic>;
    return items.map((item) {
      final map = item as Map<String, dynamic>;
      return PartnerCode(
        code: map['code'] as String,
        markup: (map['markup_pct'] as num).toDouble(), // Backend uses 'markup_pct'
        isActive: map['is_active'] as bool,
        clientCount: 0, // TODO: Backend doesn't provide client_count per code
        createdAt: DateTime.parse(map['created_at'] as String),
        description: null, // TODO: Backend doesn't provide description yet
      );
    }).toList();
  }

  @override
  Future<PartnerCode> createPartnerCode({
    required double markup,
    String? description,
  }) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      '$_basePath/codes',
      data: {
        'code': '', // Backend expects 'code' field (can be empty for auto-generation)
        'markup_pct': markup, // Backend uses 'markup_pct'
        // Backend doesn't support description field yet
      },
    );
    final data = response.data!;
    return PartnerCode(
      code: data['code'] as String,
      markup: (data['markup_pct'] as num).toDouble(),
      isActive: data['is_active'] as bool,
      clientCount: 0, // Backend doesn't provide this
      createdAt: DateTime.parse(data['created_at'] as String),
      description: description, // Use the input description since backend doesn't store it
    );
  }

  @override
  Future<PartnerCode> updateCodeMarkup({
    required String code,
    required double markup,
  }) async {
    // Backend expects code_id (UUID) in path, not code string
    // This method signature needs the UUID, not the code string
    // For now, treating 'code' parameter as the UUID string
    final response = await _apiClient.put<Map<String, dynamic>>(
      '$_basePath/codes/$code',
      data: {'markup_pct': markup}, // Backend uses 'markup_pct'
    );
    final data = response.data!;
    return PartnerCode(
      code: data['code'] as String,
      markup: (data['markup_pct'] as num).toDouble(),
      isActive: data['is_active'] as bool,
      clientCount: 0, // Backend doesn't provide this
      createdAt: DateTime.parse(data['created_at'] as String),
      description: null, // Backend doesn't provide this
    );
  }

  @override
  Future<PartnerCode> toggleCodeStatus({
    required String code,
    required bool isActive,
  }) async {
    // Backend doesn't have a /status endpoint for toggling code status
    // This functionality may not be implemented yet
    // Keeping the implementation but marking it as unimplemented
    throw UnimplementedError(
      'Backend does not have /partner/codes/{id}/status endpoint yet',
    );
  }

  @override
  Future<List<Earnings>> getEarnings({int limit = 50}) async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      '$_basePath/earnings',
      queryParameters: {'limit': limit},
    );
    // Backend returns list of PartnerEarningResponse directly
    // Schema: [{id, client_user_id, base_price, markup_amount, commission_amount, total_earning, created_at}]
    final items = response.data as List<dynamic>;
    return items.map((item) {
      final map = item as Map<String, dynamic>;
      return Earnings(
        amount: (map['total_earning'] as num).toDouble(),
        period: _formatPeriod(DateTime.parse(map['created_at'] as String)),
        date: DateTime.parse(map['created_at'] as String),
        transactionCount: 1, // Each earning record is one transaction
      );
    }).toList();
  }

  /// Format a date as a period string (e.g., "January 2024").
  String _formatPeriod(DateTime date) {
    const months = [
      'January',
      'February',
      'March',
      'April',
      'May',
      'June',
      'July',
      'August',
      'September',
      'October',
      'November',
      'December',
    ];
    return '${months[date.month - 1]} ${date.year}';
  }

  @override
  Future<BindCodeResult> bindPartnerCode(String code) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      '$_basePath/bind',
      data: {'partner_code': code}, // Backend uses 'partner_code', not 'code'
    );
    final data = response.data!;
    // Backend returns {status: "bound"}
    final status = data['status'] as String;
    return BindCodeResult(
      success: status == 'bound',
      message: status == 'bound' ? 'Successfully bound to partner' : 'Bind failed',
      newStatus: status == 'bound' ? null : BindCodeStatus.pending,
    );
  }

  void _setCachedAvailability(bool value) {
    _cachedAvailable = value;
    _cachedAt = DateTime.now();
  }
}
