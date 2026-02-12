import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

/// Validates that key widgets don't overflow at extreme text scale factors.
///
/// These tests wrap widgets in a constrained box simulating a small phone
/// screen (320dp wide) at the maximum text scale (1.3x).
void main() {
  group('Text scale extremes (1.3x on 320dp width)', () {
    Widget buildScaled(Widget child) {
      return MaterialApp(
        home: MediaQuery(
          data: const MediaQueryData(
            size: Size(320, 568), // iPhone SE size
            textScaler: TextScaler.linear(1.3),
          ),
          child: Scaffold(body: child),
        ),
      );
    }

    testWidgets('Long button text wraps without overflow', (tester) async {
      await tester.pumpWidget(buildScaled(
        Center(
          child: FilledButton(
            onPressed: () {},
            child: const Text(
              'Connect to VPN Server',
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ),
      ));

      // If no overflow error is thrown, the test passes
      expect(tester.takeException(), isNull);
    });

    testWidgets('Row with two text items handles large text', (tester) async {
      await tester.pumpWidget(buildScaled(
        const Padding(
          padding: EdgeInsets.all(16),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  'Server Location',
                  style: TextStyle(fontSize: 16),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              SizedBox(width: 8),
              Flexible(
                child: Text(
                  'United States - New York',
                  style: TextStyle(fontSize: 14),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
        ),
      ));

      expect(tester.takeException(), isNull);
    });

    testWidgets('Card with multiple lines handles large text', (tester) async {
      await tester.pumpWidget(buildScaled(
        const Card(
          child: Padding(
            padding: EdgeInsets.all(16),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Subscription Active',
                  style: TextStyle(fontSize: 18),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                SizedBox(height: 8),
                Text(
                  'Premium Plan - 365 days remaining',
                  style: TextStyle(fontSize: 14),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
        ),
      ));

      expect(tester.takeException(), isNull);
    });
  });
}
