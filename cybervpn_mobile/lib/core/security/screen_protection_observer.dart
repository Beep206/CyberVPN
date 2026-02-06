import 'dart:io';
import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// List of protected route paths that require screenshot prevention.
///
/// These routes contain sensitive information like credentials, payment details,
/// or personal data that should not be captured in screenshots.
const Set<String> protectedRoutePaths = {
  '/login',
  '/register',
  '/profile/2fa',
  // Note: PurchaseScreen protection is handled by its ScreenProtection mixin
  // since it can be accessed via multiple routes or navigation methods.
};

/// NavigatorObserver that automatically enables/disables screenshot protection
/// based on navigation to sensitive screens.
///
/// This observer works alongside the [ScreenProtection] mixin to provide
/// defense-in-depth protection. Even if a screen forgets to call
/// enableProtection(), the observer will still protect it if the route
/// is listed in [protectedRoutePaths].
///
/// To use this observer with go_router, add it to the GoRouter's observers list:
/// ```dart
/// GoRouter(
///   observers: [ScreenProtectionObserver()],
///   routes: [...],
/// )
/// ```
class ScreenProtectionObserver extends NavigatorObserver {
  static const MethodChannel _channel =
      MethodChannel('com.cybervpn.cybervpn_mobile/screen_protection');

  bool _isProtectionEnabled = false;
  String? _currentRoutePath;

  /// Enables screenshot protection via platform channel.
  Future<void> _enableProtection() async {
    if (_isProtectionEnabled) return;

    try {
      if (Platform.isAndroid || Platform.isIOS) {
        await _channel.invokeMethod('enableProtection');
        _isProtectionEnabled = true;
        if (kDebugMode) {
          print('[ScreenProtectionObserver] Protection enabled for route: $_currentRoutePath');
        }
      }
    } on PlatformException catch (e) {
      if (kDebugMode) {
        print(
            '[ScreenProtectionObserver] Failed to enable protection: ${e.message}');
      }
    } catch (e) {
      if (kDebugMode) {
        print(
            '[ScreenProtectionObserver] Unexpected error enabling protection: $e');
      }
    }
  }

  /// Disables screenshot protection via platform channel.
  Future<void> _disableProtection() async {
    if (!_isProtectionEnabled) return;

    try {
      if (Platform.isAndroid || Platform.isIOS) {
        await _channel.invokeMethod('disableProtection');
        _isProtectionEnabled = false;
        if (kDebugMode) {
          print('[ScreenProtectionObserver] Protection disabled');
        }
      }
    } on PlatformException catch (e) {
      if (kDebugMode) {
        print(
            '[ScreenProtectionObserver] Failed to disable protection: ${e.message}');
      }
    } catch (e) {
      if (kDebugMode) {
        print(
            '[ScreenProtectionObserver] Unexpected error disabling protection: $e');
      }
    }
  }

  /// Extracts the route path from a Route's settings.
  String? _getRoutePath(Route<dynamic>? route) {
    if (route == null) return null;
    // For go_router, the route name is typically the path
    return route.settings.name;
  }

  /// Checks if the given route path should be protected.
  bool _shouldProtectRoute(String? routePath) {
    if (routePath == null) return false;
    return protectedRoutePaths.contains(routePath);
  }

  /// Updates protection state based on the current route.
  void _updateProtectionForRoute(String? routePath) {
    _currentRoutePath = routePath;
    if (_shouldProtectRoute(routePath)) {
      unawaited(_enableProtection());
    } else {
      unawaited(_disableProtection());
    }
  }

  @override
  void didPush(Route<dynamic> route, Route<dynamic>? previousRoute) {
    super.didPush(route, previousRoute);
    final routePath = _getRoutePath(route);
    _updateProtectionForRoute(routePath);
  }

  @override
  void didPop(Route<dynamic> route, Route<dynamic>? previousRoute) {
    super.didPop(route, previousRoute);
    final routePath = _getRoutePath(previousRoute);
    _updateProtectionForRoute(routePath);
  }

  @override
  void didReplace({Route<dynamic>? newRoute, Route<dynamic>? oldRoute}) {
    super.didReplace(newRoute: newRoute, oldRoute: oldRoute);
    final routePath = _getRoutePath(newRoute);
    _updateProtectionForRoute(routePath);
  }

  @override
  void didRemove(Route<dynamic> route, Route<dynamic>? previousRoute) {
    super.didRemove(route, previousRoute);
    final routePath = _getRoutePath(previousRoute);
    _updateProtectionForRoute(routePath);
  }
}
