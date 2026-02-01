import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/features/settings/presentation/widgets/settings_tile.dart';

void main() {
  Widget buildTestWidget(Widget child) {
    return MaterialApp(
      home: Scaffold(body: child),
    );
  }

  // ---------------------------------------------------------------------------
  // Navigation variant
  // ---------------------------------------------------------------------------

  group('SettingsTile.navigation', () {
    testWidgets('renders title and subtitle', (tester) async {
      await tester.pumpWidget(
        buildTestWidget(
          SettingsTile.navigation(
            title: 'Language',
            subtitle: 'English',
            onTap: () {},
          ),
        ),
      );

      expect(find.text('Language'), findsOneWidget);
      expect(find.text('English'), findsOneWidget);
    });

    testWidgets('shows chevron icon', (tester) async {
      await tester.pumpWidget(
        buildTestWidget(
          SettingsTile.navigation(
            title: 'Language',
            onTap: () {},
          ),
        ),
      );

      expect(find.byIcon(Icons.chevron_right), findsOneWidget);
    });

    testWidgets('triggers onTap when tapped', (tester) async {
      var tapped = false;

      await tester.pumpWidget(
        buildTestWidget(
          SettingsTile.navigation(
            title: 'Language',
            onTap: () => tapped = true,
          ),
        ),
      );

      await tester.tap(find.text('Language'));
      expect(tapped, isTrue);
    });

    testWidgets('renders without subtitle', (tester) async {
      await tester.pumpWidget(
        buildTestWidget(
          SettingsTile.navigation(
            title: 'Theme',
            onTap: () {},
          ),
        ),
      );

      expect(find.text('Theme'), findsOneWidget);
    });
  });

  // ---------------------------------------------------------------------------
  // Toggle variant
  // ---------------------------------------------------------------------------

  group('SettingsTile.toggle', () {
    testWidgets('renders Switch with initial value', (tester) async {
      await tester.pumpWidget(
        buildTestWidget(
          SettingsTile.toggle(
            title: 'Dark Mode',
            value: true,
            onChanged: (_) {},
          ),
        ),
      );

      expect(find.text('Dark Mode'), findsOneWidget);

      final switchWidget = tester.widget<Switch>(find.byType(Switch));
      expect(switchWidget.value, isTrue);
    });

    testWidgets('calls onChanged when Switch is toggled', (tester) async {
      bool? changedValue;

      await tester.pumpWidget(
        buildTestWidget(
          SettingsTile.toggle(
            title: 'Kill Switch',
            value: false,
            onChanged: (v) => changedValue = v,
          ),
        ),
      );

      await tester.tap(find.byType(Switch));
      expect(changedValue, isTrue);
    });

    testWidgets('calls onChanged when tile text is tapped', (tester) async {
      bool? changedValue;

      await tester.pumpWidget(
        buildTestWidget(
          SettingsTile.toggle(
            title: 'Auto Connect',
            value: false,
            onChanged: (v) => changedValue = v,
          ),
        ),
      );

      await tester.tap(find.text('Auto Connect'));
      expect(changedValue, isTrue);
    });

    testWidgets('Switch reflects false value', (tester) async {
      await tester.pumpWidget(
        buildTestWidget(
          SettingsTile.toggle(
            title: 'Feature',
            value: false,
            onChanged: (_) {},
          ),
        ),
      );

      final switchWidget = tester.widget<Switch>(find.byType(Switch));
      expect(switchWidget.value, isFalse);
    });
  });

  // ---------------------------------------------------------------------------
  // Radio variant
  // ---------------------------------------------------------------------------

  group('SettingsTile.radio', () {
    testWidgets('renders Radio selected when value matches groupValue',
        (tester) async {
      await tester.pumpWidget(
        buildTestWidget(
          SettingsTile.radio(
            title: 'VLESS-Reality',
            value: 'vless-reality',
            groupValue: 'vless-reality',
            onChanged: (_) {},
          ),
        ),
      );

      expect(find.text('VLESS-Reality'), findsOneWidget);

      // RadioGroup ancestor manages the groupValue; verify via RadioGroup
      final radioGroup =
          tester.widget<RadioGroup<dynamic>>(find.byType(RadioGroup<dynamic>));
      final radio = tester.widget<Radio<dynamic>>(find.byType(Radio<dynamic>));
      expect(radio.value, equals(radioGroup.groupValue));
    });

    testWidgets('renders Radio unselected when value differs from groupValue',
        (tester) async {
      await tester.pumpWidget(
        buildTestWidget(
          SettingsTile.radio(
            title: 'VLESS-WS',
            value: 'vless-ws',
            groupValue: 'auto',
            onChanged: (_) {},
          ),
        ),
      );

      final radioGroup =
          tester.widget<RadioGroup<dynamic>>(find.byType(RadioGroup<dynamic>));
      final radio = tester.widget<Radio<dynamic>>(find.byType(Radio<dynamic>));
      expect(radio.value, isNot(equals(radioGroup.groupValue)));
    });

    testWidgets('calls onChanged with value when tile is tapped',
        (tester) async {
      dynamic changedValue;

      await tester.pumpWidget(
        buildTestWidget(
          SettingsTile.radio(
            title: 'VLESS-Reality',
            value: 'vless-reality',
            groupValue: 'auto',
            onChanged: (v) => changedValue = v,
          ),
        ),
      );

      await tester.tap(find.text('VLESS-Reality'));
      expect(changedValue, equals('vless-reality'));
    });

    testWidgets('calls onChanged when Radio widget is tapped', (tester) async {
      dynamic changedValue;

      await tester.pumpWidget(
        buildTestWidget(
          SettingsTile.radio(
            title: 'Auto',
            value: 'auto',
            groupValue: 'vless-reality',
            onChanged: (v) => changedValue = v,
          ),
        ),
      );

      await tester.tap(find.byType(Radio<dynamic>));
      expect(changedValue, equals('auto'));
    });
  });
}
