import 'package:freezed_annotation/freezed_annotation.dart';

part 'server_entity.freezed.dart';

@Freezed(fromJson: false, toJson: false)
sealed class ServerEntity with _$ServerEntity {
  const ServerEntity._();

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

  /// Deserializes a [ServerEntity] from a JSON-compatible map.
  factory ServerEntity.fromJson(Map<String, dynamic> map) => ServerEntity(
        id: map['id'] as String,
        name: map['name'] as String,
        countryCode: map['countryCode'] as String,
        countryName: map['countryName'] as String,
        city: map['city'] as String,
        address: map['address'] as String,
        port: map['port'] as int,
        protocol: map['protocol'] as String? ?? 'vless',
        isAvailable: map['isAvailable'] as bool? ?? true,
        isPremium: map['isPremium'] as bool? ?? false,
        isFavorite: map['isFavorite'] as bool? ?? false,
        ping: map['ping'] as int?,
        load: (map['load'] as num?)?.toDouble(),
      );

  /// Serializes this entity to a JSON-compatible map.
  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'countryCode': countryCode,
        'countryName': countryName,
        'city': city,
        'address': address,
        'port': port,
        'protocol': protocol,
        'isAvailable': isAvailable,
        'isPremium': isPremium,
        'isFavorite': isFavorite,
        if (ping != null) 'ping': ping,
        if (load != null) 'load': load,
      };
}
