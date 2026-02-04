import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:uni_links/uni_links.dart';
import 'package:url_launcher/url_launcher.dart';

/// Service for handling Telegram OAuth authentication via deep links.
///
/// ## Flow
/// 1. User taps "Sign in with Telegram"
/// 2. Opens Telegram app via `tg://resolve?domain=BOT_USERNAME&start=auth_TIMESTAMP`
/// 3. User approves auth in Telegram
/// 4. Telegram redirects back via `cybervpn://telegram-auth?tg_auth_result=...`
/// 5. App captures callback and sends to backend
///
/// ## Usage
/// ```dart
/// final service = TelegramOAuthService();
/// await service.init();
///
/// service.authResultStream.listen((result) {
///   if (result != null) {
///     // Send result.authData to backend
///   }
/// });
///
/// await service.startAuth();
/// ```
class TelegramOAuthService {
  /// Telegram bot username for CyberVPN OAuth.
  static const String botUsername = 'CyberVPNBot';

  /// URL scheme for receiving callbacks.
  static const String callbackScheme = 'cybervpn';

  /// Path for Telegram auth callbacks.
  static const String callbackPath = 'telegram-auth';

  /// Query parameter name for auth result.
  static const String authResultParam = 'tg_auth_result';

  StreamSubscription<String?>? _linkSubscription;
  final StreamController<TelegramAuthResult?> _authResultController =
      StreamController<TelegramAuthResult?>.broadcast();

  /// Stream of authentication results.
  ///
  /// Emits [TelegramAuthResult] when a valid callback is received.
  /// Emits `null` if the auth was cancelled or invalid.
  Stream<TelegramAuthResult?> get authResultStream =>
      _authResultController.stream;

  /// Whether the service has been initialized.
  bool _isInitialized = false;

  /// Initializes the service and starts listening for deep links.
  ///
  /// Must be called before [startAuth].
  Future<void> init() async {
    if (_isInitialized) return;

    // Handle deep link if app was launched with one
    try {
      final initialLink = await getInitialLink();
      if (initialLink != null) {
        _handleDeepLink(initialLink);
      }
    } catch (e) {
      debugPrint('TelegramOAuthService: Error getting initial link: $e');
    }

    // Listen for incoming deep links while app is running
    _linkSubscription = linkStream.listen(
      (String? link) {
        if (link != null) {
          _handleDeepLink(link);
        }
      },
      onError: (Object error) {
        debugPrint('TelegramOAuthService: Deep link stream error: $error');
        _authResultController.add(null);
      },
    );

    _isInitialized = true;
  }

  /// Starts the Telegram OAuth flow by opening the Telegram app.
  ///
  /// Returns `true` if Telegram app was launched successfully.
  /// Returns `false` if Telegram app is not installed or launch failed.
  ///
  /// When auth completes, the result will be emitted on [authResultStream].
  Future<TelegramAuthStartResult> startAuth() async {
    if (!_isInitialized) {
      await init();
    }

    // Generate timestamp for auth request tracking
    final timestamp = DateTime.now().millisecondsSinceEpoch;

    // Build Telegram deep link URL
    // Format: tg://resolve?domain=BOT_USERNAME&start=auth_TIMESTAMP
    final telegramUri = Uri(
      scheme: 'tg',
      host: 'resolve',
      queryParameters: {
        'domain': botUsername,
        'start': 'auth_$timestamp',
      },
    );

    // Try to launch Telegram app
    final canLaunch = await canLaunchUrl(telegramUri);
    if (!canLaunch) {
      return TelegramAuthStartResult.telegramNotInstalled;
    }

    try {
      final launched = await launchUrl(
        telegramUri,
        mode: LaunchMode.externalApplication,
      );

      if (!launched) {
        return TelegramAuthStartResult.launchFailed;
      }

      return TelegramAuthStartResult.launched;
    } catch (e) {
      debugPrint('TelegramOAuthService: Error launching Telegram: $e');
      return TelegramAuthStartResult.launchFailed;
    }
  }

  /// Opens the Telegram app store page for installation.
  ///
  /// Returns `true` if app store was opened successfully.
  Future<bool> openTelegramAppStore() async {
    // iOS App Store
    const iosStoreUrl = 'https://apps.apple.com/app/telegram-messenger/id686449807';
    // Google Play Store
    const androidStoreUrl = 'https://play.google.com/store/apps/details?id=org.telegram.messenger';

    final storeUri = Uri.parse(
      defaultTargetPlatform == TargetPlatform.iOS
          ? iosStoreUrl
          : androidStoreUrl,
    );

    try {
      return await launchUrl(
        storeUri,
        mode: LaunchMode.externalApplication,
      );
    } catch (e) {
      debugPrint('TelegramOAuthService: Error opening app store: $e');
      return false;
    }
  }

  /// Handles incoming deep links and parses Telegram auth callbacks.
  void _handleDeepLink(String link) {
    debugPrint('TelegramOAuthService: Received deep link: $link');

    try {
      final uri = Uri.parse(link);

      // Check if this is a Telegram auth callback
      if (uri.scheme != callbackScheme || uri.host != callbackPath) {
        debugPrint('TelegramOAuthService: Not a Telegram auth callback');
        return;
      }

      // Extract auth result
      final authData = uri.queryParameters[authResultParam];
      if (authData == null || authData.isEmpty) {
        debugPrint('TelegramOAuthService: Missing auth result parameter');
        _authResultController.add(null);
        return;
      }

      // Parse the auth result
      final result = _parseAuthResult(authData);
      _authResultController.add(result);
    } catch (e) {
      debugPrint('TelegramOAuthService: Error parsing deep link: $e');
      _authResultController.add(null);
    }
  }

  /// Parses the base64-encoded auth result from Telegram.
  TelegramAuthResult? _parseAuthResult(String authData) {
    try {
      // Auth data is base64-encoded JSON
      final decodedBytes = base64Decode(authData);
      final decodedString = utf8.decode(decodedBytes);
      final json = jsonDecode(decodedString) as Map<String, dynamic>;

      return TelegramAuthResult(
        authData: authData,
        id: json['id'] as int,
        firstName: json['first_name'] as String,
        lastName: json['last_name'] as String?,
        username: json['username'] as String?,
        photoUrl: json['photo_url'] as String?,
        authDate: json['auth_date'] != null
            ? DateTime.fromMillisecondsSinceEpoch(
                (json['auth_date'] as int) * 1000,
              )
            : null,
        hash: json['hash'] as String?,
      );
    } catch (e) {
      debugPrint('TelegramOAuthService: Error parsing auth result: $e');
      return null;
    }
  }

  /// Disposes the service and cleans up resources.
  ///
  /// Call this when the service is no longer needed.
  Future<void> dispose() async {
    await _linkSubscription?.cancel();
    await _authResultController.close();
    _isInitialized = false;
  }
}

/// Result of starting Telegram OAuth.
enum TelegramAuthStartResult {
  /// Telegram app was launched successfully.
  launched,

  /// Telegram app is not installed on the device.
  telegramNotInstalled,

  /// Failed to launch Telegram app.
  launchFailed,
}

/// Parsed result from Telegram OAuth callback.
class TelegramAuthResult {
  /// The raw base64-encoded auth data to send to backend.
  final String authData;

  /// Telegram user ID.
  final int id;

  /// User's first name.
  final String firstName;

  /// User's last name (optional).
  final String? lastName;

  /// Telegram username without @ (optional).
  final String? username;

  /// URL to user's profile photo (optional).
  final String? photoUrl;

  /// Timestamp when auth was performed.
  final DateTime? authDate;

  /// HMAC hash for verification (included in authData).
  final String? hash;

  const TelegramAuthResult({
    required this.authData,
    required this.id,
    required this.firstName,
    this.lastName,
    this.username,
    this.photoUrl,
    this.authDate,
    this.hash,
  });

  /// Full name (first + last).
  String get fullName {
    if (lastName != null && lastName!.isNotEmpty) {
      return '$firstName $lastName';
    }
    return firstName;
  }

  @override
  String toString() {
    return 'TelegramAuthResult(id: $id, name: $fullName, username: $username)';
  }
}
