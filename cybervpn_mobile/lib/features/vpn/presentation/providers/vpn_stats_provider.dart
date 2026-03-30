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

class VpnStatsSnapshotAtNotifier extends Notifier<DateTime?> {
  @override
  DateTime? build() => null;

  void set(DateTime? value) {
    state = value;
  }
}

final vpnStatsSnapshotAtProvider =
    NotifierProvider<VpnStatsSnapshotAtNotifier, DateTime?>(
      VpnStatsSnapshotAtNotifier.new,
    );

final _sessionDurationTickerProvider = StreamProvider.autoDispose<DateTime>((
  ref,
) {
  final controller = StreamController<DateTime>();
  controller.add(DateTime.now());

  final timer = Timer.periodic(const Duration(seconds: 1), (_) {
    controller.add(DateTime.now());
  });

  ref.onDispose(() {
    timer.cancel();
    unawaited(controller.close());
  });

  return controller.stream;
});

class VpnStatsNotifier extends Notifier<ConnectionStatsEntity?> {
  static const _widgetUpdateInterval = Duration(seconds: 5);

  Timer? _widgetUpdateTimer;
  StreamSubscription<ConnectionStatsEntity>? _streamSub;

  /// Previous snapshot used for delta-based speed calculation.
  ConnectionStatsEntity? _previousSnapshot;
  DateTime? _previousTimestamp;

  /// Timestamp when the current session started.
  DateTime? _sessionStartTime;

  DateTime? _lastWidgetUpdateAt;
  String? _lastWidgetServerName;

  late final WidgetBridgeService _widgetBridge;

  @override
  ConnectionStatsEntity? build() {
    _widgetBridge = ref.watch(widgetBridgeServiceProvider);

    // Listen to the connection provider and start/stop polling accordingly.
    ref.listen<AsyncValue<VpnConnectionState>>(vpnConnectionProvider, (
      previous,
      next,
    ) {
      final current = next.value;
      if (current is VpnConnected) {
        _startPolling();
      } else {
        _stopPolling();
      }
    }, fireImmediately: true);

    ref.onDispose(_dispose);

    return null;
  }

  // -- Polling lifecycle ----------------------------------------------------

  void _startPolling() {
    final timer = _widgetUpdateTimer;
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

    // Update the home-screen widget on a coarse cadence without keeping a
    // 1 Hz app-wide timer alive for the entire connection session.
    _widgetUpdateTimer = Timer.periodic(_widgetUpdateInterval, (_) {
      final current = state;
      if (current == null) {
        return;
      }

      final liveStats = _liveStatsFromSnapshot(current, DateTime.now());
      _pushWidgetUpdate(liveStats);
    });
  }

  void _stopPolling() {
    _widgetUpdateTimer?.cancel();
    _widgetUpdateTimer = null;
    unawaited(_streamSub?.cancel());
    _streamSub = null;
    _previousSnapshot = null;
    _previousTimestamp = null;
    _sessionStartTime = null;
    _lastWidgetUpdateAt = null;
    _lastWidgetServerName = null;
    ref.read(vpnStatsSnapshotAtProvider.notifier).set(null);

    // Clear stats when disconnected.
    state = null;

    // Notify the native widget that the VPN is disconnected.
    unawaited(
      _widgetBridge.updateWidgetState(
        vpnStatus: 'disconnected',
        serverName: '',
        uploadSpeed: 0,
        downloadSpeed: 0,
        sessionDuration: Duration.zero,
      ),
    );
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
    ref.read(vpnStatsSnapshotAtProvider.notifier).set(now);

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

    _pushWidgetUpdate(updated);
  }

  ConnectionStatsEntity _liveStatsFromSnapshot(
    ConnectionStatsEntity current,
    DateTime now,
  ) {
    final anchor = ref.read(vpnStatsSnapshotAtProvider);
    final startTime = _sessionStartTime;
    if (anchor == null || startTime == null) {
      return current;
    }

    final liveDuration = now.difference(startTime);
    if (liveDuration == current.connectionDuration) {
      return current;
    }

    return ConnectionStatsEntity(
      downloadSpeed: current.downloadSpeed,
      uploadSpeed: current.uploadSpeed,
      totalDownload: current.totalDownload,
      totalUpload: current.totalUpload,
      connectionDuration: liveDuration,
      serverName: current.serverName,
      protocol: current.protocol,
      ipAddress: current.ipAddress,
    );
  }

  void _pushWidgetUpdate(ConnectionStatsEntity stats) {
    final now = DateTime.now();
    final serverName = stats.serverName ?? '';
    final shouldUpdate =
        _lastWidgetUpdateAt == null ||
        serverName != _lastWidgetServerName ||
        now.difference(_lastWidgetUpdateAt!) >= _widgetUpdateInterval;

    if (!shouldUpdate) {
      return;
    }

    _lastWidgetUpdateAt = now;
    _lastWidgetServerName = serverName;

    unawaited(
      _widgetBridge.updateWidgetState(
        vpnStatus: 'connected',
        serverName: serverName,
        uploadSpeed: stats.uploadSpeed.toDouble(),
        downloadSpeed: stats.downloadSpeed.toDouble(),
        sessionDuration: stats.connectionDuration,
      ),
    );
  }

  void _dispose() {
    _widgetUpdateTimer?.cancel();
    unawaited(_streamSub?.cancel());
  }
}

// ---------------------------------------------------------------------------
// Derived providers
// ---------------------------------------------------------------------------

/// Current download and upload speed formatted as human-readable strings.
final currentSpeedProvider = Provider<({String download, String upload})>((
  ref,
) {
  final downloadSpeed = ref.watch(
    vpnStatsProvider.select((stats) => stats?.downloadSpeed ?? 0),
  );
  final uploadSpeed = ref.watch(
    vpnStatsProvider.select((stats) => stats?.uploadSpeed ?? 0),
  );

  return (
    download: DataFormatters.formatSpeed(downloadSpeed.toDouble()),
    upload: DataFormatters.formatSpeed(uploadSpeed.toDouble()),
  );
});

/// Session data usage (total download + upload since this connection started).
final sessionUsageProvider =
    Provider<({String download, String upload, String total})>((ref) {
      final totalDownload = ref.watch(
        vpnStatsProvider.select((stats) => stats?.totalDownload ?? 0),
      );
      final totalUpload = ref.watch(
        vpnStatsProvider.select((stats) => stats?.totalUpload ?? 0),
      );

      return (
        download: DataFormatters.formatBytes(totalDownload),
        upload: DataFormatters.formatBytes(totalUpload),
        total: DataFormatters.formatBytes(totalDownload + totalUpload),
      );
    });

/// Session duration formatted as a human-readable string.
final sessionDurationProvider = Provider.autoDispose<String>((ref) {
  ref.watch(_sessionDurationTickerProvider);

  final baseDuration = ref.watch(
    vpnStatsProvider.select(
      (stats) => stats?.connectionDuration ?? Duration.zero,
    ),
  );
  final snapshotAt = ref.watch(vpnStatsSnapshotAtProvider);
  final sessionStartTime = snapshotAt == null
      ? null
      : DateTime.now().subtract(baseDuration);

  final duration = sessionStartTime == null
      ? baseDuration
      : DateTime.now().difference(sessionStartTime);

  return DataFormatters.formatDuration(duration);
});
