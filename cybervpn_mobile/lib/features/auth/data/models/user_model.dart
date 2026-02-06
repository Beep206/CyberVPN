import 'package:freezed_annotation/freezed_annotation.dart';
import 'package:cybervpn_mobile/features/auth/domain/entities/user_entity.dart';

part 'user_model.freezed.dart';
part 'user_model.g.dart';

@freezed
sealed class UserModel with _$UserModel {
  const UserModel._();

  const factory UserModel({
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
  }) = _UserModel;

  factory UserModel.fromJson(Map<String, dynamic> json) => _$UserModelFromJson(json);

  UserEntity toEntity() => UserEntity(
    id: id,
    email: email,
    username: username,
    avatarUrl: avatarUrl,
    telegramId: telegramId,
    isEmailVerified: isEmailVerified,
    isPremium: isPremium,
    referralCode: referralCode,
    createdAt: createdAt,
    lastLoginAt: lastLoginAt,
  );
}
