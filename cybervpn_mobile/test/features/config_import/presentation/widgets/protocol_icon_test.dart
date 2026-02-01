import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:flutter_test/flutter_test.dart';

/// Tests for protocol SVG icon assets
///
/// Verifies that all protocol icons (VLESS, VMess, Trojan, Shadowsocks)
/// are properly registered and can be loaded.
void main() {
  group('Protocol Icon Assets', () {
    testWidgets('VLESS protocol icon loads without error',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SvgPicture.asset(
              'assets/icons/protocol_vless.svg',
              width: 24,
              height: 24,
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Verify no exceptions were thrown during loading
      expect(tester.takeException(), isNull);
    });

    testWidgets('VMess protocol icon loads without error',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SvgPicture.asset(
              'assets/icons/protocol_vmess.svg',
              width: 24,
              height: 24,
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(tester.takeException(), isNull);
    });

    testWidgets('Trojan protocol icon loads without error',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SvgPicture.asset(
              'assets/icons/protocol_trojan.svg',
              width: 24,
              height: 24,
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(tester.takeException(), isNull);
    });

    testWidgets('Shadowsocks protocol icon loads without error',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SvgPicture.asset(
              'assets/icons/protocol_ss.svg',
              width: 24,
              height: 24,
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(tester.takeException(), isNull);
    });

    testWidgets('All protocol icons can be loaded together',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Row(
              children: [
                SvgPicture.asset('assets/icons/protocol_vless.svg',
                    width: 24, height: 24),
                SvgPicture.asset('assets/icons/protocol_vmess.svg',
                    width: 24, height: 24),
                SvgPicture.asset('assets/icons/protocol_trojan.svg',
                    width: 24, height: 24),
                SvgPicture.asset('assets/icons/protocol_ss.svg',
                    width: 24, height: 24),
              ],
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(tester.takeException(), isNull);

      // Verify all 4 SvgPicture widgets are rendered
      expect(find.byType(SvgPicture), findsNWidgets(4));
    });
  });
}
