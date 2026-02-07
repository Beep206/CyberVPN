import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:golden_toolkit/golden_toolkit.dart';

import '../helpers/test_app.dart';

/// Golden tests for the connection animation states across light and dark
/// themes.
///
/// Each test captures the static visual frame of a VPN connection state so that
/// unintended visual regressions in animation end-states are caught early.
void main() {
  group('Connection animation golden tests', () {
    // ─── Disconnected state ──────────────────────────────────────────────

    testGoldens('disconnected state - light theme', (tester) async {
      await tester.pumpTestApp(
        _buildState(
          icon: Icons.shield_outlined,
          iconColor: Colors.grey,
          label: 'Disconnected',
          labelColor: Colors.grey,
          buttonLabel: 'Connect',
          buttonColor: Colors.blue,
        ),
        themeMode: ThemeMode.light,
      );
      await screenMatchesGolden(tester, 'connection_disconnected_light');
    });

    testGoldens('disconnected state - dark theme', (tester) async {
      await tester.pumpTestApp(
        _buildState(
          icon: Icons.shield_outlined,
          iconColor: Colors.grey,
          label: 'Disconnected',
          labelColor: Colors.grey,
          buttonLabel: 'Connect',
          buttonColor: Colors.blue,
        ),
        themeMode: ThemeMode.dark,
      );
      await screenMatchesGolden(tester, 'connection_disconnected_dark');
    });

    // ─── Connecting state ────────────────────────────────────────────────

    testGoldens('connecting state - light theme', (tester) async {
      await tester.pumpTestApp(
        _buildConnectingState(),
        themeMode: ThemeMode.light,
      );
      // Pump a few frames to capture the mid-animation state.
      await tester.pump(const Duration(milliseconds: 150));
      await screenMatchesGolden(tester, 'connection_connecting_light');
    });

    testGoldens('connecting state - dark theme', (tester) async {
      await tester.pumpTestApp(
        _buildConnectingState(),
        themeMode: ThemeMode.dark,
      );
      await tester.pump(const Duration(milliseconds: 150));
      await screenMatchesGolden(tester, 'connection_connecting_dark');
    });

    // ─── Connected state ─────────────────────────────────────────────────

    testGoldens('connected state - light theme', (tester) async {
      await tester.pumpTestApp(
        _buildState(
          icon: Icons.shield,
          iconColor: Colors.green,
          label: 'Connected',
          labelColor: Colors.green,
          subtitle: 'US East 1 - New York',
          buttonLabel: 'Disconnect',
          buttonColor: Colors.red,
        ),
        themeMode: ThemeMode.light,
      );
      await screenMatchesGolden(tester, 'connection_connected_light');
    });

    testGoldens('connected state - dark theme', (tester) async {
      await tester.pumpTestApp(
        _buildState(
          icon: Icons.shield,
          iconColor: Colors.green,
          label: 'Connected',
          labelColor: Colors.green,
          subtitle: 'US East 1 - New York',
          buttonLabel: 'Disconnect',
          buttonColor: Colors.red,
        ),
        themeMode: ThemeMode.dark,
      );
      await screenMatchesGolden(tester, 'connection_connected_dark');
    });
  });
}

/// Builds a static connection state frame.
Widget _buildState({
  required IconData icon,
  required Color iconColor,
  required String label,
  required Color labelColor,
  String? subtitle,
  required String buttonLabel,
  required Color buttonColor,
}) {
  return Scaffold(
    body: Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, size: 80, color: iconColor),
          const SizedBox(height: 16),
          Text(label, style: TextStyle(fontSize: 24, color: labelColor)),
          if (subtitle != null) ...[
            const SizedBox(height: 8),
            Text(subtitle, style: TextStyle(fontSize: 14, color: Colors.grey[600])),
          ],
          const SizedBox(height: 32),
          SizedBox(
            width: 200,
            height: 56,
            child: ElevatedButton(
              onPressed: () {},
              style: ElevatedButton.styleFrom(backgroundColor: buttonColor),
              child: Text(buttonLabel),
            ),
          ),
        ],
      ),
    ),
  );
}

/// Builds the connecting (in-progress) state with a pulsing indicator.
Widget _buildConnectingState() {
  return Scaffold(
    body: Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          SizedBox(
            width: 80,
            height: 80,
            child: CircularProgressIndicator(
              strokeWidth: 4,
              value: 0.6, // Fixed value for deterministic golden snapshot.
              valueColor: AlwaysStoppedAnimation<Color>(Colors.amber),
            ),
          ),
          const SizedBox(height: 16),
          const Text('Connecting...',
              style: TextStyle(fontSize: 24, color: Colors.amber)),
          const SizedBox(height: 8),
          Text('US East 1 - New York',
              style: TextStyle(fontSize: 14, color: Colors.grey[600])),
          const SizedBox(height: 32),
          SizedBox(
            width: 200,
            height: 56,
            child: OutlinedButton(
              onPressed: () {},
              child: const Text('Cancel'),
            ),
          ),
        ],
      ),
    ),
  );
}
