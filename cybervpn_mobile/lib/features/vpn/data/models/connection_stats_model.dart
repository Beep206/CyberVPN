import 'package:freezed_annotation/freezed_annotation.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/connection_stats_entity.dart';

part 'connection_stats_model.freezed.dart';
part 'connection_stats_model.g.dart';

@freezed
sealed class ConnectionStatsModel with _$ConnectionStatsModel {
  const ConnectionStatsModel._();

  const factory ConnectionStatsModel({
    @Default(0) int downloadSpeed,
    @Default(0) int uploadSpeed,
    @Default(0) int totalDownload,
    @Default(0) int totalUpload,
    @Default(0) int durationSeconds,
    String? serverName,
    String? protocol,
    String? ipAddress,
  }) = _ConnectionStatsModel;

  factory ConnectionStatsModel.fromJson(Map<String, dynamic> json) => _$ConnectionStatsModelFromJson(json);

  ConnectionStatsEntity toEntity() => ConnectionStatsEntity(
    downloadSpeed: downloadSpeed, uploadSpeed: uploadSpeed,
    totalDownload: totalDownload, totalUpload: totalUpload,
    connectionDuration: Duration(seconds: durationSeconds),
    serverName: serverName, protocol: protocol, ipAddress: ipAddress,
  );
}
