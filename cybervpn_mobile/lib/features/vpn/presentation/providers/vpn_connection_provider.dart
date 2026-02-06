import 'dart:async';
import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/constants/vpn_constants.dart';
import 'package:cybervpn_mobile/core/network/network_info.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/core/network/websocket_client.dart';
import 'package:cybervpn_mobile/core/network/websocket_provider.dart';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/profile/domain/services/device_registration_service.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_provider.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_state.dart';
import 'package:cybervpn_mobile/features/profile/presentation/providers/profile_provider.dart';
import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/vpn/data/datasources/kill_switch_service.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/connection_state_entity.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/vpn_config_entity.dart';
import 'package:cybervpn_mobile/features/vpn/domain/repositories/vpn_repository.dart';
import 'package:cybervpn_mobile/features/vpn/domain/usecases/auto_reconnect.dart';
import 'package:cybervpn_mobile/features/vpn/domain/usecases/connect_vpn.dart';
import 'package:cybervpn_mobile/features/vpn/domain/usecases/disconnect_vpn.dart';
import 'package:cybervpn_mobile/features/vpn/data/repositories/vpn_repository_impl.dart';
import 'package:cybervpn_mobile/features/config_import/domain/entities/imported_config.dart';
import 'package:cybervpn_mobile/core/di/providers.dart'
    show vpnEngineDatasourceProvider, localStorageProvider;
import 'package:cybervpn_mobile/features/review/presentation/providers/review_provider.dart';
import 'package:cybervpn_mobile/features/servers/presentation/providers/server_list_provider.dart';
import 'package:cybervpn_mobile/core/analytics/analytics_providers.dart';

// ---------------------------------------------------------------------------
// VPN Connection State -- Sealed class hierarchy
// ---------------------------------------------------------------------------

/// Sealed base class representing all possible VPN connection states.
sealed class VpnConnectionState {
  const VpnConnectionState();

  /// Convenience getters common across all states.
  bool get isConnected => this is VpnConnected;
  bool get isDisconnected => this is VpnDisconnected;
  bool get isConnecting => this is VpnConnecting;
  bool get isDisconnecting => this is VpnDisconnecting;
  bool get isReconnecting => this is VpnReconnecting;
  bool get isError => this is VpnError;

  /// Returns the server if the state carries one, otherwise null.
  ServerEntity? get server {
    return switch (this) {
      final VpnConnecting s => s.server,
      final VpnConnected s => s.server,
      final VpnReconnecting s => s.server,
      _ => null,
    };
  }
}

class VpnDisconnected extends VpnConnectionState {
  const VpnDisconnected();
}

class VpnConnecting extends VpnConnectionState {
  @override
  final ServerEntity? server;
  const VpnConnecting({this.server});
}

class VpnConnected extends VpnConnectionState {
  @override
  final ServerEntity server;
  final VpnProtocol protocol;
  const VpnConnected({required this.server, required this.protocol});
}

class VpnDisconnecting extends VpnConnectionState {
  const VpnDisconnecting();
}

class VpnReconnecting extends VpnConnectionState {
  final int attempt;
  @override
  final ServerEntity? server;
  const VpnReconnecting({required this.attempt, this.server});
}

class VpnError extends VpnConnectionState {
  final String message;
  const VpnError({required this.message});
}

// ---------------------------------------------------------------------------
// Dependency providers (override these in your DI setup / tests)
// ---------------------------------------------------------------------------

final vpnRepositoryProvider = Provider<VpnRepository>((ref) {
  return VpnRepositoryImpl(
    engine: ref.watch(vpnEngineDatasourceProvider),
    localStorage: ref.watch(localStorageProvider),
    secureStorage: ref.watch(secureStorageProvider),
  );
});

final connectVpnUseCaseProvider = Provider<ConnectVpnUseCase>((ref) {
  return ConnectVpnUseCase(ref.watch(vpnRepositoryProvider));
});

final disconnectVpnUseCaseProvider = Provider<DisconnectVpnUseCase>((ref) {
  return DisconnectVpnUseCase(ref.watch(vpnRepositoryProvider));
});

final networkInfoProvider = Provider<NetworkInfo>((ref) {
  return NetworkInfo();
});

final autoReconnectServiceProvider = Provider<AutoReconnectService>((ref) {
  return AutoReconnectService(
    repository: ref.watch(vpnRepositoryProvider),
    networkInfo: ref.watch(networkInfoProvider),
  );
});

final secureStorageProvider = Provider<SecureStorageWrapper>((ref) {
  return SecureStorageWrapper();
});

final killSwitchServiceProvider = Provider<KillSwitchService>((ref) {
  return KillSwitchService();
});

/// Holds the currently active DNS server list resolved from user settings.
///
/// Consumed by lower-level config generators and the VPN engine layer.
/// `null` means use platform / system DNS defaults.
final activeDnsServersProvider =
    NotifierProvider<ActiveDnsServersNotifier, List<String>?>(
  ActiveDnsServersNotifier.new,
);

class ActiveDnsServersNotifier extends Notifier<List<String>?> {
  @override
  List<String>? build() => null;

  void set(List<String>? servers) {
    state = servers;
  }
}

// ---------------------------------------------------------------------------
// Storage keys
// ---------------------------------------------------------------------------

const _lastServerKey = 'last_connected_server';
const _lastProtocolKey = 'last_connected_protocol';

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
        return VpnConnected(
          server: savedServer,
          protocol: lastConfig.protocol,
        );
      }
    }

    // Auto-connect on launch if enabled in settings and user is authenticated.
    final vpnSettings = ref.read(vpnSettingsProvider);
    final authState = ref.read(authProvider).value;
    final isAuthenticated = authState is AuthAuthenticated;

    if (vpnSettings.autoConnectOnLaunch && isAuthenticated) {
      _handleAutoConnect();
    }

    return const VpnDisconnected();
  }

  // -- Public API -----------------------------------------------------------

  /// Initiate a VPN connection to the given [server].
  Future<void> connect(ServerEntity server) async {
    final current = state.value;
    if (current is VpnConnected || current is VpnConnecting) return;

    state = AsyncData(VpnConnecting(server: server));

    try {
      final vpnSettings = ref.read(vpnSettingsProvider);
      final protocol = _resolveProtocol(server.protocol, vpnSettings);

      final config = VpnConfigEntity(
        id: server.id,
        name: server.name,
        serverAddress: server.address,
        port: server.port,
        protocol: protocol,
        configData: '', // populated by the repository / platform layer
      );

      await _executeConnection(config: config, server: server, protocol: protocol);
    } catch (e, st) {
      AppLogger.error('VPN connect failed', error: e, stackTrace: st);
      _autoReconnect.stop();
      await _killSwitch.disable();
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

      await _executeConnection(config: config, server: pseudoServer, protocol: protocol);
    } catch (e, st) {
      AppLogger.error('VPN connect from custom server failed', error: e, stackTrace: st);
      _autoReconnect.stop();
      await _killSwitch.disable();
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

    // Resolve DNS servers from settings and publish for lower layers.
    final dnsServers = _resolveDnsServers(vpnSettings);
    ref.read(activeDnsServersProvider.notifier).set(dnsServers);

    // Enable kill switch before connecting if the setting is on.
    if (vpnSettings.killSwitch) {
      await _killSwitch.enable();
    }

    await _connectUseCase.call(config);

    // Persist for auto-reconnect on app restart.
    await _persistLastConnection(server, protocol);

    // Start the auto-reconnect service.
    _autoReconnect.start(config);

    // Auto-register device on first connection
    _registerDeviceIfNeeded();

    state = AsyncData(VpnConnected(server: server, protocol: protocol));

    // Trigger review prompt after successful connection
    _handleReviewPrompt();
  }

  /// Gracefully disconnect from the VPN.
  ///
  /// If the user manually disconnects during an auto-connect attempt, the
  /// auto-connect will be cancelled gracefully.
  Future<void> disconnect() async {
    final current = state.value;
    if (current is VpnDisconnected || current is VpnDisconnecting) return;

    // If disconnecting during auto-connect (VpnConnecting state), log it
    // so the error handler in _handleAutoConnect doesn't treat it as a failure.
    if (current is VpnConnecting) {
      AppLogger.info('User manually disconnected during auto-connect');
    }

    state = const AsyncData(VpnDisconnecting());

    try {
      _autoReconnect.stop();
      await _disconnectUseCase.call();
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
    final current = state.value;

    if (!isOnline && current is VpnConnected) {
      // Network lost while connected -- move to reconnecting.
      state = AsyncData(VpnReconnecting(attempt: 1, server: current.server));
      return;
    }

    if (isOnline && current is VpnReconnecting) {
      // Network restored -- the AutoReconnectService handles retry logic.
      // We just update the UI state; the stream listener will transition
      // to VpnConnected once the tunnel is actually re-established.
      AppLogger.info('Network restored, auto-reconnect in progress');
    }
  }

  /// Connect to the last used server or the recommended server.
  ///
  /// Used by auto-connect features like untrusted WiFi handler.
  /// Attempts to connect to:
  /// 1. The last connected server (if saved and available)
  /// 2. The recommended server (if last server unavailable)
  /// 3. Throws if no suitable server is found
  Future<void> connectToLastOrRecommended() async {
    final current = state.value;
    if (current is VpnConnected || current is VpnConnecting) {
      AppLogger.debug('Already connected/connecting, skipping auto-connect');
      return;
    }

    // Try last connected server first
    final lastServer = await _loadLastServer();
    if (lastServer != null && lastServer.isAvailable) {
      AppLogger.info('Auto-connecting to last server: ${lastServer.name}');
      await connect(lastServer);
      return;
    }

    // Fall back to recommended server
    final recommendedServer = ref.read(recommendedServerProvider);
    if (recommendedServer != null) {
      AppLogger.info('Auto-connecting to recommended server: ${recommendedServer.name}');
      await connect(recommendedServer);
      return;
    }

    throw Exception('No available server for auto-connect');
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

  void _onRepositoryStateChanged(ConnectionStateEntity repoState) {
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

  /// Resolves DNS server addresses based on user settings.
  ///
  /// Returns `null` for system DNS (uses platform defaults) or a list of
  /// IP addresses for the selected provider.
  List<String>? _resolveDnsServers(VpnSettings vpnSettings) {
    switch (vpnSettings.dnsProvider) {
      case DnsProvider.system:
        return null;
      case DnsProvider.cloudflare:
        return [
          VpnConstants.cloudflareIPv4Primary,
          VpnConstants.cloudflareIPv4Secondary,
        ];
      case DnsProvider.google:
        return [
          VpnConstants.googleIPv4Primary,
          VpnConstants.googleIPv4Secondary,
        ];
      case DnsProvider.quad9:
        return [
          VpnConstants.quad9IPv4Primary,
          VpnConstants.quad9IPv4Secondary,
        ];
      case DnsProvider.custom:
        final custom = vpnSettings.customDns;
        if (custom != null && custom.isNotEmpty) {
          return [custom];
        }
        // Fall back to default if custom DNS is not set.
        return VpnConstants.defaultDnsServers;
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
      // Verify the VPN is currently disconnected before auto-connecting.
      final current = state.value;
      if (current is! VpnDisconnected) {
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

      // Load the last connected server from secure storage.
      final savedServer = await _loadLastServer();
      if (savedServer == null) {
        AppLogger.info('Auto-connect: no saved server found, skipping');
        return;
      }

      // Verify the saved server is available before attempting connection.
      // If the server is marked as unavailable, skip auto-connect gracefully.
      if (!savedServer.isAvailable) {
        AppLogger.info(
          'Auto-connect: saved server ${savedServer.name} is unavailable, skipping',
        );
        return;
      }

      AppLogger.info('Auto-connect: connecting to ${savedServer.name}');
      await connect(savedServer);
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
      final serverJson = jsonEncode({
        'id': server.id,
        'name': server.name,
        'countryCode': server.countryCode,
        'countryName': server.countryName,
        'city': server.city,
        'address': server.address,
        'port': server.port,
        'protocol': server.protocol,
        'isAvailable': server.isAvailable,
        'isPremium': server.isPremium,
        'isFavorite': server.isFavorite,
      });
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
      return ServerEntity(
        id: map['id'] as String,
        name: map['name'] as String,
        countryCode: map['countryCode'] as String,
        countryName: map['countryName'] as String,
        city: map['city'] as String,
        address: map['address'] as String,
        port: map['port'] as int,
        protocol: map['protocol'] as String? ?? 'vless',
        isAvailable: map['isAvailable'] as bool? ?? true,
        isPremium: map['isPremium'] as bool? ?? false,
        isFavorite: map['isFavorite'] as bool? ?? false,
      );
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
    AppLogger.warning(
      'Received force_disconnect from server: ${event.reason}',
    );

    // Disconnect the VPN immediately.
    await disconnect();

    // Update state to error with the disconnect reason so the UI can
    // display it to the user.
    state = AsyncData(
      VpnError(
        message: event.reason.isNotEmpty
            ? 'Disconnected by server: ${event.reason}'
            : 'Disconnected by server',
      ),
    );
  }

  /// Automatically register the device on first VPN connection.
  ///
  /// Runs asynchronously in the background. Registration failures are logged
  /// but do not block the VPN connection.
  Future<void> _registerDeviceIfNeeded() async {
    try {
      final device = await _deviceRegistration.registerCurrentDevice();
      if (device != null) {
        AppLogger.info('Device auto-registered on VPN connection: ${device.name}');
        // Optionally refresh the profile to include the new device in the list
        ref.read(profileProvider.notifier).refreshProfile();
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
          parameters: {
            'error': e.toString(),
          },
        );
      } catch (_) {
        // Ignore analytics logging errors
      }
    }
  }

  void _dispose() {
    _stateSubscription?.cancel();
    _networkSubscription?.cancel();
    _webSocketSubscription?.cancel();
    _autoReconnect.dispose();
  }
}

// ---------------------------------------------------------------------------
// Derived providers
// ---------------------------------------------------------------------------

/// Whether the VPN is currently connected.
final isConnectedProvider = Provider<bool>((ref) {
  final asyncState = ref.watch(vpnConnectionProvider);
  return asyncState.value?.isConnected ?? false;
});

/// The server we are currently connected to (or connecting to), if any.
final currentServerProvider = Provider<ServerEntity?>((ref) {
  final asyncState = ref.watch(vpnConnectionProvider);
  return asyncState.value?.server;
});

/// The active VPN protocol while connected.
final activeProtocolProvider = Provider<VpnProtocol?>((ref) {
  final asyncState = ref.watch(vpnConnectionProvider);
  final value = asyncState.value;
  if (value is VpnConnected) return value.protocol;
  return null;
});
