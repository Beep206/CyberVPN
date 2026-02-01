import 'package:dynamic_color/dynamic_color.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/app/theme/dynamic_colors.dart';
import 'package:cybervpn_mobile/app/theme/theme_provider.dart';
import 'package:cybervpn_mobile/app/router/app_router.dart';
import 'package:cybervpn_mobile/core/l10n/locale_config.dart';
import 'package:cybervpn_mobile/features/config_import/presentation/widgets/clipboard_import_button.dart';
import 'package:cybervpn_mobile/features/quick_actions/domain/services/quick_actions_listener.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';

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
    // Initialize quick actions listener to watch VPN state changes.
    // This keeps the listener alive for the lifetime of the app.
    ref.watch(quickActionsListenerProvider);

    return DynamicColorBuilder(
      builder: (ColorScheme? lightDynamic, ColorScheme? darkDynamic) {
        // Push platform dynamic colors into the Riverpod state graph so that
        // currentThemeDataProvider rebuilds when the wallpaper changes.
        _syncDynamicColors(ref, lightDynamic, darkDynamic);

        // Watch the derived theme data pair which includes light, dark, and mode.
        final themePair = ref.watch(currentThemeDataProvider);

        // Watch the user's locale preference from settings.
        final localeCode = ref.watch(currentLocaleProvider);

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
