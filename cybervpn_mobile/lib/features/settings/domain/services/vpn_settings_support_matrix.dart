enum VpnSettingsPlatform { android, ios, unsupported }

enum VpnSettingsSupportLevel {
  supported,
  reduced,
  unsupportedHidden,
  unsupportedVisible,
}

/// Describes how a single VPN setting should behave in the current UI.
class VpnSettingsFeatureSupport {
  const VpnSettingsFeatureSupport._(this.level, {this.message});

  const VpnSettingsFeatureSupport.supported()
    : this._(VpnSettingsSupportLevel.supported);

  const VpnSettingsFeatureSupport.reduced([String? message])
    : this._(VpnSettingsSupportLevel.reduced, message: message);

  const VpnSettingsFeatureSupport.unsupportedHidden([String? message])
    : this._(VpnSettingsSupportLevel.unsupportedHidden, message: message);

  const VpnSettingsFeatureSupport.unsupportedVisible([String? message])
    : this._(VpnSettingsSupportLevel.unsupportedVisible, message: message);

  final VpnSettingsSupportLevel level;
  final String? message;

  bool get isAvailable =>
      level == VpnSettingsSupportLevel.supported ||
      level == VpnSettingsSupportLevel.reduced;

  bool get isVisible => level != VpnSettingsSupportLevel.unsupportedHidden;

  bool get hasReducedSemantics => level == VpnSettingsSupportLevel.reduced;
}

/// One source of truth for advanced VPN settings visibility and help text.
class VpnSettingsSupportMatrix {
  const VpnSettingsSupportMatrix({
    required this.platform,
    required this.perAppProxy,
    required this.excludedRoutes,
    required this.localDns,
    required this.serverResolve,
    required this.sniffing,
    required this.proxyOnlyMode,
    required this.fragmentation,
    required this.mux,
    required this.preferredIpType,
    required this.manualMtu,
    this.advancedNoticeMessage,
  });

  factory VpnSettingsSupportMatrix.fromCapabilities({
    required VpnSettingsPlatform platform,
    required bool supportsPerAppProxy,
    required bool supportsExcludedRoutes,
    bool supportsLocalDns = false,
    bool supportsServerResolve = false,
    bool supportsSniffing = false,
    bool supportsProxyOnlyMode = false,
    required bool supportsFragmentation,
    required bool supportsMux,
    required bool supportsPreferredIpType,
    required bool supportsManualMtu,
  }) {
    switch (platform) {
      case VpnSettingsPlatform.android:
        return VpnSettingsSupportMatrix(
          platform: platform,
          perAppProxy: _fromCapability(
            supportsPerAppProxy,
            message: 'Per-App Proxy is unavailable on this Android runtime.',
          ),
          excludedRoutes: _fromCapability(
            supportsExcludedRoutes,
            message: 'Excluded Routes are unavailable on this Android runtime.',
          ),
          localDns: _fromCapability(
            supportsLocalDns,
            message:
                'Local DNS is not supported by the current Android VPN bridge.',
          ),
          serverResolve: _fromCapability(
            supportsServerResolve,
            message:
                'Server address resolve is unavailable on this Android runtime.',
          ),
          sniffing: _fromCapability(
            supportsSniffing,
            message: 'Packet analysis is unavailable on this Android runtime.',
          ),
          proxyOnlyMode: _fromCapability(
            supportsProxyOnlyMode,
            message: 'Proxy-only mode is unavailable on this Android runtime.',
          ),
          fragmentation: _fromCapability(
            supportsFragmentation,
            message: 'Fragmentation is unavailable on this Android runtime.',
          ),
          mux: _fromCapability(
            supportsMux,
            message: 'Mux is unavailable on this Android runtime.',
          ),
          preferredIpType: _fromCapability(
            supportsPreferredIpType,
            message:
                'Preferred IP Type is unavailable on this Android runtime.',
          ),
          manualMtu: _fromCapability(
            supportsManualMtu,
            message: 'Manual MTU is unavailable on this Android runtime.',
          ),
        );
      case VpnSettingsPlatform.ios:
        return VpnSettingsSupportMatrix(
          platform: platform,
          perAppProxy: supportsPerAppProxy
              ? const VpnSettingsFeatureSupport.supported()
              : const VpnSettingsFeatureSupport.unsupportedHidden(
                  'Per-App Proxy stays Android-only in this release.',
                ),
          excludedRoutes: supportsExcludedRoutes
              ? const VpnSettingsFeatureSupport.supported()
              : const VpnSettingsFeatureSupport.unsupportedHidden(
                  'Excluded Routes are not yet wired through the current iOS tunnel provider.',
                ),
          localDns: supportsLocalDns
              ? const VpnSettingsFeatureSupport.supported()
              : const VpnSettingsFeatureSupport.unsupportedVisible(
                  'Local DNS needs a dedicated mobile bridge and remains unavailable in this release.',
                ),
          serverResolve: supportsServerResolve
              ? const VpnSettingsFeatureSupport.reduced(
                  'Server resolve runs before connect and patches the generated config. iOS still keeps the current tunnel-provider flow.',
                )
              : const VpnSettingsFeatureSupport.unsupportedHidden(
                  'Server address resolve is unavailable on this iOS runtime.',
                ),
          sniffing: supportsSniffing
              ? const VpnSettingsFeatureSupport.reduced(
                  'Packet analysis is applied through the generated Xray config.',
                )
              : const VpnSettingsFeatureSupport.unsupportedHidden(
                  'Packet analysis is unavailable on this iOS runtime.',
                ),
          proxyOnlyMode: supportsProxyOnlyMode
              ? const VpnSettingsFeatureSupport.supported()
              : const VpnSettingsFeatureSupport.unsupportedHidden(
                  'Proxy-only mode stays Android-only in this release.',
                ),
          fragmentation: supportsFragmentation
              ? const VpnSettingsFeatureSupport.reduced(
                  'Applied through the Xray config. App-specific and route-specific exclusions remain unavailable on iOS.',
                )
              : const VpnSettingsFeatureSupport.unsupportedHidden(
                  'Fragmentation is unavailable on this iOS runtime.',
                ),
          mux: supportsMux
              ? const VpnSettingsFeatureSupport.reduced(
                  'Applied through the Xray config. iOS still uses the current full-tunnel provider flow.',
                )
              : const VpnSettingsFeatureSupport.unsupportedHidden(
                  'Mux is unavailable on this iOS runtime.',
                ),
          preferredIpType: supportsPreferredIpType
              ? const VpnSettingsFeatureSupport.reduced(
                  'Applied to the generated config, while iOS keeps the current full-tunnel route model.',
                )
              : const VpnSettingsFeatureSupport.unsupportedHidden(
                  'Preferred IP Type is unavailable on this iOS runtime.',
                ),
          manualMtu: supportsManualMtu
              ? const VpnSettingsFeatureSupport.supported()
              : const VpnSettingsFeatureSupport.unsupportedHidden(
                  'Manual MTU is not exposed by the current iOS tunnel provider.',
                ),
          advancedNoticeMessage:
              'iOS supports a reduced subset of advanced tunnel settings. '
              'Per-App Proxy, Excluded Routes, and Manual MTU remain Android-only in this release.',
        );
      case VpnSettingsPlatform.unsupported:
        return const VpnSettingsSupportMatrix(
          platform: VpnSettingsPlatform.unsupported,
          perAppProxy: VpnSettingsFeatureSupport.unsupportedHidden(
            'Per-App Proxy is unavailable on this platform.',
          ),
          excludedRoutes: VpnSettingsFeatureSupport.unsupportedHidden(
            'Excluded Routes are unavailable on this platform.',
          ),
          localDns: VpnSettingsFeatureSupport.unsupportedVisible(
            'Local DNS is unavailable on this platform.',
          ),
          serverResolve: VpnSettingsFeatureSupport.unsupportedHidden(
            'Server address resolve is unavailable on this platform.',
          ),
          sniffing: VpnSettingsFeatureSupport.unsupportedHidden(
            'Packet analysis is unavailable on this platform.',
          ),
          proxyOnlyMode: VpnSettingsFeatureSupport.unsupportedHidden(
            'Proxy-only mode is unavailable on this platform.',
          ),
          fragmentation: VpnSettingsFeatureSupport.unsupportedHidden(
            'Fragmentation is unavailable on this platform.',
          ),
          mux: VpnSettingsFeatureSupport.unsupportedHidden(
            'Mux is unavailable on this platform.',
          ),
          preferredIpType: VpnSettingsFeatureSupport.unsupportedHidden(
            'Preferred IP Type is unavailable on this platform.',
          ),
          manualMtu: VpnSettingsFeatureSupport.unsupportedHidden(
            'Manual MTU is unavailable on this platform.',
          ),
          advancedNoticeMessage:
              'Advanced VPN settings are unavailable on this platform.',
        );
    }
  }

  final VpnSettingsPlatform platform;
  final VpnSettingsFeatureSupport perAppProxy;
  final VpnSettingsFeatureSupport excludedRoutes;
  final VpnSettingsFeatureSupport localDns;
  final VpnSettingsFeatureSupport serverResolve;
  final VpnSettingsFeatureSupport sniffing;
  final VpnSettingsFeatureSupport proxyOnlyMode;
  final VpnSettingsFeatureSupport fragmentation;
  final VpnSettingsFeatureSupport mux;
  final VpnSettingsFeatureSupport preferredIpType;
  final VpnSettingsFeatureSupport manualMtu;
  final String? advancedNoticeMessage;

  bool get hasVisibleAdvancedControls =>
      perAppProxy.isVisible ||
      excludedRoutes.isVisible ||
      localDns.isVisible ||
      serverResolve.isVisible ||
      sniffing.isVisible ||
      proxyOnlyMode.isVisible ||
      fragmentation.isVisible ||
      mux.isVisible ||
      preferredIpType.isVisible ||
      manualMtu.isVisible;

  static VpnSettingsFeatureSupport _fromCapability(
    bool isSupported, {
    required String message,
  }) {
    if (isSupported) {
      return const VpnSettingsFeatureSupport.supported();
    }
    return VpnSettingsFeatureSupport.unsupportedVisible(message);
  }
}
