import 'dart:math' as math;

import 'package:cybervpn_mobile/core/constants/app_constants.dart';
import 'package:cybervpn_mobile/features/config_import/domain/entities/imported_config.dart';
import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/data/models/parsed_server.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/profile_server.dart';

/// Effective runtime snapshot for subscription-related settings.
class SubscriptionPolicyState {
  const SubscriptionPolicyState({
    this.autoUpdateEnabled = true,
    this.autoUpdateInterval = const Duration(hours: 24),
    this.updateNotificationsEnabled = false,
    this.autoUpdateOnOpen = true,
    this.pingOnOpenEnabled = false,
    this.connectStrategy = SubscriptionConnectStrategy.lastUsed,
    this.preventDuplicateImports = true,
    this.collapseSubscriptions = true,
    this.noFilter = false,
    this.userAgentMode = SubscriptionUserAgentMode.appDefault,
    this.customUserAgent,
    this.effectiveUserAgent = SubscriptionPolicyRuntime.defaultUserAgent,
    this.sortMode = SubscriptionSortMode.none,
  });

  final bool autoUpdateEnabled;
  final Duration autoUpdateInterval;
  final bool updateNotificationsEnabled;
  final bool autoUpdateOnOpen;
  final bool pingOnOpenEnabled;
  final SubscriptionConnectStrategy connectStrategy;
  final bool preventDuplicateImports;
  final bool collapseSubscriptions;
  final bool noFilter;
  final SubscriptionUserAgentMode userAgentMode;
  final String? customUserAgent;
  final String effectiveUserAgent;
  final SubscriptionSortMode sortMode;
}

/// Selection result for policy-driven auto-connect entrypoints.
class SubscriptionConnectSelection {
  const SubscriptionConnectSelection({
    required this.server,
    required this.requestedStrategy,
    required this.appliedStrategy,
    required this.candidateCount,
    this.usedFallback = false,
    this.note,
  });

  final ServerEntity server;
  final SubscriptionConnectStrategy requestedStrategy;
  final SubscriptionConnectStrategy appliedStrategy;
  final int candidateCount;
  final bool usedFallback;
  final String? note;
}

/// Resolves and applies Happ-like subscription policies.
class SubscriptionPolicyRuntime {
  const SubscriptionPolicyRuntime({math.Random? random}) : _random = random;

  static const String defaultUserAgent =
      '${AppConstants.appName}/${AppConstants.appVersion}';

  final math.Random? _random;

  /// Build the effective runtime policy from persisted app settings.
  SubscriptionPolicyState resolve(AppSettings settings) {
    final customUserAgent = settings.subscriptionUserAgentValue?.trim();
    final effectiveUserAgent =
        settings.subscriptionUserAgentMode == SubscriptionUserAgentMode.custom &&
            customUserAgent != null &&
            customUserAgent.isNotEmpty
        ? customUserAgent
        : defaultUserAgent;
    final intervalHours = settings.subscriptionAutoUpdateIntervalHours.clamp(
      1,
      168,
    );

    return SubscriptionPolicyState(
      autoUpdateEnabled: settings.subscriptionAutoUpdateEnabled,
      autoUpdateInterval: Duration(hours: intervalHours),
      updateNotificationsEnabled:
          settings.subscriptionUpdateNotificationsEnabled,
      autoUpdateOnOpen: settings.subscriptionAutoUpdateOnOpen,
      pingOnOpenEnabled: settings.subscriptionPingOnOpenEnabled,
      connectStrategy: settings.subscriptionConnectStrategy,
      preventDuplicateImports: settings.preventDuplicateImports,
      collapseSubscriptions: settings.collapseSubscriptions,
      noFilter: settings.subscriptionNoFilter,
      userAgentMode: settings.subscriptionUserAgentMode,
      customUserAgent: customUserAgent,
      effectiveUserAgent: effectiveUserAgent,
      sortMode: settings.subscriptionSortMode,
    );
  }

  /// Resolve the best connection target for auto-connect entrypoints.
  ///
  /// Strategy precedence:
  /// - `lastUsed` prefers the last connected server, then lowest delay.
  /// - `lowestDelay` prefers the best available candidate, then last used.
  /// - `random` chooses from the available candidate pool, then falls back
  ///   to recommended/last used when no candidate list is available yet.
  SubscriptionConnectSelection? selectAutoConnectServer({
    required SubscriptionPolicyState policy,
    required List<ServerEntity> availableServers,
    ServerEntity? lastServer,
    ServerEntity? recommendedServer,
    math.Random? random,
  }) {
    final requestedStrategy = policy.connectStrategy;
    final lastUsedCandidate =
        lastServer != null && lastServer.isAvailable ? lastServer : null;
    final fallbackRecommended =
        recommendedServer != null && recommendedServer.isAvailable
        ? recommendedServer
        : null;
    final candidatePool = _connectableCandidatePool(availableServers);

    switch (requestedStrategy) {
      case SubscriptionConnectStrategy.lastUsed:
        if (lastUsedCandidate != null) {
          return SubscriptionConnectSelection(
            server: lastUsedCandidate,
            requestedStrategy: requestedStrategy,
            appliedStrategy: SubscriptionConnectStrategy.lastUsed,
            candidateCount: candidatePool.length,
          );
        }

        final fallbackServer =
            fallbackRecommended ??
            (candidatePool.isNotEmpty ? _selectLowestDelay(candidatePool) : null);
        if (fallbackServer == null) {
          return null;
        }

        return SubscriptionConnectSelection(
          server: fallbackServer,
          requestedStrategy: requestedStrategy,
          appliedStrategy: SubscriptionConnectStrategy.lowestDelay,
          candidateCount: candidatePool.length,
          usedFallback: true,
          note: 'Last used server unavailable; falling back to the lowest-delay candidate.',
        );

      case SubscriptionConnectStrategy.lowestDelay:
        final primaryServer =
            candidatePool.isNotEmpty ? _selectLowestDelay(candidatePool) : null;
        if (primaryServer != null) {
          return SubscriptionConnectSelection(
            server: primaryServer,
            requestedStrategy: requestedStrategy,
            appliedStrategy: SubscriptionConnectStrategy.lowestDelay,
            candidateCount: candidatePool.length,
          );
        }

        final fallbackServer = fallbackRecommended ?? lastUsedCandidate;
        if (fallbackServer == null) {
          return null;
        }

        return SubscriptionConnectSelection(
          server: fallbackServer,
          requestedStrategy: requestedStrategy,
          appliedStrategy:
              fallbackRecommended != null
                  ? SubscriptionConnectStrategy.lowestDelay
                  : SubscriptionConnectStrategy.lastUsed,
          candidateCount: candidatePool.length,
          usedFallback: true,
          note:
              fallbackRecommended != null
                  ? 'Server list unavailable; using recommended fallback for lowest-delay connect.'
                  : 'Server list unavailable; falling back to the last used server.',
        );

      case SubscriptionConnectStrategy.random:
        if (candidatePool.isNotEmpty) {
          final generator = random ?? _random ?? math.Random();
          final index = generator.nextInt(candidatePool.length);
          return SubscriptionConnectSelection(
            server: candidatePool[index],
            requestedStrategy: requestedStrategy,
            appliedStrategy: SubscriptionConnectStrategy.random,
            candidateCount: candidatePool.length,
          );
        }

        final fallbackServer = fallbackRecommended ?? lastUsedCandidate;
        if (fallbackServer == null) {
          return null;
        }

        return SubscriptionConnectSelection(
          server: fallbackServer,
          requestedStrategy: requestedStrategy,
          appliedStrategy:
              fallbackRecommended != null
                  ? SubscriptionConnectStrategy.lowestDelay
                  : SubscriptionConnectStrategy.lastUsed,
          candidateCount: candidatePool.length,
          usedFallback: true,
          note:
              fallbackRecommended != null
                  ? 'Random connect requested before candidates loaded; using recommended fallback.'
                  : 'Random connect requested before candidates loaded; falling back to the last used server.',
        );
    }
  }

  /// Whether a source is due for an automatic refresh.
  bool isRefreshDue({
    required DateTime? lastUpdated,
    required SubscriptionPolicyState policy,
    DateTime? now,
  }) {
    if (!policy.autoUpdateEnabled) {
      return false;
    }
    if (lastUpdated == null) {
      return true;
    }

    final reference = now ?? DateTime.now();
    return reference.difference(lastUpdated) >= policy.autoUpdateInterval;
  }

  /// Sort imported configs for predictable UI/import ordering.
  List<ImportedConfig> sortImportedConfigs(
    List<ImportedConfig> configs,
    SubscriptionPolicyState policy,
  ) {
    final sorted = List<ImportedConfig>.from(configs);
    if (policy.sortMode != SubscriptionSortMode.alphabetical) {
      return sorted;
    }

    sorted.sort((a, b) => _compareConfigLike(
      nameA: a.name,
      nameB: b.name,
      addressA: a.serverAddress,
      addressB: b.serverAddress,
      portA: a.port,
      portB: b.port,
    ));
    return sorted;
  }

  /// Sort freshly fetched remote servers using the effective policy.
  List<ParsedServer> sortParsedServers(
    List<ParsedServer> servers,
    SubscriptionPolicyState policy, {
    List<ProfileServer> existingServers = const <ProfileServer>[],
  }) {
    final sorted = List<ParsedServer>.from(servers);

    switch (policy.sortMode) {
      case SubscriptionSortMode.none:
        return sorted;
      case SubscriptionSortMode.alphabetical:
        sorted.sort((a, b) => _compareConfigLike(
          nameA: a.name,
          nameB: b.name,
          addressA: a.serverAddress,
          addressB: b.serverAddress,
          portA: a.port,
          portB: b.port,
        ));
        return sorted;
      case SubscriptionSortMode.ping:
        final latencyBySignature = <String, int?>{
          for (final server in existingServers)
            _serverSignature(
              name: server.name,
              address: server.serverAddress,
              port: server.port,
              protocol: server.protocol.name,
            ): server.latencyMs,
        };

        sorted.sort((a, b) {
          final latencyA = latencyBySignature[_serverSignature(
            name: a.name,
            address: a.serverAddress,
            port: a.port,
            protocol: a.protocol,
          )];
          final latencyB = latencyBySignature[_serverSignature(
            name: b.name,
            address: b.serverAddress,
            port: b.port,
            protocol: b.protocol,
          )];
          final latencyCompare = _compareLatency(latencyA, latencyB);
          if (latencyCompare != 0) {
            return latencyCompare;
          }

          return _compareConfigLike(
            nameA: a.name,
            nameB: b.name,
            addressA: a.serverAddress,
            addressB: b.serverAddress,
            portA: a.port,
            portB: b.port,
          );
        });
        return sorted;
    }
  }

  /// Reorder an existing server list after latency updates.
  List<ProfileServer> sortExistingServers(
    List<ProfileServer> servers,
    SubscriptionPolicyState policy,
  ) {
    final sorted = List<ProfileServer>.from(servers);

    switch (policy.sortMode) {
      case SubscriptionSortMode.none:
        sorted.sort((a, b) => a.sortOrder.compareTo(b.sortOrder));
      case SubscriptionSortMode.alphabetical:
        sorted.sort((a, b) => _compareConfigLike(
          nameA: a.name,
          nameB: b.name,
          addressA: a.serverAddress,
          addressB: b.serverAddress,
          portA: a.port,
          portB: b.port,
        ));
      case SubscriptionSortMode.ping:
        sorted.sort((a, b) {
          final latencyCompare = _compareLatency(a.latencyMs, b.latencyMs);
          if (latencyCompare != 0) {
            return latencyCompare;
          }

          return _compareConfigLike(
            nameA: a.name,
            nameB: b.name,
            addressA: a.serverAddress,
            addressB: b.serverAddress,
            portA: a.port,
            portB: b.port,
          );
        });
    }

    return sorted
        .asMap()
        .entries
        .map((entry) => entry.value.copyWith(sortOrder: entry.key))
        .toList(growable: false);
  }

  /// Human-readable summary for the current filter compatibility flag.
  String describeNoFilter(SubscriptionPolicyState policy) {
    if (policy.noFilter) {
      return 'Client-side subscription filtering disabled; provider payload is preserved as-is.';
    }

    return 'Client-side filtering remains available for future subscription rules.';
  }

  List<ServerEntity> _connectableCandidatePool(List<ServerEntity> servers) {
    final available = <ServerEntity>[];
    final seenIds = <String>{};
    for (final server in servers) {
      if (!server.isAvailable || !seenIds.add(server.id)) {
        continue;
      }
      available.add(server);
    }

    if (available.isEmpty) {
      return const <ServerEntity>[];
    }

    final nonPremium = available.where((server) => !server.isPremium).toList();
    return nonPremium.isNotEmpty ? nonPremium : available;
  }

  ServerEntity _selectLowestDelay(List<ServerEntity> servers) {
    final sorted = List<ServerEntity>.from(servers)
      ..sort((a, b) {
        final pingCompare = _compareLatency(a.ping, b.ping);
        if (pingCompare != 0) {
          return pingCompare;
        }

        final loadCompare = _compareLoad(a.load, b.load);
        if (loadCompare != 0) {
          return loadCompare;
        }

        final nameCompare = a.name.toLowerCase().compareTo(b.name.toLowerCase());
        if (nameCompare != 0) {
          return nameCompare;
        }

        return a.id.compareTo(b.id);
      });

    return sorted.first;
  }

  int _compareLatency(int? a, int? b) {
    if (a == null && b == null) {
      return 0;
    }
    if (a == null) {
      return 1;
    }
    if (b == null) {
      return -1;
    }
    return a.compareTo(b);
  }

  int _compareLoad(double? a, double? b) {
    if (a == null && b == null) {
      return 0;
    }
    if (a == null) {
      return 1;
    }
    if (b == null) {
      return -1;
    }
    return a.compareTo(b);
  }

  int _compareConfigLike({
    required String nameA,
    required String nameB,
    required String addressA,
    required String addressB,
    required int portA,
    required int portB,
  }) {
    final nameCompare = nameA.toLowerCase().compareTo(nameB.toLowerCase());
    if (nameCompare != 0) {
      return nameCompare;
    }

    final addressCompare = addressA.toLowerCase().compareTo(
      addressB.toLowerCase(),
    );
    if (addressCompare != 0) {
      return addressCompare;
    }

    return portA.compareTo(portB);
  }

  String _serverSignature({
    required String name,
    required String address,
    required int port,
    required String protocol,
  }) {
    return '${protocol.toLowerCase()}|${name.toLowerCase()}|${address.toLowerCase()}|$port';
  }
}
