import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/app/theme/cyberpunk_theme.dart';
import 'package:cybervpn_mobile/app/theme/tokens.dart';

void main() {
  // ── Dark theme ──────────────────────────────────────────────────────────

  group('cyberpunkDarkTheme', () {
    late ThemeData theme;

    setUp(() {
      theme = cyberpunkDarkTheme();
    });

    test('brightness is dark', () {
      expect(theme.brightness, Brightness.dark);
    });

    test('uses Material 3', () {
      expect(theme.useMaterial3, isTrue);
    });

    test('primary color is matrixGreen', () {
      expect(theme.colorScheme.primary, CyberColors.matrixGreen);
    });

    test('secondary color is neonCyan', () {
      expect(theme.colorScheme.secondary, CyberColors.neonCyan);
    });

    test('tertiary color is neonPink', () {
      expect(theme.colorScheme.tertiary, CyberColors.neonPink);
    });

    test('scaffold background is deepNavy', () {
      expect(theme.scaffoldBackgroundColor, CyberColors.deepNavy);
    });

    test('surface color is darkBg', () {
      expect(theme.colorScheme.surface, CyberColors.darkBg);
    });

    test('displayLarge uses Orbitron', () {
      expect(theme.textTheme.displayLarge?.fontFamily, 'Orbitron');
    });

    test('headlineLarge uses Orbitron', () {
      expect(theme.textTheme.headlineLarge?.fontFamily, 'Orbitron');
    });

    test('bodySmall uses JetBrains Mono', () {
      expect(theme.textTheme.bodySmall?.fontFamily, 'JetBrains Mono');
    });

    test('labelSmall uses JetBrains Mono', () {
      expect(theme.textTheme.labelSmall?.fontFamily, 'JetBrains Mono');
    });

    test('appBar background is deepNavy', () {
      expect(theme.appBarTheme.backgroundColor, CyberColors.deepNavy);
    });

    test('bottomNavigationBar selectedItemColor is matrixGreen', () {
      expect(
        theme.bottomNavigationBarTheme.selectedItemColor,
        CyberColors.matrixGreen,
      );
    });
  });

  // ── Light theme ─────────────────────────────────────────────────────────

  group('cyberpunkLightTheme', () {
    late ThemeData theme;

    setUp(() {
      theme = cyberpunkLightTheme();
    });

    test('brightness is light', () {
      expect(theme.brightness, Brightness.light);
    });

    test('uses Material 3', () {
      expect(theme.useMaterial3, isTrue);
    });

    test('primary color is matrixGreen', () {
      expect(theme.colorScheme.primary, CyberColors.matrixGreen);
    });

    test('secondary color is neonCyan', () {
      expect(theme.colorScheme.secondary, CyberColors.neonCyan);
    });

    test('tertiary color is neonPink', () {
      expect(theme.colorScheme.tertiary, CyberColors.neonPink);
    });

    test('scaffold background is light gray', () {
      expect(theme.scaffoldBackgroundColor, const Color(0xFFF8F9FA));
    });

    test('surface is white', () {
      expect(theme.colorScheme.surface, const Color(0xFFFFFFFF));
    });

    test('displayLarge uses Orbitron', () {
      expect(theme.textTheme.displayLarge?.fontFamily, 'Orbitron');
    });

    test('headlineLarge uses Orbitron', () {
      expect(theme.textTheme.headlineLarge?.fontFamily, 'Orbitron');
    });

    test('bodySmall uses JetBrains Mono', () {
      expect(theme.textTheme.bodySmall?.fontFamily, 'JetBrains Mono');
    });

    test('labelSmall uses JetBrains Mono', () {
      expect(theme.textTheme.labelSmall?.fontFamily, 'JetBrains Mono');
    });

    test('appBar background is white', () {
      expect(theme.appBarTheme.backgroundColor, const Color(0xFFFFFFFF));
    });

    test('bottomNavigationBar selectedItemColor is matrixGreen', () {
      expect(
        theme.bottomNavigationBarTheme.selectedItemColor,
        CyberColors.matrixGreen,
      );
    });
  });

  // ── Widget rendering ────────────────────────────────────────────────────

  group('Widget rendering with cyberpunk themes', () {
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

    testWidgets('dark theme renders without errors', (tester) async {
      await tester.pumpWidget(buildSampleScreen(cyberpunkDarkTheme()));
      expect(find.text('CyberVPN'), findsOneWidget);
      expect(find.text('Sample Card'), findsOneWidget);
      expect(find.text('Connect'), findsOneWidget);
    });

    testWidgets('light theme renders without errors', (tester) async {
      await tester.pumpWidget(buildSampleScreen(cyberpunkLightTheme()));
      expect(find.text('CyberVPN'), findsOneWidget);
      expect(find.text('Sample Card'), findsOneWidget);
      expect(find.text('Connect'), findsOneWidget);
    });
  });

  // ── Glow helpers ────────────────────────────────────────────────────────

  group('cyberpunkGlow helpers', () {
    test('cyberpunkGlow returns BoxShadow with correct defaults', () {
      final glow = cyberpunkGlow();
      expect(glow.blurRadius, 8.0);
      expect(glow.spreadRadius, 0.0);
      expect(
        (glow.color.a * 255.0).round().clamp(0, 255),
        (0.35 * 255).round(),
      );
    });

    test('cyberpunkGlowLight returns reduced-intensity BoxShadow', () {
      final glow = cyberpunkGlowLight();
      expect(glow.blurRadius, 4.0);
      expect(glow.spreadRadius, 0.0);
      expect(
        (glow.color.a * 255.0).round().clamp(0, 255),
        (0.15 * 255).round(),
      );
    });
  });
}
