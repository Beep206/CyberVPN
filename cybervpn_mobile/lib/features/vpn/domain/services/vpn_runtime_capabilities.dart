import 'dart:io' show Platform;

import 'package:flutter/foundation.dart' show kIsWeb;

/// Declares which advanced VPN features can be applied on the current runtime.
class VpnRuntimeCapabilities {
  const VpnRuntimeCapabilities({
    required this.supportsPerAppProxy,
    required this.supportsExcludedRoutes,
    required this.supportsRoutingRules,
    required this.supportsMux,
    required this.supportsFragmentation,
    required this.supportsPreferredIpType,
    required this.supportsDnsOverride,
    required this.supportsManualMtu,
    this.supportsSniffing = false,
    this.supportsProxyOnlyMode = false,
    this.supportsServerAddressResolve = false,
    this.supportsLocalDns = false,
    this.supportsLanProxyAccess = false,
  });

  factory VpnRuntimeCapabilities.currentPlatform() {
    if (kIsWeb) {
      return const VpnRuntimeCapabilities.unsupported();
    }

    if (Platform.isAndroid) {
      return const VpnRuntimeCapabilities(
        supportsPerAppProxy: true,
        supportsExcludedRoutes: true,
        supportsRoutingRules: true,
        supportsMux: true,
        supportsFragmentation: true,
        supportsPreferredIpType: true,
        supportsDnsOverride: true,
        supportsManualMtu: true,
        supportsSniffing: true,
        supportsProxyOnlyMode: true,
        supportsServerAddressResolve: true,
        supportsLocalDns: false,
        supportsLanProxyAccess: true,
      );
    }

    if (Platform.isIOS) {
      return const VpnRuntimeCapabilities(
        supportsPerAppProxy: false,
        supportsExcludedRoutes: false,
        supportsRoutingRules: true,
        supportsMux: true,
        supportsFragmentation: true,
        supportsPreferredIpType: true,
        supportsDnsOverride: true,
        supportsManualMtu: false,
        supportsSniffing: true,
        supportsProxyOnlyMode: false,
        supportsServerAddressResolve: true,
        supportsLocalDns: false,
        supportsLanProxyAccess: false,
      );
    }

    return const VpnRuntimeCapabilities.unsupported();
  }

  const VpnRuntimeCapabilities.unsupported()
    : supportsPerAppProxy = false,
      supportsExcludedRoutes = false,
      supportsRoutingRules = false,
      supportsMux = false,
      supportsFragmentation = false,
      supportsPreferredIpType = false,
      supportsDnsOverride = false,
      supportsManualMtu = false,
      supportsSniffing = false,
      supportsProxyOnlyMode = false,
      supportsServerAddressResolve = false,
      supportsLocalDns = false,
      supportsLanProxyAccess = false;

  final bool supportsPerAppProxy;
  final bool supportsExcludedRoutes;
  final bool supportsRoutingRules;
  final bool supportsMux;
  final bool supportsFragmentation;
  final bool supportsPreferredIpType;
  final bool supportsDnsOverride;
  final bool supportsManualMtu;
  final bool supportsSniffing;
  final bool supportsProxyOnlyMode;
  final bool supportsServerAddressResolve;
  final bool supportsLocalDns;
  final bool supportsLanProxyAccess;
}
