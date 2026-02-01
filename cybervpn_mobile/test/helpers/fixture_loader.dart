import 'dart:convert';
import 'dart:io';

/// Loads and parses a JSON fixture file from `test/helpers/fixtures/`.
///
/// [name] is the filename without the directory path, e.g. `'user_fixture.json'`.
///
/// Returns the parsed JSON as a dynamic (typically [List] or [Map]).
///
/// Usage:
/// ```dart
/// final users = await loadFixture('user_fixture.json') as List<dynamic>;
/// ```
Future<dynamic> loadFixture(String name) async {
  final file = File('test/helpers/fixtures/$name');
  final content = await file.readAsString();
  return jsonDecode(content);
}

/// Synchronous version of [loadFixture].
///
/// Prefer the async version; use this only when async is inconvenient (e.g. in setUp).
dynamic loadFixtureSync(String name) {
  final file = File('test/helpers/fixtures/$name');
  final content = file.readAsStringSync();
  return jsonDecode(content);
}
