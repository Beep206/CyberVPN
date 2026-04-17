import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/features/settings/domain/services/vpn_settings_support_matrix.dart';

void main() {
  group('VpnSettingsSupportMatrix', () {
    test('maps Android capabilities to visible advanced controls', () {
      final matrix = VpnSettingsSupportMatrix.fromCapabilities(
        platform: VpnSettingsPlatform.android,
        supportsPerAppProxy: true,
        supportsExcludedRoutes: true,
        supportsServerResolve: true,
        supportsSniffing: true,
        supportsProxyOnlyMode: true,
        supportsFragmentation: true,
        supportsMux: true,
        supportsPreferredIpType: true,
        supportsManualMtu: true,
      );

      expect(matrix.platform, VpnSettingsPlatform.android);
      expect(matrix.perAppProxy.isVisible, isTrue);
      expect(matrix.excludedRoutes.isVisible, isTrue);
      expect(matrix.serverResolve.isVisible, isTrue);
      expect(matrix.sniffing.isVisible, isTrue);
      expect(matrix.proxyOnlyMode.isVisible, isTrue);
      expect(matrix.localDns.isVisible, isTrue);
      expect(matrix.localDns.isAvailable, isFalse);
      expect(matrix.manualMtu.isVisible, isTrue);
      expect(matrix.advancedNoticeMessage, isNull);
    });

    test(
      'maps iOS capabilities to reduced semantics and hidden dead toggles',
      () {
        final matrix = VpnSettingsSupportMatrix.fromCapabilities(
          platform: VpnSettingsPlatform.ios,
          supportsPerAppProxy: false,
          supportsExcludedRoutes: false,
          supportsServerResolve: true,
          supportsSniffing: true,
          supportsProxyOnlyMode: false,
          supportsFragmentation: true,
          supportsMux: true,
          supportsPreferredIpType: true,
          supportsManualMtu: false,
        );

        expect(matrix.platform, VpnSettingsPlatform.ios);
        expect(matrix.perAppProxy.isVisible, isFalse);
        expect(matrix.excludedRoutes.isVisible, isFalse);
        expect(matrix.serverResolve.hasReducedSemantics, isTrue);
        expect(matrix.sniffing.hasReducedSemantics, isTrue);
        expect(matrix.proxyOnlyMode.isVisible, isFalse);
        expect(matrix.localDns.isVisible, isTrue);
        expect(matrix.localDns.isAvailable, isFalse);
        expect(matrix.fragmentation.hasReducedSemantics, isTrue);
        expect(matrix.mux.hasReducedSemantics, isTrue);
        expect(matrix.preferredIpType.hasReducedSemantics, isTrue);
        expect(matrix.manualMtu.isVisible, isFalse);
        expect(matrix.advancedNoticeMessage, isNotNull);
      },
    );
  });
}
