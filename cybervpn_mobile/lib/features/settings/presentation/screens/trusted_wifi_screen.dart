import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/network/wifi_monitor_service.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';

// ---------------------------------------------------------------------------
// TrustedWifiScreen
// ---------------------------------------------------------------------------

/// Screen for managing the list of trusted WiFi networks.
///
/// Trusted networks won't trigger auto-connect when `autoConnectUntrustedWifi`
/// is enabled. This allows users to mark their home/work networks as safe.
///
/// Features:
/// - View current trusted networks
/// - Add current WiFi network to trusted list
/// - Manually add networks by name
/// - Remove networks from trusted list
/// - Request location permission for SSID access
class TrustedWifiScreen extends ConsumerStatefulWidget {
  const TrustedWifiScreen({super.key});

  @override
  ConsumerState<TrustedWifiScreen> createState() => _TrustedWifiScreenState();
}

class _TrustedWifiScreenState extends ConsumerState<TrustedWifiScreen> {
  final _addController = TextEditingController();
  bool _isAddingCurrent = false;

  @override
  void dispose() {
    _addController.dispose();
    super.dispose();
  }

  // ── Actions ────────────────────────────────────────────────────────────────

  Future<void> _addCurrentNetwork() async {
    setState(() => _isAddingCurrent = true);

    try {
      final wifiService = ref.read(wifiMonitorServiceProvider);

      // Check permission first
      final permStatus = await wifiService.checkPermission();

      if (permStatus != WifiPermissionStatus.granted) {
        // Request permission
        final newStatus = await wifiService.requestPermission();

        if (newStatus != WifiPermissionStatus.granted) {
          if (!mounted) return;
          _showPermissionDeniedDialog(newStatus);
          return;
        }
      }

      // Get current WiFi info
      final wifiInfo = await wifiService.getCurrentWifiInfo();

      if (!wifiInfo.hasValidSsid) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(AppLocalizations.of(context).settingsTrustedNotConnected),
          ),
        );
        return;
      }

      // Add to trusted list
      await ref.read(settingsProvider.notifier).addTrustedNetwork(
            wifiInfo.cleanSsid!,
          );

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(AppLocalizations.of(context).settingsTrustedAddedNetwork(wifiInfo.cleanSsid!)),
        ),
      );
    } catch (e) {
      AppLogger.error('Failed to add current network', error: e);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to add network: $e'),
          backgroundColor: Theme.of(context).colorScheme.error,
        ),
      );
    } finally {
      if (mounted) {
        setState(() => _isAddingCurrent = false);
      }
    }
  }

  void _showAddManualDialog() {
    unawaited(showDialog<void>(
      context: context,
      builder: (dialogCtx) {
        final dl = AppLocalizations.of(dialogCtx);
        return AlertDialog(
          title: Text(dl.settingsTrustedAddDialogTitle),
          content: TextField(
            controller: _addController,
            autofocus: true,
            decoration: InputDecoration(
              labelText: dl.settingsTrustedSsidLabel,
              hintText: dl.settingsTrustedSsidHint,
              border: const OutlineInputBorder(),
            ),
            onSubmitted: (_) => _addManualNetwork(),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogCtx).pop(),
              child: Text(dl.cancel),
            ),
            FilledButton(
              onPressed: _addManualNetwork,
              child: Text(dl.settingsTrustedAddButton),
            ),
          ],
        );
      },
    ));
  }

  Future<void> _addManualNetwork() async {
    final ssid = _addController.text.trim();
    if (ssid.isEmpty) return;

    Navigator.of(context).pop();
    await ref.read(settingsProvider.notifier).addTrustedNetwork(ssid);
    _addController.clear();

    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(AppLocalizations.of(context).settingsTrustedAddedNetwork(ssid))),
    );
  }

  Future<void> _removeNetwork(String ssid) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogCtx) {
        final dl = AppLocalizations.of(dialogCtx);
        return AlertDialog(
          title: Text(dl.settingsTrustedRemoveDialogTitle),
          content: Text(dl.settingsTrustedRemoveDialogContent(ssid)),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogCtx).pop(false),
              child: Text(dl.cancel),
            ),
            FilledButton(
              onPressed: () => Navigator.of(dialogCtx).pop(true),
              child: Text(dl.settingsTrustedRemoveButton),
            ),
          ],
        );
      },
    );

    if (confirmed == true) {
      await ref.read(settingsProvider.notifier).removeTrustedNetwork(ssid);
    }
  }

  void _showPermissionDeniedDialog(WifiPermissionStatus status) {
    final isPermanent = status == WifiPermissionStatus.permanentlyDenied;

    unawaited(showDialog<void>(
      context: context,
      builder: (dialogCtx) {
        final dl = AppLocalizations.of(dialogCtx);
        return AlertDialog(
          title: Text(dl.settingsTrustedPermissionTitle),
          content: Text(
            isPermanent
                ? dl.settingsTrustedPermissionPermanent
                : dl.settingsTrustedPermissionRequired,
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogCtx).pop(),
              child: Text(dl.cancel),
            ),
            if (isPermanent)
              FilledButton(
                onPressed: () {
                  Navigator.of(dialogCtx).pop();
                  // Open app settings
                  unawaited(ref.read(wifiMonitorServiceProvider).openAppSettings());
                },
                child: Text(dl.settingsTrustedOpenSettings),
              )
            else
              FilledButton(
                onPressed: () {
                  Navigator.of(dialogCtx).pop();
                  unawaited(_addCurrentNetwork());
                },
                child: Text(dl.settingsTrustedTryAgain),
              ),
          ],
        );
      },
    ));
  }

  // ── Build ──────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final trustedNetworks = ref.watch(trustedWifiNetworksProvider);
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final l10n = AppLocalizations.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.settingsTrustedNetworksTitle),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            tooltip: l10n.settingsTrustedAddManually,
            onPressed: _showAddManualDialog,
          ),
        ],
      ),
      body: Column(
        children: [
          // --- Add current network button ---
          _buildAddCurrentButton(colorScheme),

          // --- Info card ---
          _buildInfoCard(theme, colorScheme),

          // --- Network list ---
          Expanded(
            child: trustedNetworks.isEmpty
                ? _buildEmptyState(theme, colorScheme)
                : _buildNetworkList(trustedNetworks, theme, colorScheme),
          ),
        ],
      ),
    );
  }

  Widget _buildAddCurrentButton(ColorScheme colorScheme) {
    final l10n = AppLocalizations.of(context);

    return Padding(
      padding: const EdgeInsets.all(Spacing.md),
      child: SizedBox(
        width: double.infinity,
        child: FilledButton.icon(
          onPressed: _isAddingCurrent ? null : _addCurrentNetwork,
          icon: _isAddingCurrent
              ? SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: colorScheme.onPrimary,
                  ),
                )
              : const Icon(Icons.add_circle_outline),
          label: Text(_isAddingCurrent
              ? l10n.settingsTrustedDetectingNetwork
              : l10n.settingsTrustedAddCurrentWifi),
        ),
      ),
    );
  }

  Widget _buildInfoCard(ThemeData theme, ColorScheme colorScheme) {
    final l10n = AppLocalizations.of(context);

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: Spacing.md),
      child: Card(
        color: colorScheme.surfaceContainerHighest,
        child: Padding(
          padding: const EdgeInsets.all(Spacing.md),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(
                Icons.info_outline,
                size: 20,
                color: colorScheme.onSurfaceVariant,
              ),
              const SizedBox(width: Spacing.sm),
              Expanded(
                child: Text(
                  l10n.settingsTrustedInfoDescription,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: colorScheme.onSurfaceVariant,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildEmptyState(ThemeData theme, ColorScheme colorScheme) {
    final l10n = AppLocalizations.of(context);

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(Spacing.xl),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.wifi_lock_outlined,
              size: 64,
              color: colorScheme.outline,
            ),
            const SizedBox(height: Spacing.md),
            Text(
              l10n.settingsTrustedEmptyTitle,
              style: theme.textTheme.titleMedium?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: Spacing.sm),
            Text(
              l10n.settingsTrustedEmptyDescription,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildNetworkList(
    List<String> networks,
    ThemeData theme,
    ColorScheme colorScheme,
  ) {
    return ListView.builder(
      padding: const EdgeInsets.only(top: Spacing.sm, bottom: Spacing.xl),
      itemCount: networks.length,
      itemBuilder: (context, index) {
        final ssid = networks[index];
        return ListTile(
          leading: CircleAvatar(
            backgroundColor: colorScheme.primaryContainer,
            child: Icon(
              Icons.wifi,
              color: colorScheme.onPrimaryContainer,
            ),
          ),
          title: Text(ssid),
          subtitle: Text(
            AppLocalizations.of(context).settingsTrustedNetworkSubtitle,
            style: TextStyle(color: colorScheme.onSurfaceVariant),
          ),
          trailing: IconButton(
            icon: Icon(Icons.delete_outline, color: colorScheme.error),
            tooltip: AppLocalizations.of(context).settingsTrustedRemoveTooltip,
            onPressed: () => _removeNetwork(ssid),
          ),
        );
      },
    );
  }
}
