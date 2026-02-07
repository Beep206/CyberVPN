import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:golden_toolkit/golden_toolkit.dart';

import '../helpers/test_app.dart';

void main() {
  group('ServerList golden tests', () {
    testGoldens('server list renders correctly', (tester) async {
      await tester.pumpTestApp(
        Scaffold(
          appBar: AppBar(title: const Text('Servers')),
          body: ListView(
            children: [
              _buildServerTile('US East 1', 'New York', '45ms', true),
              _buildServerTile('DE Frankfurt', 'Frankfurt', '82ms', true),
              _buildServerTile('JP Tokyo', 'Tokyo', '120ms', false),
              _buildServerTile('NL Amsterdam', 'Amsterdam', '65ms', true),
            ],
          ),
        ),
      );

      await screenMatchesGolden(tester, 'server_list');
    });
  });
}

Widget _buildServerTile(String name, String city, String ping, bool available) {
  return ListTile(
    leading: Icon(
      Icons.dns,
      color: available ? Colors.green : Colors.red,
    ),
    title: Text(name),
    subtitle: Text(city),
    trailing: Text(
      ping,
      style: TextStyle(color: available ? Colors.green : Colors.grey),
    ),
  );
}
