import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import 'package:cybervpn_mobile/core/config/environment_config.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/widgets/settings_section.dart';
import 'package:cybervpn_mobile/features/settings/presentation/widgets/settings_tile.dart';
import 'package:cybervpn_mobile/shared/services/tooltip_preferences_service.dart';
import 'package:cybervpn_mobile/shared/widgets/feature_tooltip.dart';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/// Human-readable locale names keyed by locale code.
const _localeNames = <String, String>{
  'en': 'English',
  'ru': 'Russian',
  'uk': 'Ukrainian',
  'de': 'German',
  'fr': 'French',
  'es': 'Spanish',
  'pt': 'Portuguese',
  'it': 'Italian',
  'tr': 'Turkish',
  'ar': 'Arabic',
  'fa': 'Farsi',
  'zh': 'Chinese',
  'ja': 'Japanese',
  'ko': 'Korean',
};

// ---------------------------------------------------------------------------
// SettingsScreen
// ---------------------------------------------------------------------------

/// Main settings home screen displaying grouped sections.
///
/// Each section shows current values sourced from [settingsProvider] and
/// provides navigation to detail screens where applicable.
class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  /// Global key for the appearance tile to position the tooltip.
  final GlobalKey _appearanceTileKey = GlobalKey();

  /// Service to track shown tooltips.
  final TooltipPreferencesService _tooltipService = TooltipPreferencesService();

  @override
  void initState() {
    super.initState();
    // Show tooltip after first frame renders
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _showTooltipIfNeeded();
    });
  }

  Future<void> _showTooltipIfNeeded() async {
    const tooltipId = 'settings_cyberpunk_theme';
    final hasShown = await _tooltipService.hasShownTooltip(tooltipId);

    if (!hasShown && mounted) {
      FeatureTooltip.show(
        context: context,
        targetKey: _appearanceTileKey,
        message: 'Try our Cyberpunk theme!',
        position: TooltipPosition.bottom,
        onDismiss: () async {
          await _tooltipService.markTooltipAsShown(tooltipId);
        },
      );
    }
  }

  // ── Helpers ──────────────────────────────────────────────────────────────

  /// Launches a web URL in the default browser.
  Future<void> _launchUrl(String url) async {
    final uri = Uri.parse(url);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    } else {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Could not open URL'),
            duration: Duration(seconds: 2),
          ),
        );
      }
    }
  }

  /// Returns a human-readable label for the current [AppThemeMode].
  String _themeModeLabel(AppThemeMode mode) {
    return switch (mode) {
      AppThemeMode.materialYou => 'Material You',
      AppThemeMode.cyberpunk => 'Cyberpunk',
    };
  }

  /// Returns a human-readable label for the current [AppBrightness].
  String _brightnessLabel(AppBrightness brightness) {
    return switch (brightness) {
      AppBrightness.system => 'System',
      AppBrightness.light => 'Light',
      AppBrightness.dark => 'Dark',
    };
  }

  /// Returns a readable locale display name from a locale code.
  String _localeName(String code) {
    return _localeNames[code] ?? code;
  }

  /// Counts how many notification toggles are enabled.
  ///
  /// Security alerts are always on and not counted here since the user
  /// cannot disable them.
  int _enabledNotificationCount(AppSettings settings) {
    var count = 0;
    if (settings.notificationConnection) count++;
    if (settings.notificationExpiry) count++;
    if (settings.notificationPromotional) count++;
    if (settings.notificationReferral) count++;
    return count;
  }

  // ── Build ────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final asyncSettings = ref.watch(settingsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings'),
      ),
      body: asyncSettings.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _buildError(context, error),
        data: (settings) => _buildBody(context, settings),
      ),
    );
  }

  // ── Error state ──────────────────────────────────────────────────────────

  Widget _buildError(BuildContext context, Object error) {
    final theme = Theme.of(context);

    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.error_outline, size: 48, color: theme.colorScheme.error),
          const SizedBox(height: 12),
          Text('Failed to load settings', style: theme.textTheme.bodyLarge),
          const SizedBox(height: 8),
          FilledButton.tonal(
            onPressed: () => ref.invalidate(settingsProvider),
            child: const Text('Retry'),
          ),
        ],
      ),
    );
  }

  // ── Data state ───────────────────────────────────────────────────────────

  Widget _buildBody(BuildContext context, AppSettings settings) {
    return ListView(
      children: [
        // --- VPN Settings ---
        SettingsSection(
          title: 'VPN Settings',
          children: [
            SettingsTile.navigation(
              key: const Key('tile_vpn_settings'),
              title: 'VPN Settings',
              subtitle: _protocolLabel(settings.preferredProtocol),
              leading: const Icon(Icons.vpn_key_outlined),
              onTap: () => context.push('/settings/vpn'),
            ),
          ],
        ),

        // --- Appearance ---
        SettingsSection(
          title: 'Appearance',
          children: [
            SettingsTile.navigation(
              key: _appearanceTileKey,
              title: 'Appearance',
              subtitle:
                  '${_themeModeLabel(settings.themeMode)} / ${_brightnessLabel(settings.brightness)}',
              leading: const Icon(Icons.palette_outlined),
              onTap: () => context.push('/settings/appearance'),
            ),
          ],
        ),

        // --- Language ---
        SettingsSection(
          title: 'Language',
          children: [
            SettingsTile.navigation(
              key: const Key('tile_language'),
              title: 'Language',
              subtitle: _localeName(settings.locale),
              leading: const Icon(Icons.language_outlined),
              onTap: () => context.push('/settings/language'),
            ),
          ],
        ),

        // --- Notifications ---
        SettingsSection(
          title: 'Notifications',
          children: [
            SettingsTile.navigation(
              key: const Key('tile_notifications'),
              title: 'Notifications',
              subtitle:
                  '${_enabledNotificationCount(settings)} of 4 enabled',
              leading: const Icon(Icons.notifications_outlined),
              onTap: () => context.push('/settings/notifications'),
            ),
          ],
        ),

        // --- Account & Security ---
        SettingsSection(
          title: 'Account & Security',
          children: [
            SettingsTile.navigation(
              key: const Key('tile_account_security'),
              title: 'Account & Security',
              subtitle: 'Profile, password, 2FA',
              leading: const Icon(Icons.security_outlined),
              onTap: () => context.push('/profile'),
            ),
          ],
        ),

        // --- About ---
        SettingsSection(
          title: 'About',
          children: [
            const SettingsTile.info(
              key: Key('tile_about_version'),
              title: 'Version',
              subtitle: '1.0.0',
              leading: Icon(Icons.info_outline),
            ),
            SettingsTile.navigation(
              key: const Key('tile_about_licenses'),
              title: 'Open-source licenses',
              leading: const Icon(Icons.description_outlined),
              onTap: () => showLicensePage(
                context: context,
                applicationName: 'CyberVPN',
                applicationVersion: '1.0.0',
              ),
            ),
            SettingsTile.navigation(
              key: const Key('tile_about_privacy'),
              title: 'Privacy Policy',
              leading: const Icon(Icons.privacy_tip_outlined),
              onTap: () => _launchUrl(
                '${EnvironmentConfig.webBaseUrl}/privacy-policy',
              ),
            ),
            SettingsTile.navigation(
              key: const Key('tile_about_delete_account'),
              title: 'Delete Account',
              leading: const Icon(Icons.delete_forever_outlined),
              onTap: () => _launchUrl(
                '${EnvironmentConfig.webBaseUrl}/delete-account',
              ),
            ),
          ],
        ),

        // --- Debug & Diagnostics ---
        SettingsSection(
          title: 'Debug & Diagnostics',
          children: [
            SettingsTile.navigation(
              key: const Key('tile_debug'),
              title: 'Debug & About',
              subtitle: 'App version, logs, developer options',
              leading: const Icon(Icons.bug_report_outlined),
              onTap: () => context.push('/settings/debug'),
            ),
          ],
        ),

        // Bottom padding so content is not obscured by navigation bar.
        const SizedBox(height: 80),
      ],
    );
  }

  // ── Protocol label ───────────────────────────────────────────────────────

  /// Returns a human-readable label for the [PreferredProtocol].
  String _protocolLabel(PreferredProtocol protocol) {
    return switch (protocol) {
      PreferredProtocol.auto => 'Auto',
      PreferredProtocol.vlessReality => 'VLESS Reality',
      PreferredProtocol.vlessXhttp => 'VLESS XHTTP',
      PreferredProtocol.vlessWsTls => 'VLESS WS+TLS',
    };
  }
}
