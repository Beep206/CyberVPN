import 'package:freezed_annotation/freezed_annotation.dart';

part 'connection_state_entity.freezed.dart';

enum VpnConnectionStatus {
  disconnected,
  connecting,
  connected,
  disconnecting,
  error,
}

@freezed
sealed class ConnectionStateEntity with _$ConnectionStateEntity {
  const factory ConnectionStateEntity({
    @Default(VpnConnectionStatus.disconnected) VpnConnectionStatus status,
    String? connectedServerId,
    DateTime? connectedAt,
    String? errorMessage,
    @Default(0) int downloadSpeed,
    @Default(0) int uploadSpeed,
    @Default(0) int totalDownload,
    @Default(0) int totalUpload,
  }) = _ConnectionStateEntity;
}
