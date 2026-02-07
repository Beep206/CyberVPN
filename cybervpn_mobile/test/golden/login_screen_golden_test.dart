import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:golden_toolkit/golden_toolkit.dart';

import '../helpers/test_app.dart';

void main() {
  group('LoginScreen golden tests', () {
    testGoldens('login screen renders correctly in light mode',
        (tester) async {
      await tester.pumpTestApp(
        const Scaffold(
          body: Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.shield_outlined, size: 64),
                SizedBox(height: 16),
                Text('CyberVPN', style: TextStyle(fontSize: 32, fontWeight: FontWeight.bold)),
                SizedBox(height: 8),
                Text('Secure your connection'),
                SizedBox(height: 32),
                Padding(
                  padding: EdgeInsets.symmetric(horizontal: 24),
                  child: TextField(
                    decoration: InputDecoration(
                      labelText: 'Email',
                      prefixIcon: Icon(Icons.email_outlined),
                    ),
                  ),
                ),
                SizedBox(height: 16),
                Padding(
                  padding: EdgeInsets.symmetric(horizontal: 24),
                  child: TextField(
                    obscureText: true,
                    decoration: InputDecoration(
                      labelText: 'Password',
                      prefixIcon: Icon(Icons.lock_outlined),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
        themeMode: ThemeMode.light,
      );

      await screenMatchesGolden(tester, 'login_screen_light');
    });

    testGoldens('login screen renders correctly in dark mode', (tester) async {
      await tester.pumpTestApp(
        const Scaffold(
          body: Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.shield_outlined, size: 64),
                SizedBox(height: 16),
                Text('CyberVPN', style: TextStyle(fontSize: 32, fontWeight: FontWeight.bold)),
                SizedBox(height: 8),
                Text('Secure your connection'),
              ],
            ),
          ),
        ),
        themeMode: ThemeMode.dark,
      );

      await screenMatchesGolden(tester, 'login_screen_dark');
    });
  });
}
