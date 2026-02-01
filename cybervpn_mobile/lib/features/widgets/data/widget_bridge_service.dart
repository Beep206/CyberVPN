import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:home_widget/home_widget.dart';

import 'package:cybervpn_mobile/core/utils/app_logger.dart';

// ---------------------------------------------------------------------------
// Shared preference keys used by native home-screen widgets
// ---------------------------------------------------------------------------

/// Keys for data shared between the Flutter app and native widgets via
/// [HomeWidget.saveWidgetData].
abstract final class WidgetDataKeys {
  static const vpnStatus = 'vpn_status';
  static const serverName = 'server_name';
  static const uploadSpeed = 'upload_speed';
  static const downloadSpeed = 'download_speed';
  static const sessionDuration = 'session_duration';
}

/// Native widget provider / kind identifiers.
abstract final class WidgetIdentifiers {
  /// The Android `AppWidgetProvider` class name.
  static const androidName = 'VPNWidgetProvider';

  /// The iOS WidgetKit `kind` value.
  static const iOSName = 'VPNWidget';
}

// ---------------------------------------------------------------------------
// WidgetBridgeService
// ---------------------------------------------------------------------------

/// Bridges VPN connection state to the native home-screen widget layer.
///
/// Uses the `home_widget` package to persist key-value pairs into platform
/// shared storage (SharedPreferences on Android, UserDefaults on iOS) so
/// that the native widget can read and display the current VPN status.
class WidgetBridgeService {
  /// Creates a [WidgetBridgeService].
  ///
  /// An optional [saveWidgetData] and [updateWidget] can be injected for
  /// testing. When omitted the real [HomeWidget] static methods are used.
  WidgetBridgeService({
    SaveWidgetDataFn? saveWidgetData,
    UpdateWidgetFn? updateWidget,
  })  : _saveWidgetData = saveWidgetData ?? HomeWidget.saveWidgetData,
        _updateWidget = updateWidget ?? HomeWidget.updateWidget;

  final SaveWidgetDataFn _saveWidgetData;
  final UpdateWidgetFn _updateWidget;

  /// Persists the current VPN state into shared storage so the native widget
  /// can display it.
  ///
  /// After saving all key-value pairs, [triggerWidgetUpdate] is called to
  /// notify the OS to refresh the widget.
  Future<void> updateWidgetState({
    required String vpnStatus,
    required String serverName,
    required double uploadSpeed,
    required double downloadSpeed,
    required Duration sessionDuration,
  }) async {
    try {
      await _saveWidgetData<String>(WidgetDataKeys.vpnStatus, vpnStatus);
      await _saveWidgetData<String>(WidgetDataKeys.serverName, serverName);
      await _saveWidgetData<double>(WidgetDataKeys.uploadSpeed, uploadSpeed);
      await _saveWidgetData<double>(
        WidgetDataKeys.downloadSpeed,
        downloadSpeed,
      );
      await _saveWidgetData<int>(
        WidgetDataKeys.sessionDuration,
        sessionDuration.inSeconds,
      );

      await triggerWidgetUpdate();
    } catch (e, st) {
      AppLogger.error(
        'WidgetBridgeService: failed to update widget state',
        error: e,
        stackTrace: st,
      );
    }
  }

  /// Tells the OS to refresh the native home-screen widget.
  Future<void> triggerWidgetUpdate() async {
    try {
      await _updateWidget(
        androidName: WidgetIdentifiers.androidName,
        iOSName: WidgetIdentifiers.iOSName,
      );
    } catch (e, st) {
      AppLogger.error(
        'WidgetBridgeService: failed to trigger widget update',
        error: e,
        stackTrace: st,
      );
    }
  }
}

// ---------------------------------------------------------------------------
// Function type aliases (for DI / testing)
// ---------------------------------------------------------------------------

/// Signature matching [HomeWidget.saveWidgetData].
typedef SaveWidgetDataFn = Future<bool?> Function<T>(String id, T? data);

/// Signature matching [HomeWidget.updateWidget].
typedef UpdateWidgetFn = Future<bool?> Function({
  String? name,
  String? androidName,
  String? iOSName,
  String? qualifiedAndroidName,
});

// ---------------------------------------------------------------------------
// Riverpod provider
// ---------------------------------------------------------------------------

/// Provides a singleton [WidgetBridgeService] instance.
final widgetBridgeServiceProvider = Provider<WidgetBridgeService>((ref) {
  return WidgetBridgeService();
});
