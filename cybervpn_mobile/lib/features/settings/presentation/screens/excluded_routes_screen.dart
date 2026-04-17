import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/excluded_route_entry.dart';
import 'package:cybervpn_mobile/features/settings/domain/services/vpn_settings_support_matrix.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/vpn_settings_support_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/widgets/settings_section.dart';
import 'package:cybervpn_mobile/features/settings/presentation/widgets/settings_tile.dart';

class ExcludedRoutesScreen extends ConsumerStatefulWidget {
  const ExcludedRoutesScreen({super.key, this.embedded = false});

  final bool embedded;

  @override
  ConsumerState<ExcludedRoutesScreen> createState() =>
      _ExcludedRoutesScreenState();
}

class _ExcludedRoutesScreenState extends ConsumerState<ExcludedRoutesScreen> {
  late final TextEditingController _routeController;

  @override
  void initState() {
    super.initState();
    _routeController = TextEditingController();
  }

  @override
  void dispose() {
    _routeController.dispose();
    super.dispose();
  }

  void _showMessage(String message) {
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _addRoute() async {
    final route = _routeController.text.trim();
    if (route.isEmpty) {
      return;
    }

    final parsed = ExcludedRouteEntry.parse(route);
    if (parsed.targetType == ExcludedRouteTargetType.unknown) {
      _showMessage(
        'Enter a valid IPv4 or IPv6 address/CIDR such as 192.168.0.0/16 or 2001:db8::/32.',
      );
      return;
    }

    final settings = await ref.read(settingsProvider.future);
    final currentEntries = settings.excludedRouteEntries.isNotEmpty
        ? settings.excludedRouteEntries
        : settings.bypassSubnets.map(ExcludedRouteEntry.parse).toList();
    final updated = [...currentEntries, parsed]
      ..sort((a, b) => a.normalizedValue.compareTo(b.normalizedValue));
    await ref
        .read(settingsProvider.notifier)
        .updateExcludedRouteEntries(updated);
    _routeController.clear();
  }

  @override
  Widget build(BuildContext context) {
    final asyncSettings = ref.watch(settingsProvider);
    final support = ref.watch(vpnSettingsSupportMatrixProvider).excludedRoutes;
    final isEditable = support.isAvailable;

    final content = asyncSettings.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, _) =>
          const Center(child: Text('Failed to load excluded routes')),
      data: (settings) {
        final routeEntries = settings.excludedRouteEntries.isNotEmpty
            ? settings.excludedRouteEntries
            : settings.bypassSubnets.map(ExcludedRouteEntry.parse).toList();

        return ListView(
          children: [
            SettingsSection(
              title: 'Status',
              children: [
                SettingsTile.info(
                  key: const Key('excluded_routes_status_tile'),
                  title: 'Excluded routes',
                  subtitle: routeEntries.isEmpty
                      ? (isEditable
                            ? 'No excluded routes configured.'
                            : 'Excluded routes are unavailable on this platform.')
                      : (isEditable
                            ? '${routeEntries.length} route(s) will bypass the tunnel on the next connection.'
                            : '${routeEntries.length} route(s) remain stored for Android runtime.'),
                ),
              ],
            ),
            if (isEditable)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: Spacing.md),
                child: Row(
                  children: [
                    Expanded(
                      child: TextField(
                        key: const Key('input_excluded_route'),
                        controller: _routeController,
                        decoration: const InputDecoration(
                          labelText: 'Add excluded IPv4/IPv6 address or CIDR',
                          hintText: '192.168.0.0/16 or 2001:db8::/32',
                        ),
                        onSubmitted: (_) => _addRoute(),
                      ),
                    ),
                    const SizedBox(width: Spacing.sm),
                    FilledButton(
                      key: const Key('button_add_excluded_route'),
                      onPressed: _addRoute,
                      child: const Text('Add'),
                    ),
                  ],
                ),
              ),
            if (isEditable) const SizedBox(height: Spacing.md),
            if (routeEntries.isEmpty)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: Spacing.md),
                child: Text(
                  isEditable
                      ? 'No excluded routes have been added yet.'
                      : 'Stored excluded routes will appear here when this setting is configured on Android.',
                ),
              )
            else
              for (final route in routeEntries)
                ListTile(
                  key: Key('excluded_route_${route.normalizedValue}'),
                  title: Text(route.normalizedValue),
                  subtitle: Text(_routeTypeLabel(route)),
                  trailing: isEditable
                      ? IconButton(
                          tooltip: 'Remove route',
                          icon: const Icon(Icons.delete_outline),
                          onPressed: () {
                            final updated = routeEntries
                                .where(
                                  (entry) =>
                                      entry.normalizedValue !=
                                      route.normalizedValue,
                                )
                                .toList();
                            unawaited(
                              ref
                                  .read(settingsProvider.notifier)
                                  .updateExcludedRouteEntries(updated),
                            );
                          },
                        )
                      : null,
                ),
            Padding(
              padding: const EdgeInsets.all(Spacing.md),
              child: DecoratedBox(
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.surfaceContainerHighest,
                  borderRadius: BorderRadius.circular(Radii.lg),
                ),
                child: Padding(
                  padding: const EdgeInsets.all(Spacing.md),
                  child: Text(_capabilityMessage(support)),
                ),
              ),
            ),
            SizedBox(height: Spacing.navBarClearance(context)),
          ],
        );
      },
    );

    if (widget.embedded) {
      return content;
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Excluded Routes')),
      body: content,
    );
  }

  String _capabilityMessage(VpnSettingsFeatureSupport support) {
    if (support.isAvailable) {
      return 'Excluded IPv4 and IPv6 routes are stored as typed entries and applied on Android during the next VPN connection. '
          'Use this list for private subnets or destinations that should bypass the tunnel.';
    }

    return support.message ??
        'Excluded routes are not applied on this platform. Stored entries remain available for Android runtime.';
  }

  String _routeTypeLabel(ExcludedRouteEntry entry) {
    return switch (entry.targetType) {
      ExcludedRouteTargetType.ipv4Address => 'IPv4 address',
      ExcludedRouteTargetType.ipv4Cidr => 'IPv4 CIDR',
      ExcludedRouteTargetType.ipv6Address => 'IPv6 address',
      ExcludedRouteTargetType.ipv6Cidr => 'IPv6 CIDR',
      ExcludedRouteTargetType.unknown => 'Unknown',
    };
  }
}
