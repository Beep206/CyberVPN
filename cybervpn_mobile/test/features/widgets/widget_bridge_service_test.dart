import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/features/widgets/data/widget_bridge_service.dart';

void main() {
  group('WidgetBridgeService', () {
    late WidgetBridgeService service;
    late List<_SaveCall> saveCalls;
    late int updateCallCount;

    setUp(() {
      saveCalls = [];
      updateCallCount = 0;

      service = WidgetBridgeService(
        saveWidgetData: <T>(String id, T? data) async {
          saveCalls.add(_SaveCall(id, data));
          return true;
        },
        updateWidget: ({
          String? name,
          String? androidName,
          String? iOSName,
          String? qualifiedAndroidName,
        }) async {
          updateCallCount++;
          return true;
        },
      );
    });

    test('updateWidgetState saves all key-value pairs', () async {
      await service.updateWidgetState(
        vpnStatus: 'connected',
        serverName: 'US-East-1',
        uploadSpeed: 1024.5,
        downloadSpeed: 2048.75,
        sessionDuration: const Duration(minutes: 5, seconds: 30),
      );

      expect(saveCalls.length, 5);

      // Verify each key-value pair.
      expect(
        saveCalls[0],
        _SaveCall(WidgetDataKeys.vpnStatus, 'connected'),
      );
      expect(
        saveCalls[1],
        _SaveCall(WidgetDataKeys.serverName, 'US-East-1'),
      );
      expect(
        saveCalls[2],
        _SaveCall(WidgetDataKeys.uploadSpeed, 1024.5),
      );
      expect(
        saveCalls[3],
        _SaveCall(WidgetDataKeys.downloadSpeed, 2048.75),
      );
      expect(
        saveCalls[4],
        _SaveCall(
          WidgetDataKeys.sessionDuration,
          330, // 5 * 60 + 30
        ),
      );
    });

    test('updateWidgetState triggers widget update', () async {
      await service.updateWidgetState(
        vpnStatus: 'disconnected',
        serverName: '',
        uploadSpeed: 0,
        downloadSpeed: 0,
        sessionDuration: Duration.zero,
      );

      // updateWidget is called once by updateWidgetState (via triggerWidgetUpdate).
      expect(updateCallCount, 1);
    });

    test('triggerWidgetUpdate calls updateWidget', () async {
      await service.triggerWidgetUpdate();
      expect(updateCallCount, 1);
    });

    test('updateWidgetState handles save errors gracefully', () async {
      final errorService = WidgetBridgeService(
        saveWidgetData: <T>(String id, T? data) async {
          throw Exception('Save failed');
        },
        updateWidget: ({
          String? name,
          String? androidName,
          String? iOSName,
          String? qualifiedAndroidName,
        }) async {
          updateCallCount++;
          return true;
        },
      );

      // Should not throw.
      await errorService.updateWidgetState(
        vpnStatus: 'connected',
        serverName: 'Test',
        uploadSpeed: 0,
        downloadSpeed: 0,
        sessionDuration: Duration.zero,
      );

      // Update should NOT have been called because save threw.
      expect(updateCallCount, 0);
    });

    test('triggerWidgetUpdate handles errors gracefully', () async {
      final errorService = WidgetBridgeService(
        saveWidgetData: <T>(String id, T? data) async => true,
        updateWidget: ({
          String? name,
          String? androidName,
          String? iOSName,
          String? qualifiedAndroidName,
        }) async {
          throw Exception('Update failed');
        },
      );

      // Should not throw.
      await errorService.triggerWidgetUpdate();
    });
  });

  group('WidgetDataKeys', () {
    test('has correct key values', () {
      expect(WidgetDataKeys.vpnStatus, 'vpn_status');
      expect(WidgetDataKeys.serverName, 'server_name');
      expect(WidgetDataKeys.uploadSpeed, 'upload_speed');
      expect(WidgetDataKeys.downloadSpeed, 'download_speed');
      expect(WidgetDataKeys.sessionDuration, 'session_duration');
    });
  });

  group('WidgetIdentifiers', () {
    test('has correct identifiers', () {
      expect(WidgetIdentifiers.androidName, 'VPNWidgetProvider');
      expect(WidgetIdentifiers.iOSName, 'VPNWidget');
    });
  });
}

/// Simple record of a [HomeWidget.saveWidgetData] call for assertions.
class _SaveCall {
  _SaveCall(this.key, this.value);

  final String key;
  final Object? value;

  @override
  bool operator ==(Object other) =>
      other is _SaveCall && other.key == key && other.value == value;

  @override
  int get hashCode => Object.hash(key, value);

  @override
  String toString() => '_SaveCall($key, $value)';
}
