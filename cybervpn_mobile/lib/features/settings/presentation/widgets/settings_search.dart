import 'dart:async' show unawaited;

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';

/// A searchable setting item with keywords, display info, and navigation route.
class _SearchableSettingItem {
  const _SearchableSettingItem({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.route,
    required this.keywords,
  });

  final String title;
  final String subtitle;
  final IconData icon;
  final String route;
  final List<String> keywords;
}

/// Full-screen search overlay for finding settings across all screens.
///
/// Opens as a modal route with a search field and live-filtering list of
/// all settings items. Tapping a result navigates to the correct screen.
class SettingsSearchDelegate extends SearchDelegate<String?> {
  SettingsSearchDelegate(this.l10n);

  final AppLocalizations l10n;

  late final List<_SearchableSettingItem> _items = _buildIndex(l10n);

  static List<_SearchableSettingItem> _buildIndex(AppLocalizations l10n) {
    return [
      // -- Appearance --
      _SearchableSettingItem(
        title: l10n.settingsThemeModeLabel,
        subtitle: l10n.settingsAppearance,
        icon: Icons.palette_outlined,
        route: '/settings/appearance',
        keywords: [
          'theme',
          'dark',
          'light',
          'cyberpunk',
          'material you',
          'appearance',
        ],
      ),
      _SearchableSettingItem(
        title: l10n.settingsOledModeLabel,
        subtitle: l10n.settingsAppearance,
        icon: Icons.brightness_2_outlined,
        route: '/settings/appearance',
        keywords: ['oled', 'amoled', 'black', 'dark mode', 'pure black'],
      ),
      _SearchableSettingItem(
        title: l10n.settingsScanlineLabel,
        subtitle: l10n.settingsAppearance,
        icon: Icons.blur_linear_outlined,
        route: '/settings/appearance',
        keywords: ['scanline', 'crt', 'effect', 'overlay', 'cyberpunk'],
      ),

      // -- Language --
      _SearchableSettingItem(
        title: l10n.language,
        subtitle: l10n.settingsTitle,
        icon: Icons.language_outlined,
        route: '/settings/language',
        keywords: ['language', 'locale', 'translation', 'i18n'],
      ),

      // -- VPN --
      _SearchableSettingItem(
        title: l10n.settingsVpnProtocolLabel,
        subtitle: l10n.settingsVpn,
        icon: Icons.security_outlined,
        route: '/settings/vpn',
        keywords: ['protocol', 'vless', 'wireguard', 'ikev2', 'vpn'],
      ),
      _SearchableSettingItem(
        title: l10n.settingsAutoConnectLabel,
        subtitle: l10n.settingsVpn,
        icon: Icons.flash_on_outlined,
        route: '/settings/vpn',
        keywords: ['auto connect', 'startup', 'launch', 'automatic'],
      ),
      _SearchableSettingItem(
        title: l10n.settingsKillSwitchLabel,
        subtitle: l10n.settingsVpn,
        icon: Icons.block_outlined,
        route: '/settings/vpn',
        keywords: ['kill switch', 'leak', 'protection', 'disconnect'],
      ),
      _SearchableSettingItem(
        title: l10n.settingsSplitTunnelingLabel,
        subtitle: l10n.settingsVpn,
        icon: Icons.call_split_outlined,
        route: '/settings/vpn',
        keywords: ['split tunnel', 'bypass', 'apps', 'exclude'],
      ),
      _SearchableSettingItem(
        title: l10n.settingsDnsLabel,
        subtitle: l10n.settingsVpn,
        icon: Icons.dns_outlined,
        route: '/settings/vpn',
        keywords: ['dns', 'domain', 'nameserver', 'cloudflare', 'google'],
      ),
      _SearchableSettingItem(
        title: l10n.settingsMtuValueLabel,
        subtitle: l10n.settingsVpn,
        icon: Icons.tune_outlined,
        route: '/settings/vpn',
        keywords: ['mtu', 'packet', 'size', 'network'],
      ),
      _SearchableSettingItem(
        title: l10n.settingsTrustedNetworksTitle,
        subtitle: l10n.settingsVpn,
        icon: Icons.wifi_lock_outlined,
        route: '/settings/trusted-wifi',
        keywords: ['trusted', 'wifi', 'network', 'ssid', 'safe'],
      ),

      // -- Notifications --
      _SearchableSettingItem(
        title: l10n.settingsNotifications,
        subtitle: l10n.settingsTitle,
        icon: Icons.notifications_outlined,
        route: '/settings/notifications',
        keywords: ['notification', 'alerts', 'push', 'connection', 'expiry'],
      ),

      // -- Debug --
      _SearchableSettingItem(
        title: l10n.settingsDebug,
        subtitle: l10n.settingsTitle,
        icon: Icons.bug_report_outlined,
        route: '/settings/debug',
        keywords: ['debug', 'log', 'diagnostics', 'verbose', 'error'],
      ),
    ];
  }

  List<_SearchableSettingItem> _filterResults(String query) {
    if (query.isEmpty) return _items;
    final lower = query.toLowerCase();
    return _items.where((item) {
      return item.title.toLowerCase().contains(lower) ||
          item.subtitle.toLowerCase().contains(lower) ||
          item.keywords.any((kw) => kw.contains(lower));
    }).toList();
  }

  @override
  String get searchFieldLabel => l10n.settingsSearchHint;

  @override
  List<Widget> buildActions(BuildContext context) {
    return [
      if (query.isNotEmpty)
        IconButton(icon: const Icon(Icons.clear), onPressed: () => query = ''),
    ];
  }

  @override
  Widget? buildLeading(BuildContext context) {
    return IconButton(
      icon: Icon(
        Directionality.of(context) == TextDirection.rtl
            ? Icons.arrow_forward
            : Icons.arrow_back,
      ),
      onPressed: () => close(context, null),
    );
  }

  @override
  Widget buildResults(BuildContext context) => _buildList(context);

  @override
  Widget buildSuggestions(BuildContext context) => _buildList(context);

  Widget _buildList(BuildContext context) {
    final theme = Theme.of(context);
    final results = _filterResults(query);

    if (results.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.search_off,
              size: 48,
              color: theme.colorScheme.onSurfaceVariant,
            ),
            const SizedBox(height: Spacing.sm),
            Text(
              l10n.settingsNoLanguagesFound,
              style: theme.textTheme.bodyLarge?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      itemCount: results.length,
      itemBuilder: (context, index) {
        final item = results[index];
        return ListTile(
          leading: Icon(item.icon),
          title: Text(item.title),
          subtitle: Text(item.subtitle),
          onTap: () {
            close(context, null);
            unawaited(context.push(item.route));
          },
        );
      },
    );
  }
}
