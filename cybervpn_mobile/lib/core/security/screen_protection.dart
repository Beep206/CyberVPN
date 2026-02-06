import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'package:cybervpn_mobile/core/utils/app_logger.dart';

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
        AppLogger.debug(
          'Screen protection enabled',
          category: 'security.screen_protection',
        );
      }
    } on PlatformException catch (e) {
      AppLogger.warning(
        'Failed to enable screen protection',
        error: e,
        category: 'security.screen_protection',
      );
    } catch (e) {
      AppLogger.warning(
        'Unexpected error enabling screen protection',
        error: e,
        category: 'security.screen_protection',
      );
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
        AppLogger.debug(
          'Screen protection disabled',
          category: 'security.screen_protection',
        );
      }
    } on PlatformException catch (e) {
      AppLogger.warning(
        'Failed to disable screen protection',
        error: e,
        category: 'security.screen_protection',
      );
    } catch (e) {
      AppLogger.warning(
        'Unexpected error disabling screen protection',
        error: e,
        category: 'security.screen_protection',
      );
    }
  }

  /// Returns whether screenshot protection is currently enabled.
  bool get isProtectionEnabled => _isProtectionEnabled;
}
