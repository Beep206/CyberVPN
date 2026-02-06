import 'package:freezed_annotation/freezed_annotation.dart';

part 'server_entity.freezed.dart';

@freezed
sealed class ServerEntity with _$ServerEntity {
  const factory ServerEntity({
    required String id,
    required String name,
    required String countryCode,
    required String countryName,
    required String city,
    required String address,
    required int port,
    @Default('vless') String protocol,
    @Default(true) bool isAvailable,
    @Default(false) bool isPremium,
    @Default(false) bool isFavorite,
    int? ping,
    double? load,
  }) = _ServerEntity;
}
