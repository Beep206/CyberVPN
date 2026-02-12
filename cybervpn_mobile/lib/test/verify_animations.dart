// ignore_for_file: avoid_print
import 'dart:convert';
import 'package:flutter/services.dart';

/// Standalone script to verify all Lottie animation assets can be loaded.
///
/// Run this script during development to ensure all animation files are valid
/// and accessible.
Future<void> verifyAnimations() async {
  final animations = [
    'assets/animations/onboarding_privacy.json',
    'assets/animations/onboarding_connect.json',
    'assets/animations/onboarding_globe.json',
    'assets/animations/connecting.json',
    'assets/animations/connected_success.json',
    'assets/animations/speed_test.json',
    'assets/animations/empty_state.json',
    'assets/animations/privacy.json',
    'assets/animations/connect.json',
    'assets/animations/globe.json',
    'assets/animations/get_started.json',
  ];

  print('Verifying ${animations.length} Lottie animations...\n');

  var successCount = 0;
  var failureCount = 0;

  for (final assetPath in animations) {
    try {
      final content = await rootBundle.loadString(assetPath);
      final jsonData = jsonDecode(content);

      // Basic validation - check for required Lottie properties
      if (jsonData is Map &&
          jsonData.containsKey('v') &&
          jsonData.containsKey('layers')) {
        final size = content.length;
        final sizeKB = (size / 1024).toStringAsFixed(2);
        print('✓ $assetPath ($sizeKB KB)');
        successCount++;
      } else {
        print('✗ $assetPath - Invalid Lottie format');
        failureCount++;
      }
    } catch (e) {
      print('✗ $assetPath - Error: $e');
      failureCount++;
    }
  }

  print('\n--- Results ---');
  print('Success: $successCount');
  print('Failed: $failureCount');
  print('Total: ${animations.length}');

  if (failureCount > 0) {
    throw Exception('Animation verification failed');
  }
}
