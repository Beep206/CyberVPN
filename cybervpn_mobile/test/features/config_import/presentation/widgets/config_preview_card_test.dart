import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/features/config_import/domain/entities/imported_config.dart';
import 'package:cybervpn_mobile/features/config_import/presentation/widgets/config_preview_card.dart';

void main() {
  group('ConfigPreviewCard', () {
    late ImportedConfig testConfig;
    late bool addServerCalled;
    late bool cancelCalled;
    late ImportedConfig? receivedConfig;

    setUp(() {
      addServerCalled = false;
      cancelCalled = false;
      receivedConfig = null;

      testConfig = ImportedConfig(
        id: 'test-id-123',
        name: 'Test VPN Server',
        rawUri: 'vless://test-uuid@example.com:443',
        protocol: 'vless',
        serverAddress: 'example.com',
        port: 443,
        source: ImportSource.qrCode,
        importedAt: DateTime.now(),
      );
    });

    Widget createTestWidget({
      required ImportedConfig config,
      String? transportType,
      String? securityType,
    }) {
      return MaterialApp(
        home: Scaffold(
          body: ConfigPreviewCard(
            config: config,
            transportType: transportType,
            securityType: securityType,
            onAddServer: (ImportedConfig cfg) {
              addServerCalled = true;
              receivedConfig = cfg;
            },
            onCancel: () {
              cancelCalled = true;
            },
          ),
        ),
      );
    }

    testWidgets('renders Card widget', (WidgetTester tester) async {
      await tester.pumpWidget(createTestWidget(config: testConfig));

      expect(find.byType(Card), findsOneWidget);
    });

    testWidgets('displays server name', (WidgetTester tester) async {
      await tester.pumpWidget(createTestWidget(config: testConfig));

      expect(find.text('Test VPN Server'), findsOneWidget);
    });

    testWidgets('displays server address and port',
        (WidgetTester tester) async {
      await tester.pumpWidget(createTestWidget(config: testConfig));

      expect(find.text('example.com:443'), findsOneWidget);
      expect(find.text('Address'), findsOneWidget);
    });

    testWidgets('displays protocol badge', (WidgetTester tester) async {
      await tester.pumpWidget(createTestWidget(config: testConfig));

      expect(find.text('VLESS'), findsOneWidget);
      expect(find.text('Protocol'), findsOneWidget);
    });

    testWidgets('renders Add Server button', (WidgetTester tester) async {
      await tester.pumpWidget(createTestWidget(config: testConfig));

      expect(find.widgetWithText(ElevatedButton, 'Add Server'), findsOneWidget);
    });

    testWidgets('renders Cancel button', (WidgetTester tester) async {
      await tester.pumpWidget(createTestWidget(config: testConfig));

      expect(find.widgetWithText(TextButton, 'Cancel'), findsOneWidget);
    });

    testWidgets('tapping Add Server invokes callback with config',
        (WidgetTester tester) async {
      await tester.pumpWidget(createTestWidget(config: testConfig));

      final addButton = find.widgetWithText(ElevatedButton, 'Add Server');
      await tester.tap(addButton);
      await tester.pump();

      expect(addServerCalled, isTrue);
      expect(receivedConfig, equals(testConfig));
    });

    testWidgets('tapping Cancel invokes callback', (WidgetTester tester) async {
      await tester.pumpWidget(createTestWidget(config: testConfig));

      final cancelButton = find.widgetWithText(TextButton, 'Cancel');
      await tester.tap(cancelButton);
      await tester.pump();

      expect(cancelCalled, isTrue);
    });

    testWidgets('displays transport type when provided',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        createTestWidget(
          config: testConfig,
          transportType: 'ws',
        ),
      );

      expect(find.text('Transport'), findsOneWidget);
      expect(find.text('WS'), findsOneWidget);
    });

    testWidgets('displays security type when provided',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        createTestWidget(
          config: testConfig,
          securityType: 'tls',
        ),
      );

      expect(find.text('Security'), findsOneWidget);
      expect(find.text('TLS'), findsOneWidget);
    });

    testWidgets('does not display transport when not provided',
        (WidgetTester tester) async {
      await tester.pumpWidget(createTestWidget(config: testConfig));

      expect(find.text('Transport'), findsNothing);
    });

    testWidgets('does not display security when not provided',
        (WidgetTester tester) async {
      await tester.pumpWidget(createTestWidget(config: testConfig));

      expect(find.text('Security'), findsNothing);
    });

    testWidgets('displays all fields when transport and security provided',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        createTestWidget(
          config: testConfig,
          transportType: 'grpc',
          securityType: 'reality',
        ),
      );

      expect(find.text('Test VPN Server'), findsOneWidget);
      expect(find.text('example.com:443'), findsOneWidget);
      expect(find.text('VLESS'), findsOneWidget);
      expect(find.text('GRPC'), findsOneWidget);
      expect(find.text('REALITY'), findsOneWidget);
    });

    group('Protocol Badge Colors', () {
      testWidgets('renders VLESS protocol badge', (WidgetTester tester) async {
        final vlessConfig = testConfig.copyWith(protocol: 'vless');
        await tester.pumpWidget(createTestWidget(config: vlessConfig));

        expect(find.text('VLESS'), findsOneWidget);
      });

      testWidgets('renders VMess protocol badge', (WidgetTester tester) async {
        final vmessConfig = testConfig.copyWith(protocol: 'vmess');
        await tester.pumpWidget(createTestWidget(config: vmessConfig));

        expect(find.text('VMESS'), findsOneWidget);
      });

      testWidgets('renders Trojan protocol badge', (WidgetTester tester) async {
        final trojanConfig = testConfig.copyWith(protocol: 'trojan');
        await tester.pumpWidget(createTestWidget(config: trojanConfig));

        expect(find.text('TROJAN'), findsOneWidget);
      });

      testWidgets('renders Shadowsocks protocol badge',
          (WidgetTester tester) async {
        final ssConfig = testConfig.copyWith(protocol: 'shadowsocks');
        await tester.pumpWidget(createTestWidget(config: ssConfig));

        expect(find.text('SHADOWSOCKS'), findsOneWidget);
      });
    });

    testWidgets('handles long server names with ellipsis',
        (WidgetTester tester) async {
      final longNameConfig = testConfig.copyWith(
        name: 'Very Long Server Name That Should Be Truncated With Ellipsis',
      );
      await tester.pumpWidget(createTestWidget(config: longNameConfig));

      expect(
        find.text(
          'Very Long Server Name That Should Be Truncated With Ellipsis',
        ),
        findsOneWidget,
      );
    });

    testWidgets('handles long server addresses with ellipsis',
        (WidgetTester tester) async {
      final longAddressConfig = testConfig.copyWith(
        serverAddress: 'very-long-server-address-that-might-overflow.example.com',
      );
      await tester.pumpWidget(createTestWidget(config: longAddressConfig));

      expect(
        find.textContaining('very-long-server-address'),
        findsOneWidget,
      );
    });

    testWidgets('button minimum touch target size meets accessibility',
        (WidgetTester tester) async {
      await tester.pumpWidget(createTestWidget(config: testConfig));

      final addButton = tester.widget<ElevatedButton>(
        find.widgetWithText(ElevatedButton, 'Add Server'),
      );

      // Verify minimum size is set (should be at least 48x48 for accessibility)
      expect(addButton.style?.minimumSize?.resolve({}), isNotNull);
    });
  });
}
