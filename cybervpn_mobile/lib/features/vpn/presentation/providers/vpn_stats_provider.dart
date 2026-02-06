import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/core/utils/data_formatters.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/connection_stats_entity.dart';
import 'package:cybervpn_mobile/core/di/providers.dart'
    show vpnRepositoryProvider;
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_provider.dart';
import 'package:cybervpn_mobile/features/widgets/data/widget_bridge_service.dart';

// ---------------------------------------------------------------------------
// VPN Stats Notifier
// ---------------------------------------------------------------------------

final vpnStatsProvider =
    NotifierProvider<VpnStatsNotifier, ConnectionStatsEntity?>(
  VpnStatsNotifier.new,
);

class VpnStatsNotifier extends Notifier<ConnectionStatsEntity?> {
  Timer? _pollTimer;
  StreamSubscription<ConnectionStatsEntity>? _streamSub;

  /// Previous snapshot used for delta-based speed calculation.
  ConnectionStatsEntity? _previousSnapshot;
  DateTime? _previousTimestamp;

  /// Timestamp when the current session started.
  DateTime? _sessionStartTime;

  late final WidgetBridgeService _widgetBridge;

  @override
  ConnectionStatsEntity? build() {
    _widgetBridge = ref.watch(widgetBridgeServiceProvider);

    // Listen to the connection provider and start/stop polling accordingly.
    ref.listen<AsyncValue<VpnConnectionState>>(
      vpnConnectionProvider,
      (previous, next) {
        final current = next.value;
        if (current is VpnConnected) {
          _startPolling();
        } else {
          _stopPolling();
        }
      },
      fireImmediately: true,
    );

    ref.onDispose(_dispose);

    return null;
  }

  // -- Polling lifecycle ----------------------------------------------------

  void _startPolling() {
    // Avoid double-start.
    final timer = _pollTimer;
    if (timer != null && timer.isActive) return;

    AppLogger.info('VPN stats: starting polling');

    // Reset session counters for the new connection.
    _previousSnapshot = null;
    _previousTimestamp = null;
    _sessionStartTime = DateTime.now();

    // Subscribe to the repository stream for stats updates.
    final repository = ref.read(vpnRepositoryProvider);
    unawaited(_streamSub?.cancel());
    _streamSub = repository.connectionStatsStream.listen(
      _onStatsReceived,
      onError: (Object e) {
        AppLogger.warning('VPN stats stream error', error: e);
      },
    );

    // Poll every 1 second to keep the duration ticker alive even when no
    // new stats arrive from the platform layer.
    _pollTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      _updateDuration();
    });
  }

  void _stopPolling() {
    _pollTimer?.cancel();
    _pollTimer = null;
    unawaited(_streamSub?.cancel());
    _streamSub = null;
    _previousSnapshot = null;
    _previousTimestamp = null;

    // Clear stats when disconnected.
    state = null;

    // Notify the native widget that the VPN is disconnected.
    unawaited(_widgetBridge.updateWidgetState(
      vpnStatus: 'disconnected',
      serverName: '',
      uploadSpeed: 0,
      downloadSpeed: 0,
      sessionDuration: Duration.zero,
    ));
  }

  // -- Stats processing -----------------------------------------------------

  void _onStatsReceived(ConnectionStatsEntity raw) {
    final now = DateTime.now();

    // Calculate speed as delta bytes / delta time.
    int downloadSpeed = raw.downloadSpeed;
    int uploadSpeed = raw.uploadSpeed;

    final prevSnap = _previousSnapshot;
    final prevTime = _previousTimestamp;
    if (prevSnap != null && prevTime != null) {
      final elapsed = now.difference(prevTime);
      if (elapsed.inMilliseconds > 0) {
        final dlDelta = raw.totalDownload - prevSnap.totalDownload;
        final ulDelta = raw.totalUpload - prevSnap.totalUpload;
        final seconds = elapsed.inMilliseconds / 1000.0;

        downloadSpeed = (dlDelta / seconds).round().clamp(0, 1 << 62);
        uploadSpeed = (ulDelta / seconds).round().clamp(0, 1 << 62);
      }
    }

    _previousSnapshot = raw;
    _previousTimestamp = now;

    final startTime = _sessionStartTime;
    final sessionDuration = startTime != null
        ? now.difference(startTime)
        : raw.connectionDuration;

    final updated = ConnectionStatsEntity(
      downloadSpeed: downloadSpeed,
      uploadSpeed: uploadSpeed,
      totalDownload: raw.totalDownload,
      totalUpload: raw.totalUpload,
      connectionDuration: sessionDuration,
      serverName: raw.serverName,
      protocol: raw.protocol,
      ipAddress: raw.ipAddress,
    );
    state = updated;

    // Push latest stats to the native home-screen widget.
    unawaited(_widgetBridge.updateWidgetState(
      vpnStatus: 'connected',
      serverName: updated.serverName ?? '',
      uploadSpeed: updated.uploadSpeed.toDouble(),
      downloadSpeed: updated.downloadSpeed.toDouble(),
      sessionDuration: updated.connectionDuration,
    ));
  }

  /// Called every second by the poll timer to keep the duration ticking even
  /// when no new stats arrive from the platform layer.
  void _updateDuration() {
    final current = state;
    final startTime = _sessionStartTime;
    if (current == null || startTime == null) return;

    final now = DateTime.now();
    final sessionDuration = now.difference(startTime);

    state = ConnectionStatsEntity(
      downloadSpeed: current.downloadSpeed,
      uploadSpeed: current.uploadSpeed,
      totalDownload: current.totalDownload,
      totalUpload: current.totalUpload,
      connectionDuration: sessionDuration,
      serverName: current.serverName,
      protocol: current.protocol,
      ipAddress: current.ipAddress,
    );
  }

  void _dispose() {
    _pollTimer?.cancel();
    unawaited(_streamSub?.cancel());
  }
}

// ---------------------------------------------------------------------------
// Derived providers
// ---------------------------------------------------------------------------

/// Current download and upload speed formatted as human-readable strings.
final currentSpeedProvider = Provider<({String download, String upload})>((ref) {
  final stats = ref.watch(vpnStatsProvider);
  if (stats == null) {
    return (download: '0 B/s', upload: '0 B/s');
  }
  return (
    download: DataFormatters.formatSpeed(stats.downloadSpeed.toDouble()),
    upload: DataFormatters.formatSpeed(stats.uploadSpeed.toDouble()),
  );
});

/// Session data usage (total download + upload since this connection started).
final sessionUsageProvider =
    Provider<({String download, String upload, String total})>((ref) {
  final stats = ref.watch(vpnStatsProvider);
  if (stats == null) {
    return (download: '0 B', upload: '0 B', total: '0 B');
  }
  return (
    download: DataFormatters.formatBytes(stats.totalDownload),
    upload: DataFormatters.formatBytes(stats.totalUpload),
    total: DataFormatters.formatBytes(stats.totalDownload + stats.totalUpload),
  );
});

/// Session duration formatted as a human-readable string.
final sessionDurationProvider = Provider<String>((ref) {
  final stats = ref.watch(vpnStatsProvider);
  if (stats == null) return '0s';
  return DataFormatters.formatDuration(stats.connectionDuration);
});
