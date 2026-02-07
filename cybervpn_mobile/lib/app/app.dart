import 'dart:async';

import 'package:dynamic_color/dynamic_color.dart';
import 'package:flutter/foundation.dart';
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
import 'package:cybervpn_mobile/core/network/websocket_client.dart';
import 'package:cybervpn_mobile/core/network/websocket_provider.dart';
import 'package:cybervpn_mobile/core/services/fcm_topic_service.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/auth/domain/services/app_lock_service.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_provider.dart';
import 'package:cybervpn_mobile/features/notifications/presentation/providers/notification_provider.dart';
import 'package:cybervpn_mobile/features/notifications/presentation/widgets/in_app_banner.dart';

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
/// [MaterialApp.router] with go_router, theming (via [settingsProvider] with
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

              Widget appChild = _AppLifecycleManager(
                child: child ?? const SizedBox.shrink(),
              );

              // Add a prominent DEBUG banner in debug builds.
              if (kDebugMode) {
                appChild = Banner(
                  message: 'DEBUG',
                  location: BannerLocation.topStart,
                  color: Colors.red,
                  child: appChild,
                );
              }

              return Directionality(
                textDirection: textDirection,
                child: MediaQuery(
                  data: MediaQuery.of(context).copyWith(
                    textScaler: TextScaler.linear(scaleFactor),
                  ),
                  child: RepaintBoundary(child: appChild),
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
///
/// Uses [ConsumerStatefulWidget] with [WidgetsBindingObserver] so it can
/// observe app lifecycle events (foreground/background) and reconnect the
/// WebSocket when the app resumes.
class _AppLifecycleManager extends ConsumerStatefulWidget {
  const _AppLifecycleManager({required this.child});

  final Widget child;

  @override
  ConsumerState<_AppLifecycleManager> createState() =>
      _AppLifecycleManagerState();
}

class _AppLifecycleManagerState extends ConsumerState<_AppLifecycleManager>
    with WidgetsBindingObserver {
  /// Minimum interval between WebSocket reconnect attempts triggered by
  /// foreground transitions. Prevents rapid reconnects when the OS delivers
  /// multiple resumed events in quick succession.
  static const _reconnectDebounce = Duration(seconds: 5);

  /// Tracks the last time a foreground-triggered WebSocket reconnect was
  /// initiated so we can enforce [_reconnectDebounce].
  DateTime? _lastWsReconnectAttempt;

  /// Whether a force-disconnect dialog is currently being shown.
  /// Prevents stacking multiple dialogs if several events arrive in sequence.
  bool _isForceDisconnectDialogShowing = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _onAppResumed();
    }
  }

  /// Called when the app transitions from background to foreground.
  ///
  /// Attempts to reconnect the WebSocket if:
  /// 1. The user is authenticated.
  /// 2. The WebSocket is not already connected.
  /// 3. Enough time has elapsed since the last reconnect attempt (debounce).
  void _onAppResumed() {
    try {
      final isAuthenticated = ref.read(isAuthenticatedProvider);
      if (!isAuthenticated) {
        AppLogger.debug(
          'WebSocket foreground reconnect: user not authenticated, skipping',
          category: 'lifecycle.websocket',
        );
        return;
      }

      final client = ref.read(webSocketClientProvider);
      if (client.connectionState == WebSocketConnectionState.connected) {
        AppLogger.debug(
          'WebSocket foreground reconnect: already connected, skipping',
          category: 'lifecycle.websocket',
        );
        return;
      }

      // Debounce: skip if a reconnect was attempted very recently.
      final now = DateTime.now();
      if (_lastWsReconnectAttempt != null &&
          now.difference(_lastWsReconnectAttempt!) < _reconnectDebounce) {
        AppLogger.debug(
          'WebSocket foreground reconnect: debounced, skipping',
          category: 'lifecycle.websocket',
        );
        return;
      }

      _lastWsReconnectAttempt = now;
      AppLogger.info(
        'App resumed from background, reconnecting WebSocket',
        category: 'lifecycle.websocket',
      );
      unawaited(client.connect().catchError((Object e, StackTrace st) {
        AppLogger.warning(
          'WebSocket reconnect on foreground failed',
          error: e,
          stackTrace: st,
          category: 'lifecycle.websocket',
        );
      }));
    } catch (e, st) {
      AppLogger.error(
        'WebSocket foreground reconnect handler failed',
        error: e,
        stackTrace: st,
        category: 'lifecycle.websocket',
      );
    }
  }

  /// Shows an [AlertDialog] explaining that the VPN was force-disconnected.
  ///
  /// Uses l10n keys [forceDisconnectTitle] and [forceDisconnectMessage] for
  /// the dialog content, with [commonOk] for the dismiss button.
  void _showForceDisconnectDialog(ForceDisconnect event) {
    if (_isForceDisconnectDialogShowing) return;
    _isForceDisconnectDialogShowing = true;

    final l10n = AppLocalizations.of(context);

    unawaited(
      showDialog<void>(
        context: context,
        barrierDismissible: false,
        builder: (dialogContext) => AlertDialog(
          title: Text(l10n.forceDisconnectTitle),
          content: Text(
            event.reason.isNotEmpty
                ? '${l10n.forceDisconnectMessage}\n\n${event.reason}'
                : l10n.forceDisconnectMessage,
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: Text(l10n.commonOk),
            ),
          ],
        ),
      ).then((_) {
        _isForceDisconnectDialogShowing = false;
      }),
    );
  }

  @override
  Widget build(BuildContext context) {
    // Each _LifecycleWatcher is a separate Consumer that watches a single
    // provider. This prevents one provider change from rebuilding all others.
    return _LifecycleWatcher(
      name: 'quickActionsListener',
      watch: (ref) => ref.watch(quickActionsListenerProvider),
      child: _LifecycleWatcher(
        name: 'widgetStateListener',
        watch: (ref) => ref.watch(widgetStateListenerProvider),
        child: _LifecycleWatcher(
          name: 'widgetToggleHandler',
          watch: (ref) => ref.watch(widgetToggleHandlerProvider),
          child: _LifecycleWatcher(
            name: 'quickSettingsChannel',
            watch: (ref) => ref.watch(quickSettingsChannelProvider),
            child: _LifecycleWatcher(
              name: 'untrustedWifiHandler',
              watch: (ref) => ref.watch(untrustedWifiHandlerProvider),
              child: _LifecycleWatcher(
                name: 'fcmTopicSync',
                watch: (ref) => ref.watch(fcmTopicSyncProvider),
                child: _LifecycleWatcher(
                  name: 'notification',
                  watch: (ref) => ref.watch(notificationProvider),
                  child: _NotificationBannerListener(
                    child: _ForceDisconnectListener(
                      onForceDisconnect: _showForceDisconnectDialog,
                      child: _BiometricEnrollmentListener(
                        child: widget.child,
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Watches a single provider in isolation to prevent rebuild cascading.
class _LifecycleWatcher extends ConsumerWidget {
  const _LifecycleWatcher({
    required this.name,
    required this.watch,
    required this.child,
  });

  final String name;
  final void Function(WidgetRef ref) watch;
  final Widget child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    try {
      watch(ref);
    } catch (e, st) {
      AppLogger.error(
        '${name}Provider failed',
        category: 'lifecycle',
        error: e,
        stackTrace: st,
      );
    }
    return child;
  }
}

/// Listens to WebSocket NotificationReceived events and shows in-app banners.
class _NotificationBannerListener extends ConsumerWidget {
  const _NotificationBannerListener({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    try {
      ref.listen<AsyncValue<NotificationReceived>>(
        notificationEventsProvider,
        (_, next) {
          if (!next.hasValue) return;
          final event = next.value;
          if (event == null) return;

          final title = event.title.isNotEmpty ? event.title : AppLocalizations.of(context).notificationFallbackTitle;
          final body = event.body.isNotEmpty ? event.body : '';

          InAppBanner.show(
            context,
            BannerConfig(
              type: BannerNotificationType.info,
              title: title,
              message: body,
            ),
          );
        },
      );
    } catch (e, st) {
      AppLogger.error(
        'WebSocket notification banner listener failed',
        category: 'lifecycle',
        error: e,
        stackTrace: st,
      );
    }
    return child;
  }
}

/// Listens to WebSocket ForceDisconnect events and shows alert dialog.
class _ForceDisconnectListener extends ConsumerWidget {
  const _ForceDisconnectListener({
    required this.onForceDisconnect,
    required this.child,
  });

  final void Function(ForceDisconnect event) onForceDisconnect;
  final Widget child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    try {
      ref.listen<AsyncValue<ForceDisconnect>>(
        forceDisconnectEventsProvider,
        (_, next) {
          if (!next.hasValue) return;
          final event = next.value;
          if (event == null) return;

          AppLogger.warning(
            'ForceDisconnect event received: ${event.reason}',
            category: 'lifecycle.websocket',
          );
          onForceDisconnect(event);
        },
      );
    } catch (e, st) {
      AppLogger.error(
        'ForceDisconnect listener failed',
        category: 'lifecycle',
        error: e,
        stackTrace: st,
      );
    }
    return child;
  }
}

/// Listens to biometric enrollment changes and forces logout.
class _BiometricEnrollmentListener extends ConsumerWidget {
  const _BiometricEnrollmentListener({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    try {
      ref.listen(enrollmentChangeProvider, (_, next) {
        if (next.hasValue) {
          AppLogger.warning(
            'Biometric enrollment changed — forcing logout',
            category: 'lifecycle',
          );
          unawaited(ref.read(authProvider.notifier).logout());

          final messenger = ScaffoldMessenger.maybeOf(context);
          final l10n = AppLocalizations.of(context);
          messenger?.showSnackBar(
            SnackBar(
              content: Text(l10n.biometricDataChanged),
              duration: const Duration(seconds: 5),
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
