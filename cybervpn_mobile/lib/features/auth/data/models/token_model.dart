import 'package:freezed_annotation/freezed_annotation.dart';

part 'token_model.freezed.dart';
part 'token_model.g.dart';

@freezed
abstract class TokenModel with _$TokenModel {
  const factory TokenModel({
    required String accessToken,
    required String refreshToken,
    required int expiresIn,
    String? tokenType,
  }) = _TokenModel;

  factory TokenModel.fromJson(Map<String, dynamic> json) =>
      _$TokenModelFromJson(json);
}
