import 'package:cybervpn_mobile/core/errors/exceptions.dart';
import 'package:cybervpn_mobile/core/errors/failures.dart';
import 'package:cybervpn_mobile/core/errors/network_error_handler.dart';
import 'package:cybervpn_mobile/core/network/network_info.dart';
import 'package:cybervpn_mobile/features/profile/data/datasources/profile_remote_ds.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/device.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/oauth_provider.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/profile.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/setup_2fa_result.dart';
import 'package:cybervpn_mobile/features/profile/domain/repositories/profile_repository.dart';

/// Repository implementation for user profile management.
///
/// Delegates to [ProfileRemoteDataSource] for all network calls and uses
/// [NetworkErrorHandler] to convert infrastructure exceptions into domain
/// [Failure] types with retry logic for transient errors.
class ProfileRepositoryImpl
    with NetworkErrorHandler
    implements ProfileRepository {
  final ProfileRemoteDataSource _remoteDataSource;
  final NetworkInfo _networkInfo;

  ProfileRepositoryImpl({
    required ProfileRemoteDataSource remoteDataSource,
    required NetworkInfo networkInfo,
  })  : _remoteDataSource = remoteDataSource,
        _networkInfo = networkInfo;

  // -- Profile --

  @override
  Future<Profile> getProfile() async {
    await _ensureConnected();
    try {
      return await _remoteDataSource.getProfile();
    } on AppException catch (e) {
      throw mapExceptionToFailure(e);
    }
  }

  // -- Two-Factor Authentication --

  @override
  Future<Setup2FAResult> setup2FA() async {
    await _ensureConnected();
    try {
      return await _remoteDataSource.setup2FA();
    } on AppException catch (e) {
      throw mapExceptionToFailure(e);
    }
  }

  @override
  Future<bool> verify2FA(String code) async {
    await _ensureConnected();
    try {
      return await _remoteDataSource.verify2FA(code);
    } on AppException catch (e) {
      throw mapExceptionToFailure(e);
    }
  }

  @override
  Future<bool> validate2FA(String code) async {
    await _ensureConnected();
    try {
      return await _remoteDataSource.validate2FA(code);
    } on AppException catch (e) {
      throw mapExceptionToFailure(e);
    }
  }

  @override
  Future<void> disable2FA(String code) async {
    await _ensureConnected();
    try {
      await _remoteDataSource.disable2FA(code);
    } on AppException catch (e) {
      throw mapExceptionToFailure(e);
    }
  }

  // -- OAuth Provider Linking --

  @override
  Future<String> getOAuthAuthorizationUrl(OAuthProvider provider) async {
    await _ensureConnected();
    try {
      return await _remoteDataSource.getOAuthAuthorizationUrl(provider);
    } on AppException catch (e) {
      throw mapExceptionToFailure(e);
    }
  }

  @override
  Future<void> completeOAuthLink(OAuthProvider provider, String code) async {
    await _ensureConnected();
    try {
      await _remoteDataSource.completeOAuthLink(provider, code);
    } on AppException catch (e) {
      throw mapExceptionToFailure(e);
    }
  }

  @override
  Future<void> unlinkOAuth(OAuthProvider provider) async {
    await _ensureConnected();
    try {
      await _remoteDataSource.unlinkOAuth(provider);
    } on AppException catch (e) {
      throw mapExceptionToFailure(e);
    }
  }

  // -- Device / Session Management --

  @override
  Future<List<Device>> getDevices() async {
    await _ensureConnected();
    try {
      return await _remoteDataSource.getDevices();
    } on AppException catch (e) {
      throw mapExceptionToFailure(e);
    }
  }

  @override
  Future<Device> registerDevice({
    required String deviceName,
    required String platform,
    required String deviceId,
  }) async {
    await _ensureConnected();
    try {
      return await _remoteDataSource.registerDevice(
        deviceName: deviceName,
        platform: platform,
        deviceId: deviceId,
      );
    } on AppException catch (e) {
      throw mapExceptionToFailure(e);
    }
  }

  @override
  Future<void> removeDevice(String id) async {
    await _ensureConnected();
    try {
      await _remoteDataSource.removeDevice(id);
    } on AppException catch (e) {
      throw mapExceptionToFailure(e);
    }
  }

  // -- Account Deletion --

  @override
  Future<void> deleteAccount(String password, {String? totpCode}) async {
    await _ensureConnected();
    try {
      await _remoteDataSource.deleteAccount(password, totpCode: totpCode);
    } on AppException catch (e) {
      throw mapExceptionToFailure(e);
    }
  }

  // -- Private Helpers --

  /// Throws [NetworkFailure] if the device is offline.
  Future<void> _ensureConnected() async {
    if (!await _networkInfo.isConnected) {
      throw const NetworkFailure(message: 'No internet connection');
    }
  }
}
