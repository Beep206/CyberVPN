import 'package:flutter/services.dart';
import 'package:cybervpn_mobile/core/storage/local_storage.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

class SplitTunnelAndroid {
  static const MethodChannel _channel = MethodChannel('com.cybervpn/split_tunnel');
  final LocalStorageWrapper _localStorage;
  static const String _excludedAppsKey = 'split_tunnel_excluded_apps';

  SplitTunnelAndroid(this._localStorage);

  Future<List<String>> getInstalledApps() async {
    try {
      final result = await _channel.invokeMethod<List<dynamic>>('getInstalledApps');
      return result?.cast<String>() ?? [];
    } on PlatformException catch (e) {
      AppLogger.error('Failed to get installed apps', error: e);
      return [];
    }
  }

  Future<void> setExcludedApps(List<String> packageNames) async {
    try {
      await _channel.invokeMethod('setExcludedApps', {'packages': packageNames});
      await _localStorage.setStringList(_excludedAppsKey, packageNames);
    } on PlatformException catch (e) {
      AppLogger.error('Failed to set excluded apps', error: e);
      rethrow;
    }
  }

  List<String> getExcludedApps() {
    return _localStorage.getStringList(_excludedAppsKey) ?? [];
  }
}
