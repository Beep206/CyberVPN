import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/security/domain/entities/antiphishing_code.dart';

/// Repository for security-related operations (antiphishing codes, etc.).
abstract interface class SecurityRepository {
  /// Retrieves the user's current antiphishing code.
  ///
  /// Returns [Success] with [AntiphishingCode] if the request succeeds.
  /// Returns [Failure] with error details if the request fails.
  /// The code field will be null if the user hasn't set a code yet.
  Future<Result<AntiphishingCode>> getAntiphishingCode();

  /// Sets or updates the user's antiphishing code.
  ///
  /// [code] must be non-empty and at most 50 characters.
  /// Returns [Success] with the updated [AntiphishingCode] if successful.
  /// Returns [Failure] with error details if the request fails.
  Future<Result<AntiphishingCode>> setAntiphishingCode(String code);

  /// Deletes the user's antiphishing code.
  ///
  /// Returns [Success] with void if successful.
  /// Returns [Failure] with error details if the request fails.
  Future<Result<void>> deleteAntiphishingCode();
}
