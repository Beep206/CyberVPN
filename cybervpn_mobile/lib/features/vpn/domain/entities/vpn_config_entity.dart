import 'package:freezed_annotation/freezed_annotation.dart';

part 'vpn_config_entity.freezed.dart';

enum VpnProtocol { vless, vmess, trojan, shadowsocks }

@freezed
abstract class VpnConfigEntity with _$VpnConfigEntity {
  const factory VpnConfigEntity({
    required String id,
    required String name,
    required String serverAddress,
    required int port,
    required VpnProtocol protocol,
    required String configData,
    String? remark,
    @Default(false) bool isFavorite,
  }) = _VpnConfigEntity;
}
