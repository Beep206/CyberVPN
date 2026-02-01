import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:cybervpn_mobile/features/quick_actions/domain/services/quick_actions_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('QuickActionsService', () {
    late QuickActionsService service;

    setUp(() {
      // Set up method channel mock
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(
        const MethodChannel('plugins.flutter.io/quick_actions'),
        (MethodCall methodCall) async {
          if (methodCall.method == 'setShortcutItems') {
            return null;
          }
          if (methodCall.method == 'clearShortcutItems') {
            return null;
          }
          return null;
        },
      );

      service = QuickActionsService.instance;
    });

    tearDown(() {
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(
        const MethodChannel('plugins.flutter.io/quick_actions'),
        null,
      );
    });

    test('should have correct action type constants', () {
      expect(QuickActionsService.actionQuickConnect, 'quick_connect');
      expect(QuickActionsService.actionDisconnect, 'disconnect');
      expect(QuickActionsService.actionScanQr, 'scan_qr');
      expect(QuickActionsService.actionServers, 'servers');
    });

    test('should initialize without errors', () async {
      await service.initialize();
      // If we get here without throwing, the test passes
      expect(true, isTrue);
    });

    test('should update connection state without errors', () async {
      await service.updateForConnectionState(true);
      await service.updateForConnectionState(false);
      // If we get here without throwing, the test passes
      expect(true, isTrue);
    });
  });
}
