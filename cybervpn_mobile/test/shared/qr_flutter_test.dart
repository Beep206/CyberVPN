import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:qr_flutter/qr_flutter.dart';

void main() {
  group('qr_flutter dependency verification', () {
    testWidgets('QrImageView renders without errors', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Center(
              child: QrImageView(
                data: 'https://cybervpn.com/test',
                version: QrVersions.auto,
                size: 200.0,
              ),
            ),
          ),
        ),
      );

      expect(find.byType(QrImageView), findsOneWidget);
    });

    testWidgets('QrImageView renders with custom styling', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Center(
              child: QrImageView(
                data: 'cybervpn://referral/abc123',
                version: QrVersions.auto,
                size: 150.0,
                eyeStyle: const QrEyeStyle(
                  eyeShape: QrEyeShape.square,
                  color: Colors.black,
                ),
                dataModuleStyle: const QrDataModuleStyle(
                  dataModuleShape: QrDataModuleShape.square,
                  color: Colors.black,
                ),
              ),
            ),
          ),
        ),
      );

      expect(find.byType(QrImageView), findsOneWidget);
    });
  });
}
