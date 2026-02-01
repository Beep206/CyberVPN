import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/features/settings/presentation/widgets/settings_section.dart';

void main() {
  Widget buildTestWidget(Widget child) {
    return MaterialApp(
      home: Scaffold(body: child),
    );
  }

  group('SettingsSection', () {
    testWidgets('renders header text', (tester) async {
      await tester.pumpWidget(
        buildTestWidget(
          const SettingsSection(
            title: 'Appearance',
            children: [Text('Child 1')],
          ),
        ),
      );

      expect(find.text('Appearance'), findsOneWidget);
    });

    testWidgets('renders children below the header', (tester) async {
      await tester.pumpWidget(
        buildTestWidget(
          const SettingsSection(
            title: 'Connection',
            children: [
              Text('Child A'),
              Text('Child B'),
            ],
          ),
        ),
      );

      expect(find.text('Connection'), findsOneWidget);
      expect(find.text('Child A'), findsOneWidget);
      expect(find.text('Child B'), findsOneWidget);
    });

    testWidgets('applies primary color to header text', (tester) async {
      const primaryColor = Color(0xFF00FF88);

      await tester.pumpWidget(
        MaterialApp(
          theme: ThemeData(
            colorScheme: const ColorScheme.dark(primary: primaryColor),
          ),
          home: const Scaffold(
            body: SettingsSection(
              title: 'Theme Test',
              children: [Text('Child')],
            ),
          ),
        ),
      );

      final textWidget = tester.widget<Text>(find.text('Theme Test'));
      expect(textWidget.style?.color, equals(primaryColor));
    });
  });
}
