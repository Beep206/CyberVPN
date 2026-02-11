import 'package:cybervpn_mobile/core/data/cache_strategy.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/partner/domain/entities/partner.dart';

/// Abstract repository for partner feature operations.
///
/// Implementations must support graceful degradation via [isAvailable],
/// allowing the UI to conditionally render partner features when the
/// backend does not yet support them.
///
/// All methods return [Result<T>] to provide type-safe error handling
/// without relying on exceptions for control flow.
abstract class PartnerRepository {
  /// Checks whether the partner feature is available on the backend.
  Future<Result<bool>> isAvailable();

  /// Checks if the current user is a partner.
  ///
  /// Returns `false` if the partner feature is unavailable or user is not a partner.
  Future<Result<bool>> isPartner({
    CacheStrategy strategy = CacheStrategy.networkFirst,
  });

  /// Retrieves the current user's partner information.
  ///
  /// Returns [Failure] if user is not a partner or feature is unavailable.
  Future<Result<PartnerInfo>> getPartnerInfo({
    CacheStrategy strategy = CacheStrategy.networkFirst,
  });

  /// Fetches all partner codes for the current user.
  ///
  /// Returns empty list if user is not a partner or feature is unavailable.
  Future<Result<List<PartnerCode>>> getPartnerCodes({
    CacheStrategy strategy = CacheStrategy.networkFirst,
  });

  /// Creates a new partner code with the specified markup.
  ///
  /// [markup] - Markup percentage (e.g., 10.0 for 10%).
  /// [description] - Optional description for the code.
  Future<Result<PartnerCode>> createPartnerCode({
    required double markup,
    String? description,
  });

  /// Updates the markup for an existing partner code.
  ///
  /// [code] - The code to update.
  /// [markup] - New markup percentage.
  Future<Result<PartnerCode>> updateCodeMarkup({
    required String code,
    required double markup,
  });

  /// Toggles the active status of a partner code.
  ///
  /// [code] - The code to toggle.
  /// [isActive] - New active status.
  Future<Result<PartnerCode>> toggleCodeStatus({
    required String code,
    required bool isActive,
  });

  /// Fetches earnings history for the current partner.
  ///
  /// [limit] - Maximum number of earnings records to fetch (default 50).
  /// Returns empty list if user is not a partner or feature is unavailable.
  Future<Result<List<Earnings>>> getEarnings({int limit = 50});

  /// Binds a partner code to become a partner (for non-partners).
  ///
  /// [code] - The partner code to bind.
  Future<Result<BindCodeResult>> bindPartnerCode(String code);

  /// Shares a partner code using the platform share sheet.
  ///
  /// Returns [Failure] if platform sharing is not supported or fails.
  Future<Result<void>> sharePartnerCode(String code);
}
