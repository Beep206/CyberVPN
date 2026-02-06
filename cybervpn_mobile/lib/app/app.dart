import 'dart:async';

import 'package:dynamic_color/dynamic_color.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/app/theme/dynamic_colors.dart';
import 'package:cybervpn_mobile/app/theme/theme_provider.dart';
import 'package:cybervpn_mobile/app/router/app_router.dart';
import 'package:cybervpn_mobile/core/l10n/locale_config.dart';
import 'package:cybervpn_mobile/features/config_import/presentation/widgets/clipboard_import_button.dart';
import 'package:cybervpn_mobile/core/platform/quick_settings_channel.dart';
import 'package:cybervpn_mobile/features/quick_actions/domain/services/quick_actions_listener.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/widgets/presentation/widget_state_listener.dart';
import 'package:cybervpn_mobile/features/widgets/data/widget_toggle_handler.dart';
import 'package:cybervpn_mobile/features/vpn/domain/usecases/untrusted_wifi_handler.dart';
import 'package:cybervpn_mobile/core/services/fcm_topic_service.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/auth/domain/services/app_lock_service.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_provider.dart';

/// Convert [TextScale] enum to a double scale factor.
double _textScaleToDouble(TextScale scale, double systemScale) {
  return switch (scale) {
    TextScale.system => systemScale,
    TextScale.small => 0.85,
    TextScale.normal => 1.0,
    TextScale.large => 1.15,
    TextScale.extraLarge => 1.3,
  };
}

/// Root application widget.
///
/// Uses [ConsumerWidget] to access Riverpod providers and configures
/// [MaterialApp.router] with go_router, theming (via [ThemeNotifier] with
/// persistence), and localization delegates.
///
/// Wraps the [MaterialApp] with [DynamicColorBuilder] so that on Android 12+
/// the user's wallpaper-derived palette is fed into the theme system
/// reactively.
class CyberVpnApp extends ConsumerWidget {
  const CyberVpnApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return DynamicColorBuilder(
      builder: (ColorScheme? lightDynamic, ColorScheme? darkDynamic) {
        // Push platform dynamic colors into the Riverpod state graph so that
        // currentThemeDataProvider rebuilds when the wallpaper changes.
        _syncDynamicColors(ref, lightDynamic, darkDynamic);

        // Watch the derived theme data pair which includes light, dark, and mode.
        final themePair = ref.watch(currentThemeDataProvider);

        // Watch the user's locale preference from settings.
        final localeCode = ref.watch(currentLocaleProvider);

        // Watch the text scale setting for accessibility.
        final textScale = ref.watch(currentTextScaleProvider);

        // Watch the router provider.
        final router = ref.watch(appRouterProvider);

        return ClipboardImportObserver(
          child: MaterialApp.router(
            // -- Router ---------------------------------------------------------
            routerConfig: router,

            // -- Appearance -----------------------------------------------------
            title: 'CyberVPN',
            debugShowCheckedModeBanner: false,
            theme: themePair.light,
            darkTheme: themePair.dark,
            themeMode: themePair.themeMode,

            // -- Locale ---------------------------------------------------------
            locale: LocaleConfig.localeFromCode(localeCode),

            // -- Localization ---------------------------------------------------
            localizationsDelegates: const [
              AppLocalizations.delegate,
              GlobalMaterialLocalizations.delegate,
              GlobalCupertinoLocalizations.delegate,
              GlobalWidgetsLocalizations.delegate,
            ],
            supportedLocales: AppLocalizations.supportedLocales,

            // -- Text Direction & Scale -----------------------------------------
            // Set text direction based on locale (RTL for Arabic, Hebrew, Farsi)
            // Apply custom text scale factor for accessibility
            builder: (context, child) {
              final textDirection = LocaleConfig.isRtl(localeCode)
                  ? TextDirection.rtl
                  : TextDirection.ltr;

              // Get the system text scale to use as fallback
              final systemTextScale = MediaQuery.textScalerOf(context).scale(1);
              final scaleFactor = _textScaleToDouble(textScale, systemTextScale);

              return Directionality(
                textDirection: textDirection,
                child: MediaQuery(
                  data: MediaQuery.of(context).copyWith(
                    textScaler: TextScaler.linear(scaleFactor),
                  ),
                  child: RepaintBoundary(
                    child: _AppLifecycleManager(
                      child: child ?? const SizedBox.shrink(),
                    ),
                  ),
                ),
              );
            },
          ),
        );
      },
    );
  }

  /// Synchronises the platform-provided dynamic color schemes with the
  /// [DynamicColorNotifier] so that downstream providers react to wallpaper
  /// changes on Android 12+.
  void _syncDynamicColors(
    WidgetRef ref,
    ColorScheme? lightDynamic,
    ColorScheme? darkDynamic,
  ) {
    // Use addPostFrameCallback to avoid modifying provider state during build.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref
          .read(dynamicColorProvider.notifier)
          .update(light: lightDynamic, dark: darkDynamic);
    });
  }
}

/// Watches all lifecycle providers that must stay alive for the duration of
/// the app.
///
/// Each [ref.watch] is wrapped in a try-catch so that a single provider
/// failure cannot block the entire widget tree from rendering. Errors are
/// reported through [AppLogger] for diagnostics.
///
/// Placed inside the [MaterialApp.router] builder so that it participates in
/// the widget tree beneath the router, receiving proper [BuildContext] with
/// localization, theme, and directionality already configured.
class _AppLifecycleManager extends ConsumerWidget {
  const _AppLifecycleManager({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Initialize quick actions listener to watch VPN state changes.
    try {
      ref.watch(quickActionsListenerProvider);
    } catch (e, st) {
      AppLogger.error(
        'quickActionsListenerProvider failed',
        category: 'lifecycle',
        error: e,
        stackTrace: st,
      );
    }

    // Initialize widget state listener to sync VPN state to home screen widgets.
    try {
      ref.watch(widgetStateListenerProvider);
    } catch (e, st) {
      AppLogger.error(
        'widgetStateListenerProvider failed',
        category: 'lifecycle',
        error: e,
        stackTrace: st,
      );
    }

    // Initialize widget toggle handler to respond to widget button taps.
    try {
      ref.watch(widgetToggleHandlerProvider);
    } catch (e, st) {
      AppLogger.error(
        'widgetToggleHandlerProvider failed',
        category: 'lifecycle',
        error: e,
        stackTrace: st,
      );
    }

    // Initialize Quick Settings channel for Android Quick Settings tile.
    try {
      ref.watch(quickSettingsChannelProvider);
    } catch (e, st) {
      AppLogger.error(
        'quickSettingsChannelProvider failed',
        category: 'lifecycle',
        error: e,
        stackTrace: st,
      );
    }

    // Initialize untrusted WiFi handler to auto-connect VPN when joining
    // untrusted networks (starts/stops based on user preference).
    try {
      ref.watch(untrustedWifiHandlerProvider);
    } catch (e, st) {
      AppLogger.error(
        'untrustedWifiHandlerProvider failed',
        category: 'lifecycle',
        error: e,
        stackTrace: st,
      );
    }

    // Sync FCM topic subscriptions when settings change.
    try {
      ref.watch(fcmTopicSyncProvider);
    } catch (e, st) {
      AppLogger.error(
        'fcmTopicSyncProvider failed',
        category: 'lifecycle',
        error: e,
        stackTrace: st,
      );
    }

    // Watch for biometric enrollment changes.
    // When enrollment changes (user added/removed fingerprint or face),
    // force logout and show a message explaining re-auth is needed.
    try {
      ref.listen(enrollmentChangeProvider, (_, next) {
        if (next.hasValue) {
          AppLogger.warning(
            'Biometric enrollment changed — forcing logout',
            category: 'lifecycle',
          );
          unawaited(ref.read(authProvider.notifier).logout());

          // Show a snackbar explaining why re-auth is needed
          final messenger = ScaffoldMessenger.maybeOf(context);
          messenger?.showSnackBar(
            const SnackBar(
              content: Text(
                'Your biometric data has changed. '
                'Please sign in again for security.',
              ),
              duration: Duration(seconds: 5),
            ),
          );
        }
      });
    } catch (e, st) {
      AppLogger.error(
        'enrollmentChangeProvider listener failed',
        category: 'lifecycle',
        error: e,
        stackTrace: st,
      );
    }

    return child;
  }
}
