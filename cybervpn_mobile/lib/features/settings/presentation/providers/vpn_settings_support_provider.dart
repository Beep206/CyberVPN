import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/di/providers.dart';
import 'package:cybervpn_mobile/features/settings/domain/services/vpn_settings_support_matrix.dart';

final vpnSettingsPlatformProvider = Provider<VpnSettingsPlatform>((ref) {
  if (kIsWeb) {
    return VpnSettingsPlatform.unsupported;
  }

  switch (defaultTargetPlatform) {
    case TargetPlatform.android:
      return VpnSettingsPlatform.android;
    case TargetPlatform.iOS:
      return VpnSettingsPlatform.ios;
    default:
      return VpnSettingsPlatform.unsupported;
  }
});

final vpnSettingsSupportMatrixProvider = Provider<VpnSettingsSupportMatrix>((
  ref,
) {
  final capabilities = ref.watch(vpnRuntimeCapabilitiesProvider);
  final platform = ref.watch(vpnSettingsPlatformProvider);

  return VpnSettingsSupportMatrix.fromCapabilities(
    platform: platform,
    supportsPerAppProxy: capabilities.supportsPerAppProxy,
    supportsExcludedRoutes: capabilities.supportsExcludedRoutes,
    supportsLocalDns: capabilities.supportsLocalDns,
    supportsServerResolve: capabilities.supportsServerAddressResolve,
    supportsSniffing: capabilities.supportsSniffing,
    supportsProxyOnlyMode: capabilities.supportsProxyOnlyMode,
    supportsFragmentation: capabilities.supportsFragmentation,
    supportsMux: capabilities.supportsMux,
    supportsPreferredIpType: capabilities.supportsPreferredIpType,
    supportsManualMtu: capabilities.supportsManualMtu,
  );
});
