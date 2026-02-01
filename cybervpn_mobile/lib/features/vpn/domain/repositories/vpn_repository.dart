import 'package:cybervpn_mobile/features/vpn/domain/entities/vpn_config_entity.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/connection_state_entity.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/connection_stats_entity.dart';

abstract class VpnRepository {
  Future<void> connect(VpnConfigEntity config);
  Future<void> disconnect();
  Future<bool> get isConnected;
  Stream<ConnectionStateEntity> get connectionStateStream;
  Stream<ConnectionStatsEntity> get connectionStatsStream;
  Future<VpnConfigEntity?> getLastConfig();
  Future<void> saveConfig(VpnConfigEntity config);
  Future<List<VpnConfigEntity>> getSavedConfigs();
  Future<void> deleteConfig(String id);
}
