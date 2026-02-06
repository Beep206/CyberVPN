import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/vpn_config_entity.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/connection_state_entity.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/connection_stats_entity.dart';

abstract class VpnRepository {
  Future<Result<void>> connect(VpnConfigEntity config);
  Future<Result<void>> disconnect();
  Future<Result<bool>> get isConnected;
  Stream<ConnectionStateEntity> get connectionStateStream;
  Stream<ConnectionStatsEntity> get connectionStatsStream;
  Future<Result<VpnConfigEntity?>> getLastConfig();
  Future<Result<void>> saveConfig(VpnConfigEntity config);
  Future<Result<List<VpnConfigEntity>>> getSavedConfigs();
  Future<Result<void>> deleteConfig(String id);
}
