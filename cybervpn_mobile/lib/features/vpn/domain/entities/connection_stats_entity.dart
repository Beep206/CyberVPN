import 'package:freezed_annotation/freezed_annotation.dart';

part 'connection_stats_entity.freezed.dart';

@freezed
sealed class ConnectionStatsEntity with _$ConnectionStatsEntity {
  const factory ConnectionStatsEntity({
    @Default(0) int downloadSpeed,
    @Default(0) int uploadSpeed,
    @Default(0) int totalDownload,
    @Default(0) int totalUpload,
    @Default(Duration.zero) Duration connectionDuration,
    String? serverName,
    String? protocol,
    String? ipAddress,
  }) = _ConnectionStatsEntity;
}
