import 'dart:async' show unawaited;

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:latlong2/latlong.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:cybervpn_mobile/features/servers/presentation/providers/server_list_provider.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_provider.dart';

/// World map view of VPN servers grouped by country.
///
/// Each country with available servers is represented by a colored marker.
/// Marker color indicates latency quality:
/// - Green: < 50ms
/// - Yellow: < 100ms
/// - Red: >= 100ms
/// - Grey: no latency data
///
/// Tapping a marker opens a bottom sheet listing servers in that country.
class ServerMapScreen extends ConsumerStatefulWidget {
  const ServerMapScreen({super.key});

  @override
  ConsumerState<ServerMapScreen> createState() => _ServerMapScreenState();
}

class _ServerMapScreenState extends ConsumerState<ServerMapScreen> {
  final MapController _mapController = MapController();

  @override
  Widget build(BuildContext context) {
    final grouped = ref.watch(groupedByCountryProvider);
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    final markers = <Marker>[];

    for (final entry in grouped.entries) {
      final countryCode = entry.key;
      final servers = entry.value;
      final coords = _countryCoordinates[countryCode.toUpperCase()];
      if (coords == null) continue;

      // Use best ping among servers in this country.
      final bestPing = _bestPing(servers);
      final markerColor = _latencyColor(bestPing);

      markers.add(
        Marker(
          point: coords,
          width: 32,
          height: 32,
          child: GestureDetector(
            onTap: () => _showCountrySheet(context, countryCode, servers),
            child: _MapMarker(
              color: markerColor,
              serverCount: servers.length,
            ),
          ),
        ),
      );
    }

    return FlutterMap(
      mapController: _mapController,
      options: MapOptions(
        initialCenter: const LatLng(30, 0),
        initialZoom: 2.0,
        minZoom: 1.5,
        maxZoom: 6.0,
        interactionOptions: const InteractionOptions(
          flags: InteractiveFlag.all & ~InteractiveFlag.rotate,
        ),
        backgroundColor: isDark
            ? const Color(0xFF0A0E1A)
            : const Color(0xFFE8E8E8),
      ),
      children: [
        TileLayer(
          urlTemplate: isDark
              ? 'https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}@2x.png'
              : 'https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}@2x.png',
          subdomains: const ['a', 'b', 'c', 'd'],
          userAgentPackageName: 'com.cybervpn.mobile',
          maxZoom: 18,
        ),
        MarkerLayer(markers: markers),
      ],
    );
  }

  int? _bestPing(List<ServerEntity> servers) {
    int? best;
    for (final s in servers) {
      if (s.ping != null && (best == null || s.ping! < best)) {
        best = s.ping;
      }
    }
    return best;
  }

  Color _latencyColor(int? ping) {
    if (ping == null) return Colors.grey;
    if (ping < 50) return CyberColors.matrixGreen;
    if (ping < 100) return Colors.amber;
    return const Color(0xFFFF5252);
  }

  void _showCountrySheet(
    BuildContext context,
    String countryCode,
    List<ServerEntity> servers,
  ) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);
    final countryName =
        servers.isNotEmpty ? servers.first.countryName : countryCode;

    unawaited(showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: theme.colorScheme.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(Radii.lg)),
      ),
      builder: (context) {
        return DraggableScrollableSheet(
          initialChildSize: 0.4,
          minChildSize: 0.25,
          maxChildSize: 0.7,
          expand: false,
          builder: (context, scrollController) {
            return Column(
              children: [
                // Handle bar
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: Spacing.sm),
                  child: Container(
                    width: 32,
                    height: 4,
                    decoration: BoxDecoration(
                      color: theme.colorScheme.onSurfaceVariant
                          .withValues(alpha: 0.4),
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                ),

                // Title
                Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: Spacing.md,
                    vertical: Spacing.xs,
                  ),
                  child: Row(
                    children: [
                      Text(
                        countryName,
                        style: theme.textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(width: Spacing.sm),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 8,
                          vertical: 2,
                        ),
                        decoration: BoxDecoration(
                          color: theme.colorScheme.primaryContainer,
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Text(
                          '${servers.length}',
                          style: theme.textTheme.labelSmall?.copyWith(
                            color: theme.colorScheme.onPrimaryContainer,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),

                const Divider(),

                // Server list
                Expanded(
                  child: ListView.builder(
                    controller: scrollController,
                    itemCount: servers.length,
                    itemBuilder: (context, index) {
                      final server = servers[index];
                      return _ServerSheetTile(
                        server: server,
                        onTap: () {
                          Navigator.of(context).pop();
                          unawaited(ref
                              .read(vpnConnectionProvider.notifier)
                              .connect(server));
                        },
                      );
                    },
                  ),
                ),
              ],
            );
          },
        );
      },
    ));
  }
}

// ---------------------------------------------------------------------------
// Map marker widget
// ---------------------------------------------------------------------------

class _MapMarker extends StatelessWidget {
  const _MapMarker({
    required this.color,
    required this.serverCount,
  });

  final Color color;
  final int serverCount;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.85),
        shape: BoxShape.circle,
        border: Border.all(color: Colors.white, width: 1.5),
        boxShadow: [
          BoxShadow(
            color: color.withValues(alpha: 0.4),
            blurRadius: 6,
            spreadRadius: 1,
          ),
        ],
      ),
      child: Center(
        child: Text(
          '$serverCount',
          style: const TextStyle(
            color: Colors.white,
            fontSize: 11,
            fontWeight: FontWeight.bold,
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Server tile in bottom sheet
// ---------------------------------------------------------------------------

class _ServerSheetTile extends StatelessWidget {
  const _ServerSheetTile({
    required this.server,
    required this.onTap,
  });

  final ServerEntity server;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final ping = server.ping;
    final pingText = ping != null ? '${ping}ms' : '--';
    final pingColor = ping == null
        ? theme.colorScheme.onSurfaceVariant
        : ping < 50
            ? CyberColors.matrixGreen
            : ping < 100
                ? Colors.amber
                : const Color(0xFFFF5252);

    return ListTile(
      leading: Icon(
        Icons.dns_outlined,
        color: server.isAvailable
            ? theme.colorScheme.primary
            : theme.colorScheme.onSurfaceVariant,
      ),
      title: Text(
        server.city.isNotEmpty ? server.city : server.name,
        style: theme.textTheme.bodyMedium,
      ),
      subtitle: Text(
        '${server.protocol.toUpperCase()} · $pingText',
        style: theme.textTheme.bodySmall?.copyWith(color: pingColor),
      ),
      trailing: server.isPremium
          ? const Icon(Icons.star, color: Colors.amber, size: 18)
          : null,
      onTap: server.isAvailable ? onTap : null,
      enabled: server.isAvailable,
    );
  }
}

// ---------------------------------------------------------------------------
// Country coordinates (capital city approximate lat/lng)
// ---------------------------------------------------------------------------

const _countryCoordinates = <String, LatLng>{
  'AD': LatLng(42.5, 1.5),
  'AE': LatLng(24.47, 54.37),
  'AF': LatLng(34.53, 69.17),
  'AG': LatLng(17.12, -61.85),
  'AL': LatLng(41.33, 19.82),
  'AM': LatLng(40.18, 44.51),
  'AO': LatLng(-8.84, 13.23),
  'AR': LatLng(-34.61, -58.38),
  'AT': LatLng(48.21, 16.37),
  'AU': LatLng(-33.87, 151.21),
  'AZ': LatLng(40.41, 49.87),
  'BA': LatLng(43.86, 18.41),
  'BB': LatLng(13.1, -59.62),
  'BD': LatLng(23.81, 90.41),
  'BE': LatLng(50.85, 4.35),
  'BG': LatLng(42.70, 23.32),
  'BH': LatLng(26.23, 50.59),
  'BN': LatLng(4.94, 114.95),
  'BO': LatLng(-16.5, -68.15),
  'BR': LatLng(-15.79, -47.88),
  'BS': LatLng(25.05, -77.35),
  'BT': LatLng(27.47, 89.64),
  'BY': LatLng(53.9, 27.57),
  'BZ': LatLng(17.25, -88.77),
  'CA': LatLng(45.42, -75.69),
  'CH': LatLng(46.95, 7.45),
  'CL': LatLng(-33.45, -70.67),
  'CM': LatLng(3.87, 11.52),
  'CN': LatLng(39.90, 116.40),
  'CO': LatLng(4.71, -74.07),
  'CR': LatLng(9.93, -84.08),
  'CY': LatLng(35.17, 33.37),
  'CZ': LatLng(50.08, 14.42),
  'DE': LatLng(52.52, 13.41),
  'DK': LatLng(55.68, 12.57),
  'DO': LatLng(18.47, -69.90),
  'DZ': LatLng(36.75, 3.04),
  'EC': LatLng(-0.18, -78.47),
  'EE': LatLng(59.44, 24.75),
  'EG': LatLng(30.04, 31.24),
  'ES': LatLng(40.42, -3.70),
  'ET': LatLng(9.02, 38.75),
  'FI': LatLng(60.17, 24.94),
  'FR': LatLng(48.86, 2.35),
  'GB': LatLng(51.51, -0.13),
  'GE': LatLng(41.72, 44.79),
  'GH': LatLng(5.56, -0.19),
  'GR': LatLng(37.98, 23.73),
  'GT': LatLng(14.63, -90.51),
  'HK': LatLng(22.32, 114.17),
  'HN': LatLng(14.07, -87.19),
  'HR': LatLng(45.81, 15.98),
  'HU': LatLng(47.50, 19.04),
  'ID': LatLng(-6.21, 106.85),
  'IE': LatLng(53.35, -6.26),
  'IL': LatLng(31.77, 35.22),
  'IN': LatLng(28.61, 77.21),
  'IQ': LatLng(33.34, 44.40),
  'IR': LatLng(35.69, 51.39),
  'IS': LatLng(64.14, -21.94),
  'IT': LatLng(41.90, 12.50),
  'JM': LatLng(18.0, -76.8),
  'JO': LatLng(31.95, 35.93),
  'JP': LatLng(35.68, 139.69),
  'KE': LatLng(-1.29, 36.82),
  'KG': LatLng(42.87, 74.59),
  'KH': LatLng(11.56, 104.93),
  'KR': LatLng(37.57, 126.98),
  'KW': LatLng(29.38, 47.99),
  'KZ': LatLng(51.17, 71.43),
  'LA': LatLng(17.97, 102.63),
  'LB': LatLng(33.89, 35.50),
  'LI': LatLng(47.14, 9.52),
  'LK': LatLng(6.93, 79.85),
  'LT': LatLng(54.69, 25.28),
  'LU': LatLng(49.61, 6.13),
  'LV': LatLng(56.95, 24.11),
  'LY': LatLng(32.90, 13.18),
  'MA': LatLng(34.02, -6.84),
  'MC': LatLng(43.74, 7.42),
  'MD': LatLng(47.01, 28.86),
  'ME': LatLng(42.44, 19.26),
  'MG': LatLng(-18.91, 47.52),
  'MK': LatLng(41.99, 21.43),
  'MM': LatLng(16.87, 96.20),
  'MN': LatLng(47.92, 106.91),
  'MO': LatLng(22.20, 113.55),
  'MT': LatLng(35.90, 14.51),
  'MU': LatLng(-20.16, 57.50),
  'MX': LatLng(19.43, -99.13),
  'MY': LatLng(3.14, 101.69),
  'MZ': LatLng(-25.97, 32.58),
  'NA': LatLng(-22.56, 17.08),
  'NG': LatLng(9.06, 7.49),
  'NI': LatLng(12.14, -86.25),
  'NL': LatLng(52.37, 4.90),
  'NO': LatLng(59.91, 10.75),
  'NP': LatLng(27.72, 85.32),
  'NZ': LatLng(-41.29, 174.78),
  'OM': LatLng(23.59, 58.54),
  'PA': LatLng(8.97, -79.53),
  'PE': LatLng(-12.05, -77.04),
  'PH': LatLng(14.60, 120.98),
  'PK': LatLng(33.69, 73.04),
  'PL': LatLng(52.23, 21.01),
  'PR': LatLng(18.47, -66.12),
  'PT': LatLng(38.72, -9.14),
  'PY': LatLng(-25.26, -57.58),
  'QA': LatLng(25.29, 51.53),
  'RO': LatLng(44.43, 26.10),
  'RS': LatLng(44.79, 20.47),
  'RU': LatLng(55.76, 37.62),
  'RW': LatLng(-1.94, 30.06),
  'SA': LatLng(24.69, 46.72),
  'SE': LatLng(59.33, 18.07),
  'SG': LatLng(1.35, 103.82),
  'SI': LatLng(46.05, 14.51),
  'SK': LatLng(48.15, 17.11),
  'SN': LatLng(14.69, -17.44),
  'TH': LatLng(13.76, 100.50),
  'TN': LatLng(36.81, 10.18),
  'TR': LatLng(39.93, 32.85),
  'TT': LatLng(10.65, -61.50),
  'TW': LatLng(25.03, 121.57),
  'TZ': LatLng(-6.79, 39.28),
  'UA': LatLng(50.45, 30.52),
  'UG': LatLng(0.35, 32.58),
  'US': LatLng(38.90, -77.04),
  'UY': LatLng(-34.88, -56.17),
  'UZ': LatLng(41.30, 69.28),
  'VE': LatLng(10.49, -66.88),
  'VN': LatLng(21.03, 105.85),
  'ZA': LatLng(-33.92, 18.42),
  'ZW': LatLng(-17.83, 31.05),
};
