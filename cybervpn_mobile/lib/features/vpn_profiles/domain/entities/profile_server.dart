import 'package:freezed_annotation/freezed_annotation.dart';

import 'package:cybervpn_mobile/core/domain/vpn_protocol.dart';

part 'profile_server.freezed.dart';

@freezed
sealed class ProfileServer with _$ProfileServer {
  const factory ProfileServer({
    required String id,
    required String profileId,
    required String name,
    required String serverAddress,
    required int port,
    required VpnProtocol protocol,
    required String configData,
    String? remark,
    @Default(false) bool isFavorite,
    required int sortOrder,
    int? latencyMs,
    required DateTime createdAt,
  }) = _ProfileServer;
}
