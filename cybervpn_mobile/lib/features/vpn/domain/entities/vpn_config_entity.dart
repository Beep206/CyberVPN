import 'package:freezed_annotation/freezed_annotation.dart';

import 'package:cybervpn_mobile/core/domain/vpn_protocol.dart';
export 'package:cybervpn_mobile/core/domain/vpn_protocol.dart';

part 'vpn_config_entity.freezed.dart';

@freezed
sealed class VpnConfigEntity with _$VpnConfigEntity {
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
