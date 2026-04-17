import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/di/providers.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/core/utils/data_formatters.dart';
import 'package:cybervpn_mobile/features/config_import/presentation/providers/config_import_provider.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/widgets/settings_section.dart';
import 'package:cybervpn_mobile/features/settings/presentation/widgets/settings_tile.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/di/profile_providers.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/vpn_profile.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/presentation/providers/profile_update_notifier.dart';

/// Subscription-related operational settings and entry points.
class SubscriptionSettingsScreen extends ConsumerStatefulWidget {
  const SubscriptionSettingsScreen({super.key, this.embedded = false});

  final bool embedded;

  @override
  ConsumerState<SubscriptionSettingsScreen> createState() =>
      _SubscriptionSettingsScreenState();
}

class _SubscriptionSettingsScreenState
    extends ConsumerState<SubscriptionSettingsScreen> {
  late final TextEditingController _userAgentController;
  late final FocusNode _userAgentFocusNode;

  bool? _providerProfilesExpanded;
  bool? _snapshotsExpanded;

  @override
  void initState() {
    super.initState();
    _userAgentController = TextEditingController();
    _userAgentFocusNode = FocusNode();
  }

  @override
  void dispose() {
    _userAgentController.dispose();
    _userAgentFocusNode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final importedConfigs = ref.watch(importedConfigsProvider);
    final subscriptionMetadata = ref.watch(subscriptionUrlMetadataProvider);
    final remoteProfilesAsync = ref.watch(profileListProvider);
    final updateState = ref.watch(profileUpdateNotifierProvider);
    final settings = ref.watch(settingsProvider).value ?? const AppSettings();
    final subscriptionSettings = ref.watch(subscriptionSettingsProvider);
    final policyRuntime = ref.watch(subscriptionPolicyRuntimeProvider);
    final policy = policyRuntime.resolve(settings);
    final remoteProfiles =
        remoteProfilesAsync.value?.whereType<RemoteVpnProfile>().toList(
          growable: false,
        ) ??
        const <RemoteVpnProfile>[];
    final isRefreshingAny =
        ref.watch(isImportingProvider) || updateState.isUpdating;

    if (!_userAgentFocusNode.hasFocus) {
      final nextText = settings.subscriptionUserAgentValue ?? '';
      if (_userAgentController.text != nextText) {
        _userAgentController.value = TextEditingValue(
          text: nextText,
          selection: TextSelection.collapsed(offset: nextText.length),
        );
      }
    }

    _providerProfilesExpanded ??= !subscriptionSettings.collapseSubscriptions;
    _snapshotsExpanded ??= !subscriptionSettings.collapseSubscriptions;

    final content = ListView(
      children: [
        SettingsSection(
          title: 'Summary',
          children: [
            SettingsTile.info(
              key: const Key('summary_effective_user_agent'),
              title: 'Effective User-Agent',
              subtitle: policy.effectiveUserAgent,
              leading: const Icon(Icons.badge_outlined),
            ),
            SettingsTile.info(
              title: 'Automation',
              subtitle: subscriptionSettings.autoUpdateEnabled
                  ? 'Every ${policy.autoUpdateInterval.inHours} hour(s) • ${subscriptionSettings.autoUpdateOnOpen ? 'refresh on open' : 'manual open only'}'
                  : 'Auto update disabled',
              leading: const Icon(Icons.schedule_outlined),
            ),
            SettingsTile.info(
              title: 'Startup Behavior',
              subtitle:
                  '${subscriptionSettings.pingOnOpenEnabled ? 'Ping on open enabled' : 'Ping on open disabled'} • Connect to ${_connectStrategyLabel(subscriptionSettings.connectStrategy)}',
              leading: const Icon(Icons.play_circle_outline),
            ),
            SettingsTile.info(
              title: 'Ordering',
              subtitle:
                  '${_sortModeLabel(subscriptionSettings.sortMode)} • ${subscriptionSettings.preventDuplicateImports ? 'dedupe on' : 'dedupe off'}',
              leading: const Icon(Icons.sort_outlined),
            ),
          ],
        ),
        SettingsSection(
          title: 'Automation',
          children: [
            SettingsTile.toggle(
              key: const Key('toggle_subscription_auto_update'),
              title: 'Automatic Subscription Updates',
              subtitle:
                  'Refresh subscription sources in the background using the global interval.',
              leading: const Icon(Icons.sync_outlined),
              value: subscriptionSettings.autoUpdateEnabled,
              onChanged: (dynamic value) => ref
                  .read(settingsProvider.notifier)
                  .updateSubscriptionSettings(autoUpdateEnabled: value as bool),
            ),
            _EnumDropdownTile<int>(
              key: const Key('dropdown_subscription_interval'),
              title: 'Auto-Update Interval',
              subtitle: 'Global interval used for on-open subscription refresh.',
              leading: const Icon(Icons.timer_outlined),
              value: subscriptionSettings.autoUpdateIntervalHours,
              items: const [1, 3, 6, 12, 24, 48, 72],
              labelBuilder: (value) => '$value hour(s)',
              onChanged: subscriptionSettings.autoUpdateEnabled
                  ? (value) => ref
                        .read(settingsProvider.notifier)
                        .updateSubscriptionSettings(
                          autoUpdateIntervalHours: value,
                        )
                  : null,
            ),
            SettingsTile.toggle(
              key: const Key('toggle_subscription_update_notifications'),
              title: 'Update Notifications',
              subtitle:
                  'Show a local notification after automatic refresh completes.',
              leading: const Icon(Icons.notifications_active_outlined),
              value: subscriptionSettings.updateNotificationsEnabled,
              onChanged: (dynamic value) => ref
                  .read(settingsProvider.notifier)
                  .updateSubscriptionSettings(
                    updateNotificationsEnabled: value as bool,
                  ),
            ),
            SettingsTile.toggle(
              key: const Key('toggle_subscription_auto_update_on_open'),
              title: 'Update on Open',
              subtitle: 'Apply due refreshes on app startup and resume.',
              leading: const Icon(Icons.open_in_browser_outlined),
              value: subscriptionSettings.autoUpdateOnOpen,
              onChanged: (dynamic value) => ref
                  .read(settingsProvider.notifier)
                  .updateSubscriptionSettings(autoUpdateOnOpen: value as bool),
            ),
            SettingsTile.toggle(
              key: const Key('toggle_subscription_ping_on_open'),
              title: 'Ping on Open',
              subtitle:
                  'Measure provider-profile latency and update stored ping ordering on open.',
              leading: const Icon(Icons.network_ping_outlined),
              value: subscriptionSettings.pingOnOpenEnabled,
              onChanged: (dynamic value) => ref
                  .read(settingsProvider.notifier)
                  .updateSubscriptionSettings(pingOnOpenEnabled: value as bool),
            ),
          ],
        ),
        SettingsSection(
          title: 'Behavior',
          children: [
            _EnumDropdownTile<SubscriptionConnectStrategy>(
              key: const Key('dropdown_subscription_connect_strategy'),
              title: 'Connect To',
              subtitle:
                  'Preferred server selection when subscription auto-connect is requested.',
              leading: const Icon(Icons.route_outlined),
              value: subscriptionSettings.connectStrategy,
              items: SubscriptionConnectStrategy.values,
              labelBuilder: _connectStrategyLabel,
              onChanged: (value) => ref
                  .read(settingsProvider.notifier)
                  .updateSubscriptionSettings(connectStrategy: value),
            ),
            SettingsTile.toggle(
              key: const Key('toggle_subscription_prevent_duplicates'),
              title: 'Prevent Duplicate Imports',
              subtitle:
                  'Deduplicate by raw URI when importing single links or subscription payloads.',
              leading: const Icon(Icons.content_copy_outlined),
              value: subscriptionSettings.preventDuplicateImports,
              onChanged: (dynamic value) => ref
                  .read(settingsProvider.notifier)
                  .updateSubscriptionSettings(
                    preventDuplicateImports: value as bool,
                  ),
            ),
            SettingsTile.toggle(
              key: const Key('toggle_subscription_collapse'),
              title: 'Collapse Subscription Sections',
              subtitle:
                  'Collapse provider-profile and snapshot sections by default.',
              leading: const Icon(Icons.unfold_less_outlined),
              value: subscriptionSettings.collapseSubscriptions,
              onChanged: (dynamic value) =>
                  _toggleCollapseSubscriptions(value as bool),
            ),
            SettingsTile.toggle(
              key: const Key('toggle_subscription_no_filter'),
              title: 'No Filter',
              subtitle: policyRuntime.describeNoFilter(policy),
              leading: const Icon(Icons.filter_alt_off_outlined),
              value: subscriptionSettings.noFilter,
              onChanged: (dynamic value) => ref
                  .read(settingsProvider.notifier)
                  .updateSubscriptionSettings(noFilter: value as bool),
            ),
            _EnumDropdownTile<SubscriptionSortMode>(
              key: const Key('dropdown_subscription_sort_mode'),
              title: 'Subscription Server Sorting',
              subtitle:
                  'Controls ordering inside provider-managed subscription profiles.',
              leading: const Icon(Icons.sort_by_alpha_outlined),
              value: subscriptionSettings.sortMode,
              items: SubscriptionSortMode.values,
              labelBuilder: _sortModeLabel,
              onChanged: (value) => ref
                  .read(settingsProvider.notifier)
                  .updateSubscriptionSettings(sortMode: value),
            ),
          ],
        ),
        SettingsSection(
          title: 'User-Agent',
          children: [
            _EnumDropdownTile<SubscriptionUserAgentMode>(
              key: const Key('dropdown_subscription_user_agent_mode'),
              title: 'User-Agent Mode',
              subtitle:
                  'Choose between the app default identity and a custom override.',
              leading: const Icon(Icons.fingerprint_outlined),
              value: subscriptionSettings.userAgentMode,
              items: SubscriptionUserAgentMode.values,
              labelBuilder: (value) => switch (value) {
                SubscriptionUserAgentMode.appDefault => 'App Default',
                SubscriptionUserAgentMode.custom => 'Custom',
              },
              onChanged: (value) async {
                await ref
                    .read(settingsProvider.notifier)
                    .updateSubscriptionUserAgent(
                      mode: value,
                      value: _userAgentController.text,
                    );
                if (!mounted) return;
                setState(() {});
              },
            ),
            if (subscriptionSettings.userAgentMode ==
                SubscriptionUserAgentMode.custom)
              Padding(
                padding: const EdgeInsets.fromLTRB(
                  Spacing.md,
                  Spacing.sm,
                  Spacing.md,
                  Spacing.sm,
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    TextField(
                      key: const Key('field_subscription_user_agent'),
                      controller: _userAgentController,
                      focusNode: _userAgentFocusNode,
                      decoration: const InputDecoration(
                        labelText: 'Custom User-Agent',
                        hintText: 'CyberVPN/1.0',
                      ),
                    ),
                    const SizedBox(height: Spacing.sm),
                    Wrap(
                      spacing: Spacing.sm,
                      runSpacing: Spacing.sm,
                      children: [
                        FilledButton.tonalIcon(
                          key: const Key('button_save_subscription_user_agent'),
                          onPressed: _saveCustomUserAgent,
                          icon: const Icon(Icons.save_outlined),
                          label: const Text('Save'),
                        ),
                        OutlinedButton.icon(
                          key: const Key('button_reset_subscription_user_agent'),
                          onPressed: _resetUserAgentOverride,
                          icon: const Icon(Icons.restart_alt_outlined),
                          label: const Text('Reset to Default'),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            SettingsTile.info(
              title: 'Effective Request Header',
              subtitle: policy.effectiveUserAgent,
              leading: const Icon(Icons.http_outlined),
            ),
          ],
        ),
        SettingsSection(
          title: 'Import Sources',
          children: [
            SettingsTile.navigation(
              key: const Key('nav_subscription_import_list'),
              title: 'Imported Configurations',
              subtitle: importedConfigs.isEmpty
                  ? 'Manage QR, clipboard, and manual imports in one place'
                  : '${importedConfigs.length} imported config(s) available',
              leading: const Icon(Icons.download_outlined),
              onTap: () => context.push('/config-import'),
            ),
            SettingsTile.navigation(
              key: const Key('nav_subscription_add_url'),
              title: 'Add Subscription URL',
              subtitle: remoteProfiles.isEmpty
                  ? 'Create a provider-managed profile from a URL'
                  : '${remoteProfiles.length} provider profile(s) tracked',
              leading: const Icon(Icons.link_outlined),
              onTap: () => context.push('/profiles/add/url'),
            ),
            SettingsTile.navigation(
              key: const Key('nav_subscription_qr_scanner'),
              title: 'Scan QR Code',
              subtitle:
                  'Open the QR scanner without leaving the subscription area',
              leading: const Icon(Icons.qr_code_scanner_outlined),
              onTap: () => context.push('/config-import/qr-scanner'),
            ),
          ],
        ),
        SettingsSection(
          title: 'Provider Profiles',
          children: [
            ListTile(
              key: const Key('toggle_provider_profiles_section'),
              leading: const Icon(Icons.folder_special_outlined),
              title: const Text('Provider Profiles'),
              subtitle: Text(
                remoteProfiles.isEmpty
                    ? 'No provider-managed profiles imported yet.'
                    : '${remoteProfiles.length} provider profile(s) ready for refresh and support actions.',
              ),
              trailing: Icon(
                _providerProfilesExpanded == true
                    ? Icons.expand_less
                    : Icons.expand_more,
              ),
              onTap: () => setState(() {
                _providerProfilesExpanded = !(_providerProfilesExpanded ?? true);
              }),
            ),
            if (_providerProfilesExpanded == true) ...[
              Padding(
                padding: const EdgeInsets.fromLTRB(
                  Spacing.md,
                  Spacing.sm,
                  Spacing.md,
                  Spacing.sm,
                ),
                child: Row(
                  children: [
                    const Expanded(
                      child: Text(
                        'Manual refresh ignores due checks and uses the current User-Agent policy.',
                      ),
                    ),
                    FilledButton.tonalIcon(
                      key: const Key('button_refresh_all_subscriptions'),
                      onPressed: isRefreshingAny
                          ? null
                          : () => _refreshAllSources(remoteProfiles),
                      icon: isRefreshingAny
                          ? const SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.refresh),
                      label: const Text('Refresh All'),
                    ),
                  ],
                ),
              ),
              if (remoteProfilesAsync.isLoading)
                const ListTile(
                  title: Text('Loading provider profiles...'),
                  subtitle: Text(
                    'Reading provider-managed subscriptions from the profile store.',
                  ),
                )
              else if (remoteProfilesAsync.hasError)
                const ListTile(
                  title: Text('Failed to load provider profiles'),
                  subtitle: Text(
                    'The billing and import entry points still work, but provider profile metadata is unavailable.',
                  ),
                )
              else if (remoteProfiles.isEmpty)
                const ListTile(
                  title: Text('No provider-managed profiles'),
                  subtitle: Text(
                    'Add a subscription URL to create a refreshable provider profile with metadata and support links.',
                  ),
                )
              else
                for (final profile in remoteProfiles)
                  _RemoteSubscriptionCard(
                    profile: profile,
                    isRefreshing:
                        updateState.isUpdating ||
                        updateState.updatingProfileId == profile.id,
                    onRefresh: () => _refreshSingleProfile(profile.id),
                    onOpenSupport: profile.supportUrl == null
                        ? null
                        : () => _launchExternalUrl(profile.supportUrl!),
                    onOpenProviderPage: profile.testUrl == null
                        ? null
                        : () => _launchExternalUrl(profile.testUrl!),
                  ),
            ],
          ],
        ),
        SettingsSection(
          title: 'Imported Subscription Snapshots',
          children: [
            ListTile(
              key: const Key('toggle_subscription_snapshots_section'),
              leading: const Icon(Icons.cloud_sync_outlined),
              title: const Text('Imported Subscription Snapshots'),
              subtitle: Text(
                subscriptionMetadata.isEmpty
                    ? 'No imported subscription snapshots yet.'
                    : '${subscriptionMetadata.length} imported source(s) tracked.',
              ),
              trailing: Icon(
                _snapshotsExpanded == true
                    ? Icons.expand_less
                    : Icons.expand_more,
              ),
              onTap: () => setState(() {
                _snapshotsExpanded = !(_snapshotsExpanded ?? true);
              }),
            ),
            if (_snapshotsExpanded == true)
              if (subscriptionMetadata.isEmpty)
                const ListTile(
                  title: Text('No imported subscription snapshots yet'),
                  subtitle: Text(
                    'Imported subscription URLs appear here with server counts and last refresh timestamps.',
                  ),
                )
              else
                for (final metadata in subscriptionMetadata)
                  SettingsTile.info(
                    key: Key('subscription_source_${metadata.url}'),
                    title: metadata.url,
                    subtitle:
                        '${metadata.serverCount} server(s) • updated ${_formatTimestamp(metadata.lastUpdated)}',
                    leading: const Icon(Icons.cloud_outlined),
                  ),
          ],
        ),
        SettingsSection(
          title: 'Billing',
          children: [
            SettingsTile.navigation(
              key: const Key('nav_subscription_plans'),
              title: 'Plans & Upgrades',
              subtitle: 'Open the purchase and upgrade flow',
              leading: const Icon(Icons.workspace_premium_outlined),
              onTap: () => context.push('/subscribe'),
            ),
            SettingsTile.navigation(
              key: const Key('nav_subscription_payment_history'),
              title: 'Payment History',
              subtitle: 'View completed purchases and invoices',
              leading: const Icon(Icons.receipt_long_outlined),
              onTap: () => context.push('/payment-history'),
            ),
          ],
        ),
        const Padding(
          padding: EdgeInsets.fromLTRB(
            Spacing.md,
            Spacing.sm,
            Spacing.md,
            Spacing.lg,
          ),
          child: _InfoNotice(
            message:
                'Phase 10 makes subscriptions policy-driven: User-Agent, dedupe, sorting, startup refresh and ping-on-open now use one effective runtime contract.',
          ),
        ),
        SizedBox(height: Spacing.navBarClearance(context)),
      ],
    );

    if (widget.embedded) {
      return content;
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Subscriptions')),
      body: content,
    );
  }

  Future<void> _refreshAllSources(List<RemoteVpnProfile> remoteProfiles) async {
    final refreshedImported = await ref
        .read(configImportProvider.notifier)
        .refreshSubscriptions();
    final result = await ref
        .read(profileUpdateNotifierProvider.notifier)
        .refreshProfilesNow(remoteProfiles.map((profile) => profile.id));

    if (!mounted) return;

    final updatedProfiles = switch (result) {
      Success(:final data) => data,
      Failure() => 0,
    };

    final message = remoteProfiles.isEmpty && refreshedImported == 0
        ? 'No subscription sources to refresh.'
        : 'Refreshed $updatedProfiles provider profile(s) and $refreshedImported imported source(s).';

    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _refreshSingleProfile(String profileId) async {
    final result = await ref
        .read(profileUpdateNotifierProvider.notifier)
        .updateSingle(profileId);

    if (!mounted) return;

    final message = switch (result) {
      Success() => 'Provider profile refreshed.',
      Failure(:final failure) => failure.message,
    };

    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _saveCustomUserAgent() async {
    final value = _userAgentController.text.trim();
    if (value.isEmpty) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Custom User-Agent cannot be empty.')),
      );
      return;
    }

    await ref.read(settingsProvider.notifier).updateSubscriptionUserAgent(
      mode: SubscriptionUserAgentMode.custom,
      value: value,
    );

    if (!mounted) return;
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(const SnackBar(content: Text('User-Agent saved.')));
  }

  Future<void> _resetUserAgentOverride() async {
    _userAgentController.clear();
    await ref.read(settingsProvider.notifier).updateSubscriptionUserAgent(
      mode: SubscriptionUserAgentMode.appDefault,
    );

    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Reverted to the app default User-Agent.')),
    );
  }

  Future<void> _toggleCollapseSubscriptions(bool enabled) async {
    await ref
        .read(settingsProvider.notifier)
        .updateSubscriptionSettings(collapseSubscriptions: enabled);
    if (!mounted) return;
    setState(() {
      _providerProfilesExpanded = !enabled;
      _snapshotsExpanded = !enabled;
    });
  }

  Future<void> _launchExternalUrl(String value) async {
    final uri = Uri.tryParse(value);
    if (uri == null) {
      return;
    }

    final launched = await launchUrl(
      uri,
      mode: LaunchMode.externalApplication,
    ).catchError((_) => false);

    if (!mounted || launched) {
      return;
    }

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Could not open provider link.')),
    );
  }

  static String _formatTimestamp(DateTime value) {
    final local = value.toLocal();
    final hours = local.hour.toString().padLeft(2, '0');
    final minutes = local.minute.toString().padLeft(2, '0');
    return '${local.year}-${local.month.toString().padLeft(2, '0')}-${local.day.toString().padLeft(2, '0')} $hours:$minutes';
  }

  static String _connectStrategyLabel(SubscriptionConnectStrategy value) {
    return switch (value) {
      SubscriptionConnectStrategy.lastUsed => 'Last Used',
      SubscriptionConnectStrategy.lowestDelay => 'Lowest Delay',
      SubscriptionConnectStrategy.random => 'Random',
    };
  }

  static String _sortModeLabel(SubscriptionSortMode value) {
    return switch (value) {
      SubscriptionSortMode.none => 'No Sorting',
      SubscriptionSortMode.ping => 'Sort by Ping',
      SubscriptionSortMode.alphabetical => 'Alphabetical',
    };
  }
}

class _EnumDropdownTile<T> extends StatelessWidget {
  const _EnumDropdownTile({
    super.key,
    required this.title,
    required this.subtitle,
    required this.leading,
    required this.value,
    required this.items,
    required this.labelBuilder,
    required this.onChanged,
  });

  final String title;
  final String subtitle;
  final Widget leading;
  final T value;
  final List<T> items;
  final String Function(T value) labelBuilder;
  final ValueChanged<T>? onChanged;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(
        Spacing.md,
        Spacing.sm,
        Spacing.md,
        Spacing.sm,
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.only(top: Spacing.sm),
            child: leading,
          ),
          const SizedBox(width: Spacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: Theme.of(context).textTheme.bodyLarge),
                const SizedBox(height: Spacing.xs),
                Text(
                  subtitle,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
                ),
                const SizedBox(height: Spacing.sm),
                DropdownButtonFormField<T>(
                  initialValue: value,
                  items: items
                      .map(
                        (item) => DropdownMenuItem<T>(
                          value: item,
                          child: Text(labelBuilder(item)),
                        ),
                      )
                      .toList(growable: false),
                  onChanged: onChanged == null
                      ? null
                      : (next) {
                          if (next != null) {
                            onChanged!(next);
                          }
                        },
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _RemoteSubscriptionCard extends StatelessWidget {
  const _RemoteSubscriptionCard({
    required this.profile,
    required this.isRefreshing,
    required this.onRefresh,
    this.onOpenSupport,
    this.onOpenProviderPage,
  });

  final RemoteVpnProfile profile;
  final bool isRefreshing;
  final Future<void> Function() onRefresh;
  final VoidCallback? onOpenSupport;
  final VoidCallback? onOpenProviderPage;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final consumedBytes = profile.uploadBytes + profile.downloadBytes;
    final hasTrafficLimit = profile.totalBytes > 0;
    final lastUpdated = profile.lastUpdatedAt == null
        ? 'Never'
        : _SubscriptionSettingsScreenState._formatTimestamp(
            profile.lastUpdatedAt!,
          );
    final expiryLabel = profile.expiresAt == null
        ? 'No expiry'
        : DataFormatters.formatDate(profile.expiresAt!);

    return Padding(
      padding: const EdgeInsets.fromLTRB(
        Spacing.md,
        Spacing.sm,
        Spacing.md,
        Spacing.sm,
      ),
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: theme.colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(Radii.lg),
        ),
        child: Padding(
          padding: const EdgeInsets.all(Spacing.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      profile.name,
                      key: Key('provider_profile_${profile.id}'),
                      style: theme.textTheme.titleMedium,
                    ),
                  ),
                  if (profile.isActive)
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: Spacing.sm,
                        vertical: 4,
                      ),
                      decoration: BoxDecoration(
                        color: theme.colorScheme.primaryContainer,
                        borderRadius: BorderRadius.circular(Radii.lg),
                      ),
                      child: Text(
                        'Active',
                        style: theme.textTheme.labelSmall?.copyWith(
                          color: theme.colorScheme.onPrimaryContainer,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                ],
              ),
              const SizedBox(height: Spacing.xs),
              Text(
                '${profile.servers.length} server(s) • update every ${profile.updateIntervalMinutes} min • last updated $lastUpdated',
              ),
              const SizedBox(height: Spacing.xs),
              Text(
                hasTrafficLimit
                    ? 'Usage ${DataFormatters.formatBytes(consumedBytes)} / ${DataFormatters.formatBytes(profile.totalBytes)} • expires $expiryLabel'
                    : 'Unlimited traffic • expires $expiryLabel',
              ),
              const SizedBox(height: Spacing.xs),
              Text(
                'Source URL is stored encrypted at rest. Use support or provider links for provider-managed actions.',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: Spacing.md),
              Wrap(
                spacing: Spacing.sm,
                runSpacing: Spacing.sm,
                children: [
                  FilledButton.tonalIcon(
                    key: Key('button_refresh_profile_${profile.id}'),
                    onPressed: isRefreshing
                        ? null
                        : () => unawaited(onRefresh()),
                    icon: isRefreshing
                        ? const SizedBox(
                            width: 14,
                            height: 14,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.refresh),
                    label: const Text('Refresh'),
                  ),
                  OutlinedButton.icon(
                    key: Key('button_support_profile_${profile.id}'),
                    onPressed: onOpenSupport,
                    icon: const Icon(Icons.support_agent_outlined),
                    label: const Text('Support'),
                  ),
                  OutlinedButton.icon(
                    key: Key('button_provider_page_${profile.id}'),
                    onPressed: onOpenProviderPage,
                    icon: const Icon(Icons.open_in_new_outlined),
                    label: const Text('Provider Page'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _InfoNotice extends StatelessWidget {
  const _InfoNotice({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(Radii.lg),
      ),
      child: Padding(
        padding: const EdgeInsets.all(Spacing.md),
        child: Text(message),
      ),
    );
  }
}
