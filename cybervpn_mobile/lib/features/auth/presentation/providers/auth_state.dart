import 'package:cybervpn_mobile/features/auth/domain/entities/user_entity.dart';

/// Sealed class representing the authentication state.
///
/// Uses a sealed hierarchy so downstream consumers can exhaustively
/// pattern-match on state variants.
sealed class AuthState {
  const AuthState();
}

/// The auth subsystem is performing an async operation (login, register, etc.).
final class AuthLoading extends AuthState {
  const AuthLoading();
}

/// The user is authenticated with a valid [user] entity.
final class AuthAuthenticated extends AuthState {
  final UserEntity user;
  const AuthAuthenticated(this.user);

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is AuthAuthenticated &&
          runtimeType == other.runtimeType &&
          user == other.user;

  @override
  int get hashCode => user.hashCode;
}

/// No valid session exists; the user must authenticate.
final class AuthUnauthenticated extends AuthState {
  const AuthUnauthenticated();
}

/// An error occurred during an auth operation.
final class AuthError extends AuthState {
  final String message;
  const AuthError(this.message);

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is AuthError &&
          runtimeType == other.runtimeType &&
          message == other.message;

  @override
  int get hashCode => message.hashCode;
}
