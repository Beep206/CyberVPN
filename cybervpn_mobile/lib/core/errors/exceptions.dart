/// Base exception class for the application.
///
/// All infrastructure-level exceptions extend this class, providing a
/// consistent interface that maps to domain [Failure] types.
abstract class AppException implements Exception {
  final String message;
  final int? code;

  const AppException({required this.message, this.code});

  @override
  String toString() => '$runtimeType(message: $message, code: $code)';
}

/// Exception originating from the remote server (e.g. 4xx/5xx responses).
class ServerException extends AppException {
  const ServerException({required super.message, super.code});
}

/// Exception originating from local cache or storage operations.
class CacheException extends AppException {
  const CacheException({required super.message, super.code});
}

/// Exception due to network connectivity issues.
class NetworkException extends AppException {
  const NetworkException({required super.message, super.code});
}

/// Exception related to authentication or authorization.
class AuthException extends AppException {
  const AuthException({required super.message, super.code});
}

/// Exception related to VPN connection or tunnel operations.
class VpnException extends AppException {
  const VpnException({required super.message, super.code});
}

/// Exception thrown when certificate pinning validation fails.
///
/// This indicates a potential MITM attack or misconfigured certificate.
class CertificatePinningException extends AppException {
  const CertificatePinningException({
    required super.message,
    this.fingerprint,
    this.subject,
  }) : super(code: null);

  /// The SHA-256 fingerprint of the rejected certificate.
  final String? fingerprint;

  /// The subject of the rejected certificate.
  final String? subject;

  @override
  String toString() {
    return 'CertificatePinningException(message: $message, '
        'fingerprint: $fingerprint, subject: $subject)';
  }
}
