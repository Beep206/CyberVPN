import 'package:cybervpn_mobile/app/theme/cyberpunk_theme.dart';
import 'package:cybervpn_mobile/shared/widgets/glitch_text.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('renders plain text when ticker mode is disabled', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: cyberpunkDarkTheme(),
        home: const TickerMode(
          enabled: false,
          child: Scaffold(
            body: Center(child: GlitchText(text: 'CYBER VPN')),
          ),
        ),
      ),
    );

    expect(find.text('CYBER VPN'), findsOneWidget);
  });

  testWidgets('renders glitch layers when ticker mode is enabled', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: cyberpunkDarkTheme(),
        home: const Scaffold(
          body: Center(child: GlitchText(text: 'CYBER VPN')),
        ),
      ),
    );
    await tester.pump(const Duration(milliseconds: 120));

    expect(find.text('CYBER VPN'), findsNWidgets(3));
  });
}
