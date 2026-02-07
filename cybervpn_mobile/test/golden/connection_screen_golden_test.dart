import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:golden_toolkit/golden_toolkit.dart';

import '../helpers/test_app.dart';

void main() {
  group('ConnectionScreen golden tests', () {
    testGoldens('disconnected state renders correctly', (tester) async {
      await tester.pumpTestApp(
        const Scaffold(
          body: Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.shield_outlined, size: 80, color: Colors.grey),
                SizedBox(height: 16),
                Text('Disconnected',
                    style: TextStyle(fontSize: 24, color: Colors.grey)),
                SizedBox(height: 32),
                SizedBox(
                  width: 200,
                  height: 56,
                  child: ElevatedButton(
                    onPressed: null,
                    child: Text('Connect'),
                  ),
                ),
              ],
            ),
          ),
        ),
      );

      await screenMatchesGolden(tester, 'connection_disconnected');
    });

    testGoldens('connected state renders correctly', (tester) async {
      await tester.pumpTestApp(
        Scaffold(
          body: Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.shield, size: 80, color: Colors.green),
                const SizedBox(height: 16),
                const Text('Connected',
                    style: TextStyle(fontSize: 24, color: Colors.green)),
                const SizedBox(height: 8),
                Text('US East 1 - New York',
                    style: TextStyle(fontSize: 14, color: Colors.grey[600])),
                const SizedBox(height: 32),
                SizedBox(
                  width: 200,
                  height: 56,
                  child: ElevatedButton(
                    onPressed: () {},
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.red,
                    ),
                    child: const Text('Disconnect'),
                  ),
                ),
              ],
            ),
          ),
        ),
      );

      await screenMatchesGolden(tester, 'connection_connected');
    });
  });
}
