import 'dart:async';
import 'dart:convert';

import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/network/network_info.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/core/network/websocket_client.dart';
import 'package:cybervpn_mobile/core/network/websocket_provider.dart';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/profile/domain/services/device_registration_service.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_provider.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_state.dart';
import 'package:cybervpn_mobile/features/profile/presentation/providers/profile_provider.dart'
    show profileProvider;
import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/per_app_proxy_providers.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/vpn/data/datasources/kill_switch_service.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/connection_state_entity.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/vpn_config_entity.dart';
import 'package:cybervpn_mobile/features/vpn/domain/repositories/vpn_repository.dart';
import 'package:cybervpn_mobile/features/vpn/domain/usecases/auto_reconnect.dart';
import 'package:cybervpn_mobile/features/vpn/domain/usecases/connect_vpn.dart';
import 'package:cybervpn_mobile/features/vpn/domain/usecases/disconnect_vpn.dart';
import 'package:cybervpn_mobile/features/config_import/domain/entities/imported_config.dart';
import 'package:cybervpn_mobile/core/di/providers.dart'
    show
        secureStorageProvider,
        networkInfoProvider,
        vpnRepositoryProvider,
        connectVpnUseCaseProvider,
        disconnectVpnUseCaseProvider,
        autoReconnectServiceProvider,
        killSwitchServiceProvider,
        activeDnsServersProvider,
        deviceRegistrationServiceProvider,
        vpnRuntimeCapabilitiesProvider,
        vpnRuntimeConfigBuilderProvider,
        vpnServerAddressResolverProvider,
        subscriptionPolicyRuntimeProvider;
import 'package:cybervpn_mobile/features/review/presentation/providers/review_provider.dart';
import 'package:cybervpn_mobile/features/servers/presentation/providers/recent_servers_provider.dart'
    show recentServerIdsProvider;
import 'package:cybervpn_mobile/features/servers/presentation/providers/server_list_provider.dart'
    show allServersWithPingProvider, recommendedServerProvider;
import 'package:cybervpn_mobile/features/vpn_profiles/di/profile_providers.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/vpn_profile.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/services/subscription_policy_runtime.dart';
import 'package:cybervpn_mobile/core/analytics/analytics_providers.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_state.dart';

// ---------------------------------------------------------------------------
// Storage keys
// ---------------------------------------------------------------------------

const _lastServerKey = 'last_connected_server';
const _lastProtocolKey = 'last_connected_protocol';
const _activeProfileLookupTimeout = Duration(milliseconds: 750);

// ---------------------------------------------------------------------------
// VpnConnectionNotifier
// ---------------------------------------------------------------------------

final vpnConnectionProvider =
    AsyncNotifierProvider<VpnConnectionNotifier, VpnConnectionState>(
      VpnConnectionNotifier.new,
    );

class VpnConnectionNotifier extends AsyncNotifier<VpnConnectionState> {
  late final ConnectVpnUseCase _connectUseCase;
  late final DisconnectVpnUseCase _disconnectUseCase;
  late final AutoReconnectService _autoReconnect;
  late final VpnRepository _repository;
  late final SecureStorageWrapper _storage;
  late final NetworkInfo _networkInfo;
  late final KillSwitchService _killSwitch;
  late final DeviceRegistrationService _deviceRegistration;

  StreamSubscription<ConnectionStateEntity>? _stateSubscription;
  StreamSubscription<bool>? _networkSubscription;
  StreamSubscription<ForceDisconnect>? _webSocketSubscription;

  /// Observes app lifecycle events to reconcile VPN state when the app
  /// resumes from background. Without this, the UI can show "Connected"
  /// when the OS has killed the VPN tunnel while the app was paused.
  _VpnLifecycleObserver? _lifecycleObserver;

  /// Flag to prevent duplicate auto-connect attempts during initialization.
  bool _autoConnectAttempted = false;

  @override
  Future<VpnConnectionState> build() async {
    _connectUseCase = ref.watch(connectVpnUseCaseProvider);
    _disconnectUseCase = ref.watch(disconnectVpnUseCaseProvider);
    _autoReconnect = ref.watch(autoReconnectServiceProvider);
    _repository = ref.watch(vpnRepositoryProvider);
    _storage = ref.watch(secureStorageProvider);
    _networkInfo = ref.watch(networkInfoProvider);
    _killSwitch = ref.watch(killSwitchServiceProvider);
    _deviceRegistration = ref.watch(deviceRegistrationServiceProvider);

    // Clean up subscriptions when the provider is disposed.
    ref.onDispose(_dispose);

    // Observe app lifecycle events (pause/resume) to reconcile VPN state.
    _lifecycleObserver = _VpnLifecycleObserver(
      onResumed: _reconcileStateOnResume,
    );
    WidgetsBinding.instance.addObserver(_lifecycleObserver!);

    // Listen to the repository's connection-state stream for external changes.
    _stateSubscription = _repository.connectionStateStream.listen(
      _onRepositoryStateChanged,
      onError: (Object error) {
        AppLogger.error('VPN state stream error', error: error);
        state = AsyncData(VpnError(message: error.toString()));
      },
    );

    // Listen to network connectivity changes.
    _networkSubscription = _networkInfo.onConnectivityChanged.listen(
      handleNetworkChange,
    );

    // Listen to WebSocket force_disconnect events.
    _listenToWebSocketEvents();

    // Check whether we are already connected (e.g. after process restart).
    final connectedResult = await _repository.isConnected;
    final alreadyConnected = switch (connectedResult) {
      Success(:final data) => data,
      Failure() => false,
    };
    if (alreadyConnected) {
      final lastConfigResult = await _repository.getLastConfig();
      final lastConfig = lastConfigResult.dataOrNull;
      final savedServer = await _loadLastServer();
      if (savedServer != null && lastConfig != null) {
        return VpnConnected(server: savedServer, protocol: lastConfig.protocol);
      }
    }

    // Auto-connect on launch if enabled in settings and user is authenticated.
    final vpnSettings = ref.read(vpnSettingsProvider);
    final authState = ref.read(authProvider).value;
    final isAuthenticated = authState is AuthAuthenticated;

    if (vpnSettings.autoConnectOnLaunch && isAuthenticated) {
      unawaited(_handleAutoConnect());
    }

    return const VpnDisconnected();
  }

  // -- Public API -----------------------------------------------------------

  /// Initiate a VPN connection to the given [server].
  Future<void> connect(ServerEntity server) async {
    final current = state.value;
    if (current is VpnConnected || current is VpnConnecting) return;

    state = AsyncData(VpnConnecting(server: server));

    // Track in recent servers list.
    unawaited(ref.read(recentServerIdsProvider.notifier).addServer(server.id));

    try {
      final vpnSettings = ref.read(vpnSettingsProvider);
      final protocol = _resolveProtocol(server.protocol, vpnSettings);

      final config = VpnConfigEntity(
        id: server.id,
        name: server.name,
        serverAddress: server.address,
        port: server.port,
        protocol: protocol,
        configData: await _resolveProfileConfigData(server) ?? '',
      );
      if (!ref.mounted) return;

      await _executeConnection(
        config: config,
        server: server,
        protocol: protocol,
      );
    } catch (e, st) {
      AppLogger.error('VPN connect failed', error: e, stackTrace: st);
      _autoReconnect.stop();
      await _killSwitch.disable();
      if (!ref.mounted) return;
      state = AsyncData(VpnError(message: e.toString()));
    }
  }

  /// Connect to a custom imported server.
  ///
  /// Converts the [ImportedConfig] to a [VpnConfigEntity] and initiates
  /// a VPN connection. Custom servers use their raw URI as config data.
  Future<void> connectFromCustomServer(ImportedConfig customServer) async {
    final current = state.value;
    if (current is VpnConnected || current is VpnConnecting) return;

    // Create a pseudo ServerEntity for state tracking
    final pseudoServer = ServerEntity(
      id: customServer.id,
      name: customServer.name,
      countryCode: 'XX',
      countryName: 'Custom',
      city: customServer.serverAddress,
      address: customServer.serverAddress,
      port: customServer.port,
      protocol: customServer.protocol,
      isAvailable: customServer.isReachable ?? true,
    );

    state = AsyncData(VpnConnecting(server: pseudoServer));

    try {
      final protocol = VpnProtocol.values.firstWhere(
        (p) => p.name.toLowerCase() == customServer.protocol.toLowerCase(),
        orElse: () => VpnProtocol.vless,
      );

      final config = VpnConfigEntity(
        id: customServer.id,
        name: customServer.name,
        serverAddress: customServer.serverAddress,
        port: customServer.port,
        protocol: protocol,
        configData: customServer.rawUri,
      );
      if (!ref.mounted) return;

      await _executeConnection(
        config: config,
        server: pseudoServer,
        protocol: protocol,
      );
    } catch (e, st) {
      AppLogger.error(
        'VPN connect from custom server failed',
        error: e,
        stackTrace: st,
      );
      _autoReconnect.stop();
      await _killSwitch.disable();
      if (!ref.mounted) return;
      state = AsyncData(VpnError(message: e.toString()));
    }
  }

  /// Shared connection execution logic.
  ///
  /// Handles DNS resolution, kill switch, connect use case, persistence,
  /// auto-reconnect, device registration, and state transition.
  Future<void> _executeConnection({
    required VpnConfigEntity config,
    required ServerEntity server,
    required VpnProtocol protocol,
  }) async {
    final vpnSettings = ref.read(vpnSettingsProvider);
    final runtimeConfig = await _applyRuntimeSettings(
      config,
      vpnSettings: vpnSettings,
    );
    if (!ref.mounted) return;

    ref.read(activeDnsServersProvider.notifier).set(runtimeConfig.dnsServers);

    // Enable kill switch before connecting if the setting is on.
    if (vpnSettings.killSwitch) {
      await _killSwitch.enable();
      if (!ref.mounted) return;
    }

    final connectResult = await _connectUseCase.call(runtimeConfig);
    if (connectResult case Failure(:final failure)) throw failure;
    if (!ref.mounted) return;

    // Persist for auto-reconnect on app restart.
    await _persistLastConnection(server, protocol);
    if (!ref.mounted) return;

    // Start the auto-reconnect service.
    _autoReconnect.start(runtimeConfig);

    // Auto-register device on first connection
    unawaited(_registerDeviceIfNeeded());

    state = AsyncData(VpnConnected(server: server, protocol: protocol));

    // Trigger review prompt after successful connection
    unawaited(_handleReviewPrompt());
  }

  /// Gracefully disconnect from the VPN.
  ///
  /// If the user manually disconnects during an auto-connect attempt, the
  /// auto-connect will be cancelled gracefully.
  Future<void> disconnect() async {
    switch (state.value) {
      case VpnDisconnected() || VpnDisconnecting():
        return;
      case VpnConnecting():
        AppLogger.info('User manually disconnected during auto-connect');
      default:
        break;
    }

    state = const AsyncData(VpnDisconnecting());

    try {
      _autoReconnect.stop();
      final disconnectResult = await _disconnectUseCase.call();
      if (disconnectResult case Failure(:final failure)) throw failure;
      await _clearPersistedConnection();

      // Disable kill switch after disconnecting.
      await _killSwitch.disable();

      state = const AsyncData(VpnDisconnected());
    } catch (e, st) {
      AppLogger.error('VPN disconnect failed', error: e, stackTrace: st);
      state = AsyncData(VpnError(message: e.toString()));
    }
  }

  /// React to network connectivity changes.
  ///
  /// When the device comes back online and the VPN was previously connected,
  /// a reconnection attempt is triggered via the [AutoReconnectService].
  Future<void> handleNetworkChange(bool isOnline) async {
    switch (state.value) {
      case VpnConnected(:final server) when !isOnline:
        // Network lost while connected -- move to reconnecting.
        state = AsyncData(VpnReconnecting(attempt: 1, server: server));
        return;
      default:
        break;
    }

    final current = state.value;

    if (isOnline && current is VpnReconnecting) {
      // Network restored -- the AutoReconnectService handles retry logic.
      // We just update the UI state; the stream listener will transition
      // to VpnConnected once the tunnel is actually re-established.
      AppLogger.info('Network restored, auto-reconnect in progress');
    }
  }

  /// Connect using the current subscription auto-connect strategy.
  ///
  /// Used by launch auto-connect, quick actions, and untrusted WiFi flows.
  Future<void> connectBySubscriptionPolicy({
    String trigger = 'auto_connect',
  }) async {
    final current = state.value;
    if (current is VpnConnected || current is VpnConnecting) {
      AppLogger.debug(
        'Already connected/connecting, skipping policy connect',
        category: 'vpn.auto-connect',
        data: {'trigger': trigger},
      );
      return;
    }

    final selection = await _resolveSubscriptionConnectSelection(
      trigger: trigger,
    );
    if (selection == null) {
      throw Exception('No available server for auto-connect');
    }

    AppLogger.info(
      'Policy-driven auto-connect target resolved',
      category: 'vpn.auto-connect',
      data: {
        'trigger': trigger,
        'requestedStrategy': selection.requestedStrategy.name,
        'appliedStrategy': selection.appliedStrategy.name,
        'candidateCount': selection.candidateCount,
        'usedFallback': selection.usedFallback,
        'selectedServerId': selection.server.id,
        'selectedServerName': selection.server.name,
        'note': selection.note,
      },
    );

    await connect(selection.server);
  }

  /// Backwards-compatible alias for legacy call sites.
  Future<void> connectToLastOrRecommended() async {
    await connectBySubscriptionPolicy(trigger: 'legacy_auto_connect');
  }

  /// Apply or remove the kill switch immediately (e.g. when the user toggles
  /// the setting while already connected).
  Future<void> applyKillSwitchSetting(bool enabled) async {
    final current = state.value;
    if (current is! VpnConnected) return;

    if (enabled) {
      await _killSwitch.enable();
    } else {
      await _killSwitch.disable();
    }
  }

  // -- Private helpers ------------------------------------------------------

  Future<SubscriptionConnectSelection?> _resolveSubscriptionConnectSelection({
    required String trigger,
  }) async {
    final subscriptionSettings = ref.read(subscriptionSettingsProvider);
    final policyRuntime = ref.read(subscriptionPolicyRuntimeProvider);
    final policy = SubscriptionPolicyState(
      autoUpdateEnabled: subscriptionSettings.autoUpdateEnabled,
      autoUpdateInterval: Duration(
        hours: subscriptionSettings.autoUpdateIntervalHours.clamp(1, 168),
      ),
      updateNotificationsEnabled:
          subscriptionSettings.updateNotificationsEnabled,
      autoUpdateOnOpen: subscriptionSettings.autoUpdateOnOpen,
      pingOnOpenEnabled: subscriptionSettings.pingOnOpenEnabled,
      connectStrategy: subscriptionSettings.connectStrategy,
      preventDuplicateImports: subscriptionSettings.preventDuplicateImports,
      collapseSubscriptions: subscriptionSettings.collapseSubscriptions,
      noFilter: subscriptionSettings.noFilter,
      userAgentMode: subscriptionSettings.userAgentMode,
      customUserAgent: subscriptionSettings.userAgentValue,
      effectiveUserAgent: SubscriptionPolicyRuntime.defaultUserAgent,
      sortMode: subscriptionSettings.sortMode,
    );
    final lastServer = await _loadLastServer();
    final availableServers = ref.read(allServersWithPingProvider);
    final recommendedServer = ref.read(recommendedServerProvider);

    final selection = policyRuntime.selectAutoConnectServer(
      policy: policy,
      availableServers: availableServers,
      lastServer: lastServer,
      recommendedServer: recommendedServer,
    );

    if (selection == null) {
      AppLogger.info(
        'Policy-driven auto-connect could not resolve a server',
        category: 'vpn.auto-connect',
        data: {
          'trigger': trigger,
          'requestedStrategy': policy.connectStrategy.name,
          'availableServerCount': availableServers.length,
          'hasLastServer': lastServer != null,
          'hasRecommendedServer': recommendedServer != null,
        },
      );
    }

    return selection;
  }

  Future<String?> _resolveProfileConfigData(ServerEntity server) async {
    final activeProfileState = ref.read(activeVpnProfileProvider);
    final hasResolvedProfile = activeProfileState is AsyncData;

    var activeProfile = switch (activeProfileState) {
      AsyncData(:final value) => value,
      _ => null,
    };

    if (!hasResolvedProfile) {
      final subscription = ref.container.listen<AsyncValue<VpnProfile?>>(
        activeVpnProfileProvider,
        (_, _) {},
      );
      try {
        final refreshedState = ref.read(activeVpnProfileProvider);
        if (refreshedState case AsyncData(:final value)) {
          activeProfile = value;
        } else {
          activeProfile = await ref
              .read(activeVpnProfileProvider.future)
              .timeout(_activeProfileLookupTimeout, onTimeout: () => null)
              .catchError((Object error, StackTrace stackTrace) {
                AppLogger.warning(
                  'Failed to resolve active VPN profile during config lookup',
                  category: 'vpn.connect',
                  error: error,
                  stackTrace: stackTrace,
                  data: {'serverId': server.id},
                );
                return null;
              });
        }
      } finally {
        subscription.close();
      }
    }

    if (activeProfile == null) {
      return null;
    }

    for (final profileServer in activeProfile.servers) {
      final matchesId = profileServer.id == server.id;
      final matchesEndpoint =
          profileServer.serverAddress == server.address &&
          profileServer.port == server.port &&
          profileServer.protocol.name.toLowerCase() ==
              server.protocol.toLowerCase();

      if (matchesId || matchesEndpoint) {
        return profileServer.configData;
      }
    }

    return null;
  }

  Future<VpnConfigEntity> _applyRuntimeSettings(
    VpnConfigEntity config, {
    required VpnSettings vpnSettings,
  }) async {
    final blockedApps = await _resolveBlockedApps(vpnSettings);
    final builder = ref.read(vpnRuntimeConfigBuilderProvider);
    final capabilities = ref.read(vpnRuntimeCapabilitiesProvider);
    final resolver = ref.read(vpnServerAddressResolverProvider);
    final resolveResult = await resolver.resolve(
      sourceConfig: config,
      vpnSettings: vpnSettings,
      capabilities: capabilities,
    );
    final buildResult = builder.build(
      sourceConfig: resolveResult.config,
      vpnSettings: vpnSettings,
      capabilities: capabilities,
      blockedApps: blockedApps,
    );
    final appliedSettings = [
      ...resolveResult.appliedSettings,
      ...buildResult.appliedSettings,
    ];
    final skippedSettings = <String, String>{
      ...resolveResult.skippedSettings,
      ...buildResult.skippedSettings,
    };
    final allowLanConnections =
        vpnSettings.allowLanConnections && capabilities.supportsLanProxyAccess;
    if (vpnSettings.allowLanConnections && !capabilities.supportsLanProxyAccess) {
      skippedSettings['allowLanConnections'] =
          'LAN proxy access is unsupported on this platform';
    }
    final runtimeConfig = buildResult.config.copyWith(
      allowLanConnections: allowLanConnections,
    );
    if (allowLanConnections) {
      appliedSettings.add('allowLanConnections');
    }

    AppLogger.info(
      'VPN runtime config prepared',
      category: 'vpn.runtime',
      data: {
        'serverId': config.id,
        'resolvedServerAddress': resolveResult.selectedAddress,
        'resolvedCandidateCount': resolveResult.candidateAddresses.length,
        'resolvedCandidates': resolveResult.candidateAddresses,
        'activeRoutingProfileId': vpnSettings.activeRoutingProfileId,
        'perAppProxyMode': vpnSettings.perAppProxyMode.name,
        'perAppSelectionCount': vpnSettings.perAppProxyAppIds.length,
        'blockedAppCount': runtimeConfig.blockedApps.length,
        'pingMode': vpnSettings.pingMode.name,
        'muxEnabled': vpnSettings.muxEnabled,
        'fragmentationEnabled': vpnSettings.fragmentationEnabled,
        'sniffingEnabled': vpnSettings.sniffingEnabled,
        'preferredIpType': vpnSettings.preferredIpType.name,
        'vpnRunMode': vpnSettings.vpnRunMode.name,
        'proxyOnly': runtimeConfig.proxyOnly,
        'allowLanConnections': runtimeConfig.allowLanConnections,
        'serverAddressResolveEnabled': vpnSettings.serverAddressResolveEnabled,
        'useDnsFromJson': vpnSettings.useDnsFromJson,
        'useLocalDns': vpnSettings.useLocalDns,
        'localDnsPort': vpnSettings.localDnsPort,
        'applied': appliedSettings,
        'skipped': skippedSettings,
        'bypassSubnets': runtimeConfig.bypassSubnets,
        'bypassSubnetCount': runtimeConfig.bypassSubnets.length,
        'dnsServers': runtimeConfig.dnsServers,
        'dnsServerCount': runtimeConfig.dnsServers?.length ?? 0,
        'mtu': runtimeConfig.mtu,
      },
    );

    if (skippedSettings.isNotEmpty) {
      AppLogger.warning(
        'VPN runtime settings fell back to supported subset',
        category: 'vpn.runtime',
        data: {
          'serverId': config.id,
          'unsupportedFallbacks': skippedSettings,
          'activeRoutingProfileId': vpnSettings.activeRoutingProfileId,
          'perAppProxyMode': vpnSettings.perAppProxyMode.name,
          'pingMode': vpnSettings.pingMode.name,
          'muxEnabled': vpnSettings.muxEnabled,
          'fragmentationEnabled': vpnSettings.fragmentationEnabled,
          'sniffingEnabled': vpnSettings.sniffingEnabled,
          'preferredIpType': vpnSettings.preferredIpType.name,
          'vpnRunMode': vpnSettings.vpnRunMode.name,
          'serverAddressResolveEnabled':
              vpnSettings.serverAddressResolveEnabled,
          'useDnsFromJson': vpnSettings.useDnsFromJson,
          'useLocalDns': vpnSettings.useLocalDns,
        },
      );
    }

    if (runtimeConfig.configData.isEmpty) {
      AppLogger.warning(
        'VPN configData is empty before connect; runtime may fail for API-backed servers without active profile config',
        category: 'vpn.connect',
        data: {'serverId': config.id, 'serverAddress': config.serverAddress},
      );
    }

    return runtimeConfig;
  }

  Future<List<String>> _resolveBlockedApps(VpnSettings vpnSettings) async {
    final mode = vpnSettings.perAppProxyMode;
    if (mode == PerAppProxyMode.off) {
      return const <String>[];
    }

    final selectedAppIds =
        vpnSettings.perAppProxyAppIds
            .map((appId) => appId.trim())
            .where((appId) => appId.isNotEmpty)
            .toSet()
            .toList()
          ..sort();

    final platformService = ref.read(perAppProxyPlatformServiceProvider);
    if (!platformService.isSupported) {
      AppLogger.info(
        'Per-app proxy ignored on unsupported platform',
        category: 'vpn.connect',
        data: {'mode': mode.name, 'selectedAppCount': selectedAppIds.length},
      );
      return const <String>[];
    }

    if (mode == PerAppProxyMode.bypassSelected) {
      return selectedAppIds;
    }

    final installedApps = await platformService.getInstalledApps();
    final currentPackageName = await platformService.getCurrentPackageName();
    final resolver = ref.read(perAppProxyRuntimeResolverProvider);

    return resolver.resolveBlockedApps(
      mode: mode,
      selectedAppIds: selectedAppIds,
      installedApps: installedApps,
      currentPackageName: currentPackageName,
    );
  }

  void _onRepositoryStateChanged(ConnectionStateEntity repoState) {
    if (!ref.mounted) return;

    final current = state.value;
    final vpnSettings = ref.read(vpnSettingsProvider);

    switch (repoState.status) {
      case VpnConnectionStatus.connected:
        final server = current?.server;
        if (server != null) {
          final protocol = _resolveProtocol(server.protocol, vpnSettings);
          state = AsyncData(VpnConnected(server: server, protocol: protocol));
        }
      case VpnConnectionStatus.disconnected:
        if (current is! VpnDisconnecting) {
          // Unexpected disconnection -- possibly network issue.
          _autoReconnect.stop();
        }
        state = const AsyncData(VpnDisconnected());
      case VpnConnectionStatus.connecting:
        state = AsyncData(VpnConnecting(server: current?.server));
      case VpnConnectionStatus.disconnecting:
        state = const AsyncData(VpnDisconnecting());
      case VpnConnectionStatus.error:
        _autoReconnect.stop();
        state = AsyncData(
          VpnError(message: repoState.errorMessage ?? 'Unknown error'),
        );
    }
  }

  /// Resolves the VPN protocol to use based on user settings and server info.
  ///
  /// If the user has selected [PreferredProtocol.auto], falls back to parsing
  /// the server's [raw] protocol string. Otherwise the explicit preference
  /// takes priority.
  VpnProtocol _resolveProtocol(String raw, VpnSettings vpnSettings) {
    switch (vpnSettings.preferredProtocol) {
      case PreferredProtocol.auto:
        // Fall back to auto-detection from the server's protocol string.
        return VpnProtocol.values.firstWhere(
          (p) => p.name.toLowerCase() == raw.toLowerCase(),
          orElse: () => VpnProtocol.vless,
        );
      case PreferredProtocol.vlessReality:
        return VpnProtocol.vless;
      case PreferredProtocol.vlessXhttp:
        return VpnProtocol.vless;
      case PreferredProtocol.vlessWsTls:
        return VpnProtocol.vless;
    }
  }

  /// Attempt auto-connect using the last connected server.
  ///
  /// Runs asynchronously after the provider is initialized. Gracefully
  /// handles cases where no saved server exists or connectivity is unavailable.
  /// Uses [_autoConnectAttempted] flag to prevent duplicate attempts.
  ///
  /// Edge cases handled:
  /// - No network connectivity: skip silently
  /// - No last server: skip silently
  /// - Server unavailable: skip silently (logged)
  /// - VPN already connected/connecting: skip silently
  /// - Connection errors: logged but do not block app startup
  Future<void> _handleAutoConnect() async {
    // Prevent duplicate auto-connect attempts.
    if (_autoConnectAttempted) {
      AppLogger.debug('Auto-connect: already attempted, skipping');
      return;
    }
    _autoConnectAttempted = true;

    try {
      // Verify the VPN is not already connected/connecting.
      // During build(), state.value is null (AsyncLoading) — allow that case
      // because build() returns VpnDisconnected immediately after scheduling us.
      final current = state.value;
      if (current is VpnConnected || current is VpnConnecting) {
        AppLogger.info(
          'Auto-connect: VPN already in state ${current.runtimeType}, skipping',
        );
        return;
      }

      // Check network connectivity first (fail-fast).
      final hasNetwork = await _networkInfo.isConnected;
      if (!hasNetwork) {
        AppLogger.info('Auto-connect: no network connectivity, skipping');
        return;
      }

      await connectBySubscriptionPolicy(trigger: 'launch');
    } catch (e, st) {
      // Log auto-connect failures but do not block app startup.
      // The error will be shown in the UI via the VpnError state if the
      // connection attempt was initiated.
      AppLogger.error(
        'Auto-connect failed',
        error: e,
        stackTrace: st,
        category: 'vpn.auto-connect',
      );
    }
  }

  // -- Persistence ----------------------------------------------------------

  Future<void> _persistLastConnection(
    ServerEntity server,
    VpnProtocol protocol,
  ) async {
    try {
      final serverJson = jsonEncode(server.toJson());
      await _storage.write(key: _lastServerKey, value: serverJson);
      await _storage.write(key: _lastProtocolKey, value: protocol.name);
    } catch (e) {
      AppLogger.warning('Failed to persist last connection', error: e);
    }
  }

  Future<ServerEntity?> _loadLastServer() async {
    try {
      final raw = await _storage.read(key: _lastServerKey);
      if (raw == null) return null;
      final map = jsonDecode(raw) as Map<String, dynamic>;
      return ServerEntity.fromJson(map);
    } catch (e) {
      AppLogger.warning('Failed to load last server', error: e);
      return null;
    }
  }

  Future<void> _clearPersistedConnection() async {
    try {
      await _storage.delete(key: _lastServerKey);
      await _storage.delete(key: _lastProtocolKey);
    } catch (e) {
      AppLogger.warning('Failed to clear persisted connection', error: e);
    }
  }

  /// Listens to WebSocket force_disconnect events and disconnects
  /// the VPN immediately.
  void _listenToWebSocketEvents() {
    try {
      final client = ref.read(webSocketClientProvider);
      _webSocketSubscription = client.forceDisconnectEvents.listen(
        _onForceDisconnect,
        onError: (Object e) {
          AppLogger.error('WebSocket force_disconnect stream error', error: e);
        },
      );
    } catch (e) {
      AppLogger.error(
        'Failed to listen to WebSocket force_disconnect stream',
        error: e,
      );
    }
  }

  /// Handles incoming force_disconnect WebSocket events.
  ///
  /// Immediately disconnects the VPN and logs the reason.
  /// The UI layer should show an alert/snackbar to the user.
  Future<void> _onForceDisconnect(ForceDisconnect event) async {
    AppLogger.warning('Received force_disconnect from server: ${event.reason}');

    // Disconnect the VPN immediately.
    await disconnect();
    if (!ref.mounted) return;

    // Transition to VpnForceDisconnected so the UI shows a dialog.
    state = AsyncData(VpnForceDisconnected(reason: event.reason));
  }

  /// Automatically register the device on first VPN connection.
  ///
  /// Runs asynchronously in the background. Registration failures are logged
  /// but do not block the VPN connection.
  Future<void> _registerDeviceIfNeeded() async {
    try {
      final device = await _deviceRegistration.registerCurrentDevice();
      if (device != null) {
        AppLogger.info(
          'Device auto-registered on VPN connection: ${device.name}',
        );
        // Optionally refresh the profile to include the new device in the list
        unawaited(ref.read(profileProvider.notifier).refreshProfile());
      }
    } catch (e, st) {
      // Non-critical error - log but don't fail the connection
      AppLogger.warning(
        'Device auto-registration failed',
        error: e,
        stackTrace: st,
      );
    }
  }

  /// Handles review prompt logic after successful VPN connection.
  ///
  /// Increments the connection counter and requests a review if conditions
  /// are met. Logs analytics events for tracking prompt behavior.
  ///
  /// Runs asynchronously in the background. Failures are logged but do not
  /// affect the VPN connection.
  Future<void> _handleReviewPrompt() async {
    try {
      final reviewService = ref.read(reviewServiceProvider);
      final analytics = ref.read(analyticsProvider);

      // Increment connection count
      await reviewService.incrementConnectionCount();

      // Check if review should be shown
      if (!reviewService.shouldShowReview()) {
        final metrics = reviewService.getMetrics();
        await analytics.logEvent(
          'review_prompt_conditions_not_met',
          parameters: {
            'connection_count': metrics['connectionCount'],
            'days_since_install': metrics['daysSinceInstall'],
            'days_since_last_prompt': metrics['daysSinceLastPrompt'] ?? -1,
            'yearly_prompt_count': metrics['yearlyPromptCount'],
          },
        );
        return;
      }

      // Request review
      final success = await reviewService.requestReview();
      if (success) {
        final metrics = reviewService.getMetrics();
        await analytics.logEvent(
          'review_prompt_shown',
          parameters: {
            'connection_count': metrics['connectionCount'],
            'days_since_install': metrics['daysSinceInstall'],
          },
        );
        AppLogger.info(
          'Review prompt shown after successful connection',
          category: 'review',
        );
      }
    } catch (e, st) {
      // Non-critical error - log but don't fail the connection
      AppLogger.warning(
        'Failed to handle review prompt',
        error: e,
        stackTrace: st,
        category: 'review',
      );

      try {
        final analytics = ref.read(analyticsProvider);
        await analytics.logEvent(
          'review_prompt_error',
          parameters: {'error': e.toString()},
        );
      } catch (e) {
        // Ignore analytics logging errors
      }
    }
  }

  /// Reconciles the UI VPN state with the actual engine state when the
  /// app resumes from background.
  ///
  /// iOS aggressively kills background VPN tunnels, so the UI may show
  /// "Connected" when the tunnel is dead. This check catches that mismatch
  /// and transitions the state accordingly.
  Future<void> _reconcileStateOnResume() async {
    final current = state.value;
    if (current is! VpnConnected) {
      return; // only reconcile when UI says connected
    }

    try {
      final connectedResult = await _repository.isConnected;
      if (!ref.mounted) return;
      final isActuallyConnected = switch (connectedResult) {
        Success(:final data) => data,
        Failure() => false,
      };

      if (!isActuallyConnected) {
        AppLogger.warning(
          'VPN state mismatch on resume: UI shows connected but engine is disconnected',
          category: 'vpn.lifecycle',
        );
        // Always attempt auto-reconnect when returning from background
        // if the user was previously connected and the server is available.
        if (current.server.isAvailable) {
          state = AsyncData(
            VpnReconnecting(attempt: 1, server: current.server),
          );
          try {
            await connect(current.server);
          } catch (e) {
            AppLogger.error(
              'Auto-reconnect on resume failed',
              error: e,
              category: 'vpn.lifecycle',
            );
            state = const AsyncData(VpnDisconnected());
          }
        } else {
          state = const AsyncData(VpnDisconnected());
        }
      } else {
        AppLogger.debug(
          'VPN state reconciliation on resume: still connected',
          category: 'vpn.lifecycle',
        );
      }
    } catch (e, st) {
      AppLogger.error(
        'Failed to reconcile VPN state on resume',
        error: e,
        stackTrace: st,
        category: 'vpn.lifecycle',
      );
    }
  }

  void _dispose() {
    if (_lifecycleObserver != null) {
      WidgetsBinding.instance.removeObserver(_lifecycleObserver!);
      _lifecycleObserver = null;
    }
    unawaited(_stateSubscription?.cancel());
    unawaited(_networkSubscription?.cancel());
    unawaited(_webSocketSubscription?.cancel());
    _autoReconnect.dispose();
  }
}

// ---------------------------------------------------------------------------
// Lifecycle observer
// ---------------------------------------------------------------------------

/// Lightweight [WidgetsBindingObserver] that triggers a callback when the
/// app transitions from background to foreground (resumed).
class _VpnLifecycleObserver extends WidgetsBindingObserver {
  final Future<void> Function() onResumed;

  _VpnLifecycleObserver({required this.onResumed});

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      unawaited(onResumed());
    }
  }
}
