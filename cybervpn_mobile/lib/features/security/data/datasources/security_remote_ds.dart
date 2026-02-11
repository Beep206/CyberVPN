import 'package:cybervpn_mobile/core/constants/api_constants.dart';
import 'package:cybervpn_mobile/core/network/api_client.dart';
import 'package:cybervpn_mobile/features/security/domain/entities/antiphishing_code.dart';

/// Remote data source for security-related API calls.
class SecurityRemoteDataSource {
  const SecurityRemoteDataSource(this._apiClient);

  final ApiClient _apiClient;

  /// Fetches the user's antiphishing code from the backend.
  ///
  /// GET /api/v1/security/antiphishing
  /// Returns [AntiphishingCode] with code=null if not set, or with the actual code.
  /// Throws [ServerException] on error (401, 404, etc.).
  Future<AntiphishingCode> getAntiphishingCode() async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      ApiConstants.getAntiphishingCode,
    );

    final data = response.data;
    if (data == null) {
      return const AntiphishingCode(code: null);
    }

    // Backend returns { "code": string | null }
    final code = data['code'] as String?;
    return AntiphishingCode(code: code);
  }

  /// Sets or updates the user's antiphishing code.
  ///
  /// POST /api/v1/security/antiphishing
  /// Request: { "code": string }
  /// Response: { "code": string, "message": "..." }
  /// Throws [ServerException] on error (400, 401, etc.).
  Future<AntiphishingCode> setAntiphishingCode(String code) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      ApiConstants.setAntiphishingCode,
      data: {'code': code},
    );

    final data = response.data;
    if (data == null) {
      throw Exception('Empty response from server');
    }

    // Backend returns { "code": string, "message": "..." }
    final updatedCode = data['code'] as String?;
    return AntiphishingCode(code: updatedCode);
  }

  /// Deletes the user's antiphishing code.
  ///
  /// DELETE /api/v1/security/antiphishing
  /// Response: { "message": "..." }
  /// Throws [ServerException] on error (401, 404, etc.).
  Future<void> deleteAntiphishingCode() async {
    await _apiClient.delete<Map<String, dynamic>>(
      ApiConstants.deleteAntiphishingCode,
    );
  }
}
