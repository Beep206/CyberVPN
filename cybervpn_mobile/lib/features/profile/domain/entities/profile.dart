import 'package:freezed_annotation/freezed_annotation.dart';

import 'package:cybervpn_mobile/features/profile/domain/entities/oauth_provider.dart';

part 'profile.freezed.dart';

/// User profile entity
///
/// Contains the user's profile information including authentication
/// state, linked OAuth providers, and 2FA status.
@freezed
abstract class Profile with _$Profile {
  const factory Profile({
    required String id,
    required String email,
    String? username,
    String? avatarUrl,
    String? telegramId,
    @Default(false) bool isEmailVerified,
    @Default(false) bool is2FAEnabled,
    @Default([]) List<OAuthProvider> linkedProviders,
    DateTime? createdAt,
    DateTime? lastLoginAt,
  }) = _Profile;
}
