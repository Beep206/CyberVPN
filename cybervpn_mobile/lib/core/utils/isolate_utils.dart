import 'dart:convert';

import 'package:flutter/foundation.dart';

/// Utility functions for offloading heavy computation to isolates.
///
/// Uses [compute] to run JSON parsing and other CPU-intensive work
/// on a background isolate, preventing UI jank.
class IsolateUtils {
  const IsolateUtils._();

  /// Threshold in bytes above which JSON parsing is offloaded to an isolate.
  /// Below this threshold, inline parsing on the main isolate is faster
  /// due to isolate spawn overhead (~2-5ms).
  static const int _isolateThreshold = 50 * 1024; // 50 KB

  /// Parses a JSON string into a dynamic value, using a background isolate
  /// for large payloads (> 50 KB).
  ///
  /// For small payloads, parses inline to avoid isolate overhead.
  static Future<dynamic> parseJson(String jsonString) async {
    if (jsonString.length < _isolateThreshold) {
      return jsonDecode(jsonString);
    }
    return compute(_parseJsonIsolate, jsonString);
  }

  /// Encodes a value to a JSON string, using a background isolate
  /// for large objects.
  static Future<String> encodeJson(Object value) async {
    return compute(_encodeJsonIsolate, value);
  }

  /// Parses a JSON list string into a List<Map<String, dynamic>>,
  /// always using an isolate (intended for server list responses).
  static Future<List<Map<String, dynamic>>> parseJsonList(
      String jsonString) async {
    if (jsonString.length < _isolateThreshold) {
      final decoded = jsonDecode(jsonString);
      if (decoded is List) {
        return decoded.cast<Map<String, dynamic>>();
      }
      return [];
    }
    return compute(_parseJsonListIsolate, jsonString);
  }
}

// Top-level functions required by compute() (cannot be closures or methods).

dynamic _parseJsonIsolate(String jsonString) => jsonDecode(jsonString);

String _encodeJsonIsolate(Object value) => jsonEncode(value);

List<Map<String, dynamic>> _parseJsonListIsolate(String jsonString) {
  final decoded = jsonDecode(jsonString);
  if (decoded is List) {
    return decoded.cast<Map<String, dynamic>>();
  }
  return [];
}
