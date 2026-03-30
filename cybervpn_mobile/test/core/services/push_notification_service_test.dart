import 'package:cybervpn_mobile/core/services/push_notification_service.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('PushNotificationService', () {
    test('initialize exits cleanly when Firebase is not configured', () async {
      final service = PushNotificationService.instance;
      service.onNotificationTap = null;

      expect(Firebase.apps, isEmpty);

      await service.initialize();

      expect(service.token, isNull);
      expect(service.onNotificationTap, isNull);
    });
  });
}
