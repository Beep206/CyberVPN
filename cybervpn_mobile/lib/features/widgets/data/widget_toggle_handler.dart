import 'package:flutter/services.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_provider.dart';

/// Background callback channel name for widget toggle actions.
const _kWidgetToggleChannel = 'com.cybervpn.cybervpn_mobile/widget_toggle';

/// Provider for [WidgetToggleHandler].
final widgetToggleHandlerProvider = Provider<WidgetToggleHandler>((ref) {
  return WidgetToggleHandler(ref: ref);
});

/// Handles VPN toggle actions initiated from home screen widgets.
///
/// Listens to native broadcasts and triggers VPN connect/disconnect
/// via the [VpnConnectionNotifier].
class WidgetToggleHandler {
  final Ref ref;
  final MethodChannel _channel;

  WidgetToggleHandler({
    required this.ref,
  }) : _channel = const MethodChannel(_kWidgetToggleChannel) {
    _setupMethodCallHandler();
  }

  /// Sets up the method channel handler for widget toggle actions.
  void _setupMethodCallHandler() {
    _channel.setMethodCallHandler(_handleMethodCall);
    AppLogger.info('WidgetToggleHandler: Method channel initialized');
  }

  /// Handles incoming method calls from native code.
  Future<dynamic> _handleMethodCall(MethodCall call) async {
    AppLogger.info('WidgetToggleHandler: Received method call: ${call.method}');

    switch (call.method) {
      case 'toggleVpn':
        return await _handleToggleVpn();
      default:
        throw PlatformException(
          code: 'UNIMPLEMENTED',
          message: 'Method ${call.method} not implemented',
        );
    }
  }

  /// Handles VPN toggle action from widget.
  ///
  /// If VPN is connected or connecting, disconnects.
  /// If VPN is disconnected, the widget tap opens the app (handled by MainActivity).
  /// Note: Auto-connect from widget when disconnected requires additional implementation
  /// to load the last server and call connect(). For now, widget toggle only disconnects.
  Future<bool> _handleToggleVpn() async {
    try {
      final asyncState = ref.read(vpnConnectionProvider);
      final connectionState = asyncState.value;

      if (connectionState == null) {
        AppLogger.warning('WidgetToggleHandler: Connection state not available');
        return false;
      }

      final notifier = ref.read(vpnConnectionProvider.notifier);

      if (connectionState.isConnected || connectionState.isConnecting) {
        // Disconnect VPN
        AppLogger.info('WidgetToggleHandler: Disconnecting VPN from widget');
        await notifier.disconnect();
        return true;
      } else {
        // When disconnected, the widget button should open the app
        // This is handled natively - MainActivity will launch on button tap
        AppLogger.info('WidgetToggleHandler: VPN is disconnected, tap will open app');
        return true;
      }
    } catch (e, st) {
      AppLogger.error(
        'WidgetToggleHandler: Failed to toggle VPN',
        error: e,
        stackTrace: st,
      );
      return false;
    }
  }
}

/// Background callback entry point for handling widget actions when app is terminated.
///
/// This is registered with the Flutter engine to handle background widget interactions.
@pragma('vm:entry-point')
void widgetBackgroundCallback() {
  WidgetsFlutterBinding.ensureInitialized();

  // Handle background method channel calls
  const channel = MethodChannel(_kWidgetToggleChannel);

  channel.setMethodCallHandler((call) async {
    AppLogger.info('Background: Received widget method call: ${call.method}');

    // In background mode, we can't directly access Riverpod providers
    // So we'll just log the action. The actual toggle will happen when
    // the app comes to foreground or when the user opens the app.

    // Alternative: You could use a WorkManager or similar to trigger
    // VPN operations in the background, but this requires additional setup.

    return null;
  });
}
