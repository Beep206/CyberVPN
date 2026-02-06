import 'package:cybervpn_mobile/core/errors/failures.dart' as failures;
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/types/result.dart';

/// Structured error types for user-facing error handling.
///
/// [AppError] is a sealed class hierarchy that provides:
/// - Exhaustive pattern matching via `switch` expressions
/// - Localized error messages via [localizedMessage]
/// - Typed error codes for specific error categories
///
/// These errors are intended for the presentation layer (UI). Domain/infra
/// layers should continue using [Failure] subclasses with [Result<T>].
///
/// Example:
/// ```dart
/// final error = AppError.fromFailure(failure);
/// final message = error.localizedMessage(l10n);
/// ```
sealed class AppError {
  const AppError({required this.message, this.code});

  /// Human-readable error message (for logging/debugging).
  final String message;

  /// Optional error code for programmatic handling.
  final int? code;

  /// Creates an [AppError] from a domain [Failure] message and code.
  ///
  /// Maps failure types to the appropriate [AppError] subclass based on
  /// the error code or message content.
  factory AppError.network({required String message, int? code}) =
      NetworkError;

  factory AppError.auth({
    required String message,
    int? code,
    AuthErrorCode errorCode,
  }) = AuthError;

  factory AppError.server({required String message, int? code}) = ServerError;

  factory AppError.subscription({required String message, int? code}) =
      SubscriptionError;

  factory AppError.vpn({required String message, int? code}) = VpnError;

  factory AppError.cache({required String message, int? code}) = CacheError;

  factory AppError.validation({required String message, int? code}) =
      ValidationError;

  factory AppError.timeout({required String message, int? code}) =
      TimeoutError;

  factory AppError.unknown({required String message, int? code}) =
      UnknownError;

  /// Converts a domain [failures.Failure] to a presentation [AppError].
  ///
  /// Maps each failure subtype to the corresponding [AppError] subtype,
  /// preserving the error message and code.
  static AppError fromFailure(failures.Failure failure) => switch (failure) {
        failures.NetworkFailure(:final message, :final code) =>
          NetworkError(message: message, code: code),
        failures.AuthFailure(:final message, :final code) =>
          AuthError(message: message, code: code),
        failures.ServerFailure(:final message, :final code) =>
          ServerError(message: message, code: code),
        failures.SubscriptionFailure(:final message, :final code) =>
          SubscriptionError(message: message, code: code),
        failures.VpnFailure(:final message, :final code) =>
          VpnError(message: message, code: code),
        failures.CacheFailure(:final message, :final code) =>
          CacheError(message: message, code: code),
        failures.ValidationFailure(:final message, :final code) =>
          ValidationError(message: message, code: code),
        failures.TimeoutFailure(:final message, :final code) =>
          TimeoutError(message: message, code: code),
        _ => UnknownError(message: failure.message, code: failure.code),
      };
}

/// Error due to network connectivity issues (no internet, DNS failure, etc.).
final class NetworkError extends AppError {
  const NetworkError({required super.message, super.code});
}

/// Error related to authentication or authorization.
final class AuthError extends AppError {
  const AuthError({
    required super.message,
    super.code,
    this.errorCode = AuthErrorCode.unknown,
  });

  /// Typed error code for specific auth failure scenarios.
  final AuthErrorCode errorCode;
}

/// Error originating from the remote server (4xx/5xx responses).
final class ServerError extends AppError {
  const ServerError({required super.message, super.code});
}

/// Error related to subscription or billing operations.
final class SubscriptionError extends AppError {
  const SubscriptionError({required super.message, super.code});
}

/// Error related to VPN connection or tunnel operations.
final class VpnError extends AppError {
  const VpnError({required super.message, super.code});
}

/// Error from local cache or storage operations.
final class CacheError extends AppError {
  const CacheError({required super.message, super.code});
}

/// Error caused by invalid input or data validation.
final class ValidationError extends AppError {
  const ValidationError({required super.message, super.code});
}

/// Error caused by an operation exceeding its time limit.
final class TimeoutError extends AppError {
  const TimeoutError({required super.message, super.code});
}

/// Catch-all error for unexpected or unclassified failures.
final class UnknownError extends AppError {
  const UnknownError({required super.message, super.code});
}

/// Typed error codes for authentication failures.
///
/// Allows the UI to show context-specific messages and actions
/// (e.g. "Resend verification email" for [emailNotVerified]).
enum AuthErrorCode {
  /// Invalid email or password.
  invalidCredentials,

  /// User account is not verified.
  emailNotVerified,

  /// User account has been deactivated.
  accountDisabled,

  /// Session has expired, re-login required.
  sessionExpired,

  /// Refresh token is invalid or revoked.
  tokenRevoked,

  /// Too many login attempts.
  tooManyAttempts,

  /// Biometric authentication failed.
  biometricFailed,

  /// Unclassified auth error.
  unknown,
}

/// Extension providing localized user-facing error messages.
///
/// Uses the generated [AppLocalizations] to return translated error messages
/// appropriate for display in the UI.
///
/// ```dart
/// final error = AppError.network(message: 'DNS failure');
/// final userMessage = error.localizedMessage(l10n);
/// // Returns localized "No internet connection. Check your network settings."
/// ```
extension AppErrorLocalization on AppError {
  /// Returns a localized, user-friendly error message.
  String localizedMessage(AppLocalizations l10n) => switch (this) {
        NetworkError() => l10n.errorNetworkUnreachable,
        AuthError(:final errorCode) => switch (errorCode) {
            AuthErrorCode.invalidCredentials => l10n.errorInvalidCredentials,
            AuthErrorCode.sessionExpired => l10n.errorTokenExpired,
            AuthErrorCode.tooManyAttempts => l10n.errorRateLimited,
            AuthErrorCode.accountDisabled => l10n.errorAccountLocked,
            _ => l10n.errorAuthenticationFailed,
          },
        ServerError() => l10n.errorServerError,
        SubscriptionError() =>
          code == 402
              ? l10n.errorSubscriptionRequired
              : l10n.errorSubscriptionExpired,
        VpnError() => l10n.errorConnectionFailed,
        CacheError() => l10n.errorUnexpected,
        ValidationError() => message,
        TimeoutError() => l10n.errorConnectionTimeout,
        UnknownError() => l10n.errorUnexpected,
      };
}

/// Extension on [Result] for convenient [AppError] conversion.
///
/// ```dart
/// final result = await repository.getUser(id);
/// final error = result.appErrorOrNull;
/// if (error != null) {
///   showSnackBar(error.localizedMessage(l10n));
/// }
/// ```
extension ResultAppErrorExtension<T> on Result<T> {
  /// Returns the [AppError] if this is a [Failure], or `null` if [Success].
  AppError? get appErrorOrNull => switch (this) {
        Success() => null,
        Failure(:final failure) => AppError.fromFailure(failure),
      };
}
