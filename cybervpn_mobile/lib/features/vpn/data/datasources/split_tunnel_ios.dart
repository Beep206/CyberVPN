import 'package:flutter/services.dart';
import 'package:cybervpn_mobile/core/storage/local_storage.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

class SplitTunnelIos {
  static const MethodChannel _channel = MethodChannel('com.cybervpn/split_tunnel');
  final LocalStorageWrapper _localStorage;
  static const String _excludedDomainsKey = 'split_tunnel_excluded_domains';

  SplitTunnelIos(this._localStorage);

  Future<void> setExcludedDomains(List<String> domains) async {
    try {
      await _channel.invokeMethod('setExcludedDomains', {'domains': domains});
      await _localStorage.setStringList(_excludedDomainsKey, domains);
    } on PlatformException catch (e) {
      AppLogger.error('Failed to set excluded domains', error: e);
      rethrow;
    }
  }

  Future<List<String>> getExcludedDomains() async {
    return await _localStorage.getStringList(_excludedDomainsKey) ?? [];
  }

  Future<void> addExcludedDomain(String domain) async {
    final current = await getExcludedDomains();
    if (!current.contains(domain)) {
      current.add(domain);
      await setExcludedDomains(current);
    }
  }

  Future<void> removeExcludedDomain(String domain) async {
    final current = await getExcludedDomains();
    current.remove(domain);
    await setExcludedDomains(current);
  }
}
