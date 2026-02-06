import 'package:freezed_annotation/freezed_annotation.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/vpn_config_entity.dart';

part 'vpn_config_model.freezed.dart';
part 'vpn_config_model.g.dart';

@freezed
sealed class VpnConfigModel with _$VpnConfigModel {
  const VpnConfigModel._();

  const factory VpnConfigModel({
    required String id,
    required String name,
    required String serverAddress,
    required int port,
    required String protocol,
    required String configData,
    String? remark,
    @Default(false) bool isFavorite,
  }) = _VpnConfigModel;

  factory VpnConfigModel.fromJson(Map<String, dynamic> json) => _$VpnConfigModelFromJson(json);

  VpnConfigEntity toEntity() => VpnConfigEntity(
    id: id, name: name, serverAddress: serverAddress, port: port,
    protocol: VpnProtocol.values.firstWhere((e) => e.name == protocol, orElse: () => VpnProtocol.vless),
    configData: configData, remark: remark, isFavorite: isFavorite,
  );
}
