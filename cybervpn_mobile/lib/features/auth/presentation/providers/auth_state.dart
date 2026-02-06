import 'package:freezed_annotation/freezed_annotation.dart';

import 'package:cybervpn_mobile/features/auth/domain/entities/user_entity.dart';

part 'auth_state.freezed.dart';

/// Sealed class representing the authentication state.
///
/// Uses a freezed union type so downstream consumers can exhaustively
/// pattern-match on state variants with auto-generated ==, hashCode,
/// and toString.
@freezed
sealed class AuthState with _$AuthState {
  /// The auth subsystem is performing an async operation (login, register, etc.).
  const factory AuthState.loading() = AuthLoading;

  /// The user is authenticated with a valid [user] entity.
  const factory AuthState.authenticated(UserEntity user) = AuthAuthenticated;

  /// No valid session exists; the user must authenticate.
  const factory AuthState.unauthenticated() = AuthUnauthenticated;

  /// An error occurred during an auth operation.
  const factory AuthState.error(String message) = AuthError;
}
