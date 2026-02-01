import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/app/theme/material_you_theme.dart';
import 'package:cybervpn_mobile/app/theme/tokens.dart';

void main() {
  // ── Light theme ─────────────────────────────────────────────────────────

  group('materialYouLightTheme', () {
    late ThemeData theme;

    setUp(() {
      theme = materialYouLightTheme();
    });

    test('brightness is light', () {
      expect(theme.brightness, Brightness.light);
    });

    test('color scheme brightness is light', () {
      expect(theme.colorScheme.brightness, Brightness.light);
    });

    test('uses Material 3', () {
      expect(theme.useMaterial3, isTrue);
    });

    test('card border radius is 16 (Radii.lg)', () {
      final cardShape = theme.cardTheme.shape as RoundedRectangleBorder;
      final radius = cardShape.borderRadius as BorderRadius;
      expect(radius.topLeft.x, Radii.lg);
    });

    test('elevated button border radius is 12 (Radii.md)', () {
      final style = theme.elevatedButtonTheme.style!;
      final shape = style.shape!.resolve({}) as RoundedRectangleBorder;
      final radius = shape.borderRadius as BorderRadius;
      expect(radius.topLeft.x, Radii.md);
    });

    test('input decoration is filled', () {
      expect(theme.inputDecorationTheme.filled, isTrue);
    });

    test('input decoration border radius is 12 (Radii.md)', () {
      final border = theme.inputDecorationTheme.border as OutlineInputBorder;
      expect(border.borderRadius.topLeft.x, Radii.md);
    });

    test('appBar elevation is 0', () {
      expect(theme.appBarTheme.elevation, 0);
    });

    test('appBar is center-titled', () {
      expect(theme.appBarTheme.centerTitle, isTrue);
    });
  });

  // ── Dark theme ──────────────────────────────────────────────────────────

  group('materialYouDarkTheme', () {
    late ThemeData theme;

    setUp(() {
      theme = materialYouDarkTheme();
    });

    test('brightness is dark', () {
      expect(theme.brightness, Brightness.dark);
    });

    test('color scheme brightness is dark', () {
      expect(theme.colorScheme.brightness, Brightness.dark);
    });

    test('uses Material 3', () {
      expect(theme.useMaterial3, isTrue);
    });

    test('card border radius is 16 (Radii.lg)', () {
      final cardShape = theme.cardTheme.shape as RoundedRectangleBorder;
      final radius = cardShape.borderRadius as BorderRadius;
      expect(radius.topLeft.x, Radii.lg);
    });

    test('elevated button border radius is 12 (Radii.md)', () {
      final style = theme.elevatedButtonTheme.style!;
      final shape = style.shape!.resolve({}) as RoundedRectangleBorder;
      final radius = shape.borderRadius as BorderRadius;
      expect(radius.topLeft.x, Radii.md);
    });

    test('input decoration is filled', () {
      expect(theme.inputDecorationTheme.filled, isTrue);
    });

    test('input decoration border radius is 12 (Radii.md)', () {
      final border = theme.inputDecorationTheme.border as OutlineInputBorder;
      expect(border.borderRadius.topLeft.x, Radii.md);
    });
  });

  // ── Dynamic color override ────────────────────────────────────────────

  group('dynamic color override', () {
    test('light theme accepts custom ColorScheme', () {
      final customScheme = ColorScheme.fromSeed(
        seedColor: Colors.blue,
        brightness: Brightness.light,
      );
      final theme = materialYouLightTheme(dynamicColorScheme: customScheme);
      expect(theme.colorScheme.primary, customScheme.primary);
      expect(theme.colorScheme.brightness, Brightness.light);
    });

    test('dark theme accepts custom ColorScheme', () {
      final customScheme = ColorScheme.fromSeed(
        seedColor: Colors.blue,
        brightness: Brightness.dark,
      );
      final theme = materialYouDarkTheme(dynamicColorScheme: customScheme);
      expect(theme.colorScheme.primary, customScheme.primary);
      expect(theme.colorScheme.brightness, Brightness.dark);
    });

    test('light theme uses seed fallback when no dynamic scheme', () {
      final theme = materialYouLightTheme();
      final fallback = ColorScheme.fromSeed(
        seedColor: MaterialColors.seed,
        brightness: Brightness.light,
      );
      expect(theme.colorScheme.primary, fallback.primary);
    });

    test('dark theme uses seed fallback when no dynamic scheme', () {
      final theme = materialYouDarkTheme();
      final fallback = ColorScheme.fromSeed(
        seedColor: MaterialColors.seed,
        brightness: Brightness.dark,
      );
      expect(theme.colorScheme.primary, fallback.primary);
    });
  });

  // ── VPN state colors ──────────────────────────────────────────────────

  group('VpnStateColors extension', () {
    test('light scheme vpnConnected is green', () {
      final scheme = ColorScheme.fromSeed(
        seedColor: MaterialColors.seed,
        brightness: Brightness.light,
      );
      expect(scheme.vpnConnected, const Color(0xFF2E7D32));
    });

    test('dark scheme vpnConnected is green', () {
      final scheme = ColorScheme.fromSeed(
        seedColor: MaterialColors.seed,
        brightness: Brightness.dark,
      );
      expect(scheme.vpnConnected, const Color(0xFF66BB6A));
    });

    test('vpnDisconnected equals onSurfaceVariant', () {
      final scheme = ColorScheme.fromSeed(
        seedColor: MaterialColors.seed,
        brightness: Brightness.light,
      );
      expect(scheme.vpnDisconnected, scheme.onSurfaceVariant);
    });

    test('vpnError equals error color', () {
      final scheme = ColorScheme.fromSeed(
        seedColor: MaterialColors.seed,
        brightness: Brightness.light,
      );
      expect(scheme.vpnError, scheme.error);
    });
  });

  // ── Widget rendering ──────────────────────────────────────────────────

  group('Widget rendering with Material You themes', () {
    Widget buildSampleScreen(ThemeData theme) {
      return MaterialApp(
        theme: theme,
        home: Scaffold(
          appBar: AppBar(title: const Text('CyberVPN')),
          body: const Column(
            children: [
              Card(
                child: Padding(
                  padding: EdgeInsets.all(16),
                  child: Text('Sample Card'),
                ),
              ),
              TextField(decoration: InputDecoration(hintText: 'Input')),
              ElevatedButton(
                onPressed: null,
                child: Text('Connect'),
              ),
            ],
          ),
        ),
      );
    }

    testWidgets('light theme renders without errors', (tester) async {
      await tester.pumpWidget(buildSampleScreen(materialYouLightTheme()));
      expect(find.text('CyberVPN'), findsOneWidget);
      expect(find.text('Sample Card'), findsOneWidget);
      expect(find.text('Connect'), findsOneWidget);
    });

    testWidgets('dark theme renders without errors', (tester) async {
      await tester.pumpWidget(buildSampleScreen(materialYouDarkTheme()));
      expect(find.text('CyberVPN'), findsOneWidget);
      expect(find.text('Sample Card'), findsOneWidget);
      expect(find.text('Connect'), findsOneWidget);
    });
  });
}
