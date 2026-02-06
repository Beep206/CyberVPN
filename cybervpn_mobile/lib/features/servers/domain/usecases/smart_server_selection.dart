import 'package:meta/meta.dart';

import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:cybervpn_mobile/features/servers/domain/repositories/server_repository.dart';

/// Smart server selection algorithm.
///
/// Score formula:
///   score = (latencyNorm * 0.4) + (loadNorm * 0.3) + (distanceNorm * 0.2) + (protocolNorm * 0.1)
///
/// Each factor is normalized to the [0, 1] range.
/// Servers with load >= 70 % are penalized.
/// Returns the server with the **lowest** score.
@immutable
class SmartServerSelection {
  const SmartServerSelection(this._repository);

  final ServerRepository _repository;

  // ---------------------------------------------------------------------------
  // Weights
  // ---------------------------------------------------------------------------

  static const double _latencyWeight = 0.4;
  static const double _loadWeight = 0.3;
  static const double _distanceWeight = 0.2;
  static const double _protocolWeight = 0.1;

  /// Load threshold above which a penalty is applied.
  static const double _loadPenaltyThreshold = 0.70;

  /// Penalty multiplier for servers above the load threshold.
  static const double _highLoadPenalty = 1.5;

  // ---------------------------------------------------------------------------
  // Reference maximums used for normalization
  // ---------------------------------------------------------------------------

  /// Maximum latency (ms) considered for normalization.
  static const int _maxLatencyMs = 500;

  // ---------------------------------------------------------------------------
  // Preferred protocols ranked from best to worst
  // ---------------------------------------------------------------------------

  static const List<String> _protocolRank = [
    'vless',
    'vmess',
    'trojan',
    'shadowsocks',
  ];

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------

  /// Returns the best recommended server from the full server list.
  ///
  /// [userLatitude] and [userLongitude] are optional; if provided they are
  /// used for the distance factor. When absent, distance is treated as 0 for
  /// all servers (effectively removing it from scoring).
  ///
  /// [preferredProtocol] can be supplied to boost servers that support it.
  Future<ServerEntity?> getRecommendedServer({
    double? userLatitude,
    double? userLongitude,
    String? preferredProtocol,
  }) async {
    final serversResult = await _repository.getServers();
    final servers = switch (serversResult) {
      Success(:final data) => data,
      Failure() => <ServerEntity>[],
    };

    if (servers.isEmpty) return null;

    // Filter to available servers only.
    final available = servers.where((s) => s.isAvailable).toList();
    if (available.isEmpty) return null;

    ServerEntity? best;
    double bestScore = double.infinity;

    for (final server in available) {
      final score = _computeScore(
        server,
        userLat: userLatitude,
        userLon: userLongitude,
        preferredProtocol: preferredProtocol,
      );

      if (score < bestScore) {
        bestScore = score;
        best = server;
      }
    }

    return best;
  }

  /// Compute scores for all available servers and return them sorted ascending.
  Future<List<ScoredServer>> getRankedServers({
    double? userLatitude,
    double? userLongitude,
    String? preferredProtocol,
  }) async {
    final serversResult = await _repository.getServers();
    final servers = switch (serversResult) {
      Success(:final data) => data,
      Failure() => <ServerEntity>[],
    };
    final available = servers.where((s) => s.isAvailable).toList();

    final scored = available.map((server) {
      final score = _computeScore(
        server,
        userLat: userLatitude,
        userLon: userLongitude,
        preferredProtocol: preferredProtocol,
      );
      return ScoredServer(server: server, score: score);
    }).toList();

    scored.sort((a, b) => a.score.compareTo(b.score));
    return scored;
  }

  // ---------------------------------------------------------------------------
  // Private – scoring
  // ---------------------------------------------------------------------------

  double _computeScore(
    ServerEntity server, {
    double? userLat,
    double? userLon,
    String? preferredProtocol,
  }) {
    final latencyNorm = _normalizeLatency(server.ping);
    final loadNorm = _normalizeLoad(server.load);
    final distanceNorm = _normalizeDistance(server, userLat, userLon);
    final protocolNorm =
        _normalizeProtocol(server.protocol, preferredProtocol);

    double score = (latencyNorm * _latencyWeight) +
        (loadNorm * _loadWeight) +
        (distanceNorm * _distanceWeight) +
        (protocolNorm * _protocolWeight);

    // Apply penalty for high-load servers.
    if ((server.load ?? 0) >= _loadPenaltyThreshold) {
      score *= _highLoadPenalty;
    }

    return score;
  }

  // ---------------------------------------------------------------------------
  // Normalization helpers (all return 0..1)
  // ---------------------------------------------------------------------------

  /// Normalize latency to [0, 1]. Lower is better.
  double _normalizeLatency(int? pingMs) {
    if (pingMs == null) return 1.0; // Unknown treated as worst.
    return (pingMs / _maxLatencyMs).clamp(0.0, 1.0);
  }

  /// Normalize server load to [0, 1]. Lower is better.
  double _normalizeLoad(double? load) {
    if (load == null) return 0.5; // Unknown treated as mid.
    return load.clamp(0.0, 1.0);
  }

  /// Normalize geographic distance to [0, 1]. Lower is better.
  double _normalizeDistance(
    ServerEntity server,
    double? userLat,
    double? userLon,
  ) {
    if (userLat == null || userLon == null) return 0.0;

    // Use a simple estimated distance based on the server address.
    // In a real implementation you would have server lat/lon on the entity.
    // For now, return 0.0 as a placeholder (distance factor effectively zeroed).
    return 0.0;
  }

  /// Normalize protocol preference to [0, 1]. Lower is better.
  double _normalizeProtocol(String protocol, String? preferred) {
    // If user has a preference, exact match = 0, otherwise = 1.
    if (preferred != null) {
      return protocol.toLowerCase() == preferred.toLowerCase() ? 0.0 : 1.0;
    }

    // Fall back to ranked list.
    final index = _protocolRank.indexOf(protocol.toLowerCase());
    if (index == -1) return 1.0;
    return index / (_protocolRank.length - 1).clamp(1, _protocolRank.length);
  }
}

// ---------------------------------------------------------------------------
// Data class for scored results
// ---------------------------------------------------------------------------

/// A server paired with its computed selection score.
class ScoredServer {
  const ScoredServer({required this.server, required this.score});

  final ServerEntity server;

  /// Lower is better (0 = perfect, higher = worse).
  final double score;

  @override
  String toString() =>
      'ScoredServer(${server.name}, score: ${score.toStringAsFixed(3)})';
}
