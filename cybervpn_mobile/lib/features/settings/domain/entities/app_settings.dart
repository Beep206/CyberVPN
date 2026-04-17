import 'package:freezed_annotation/freezed_annotation.dart';

import 'package:cybervpn_mobile/features/settings/domain/entities/excluded_route_entry.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/routing_profile.dart';

part 'app_settings.freezed.dart';

/// Theme mode for the application UI
enum AppThemeMode { materialYou, cyberpunk }

/// Brightness setting for the application
enum AppBrightness { system, light, dark }

/// Preferred VPN protocol
enum PreferredProtocol { auto, vlessReality, vlessXhttp, vlessWsTls }

/// DNS provider for VPN connections
enum DnsProvider { system, cloudflare, google, quad9, custom }

/// MTU mode for VPN connections
enum MtuMode { auto, manual }

/// Log level for application diagnostics
enum LogLevel { auto, debug, info, warning, error, none }

/// Per-app proxy behavior.
enum PerAppProxyMode { off, proxySelected, bypassSelected }

/// Preferred IP family for outbound resolution.
enum PreferredIpType { auto, ipv4, ipv6 }

/// Runtime mode used when starting the VPN engine.
enum VpnRunMode { vpn, proxyOnly }

/// Server ping strategy used by the app.
enum PingMode { tcp, realDelay, proxyGet, proxyHead, icmp }

/// How ping values are rendered in server lists.
enum PingDisplayMode { latency, quality }

/// Happ-like ping presentation mode used for future server lists and summaries.
enum PingResultMode { time, icon }

/// Strategy used when auto-connecting from a subscription source.
enum SubscriptionConnectStrategy { lastUsed, lowestDelay, random }

/// Controls how subscription requests choose their User-Agent header.
enum SubscriptionUserAgentMode { appDefault, custom }

/// Sort strategy applied to servers inside one subscription source.
enum SubscriptionSortMode { none, ping, alphabetical }

/// Text scale factor for accessibility
enum TextScale {
  /// System default text scale
  system,

  /// Small text (0.85x)
  small,

  /// Default text (1.0x)
  normal,

  /// Large text (1.15x)
  large,

  /// Extra large text (1.3x)
  extraLarge,
}

/// Application settings entity
///
/// Contains all user-configurable settings including theme, connection,
/// notification, and privacy preferences.
@freezed
sealed class AppSettings with _$AppSettings {
  const factory AppSettings({
    // Appearance
    @Default(AppThemeMode.cyberpunk) AppThemeMode themeMode,
    @Default(AppBrightness.system) AppBrightness brightness,
    @Default(false) bool dynamicColor,
    @Default(false) bool oledMode,
    @Default(false) bool scanlineEffect,
    @Default(TextScale.system) TextScale textScale,

    // Connection
    @Default(PreferredProtocol.auto) PreferredProtocol preferredProtocol,
    @Default(false) bool autoConnectOnLaunch,
    @Default(false) bool autoConnectUntrustedWifi,
    @Default(false) bool killSwitch,

    // Trusted WiFi Networks (SSIDs that won't trigger auto-connect)
    @Default(<String>[]) List<String> trustedWifiNetworks,

    // Routing
    @Default(false) bool routingEnabled,
    @Default(<RoutingProfile>[]) List<RoutingProfile> routingProfiles,
    String? activeRoutingProfileId,
    @Default(<String>[]) List<String> bypassSubnets,
    @Default(<ExcludedRouteEntry>[])
    List<ExcludedRouteEntry> excludedRouteEntries,

    // Split Tunneling
    @Default(false) bool splitTunneling,
    @Default(PerAppProxyMode.off) PerAppProxyMode perAppProxyMode,
    @Default(<String>[]) List<String> perAppProxyAppIds,

    // DNS
    @Default(DnsProvider.system) DnsProvider dnsProvider,
    String? customDns,
    @Default(false) bool useLocalDns,
    @Default(1053) int localDnsPort,
    @Default(false) bool useDnsFromJson,

    // Xray transport features
    @Default(false) bool fragmentationEnabled,
    @Default(false) bool muxEnabled,
    @Default(PreferredIpType.auto) PreferredIpType preferredIpType,
    @Default(false) bool sniffingEnabled,
    @Default(VpnRunMode.vpn) VpnRunMode vpnRunMode,
    @Default(false) bool serverAddressResolveEnabled,
    String? serverAddressResolveDohUrl,
    String? serverAddressResolveDnsIp,

    // Ping
    @Default(PingMode.tcp) PingMode pingMode,
    @Default('https://google.com/generate_204') String pingTestUrl,
    @Default(PingDisplayMode.latency) PingDisplayMode pingDisplayMode,
    @Default(PingResultMode.time) PingResultMode pingResultMode,

    // MTU
    @Default(MtuMode.auto) MtuMode mtuMode,
    @Default(1400) int mtuValue,

    // Subscription policies
    @Default(true) bool subscriptionAutoUpdateEnabled,
    @Default(24) int subscriptionAutoUpdateIntervalHours,
    @Default(false) bool subscriptionUpdateNotificationsEnabled,
    @Default(true) bool subscriptionAutoUpdateOnOpen,
    @Default(false) bool subscriptionPingOnOpenEnabled,
    @Default(SubscriptionConnectStrategy.lastUsed)
    SubscriptionConnectStrategy subscriptionConnectStrategy,
    @Default(true) bool preventDuplicateImports,
    @Default(true) bool collapseSubscriptions,
    @Default(false) bool subscriptionNoFilter,
    @Default(SubscriptionUserAgentMode.appDefault)
    SubscriptionUserAgentMode subscriptionUserAgentMode,
    String? subscriptionUserAgentValue,
    @Default(SubscriptionSortMode.none)
    SubscriptionSortMode subscriptionSortMode,

    // Device / OS integrations
    @Default(false) bool allowLanConnections,
    @Default(false) bool appAutoStart,

    // Locale
    @Default('en') String locale,

    // Notifications
    @Default(true) bool notificationConnection,
    @Default(true) bool notificationExpiry,
    @Default(false) bool notificationPromotional,
    @Default(true) bool notificationReferral,
    @Default(true) bool notificationVpnSpeed,

    // Server View
    @Default(false) bool preferMapView,

    // Privacy
    @Default(false) bool clipboardAutoDetect,

    // Haptics
    @Default(true) bool hapticsEnabled,

    // Diagnostics
    @Default(LogLevel.info) LogLevel logLevel,
  }) = _AppSettings;
}
