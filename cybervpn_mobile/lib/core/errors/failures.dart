/// Base failure class for the application.
///
/// All domain-level failures extend this sealed class, providing a consistent
/// interface for error handling across the app. Exhaustive pattern matching
/// is enforced at compile time via the `sealed` keyword.
sealed class Failure {
  final String message;
  final int? code;

  const Failure({required this.message, this.code});

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is Failure &&
          runtimeType == other.runtimeType &&
          message == other.message &&
          code == other.code;

  @override
  int get hashCode => Object.hash(runtimeType, message, code);

  @override
  String toString() => '$runtimeType(message: $message, code: $code)';

  /// Serializes this failure to a JSON-compatible map for structured telemetry.
  Map<String, dynamic> toJson() => {
        'type': runtimeType.toString(),
        'message': message,
        if (code != null) 'code': code,
      };
}

/// Failure originating from the remote server (e.g. 4xx/5xx responses).
class ServerFailure extends Failure {
  const ServerFailure({required super.message, super.code});
}

/// Failure originating from local cache or storage operations.
class CacheFailure extends Failure {
  const CacheFailure({required super.message, super.code});
}

/// Failure due to network connectivity issues.
class NetworkFailure extends Failure {
  const NetworkFailure({required super.message, super.code});
}

/// Failure related to authentication or authorization.
class AuthFailure extends Failure {
  const AuthFailure({required super.message, super.code});
}

/// Failure related to VPN connection or tunnel operations.
class VpnFailure extends Failure {
  const VpnFailure({required super.message, super.code});
}

/// Failure related to subscription or billing operations.
class SubscriptionFailure extends Failure {
  const SubscriptionFailure({required super.message, super.code});
}

/// Failure caused by invalid input or data validation.
class ValidationFailure extends Failure {
  const ValidationFailure({required super.message, super.code});
}

/// Failure caused by an operation exceeding its time limit.
class TimeoutFailure extends Failure {
  const TimeoutFailure({required super.message, super.code});
}

/// Failure caused by insufficient permissions (HTTP 403).
class AccessDeniedFailure extends Failure {
  const AccessDeniedFailure({required super.message, super.code});
}

/// Failure caused by rate limiting (HTTP 429).
class RateLimitFailure extends Failure {
  final Duration? retryAfter;

  const RateLimitFailure({required super.message, super.code, this.retryAfter});

  @override
  Map<String, dynamic> toJson() => {
        ...super.toJson(),
        if (retryAfter != null) 'retryAfterMs': retryAfter!.inMilliseconds,
      };

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is RateLimitFailure &&
          message == other.message &&
          code == other.code &&
          retryAfter == other.retryAfter;

  @override
  int get hashCode => Object.hash(runtimeType, message, code, retryAfter);
}

/// Catch-all failure for unexpected or unclassified errors.
class UnknownFailure extends Failure {
  const UnknownFailure({required super.message, super.code});
}
