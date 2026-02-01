import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// Mixin that provides screenshot prevention functionality for sensitive screens.
///
/// Apply this mixin to the State class of screens that contain sensitive information
/// like login credentials, payment details, or personal data.
///
/// Example:
/// ```dart
/// class LoginScreenState extends State<LoginScreen> with ScreenProtection {
///   @override
///   void initState() {
///     super.initState();
///     enableProtection();
///   }
///
///   @override
///   void dispose() {
///     disableProtection();
///     super.dispose();
///   }
/// }
/// ```
mixin ScreenProtection<T extends StatefulWidget> on State<T> {
  static const MethodChannel _channel =
      MethodChannel('com.cybervpn.cybervpn_mobile/screen_protection');

  bool _isProtectionEnabled = false;

  /// Enables screenshot protection on the current screen.
  ///
  /// On Android: Sets FLAG_SECURE on the window.
  /// On iOS: Uses secure text field overlay technique.
  ///
  /// This should be called in initState() of screens that need protection.
  Future<void> enableProtection() async {
    if (_isProtectionEnabled) return;

    try {
      if (Platform.isAndroid || Platform.isIOS) {
        await _channel.invokeMethod('enableProtection');
        _isProtectionEnabled = true;
        if (kDebugMode) {
          print('[ScreenProtection] Protection enabled');
        }
      }
    } on PlatformException catch (e) {
      if (kDebugMode) {
        print('[ScreenProtection] Failed to enable protection: ${e.message}');
      }
    } catch (e) {
      if (kDebugMode) {
        print('[ScreenProtection] Unexpected error enabling protection: $e');
      }
    }
  }

  /// Disables screenshot protection on the current screen.
  ///
  /// On Android: Removes FLAG_SECURE from the window.
  /// On iOS: Removes the secure text field overlay.
  ///
  /// This should be called in dispose() to ensure protection is removed when
  /// navigating away from the screen.
  Future<void> disableProtection() async {
    if (!_isProtectionEnabled) return;

    try {
      if (Platform.isAndroid || Platform.isIOS) {
        await _channel.invokeMethod('disableProtection');
        _isProtectionEnabled = false;
        if (kDebugMode) {
          print('[ScreenProtection] Protection disabled');
        }
      }
    } on PlatformException catch (e) {
      if (kDebugMode) {
        print('[ScreenProtection] Failed to disable protection: ${e.message}');
      }
    } catch (e) {
      if (kDebugMode) {
        print('[ScreenProtection] Unexpected error disabling protection: $e');
      }
    }
  }

  /// Returns whether screenshot protection is currently enabled.
  bool get isProtectionEnabled => _isProtectionEnabled;
}
