import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/config/environment_config.dart';
import 'package:cybervpn_mobile/core/haptics/haptic_service.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/widgets/settings_section.dart';
import 'package:cybervpn_mobile/features/settings/presentation/widgets/settings_tile.dart';
import 'package:cybervpn_mobile/shared/services/tooltip_preferences_service.dart';
import 'package:cybervpn_mobile/shared/widgets/feature_tooltip.dart';
import 'package:cybervpn_mobile/features/settings/presentation/screens/appearance_screen.dart';
import 'package:cybervpn_mobile/features/settings/presentation/screens/debug_screen.dart';
import 'package:cybervpn_mobile/features/settings/presentation/screens/language_screen.dart';
import 'package:cybervpn_mobile/features/settings/presentation/screens/notification_prefs_screen.dart';
import 'package:cybervpn_mobile/features/settings/presentation/screens/vpn_settings_screen.dart';
import 'package:cybervpn_mobile/features/settings/presentation/widgets/settings_search.dart';
import 'package:cybervpn_mobile/shared/widgets/glitch_text.dart';
import 'package:cybervpn_mobile/shared/widgets/responsive_layout.dart';

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

/// Represents a settings detail page for the master-detail layout.
enum _SettingsDetail { vpn, appearance, language, notifications, account, debug }

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  /// Global key for the appearance tile to position the tooltip.
  final GlobalKey _appearanceTileKey = GlobalKey();

  /// Currently selected detail page for tablet layout.
  _SettingsDetail? _selectedDetail;

  /// Service to track shown tooltips.
  final TooltipPreferencesService _tooltipService = TooltipPreferencesService();

  @override
  void initState() {
    super.initState();
    // Show tooltip after first frame renders
    WidgetsBinding.instance.addPostFrameCallback((_) {
      unawaited(_showTooltipIfNeeded());
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
        // Trigger error haptic when URL cannot be opened.
        final haptics = ref.read(hapticServiceProvider);
        unawaited(haptics.error());

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(AppLocalizations.of(context).settingsCouldNotOpenUrl),
            duration: const Duration(seconds: 2),
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

  /// Whether we should use the wide layout (tablet / landscape).
  bool _isWide(BuildContext context) =>
      ResponsiveLayout.isAtLeastMediumOf(context);

  /// Navigate to a detail page: push on phone, select pane on tablet.
  void _navigateToDetail(BuildContext context, _SettingsDetail detail, String route) {
    if (_isWide(context)) {
      setState(() => _selectedDetail = detail);
    } else {
      unawaited(context.push(route));
    }
  }

  /// Builds the right-hand detail pane content for tablet layout.
  Widget _buildDetailPane(BuildContext context) {
    return switch (_selectedDetail) {
      _SettingsDetail.vpn => const VpnSettingsScreen(embedded: true),
      _SettingsDetail.appearance => const AppearanceScreen(embedded: true),
      _SettingsDetail.language => const LanguageScreen(embedded: true),
      _SettingsDetail.notifications => const NotificationPrefsScreen(embedded: true),
      _SettingsDetail.account => const _DetailPlaceholder(icon: Icons.security_outlined),
      _SettingsDetail.debug => const DebugScreen(embedded: true),
      null => Center(
          child: Text(
            AppLocalizations.of(context).settingsSelectCategory,
            style: Theme.of(context).textTheme.bodyLarge?.copyWith(
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
        ),
    };
  }

  @override
  Widget build(BuildContext context) {
    final asyncSettings = ref.watch(settingsProvider);
    final l10n = AppLocalizations.of(context);
    final isWide = _isWide(context);

    final body = asyncSettings.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, _) => _buildError(context, error),
      data: (settings) => _buildBody(context, settings),
    );

    Widget searchAction() => IconButton(
          icon: const Icon(Icons.search),
          tooltip: l10n.settingsSearchHint,
          onPressed: () => showSearch(
            context: context,
            delegate: SettingsSearchDelegate(l10n),
          ),
        );

    if (isWide) {
      return Scaffold(
        appBar: AppBar(
          title: GlitchText(
            text: l10n.settingsTitle,
            style: Theme.of(context).appBarTheme.titleTextStyle,
          ),
          actions: [searchAction()],
        ),
        body: Row(
          children: [
            SizedBox(width: 320, child: body),
            const VerticalDivider(thickness: 1, width: 1),
            Expanded(child: _buildDetailPane(context)),
          ],
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: GlitchText(
          text: l10n.settingsTitle,
          style: Theme.of(context).appBarTheme.titleTextStyle,
        ),
        actions: [searchAction()],
      ),
      body: body,
    );
  }

  // ── Error state ──────────────────────────────────────────────────────────

  Widget _buildError(BuildContext context, Object error) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);

    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.error_outline, size: 48, color: theme.colorScheme.error),
          const SizedBox(height: 12),
          Text(l10n.settingsLoadError, style: theme.textTheme.bodyLarge),
          const SizedBox(height: 8),
          FilledButton.tonal(
            onPressed: () => ref.invalidate(settingsProvider),
            child: Text(l10n.retry),
          ),
        ],
      ),
    );
  }

  // ── Data state ───────────────────────────────────────────────────────────

  Widget _buildBody(BuildContext context, AppSettings settings) {
    final l10n = AppLocalizations.of(context);

    return ListView(
      children: [
        // --- VPN Settings ---
        SettingsSection(
          title: l10n.settingsVpn,
          children: [
            SettingsTile.navigation(
              key: const Key('tile_vpn_settings'),
              title: l10n.settingsVpn,
              subtitle: _protocolLabel(settings.preferredProtocol),
              leading: const Icon(Icons.vpn_key_outlined),
              onTap: () => _navigateToDetail(context, _SettingsDetail.vpn, '/settings/vpn'),
            ),
          ],
        ),

        // --- Appearance ---
        SettingsSection(
          title: l10n.settingsAppearance,
          children: [
            SettingsTile.navigation(
              key: _appearanceTileKey,
              title: l10n.settingsAppearance,
              subtitle:
                  '${_themeModeLabel(settings.themeMode)} / ${_brightnessLabel(settings.brightness)}',
              leading: const Icon(Icons.palette_outlined),
              onTap: () => _navigateToDetail(context, _SettingsDetail.appearance, '/settings/appearance'),
            ),
          ],
        ),

        // --- Language ---
        SettingsSection(
          title: l10n.language,
          children: [
            SettingsTile.navigation(
              key: const Key('tile_language'),
              title: l10n.language,
              subtitle: _localeName(settings.locale),
              leading: const Icon(Icons.language_outlined),
              onTap: () => _navigateToDetail(context, _SettingsDetail.language, '/settings/language'),
            ),
          ],
        ),

        // --- Notifications ---
        SettingsSection(
          title: l10n.settingsNotifications,
          children: [
            SettingsTile.navigation(
              key: const Key('tile_notifications'),
              title: l10n.settingsNotifications,
              subtitle: l10n.settingsNotificationCountEnabled(
                  _enabledNotificationCount(settings)),
              leading: const Icon(Icons.notifications_outlined),
              onTap: () => _navigateToDetail(context, _SettingsDetail.notifications, '/settings/notifications'),
            ),
          ],
        ),

        // --- Account & Security ---
        SettingsSection(
          title: l10n.settingsAccountSecurity,
          children: [
            SettingsTile.navigation(
              key: const Key('tile_account_security'),
              title: l10n.settingsAccountSecurity,
              subtitle: l10n.settingsAccountSecuritySubtitle,
              leading: const Icon(Icons.security_outlined),
              onTap: () => context.push('/profile'),
            ),
          ],
        ),

        // --- About ---
        SettingsSection(
          title: l10n.settingsAbout,
          children: [
            SettingsTile.info(
              key: const Key('tile_about_version'),
              title: l10n.settingsVersionLabel,
              subtitle: '1.0.0',
              leading: const Icon(Icons.info_outline),
            ),
            SettingsTile.navigation(
              key: const Key('tile_about_licenses'),
              title: l10n.settingsOpenSourceLicenses,
              leading: const Icon(Icons.description_outlined),
              onTap: () => showLicensePage(
                context: context,
                applicationName: 'CyberVPN',
                applicationVersion: '1.0.0',
              ),
            ),
            SettingsTile.navigation(
              key: const Key('tile_about_privacy'),
              title: l10n.privacyPolicy,
              leading: const Icon(Icons.privacy_tip_outlined),
              onTap: () => _launchUrl(
                '${EnvironmentConfig.webBaseUrl}/privacy-policy',
              ),
            ),
            SettingsTile.navigation(
              key: const Key('tile_about_delete_account'),
              title: l10n.profileDeleteAccount,
              leading: const Icon(Icons.delete_forever_outlined),
              onTap: () => context.push('/profile/delete-account'),
            ),
          ],
        ),

        // --- Debug & Diagnostics ---
        SettingsSection(
          title: l10n.settingsDebugDiagnostics,
          children: [
            SettingsTile.navigation(
              key: const Key('tile_debug'),
              title: l10n.settingsDebugAbout,
              subtitle: l10n.settingsDebugAboutSubtitle,
              leading: const Icon(Icons.bug_report_outlined),
              onTap: () => _navigateToDetail(context, _SettingsDetail.debug, '/settings/debug'),
            ),
          ],
        ),

        // Bottom padding so content is not obscured by navigation bar.
        SizedBox(height: Spacing.navBarClearance(context)),
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

/// Placeholder widget shown in the detail pane when a full-screen navigation
/// target does not have an embeddable variant.
class _DetailPlaceholder extends StatelessWidget {
  final IconData icon;
  const _DetailPlaceholder({required this.icon});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Icon(icon, size: 48, color: Theme.of(context).colorScheme.outlineVariant),
    );
  }
}
