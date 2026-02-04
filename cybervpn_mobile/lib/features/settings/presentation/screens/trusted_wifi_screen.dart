import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
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
          const SnackBar(
            content: Text('Not connected to WiFi or SSID unavailable'),
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
          content: Text('Added "${wifiInfo.cleanSsid}" to trusted networks'),
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
    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Add Trusted Network'),
        content: TextField(
          controller: _addController,
          autofocus: true,
          decoration: const InputDecoration(
            labelText: 'Network name (SSID)',
            hintText: 'e.g. My Home WiFi',
            border: OutlineInputBorder(),
          ),
          onSubmitted: (_) => _addManualNetwork(),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: _addManualNetwork,
            child: const Text('Add'),
          ),
        ],
      ),
    );
  }

  Future<void> _addManualNetwork() async {
    final ssid = _addController.text.trim();
    if (ssid.isEmpty) return;

    Navigator.of(context).pop();
    await ref.read(settingsProvider.notifier).addTrustedNetwork(ssid);
    _addController.clear();

    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Added "$ssid" to trusted networks')),
    );
  }

  Future<void> _removeNetwork(String ssid) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Remove Network?'),
        content: Text('Remove "$ssid" from trusted networks?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Remove'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      await ref.read(settingsProvider.notifier).removeTrustedNetwork(ssid);
    }
  }

  void _showPermissionDeniedDialog(WifiPermissionStatus status) {
    final isPermanent = status == WifiPermissionStatus.permanentlyDenied;

    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Permission Required'),
        content: Text(
          isPermanent
              ? 'Location permission is required to detect WiFi networks. '
                  'Please enable it in your device settings.'
              : 'Location permission is required to detect WiFi network names. '
                  'This is a platform requirement for privacy reasons.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          if (isPermanent)
            FilledButton(
              onPressed: () {
                Navigator.of(context).pop();
                // Open app settings
                ref.read(wifiMonitorServiceProvider).openAppSettings();
              },
              child: const Text('Open Settings'),
            )
          else
            FilledButton(
              onPressed: () {
                Navigator.of(context).pop();
                _addCurrentNetwork();
              },
              child: const Text('Try Again'),
            ),
        ],
      ),
    );
  }

  // ── Build ──────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final trustedNetworks = ref.watch(trustedWifiNetworksProvider);
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Trusted Networks'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            tooltip: 'Add network manually',
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
              ? 'Detecting network...'
              : 'Add Current WiFi Network'),
        ),
      ),
    );
  }

  Widget _buildInfoCard(ThemeData theme, ColorScheme colorScheme) {
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
                  'Trusted networks won\'t trigger auto-connect. '
                  'Add your home or work WiFi networks here.',
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
              'No trusted networks',
              style: theme.textTheme.titleMedium?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: Spacing.sm),
            Text(
              'Add networks you trust, like your home WiFi, '
              'to prevent auto-connecting when on these networks.',
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
            'Trusted network',
            style: TextStyle(color: colorScheme.onSurfaceVariant),
          ),
          trailing: IconButton(
            icon: Icon(Icons.delete_outline, color: colorScheme.error),
            tooltip: 'Remove from trusted',
            onPressed: () => _removeNetwork(ssid),
          ),
        );
      },
    );
  }
}
