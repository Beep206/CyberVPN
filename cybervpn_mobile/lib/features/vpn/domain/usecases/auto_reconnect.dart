import 'dart:async';
import 'package:cybervpn_mobile/core/constants/vpn_constants.dart';
import 'package:cybervpn_mobile/core/network/network_info.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/vpn_config_entity.dart';
import 'package:cybervpn_mobile/features/vpn/domain/repositories/vpn_repository.dart';

class AutoReconnectService {
  final VpnRepository _repository;
  final NetworkInfo _networkInfo;
  StreamSubscription<bool>? _connectivitySub;
  VpnConfigEntity? _lastConfig;
  int _retryCount = 0;

  AutoReconnectService({required VpnRepository repository, required NetworkInfo networkInfo})
      : _repository = repository,
        _networkInfo = networkInfo;

  void start(VpnConfigEntity config) {
    _lastConfig = config;
    _retryCount = 0;
    _connectivitySub?.cancel();
    _connectivitySub = _networkInfo.onConnectivityChanged.listen((connected) async {
      final isConnectedResult = await _repository.isConnected;
      final isCurrentlyConnected = switch (isConnectedResult) {
        Success(:final data) => data,
        Failure() => false,
      };
      if (connected && _lastConfig != null && !isCurrentlyConnected) {
        await _attemptReconnect();
      }
    });
  }

  Future<void> _attemptReconnect() async {
    if (_lastConfig == null || _retryCount >= VpnConstants.maxReconnectAttempts) {
      AppLogger.warning('Auto-reconnect: max attempts reached');
      return;
    }
    _retryCount++;
    try {
      AppLogger.info('Auto-reconnect: attempt $_retryCount');
      await _repository.connect(_lastConfig!);
      _retryCount = 0;
    } catch (e) {
      AppLogger.error('Auto-reconnect failed', error: e);
      await Future<void>.delayed(Duration(seconds: VpnConstants.reconnectDelaySeconds * _retryCount));
      if (_retryCount < VpnConstants.maxReconnectAttempts) {
        await _attemptReconnect();
      }
    }
  }

  void stop() {
    _connectivitySub?.cancel();
    _connectivitySub = null;
    _lastConfig = null;
    _retryCount = 0;
  }

  void dispose() {
    stop();
  }
}
