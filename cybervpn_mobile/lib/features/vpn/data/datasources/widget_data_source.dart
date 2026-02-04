import 'package:home_widget/home_widget.dart';

/// Data source for updating iOS WidgetKit widgets
///
/// This class manages communication between the Flutter app and iOS widgets
/// using the home_widget package and App Group shared UserDefaults.
class WidgetDataSource {
  /// App Group identifier for shared data access
  ///
  /// Must match the App Group configured in Xcode for both
  /// Runner target and CyberVPNWidget target.
  static const String _appGroupId = 'group.com.cybervpn.widgets';

  /// Keys for shared UserDefaults storage
  static const String _keyVpnStatus = 'vpn_status';
  static const String _keyServerName = 'server_name';
  static const String _keyUploadSpeed = 'upload_speed';
  static const String _keyDownloadSpeed = 'download_speed';
  static const String _keyLastUpdate = 'last_update';

  /// Widget identifier for iOS
  static const String _iosWidgetName = 'CyberVPNWidget';

  /// Update widget with current VPN status
  ///
  /// This method writes VPN connection data to shared UserDefaults
  /// and triggers a widget timeline update.
  ///
  /// Parameters:
  /// - [status]: Connection status ('connected', 'disconnected', 'connecting')
  /// - [serverName]: Current server name or 'Not connected'
  /// - [uploadSpeed]: Current upload speed formatted (e.g., '1.2 MB/s')
  /// - [downloadSpeed]: Current download speed formatted (e.g., '5.8 MB/s')
  Future<void> updateWidgetData({
    required String status,
    required String serverName,
    required String uploadSpeed,
    required String downloadSpeed,
  }) async {
    try {
      // Write data to shared UserDefaults
      await HomeWidget.saveWidgetData<String>(_keyVpnStatus, status);
      await HomeWidget.saveWidgetData<String>(_keyServerName, serverName);
      await HomeWidget.saveWidgetData<String>(_keyUploadSpeed, uploadSpeed);
      await HomeWidget.saveWidgetData<String>(
        _keyDownloadSpeed,
        downloadSpeed,
      );
      await HomeWidget.saveWidgetData<String>(
        _keyLastUpdate,
        DateTime.now().toIso8601String(),
      );

      // Trigger widget update
      await HomeWidget.updateWidget(
        iOSName: _iosWidgetName,
      );
    } catch (e) {
      // Log error but don't crash - widget updates are non-critical
      // In production, this would be reported to error monitoring
      // ignore: avoid_print
      print('Error updating widget data: $e');
    }
  }

  /// Initialize widget data source on app startup
  ///
  /// This method configures the App Group ID for shared data access.
  /// Must be called before any other widget operations.
  Future<void> initialize() async {
    try {
      await HomeWidget.setAppGroupId(_appGroupId);
    } catch (e) {
      // Log error but don't crash - widget support is optional
      // ignore: avoid_print
      print('Error initializing widget data source: $e');
    }
  }

  /// Clear widget data (e.g., on logout)
  Future<void> clearWidgetData() async {
    try {
      await updateWidgetData(
        status: 'disconnected',
        serverName: 'Not connected',
        uploadSpeed: '0 KB/s',
        downloadSpeed: '0 KB/s',
      );
    } catch (e) {
      // ignore: avoid_print
      print('Error clearing widget data: $e');
    }
  }
}
