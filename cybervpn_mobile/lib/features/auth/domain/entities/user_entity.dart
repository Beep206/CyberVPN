import 'package:freezed_annotation/freezed_annotation.dart';

part 'user_entity.freezed.dart';

@freezed
sealed class UserEntity with _$UserEntity {
  const factory UserEntity({
    required String id,
    required String email,
    String? username,
    String? avatarUrl,
    String? telegramId,
    @Default(false) bool isEmailVerified,
    @Default(false) bool isPremium,
    String? referralCode,
    DateTime? createdAt,
    DateTime? lastLoginAt,
  }) = _UserEntity;
}
