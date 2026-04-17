import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/di/providers.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/widgets/settings_section.dart';
import 'package:cybervpn_mobile/features/settings/presentation/widgets/settings_tile.dart';

/// Ping strategy settings screen.
class PingSettingsScreen extends ConsumerStatefulWidget {
  const PingSettingsScreen({super.key, this.embedded = false});

  final bool embedded;

  @override
  ConsumerState<PingSettingsScreen> createState() => _PingSettingsScreenState();
}

class _PingSettingsScreenState extends ConsumerState<PingSettingsScreen> {
  late final TextEditingController _urlController;

  @override
  void initState() {
    super.initState();
    _urlController = TextEditingController();
  }

  @override
  void dispose() {
    _urlController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final asyncSettings = ref.watch(settingsProvider);

    final content = asyncSettings.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, _) =>
          const Center(child: Text('Failed to load ping settings')),
      data: _buildBody,
    );

    if (widget.embedded) {
      return content;
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Ping')),
      body: content,
    );
  }

  Widget _buildBody(AppSettings settings) {
    final notifier = ref.read(settingsProvider.notifier);
    final pingPolicy = ref.read(pingPolicyRuntimeProvider);
    final normalizedMode = pingPolicy.normalizeMode(settings.pingMode);

    if (_urlController.text != settings.pingTestUrl) {
      _urlController.text = settings.pingTestUrl;
    }

    return ListView(
      children: [
        SettingsSection(
          title: 'Mode',
          children: [
            SettingsTile.radio(
              key: const Key('radio_ping_mode_proxy_get'),
              title: 'Via Proxy GET',
              subtitle:
                  'Run latency probes through the proxy using GET requests for Happ-style reachability checks.',
              value: PingMode.proxyGet,
              groupValue: normalizedMode,
              onChanged: (_) =>
                  notifier.updatePingSettings(mode: PingMode.proxyGet),
            ),
            SettingsTile.radio(
              key: const Key('radio_ping_mode_proxy_head'),
              title: 'Via Proxy HEAD',
              subtitle:
                  'Use lightweight HEAD probes through the proxy. Legacy Real Delay is normalized to this mode.',
              value: PingMode.proxyHead,
              groupValue: normalizedMode,
              onChanged: (_) =>
                  notifier.updatePingSettings(mode: PingMode.proxyHead),
            ),
            SettingsTile.radio(
              key: const Key('radio_ping_mode_tcp'),
              title: 'TCP',
              subtitle:
                  'Measure connect latency without issuing proxy HTTP requests.',
              value: PingMode.tcp,
              groupValue: normalizedMode,
              onChanged: (_) => notifier.updatePingSettings(mode: PingMode.tcp),
            ),
            SettingsTile.radio(
              key: const Key('radio_ping_mode_icmp'),
              title: 'ICMP',
              subtitle:
                  'Stored as a Happ-compatible preference. Unsupported runtimes fall back to TCP connect.',
              value: PingMode.icmp,
              groupValue: normalizedMode,
              onChanged: (_) =>
                  notifier.updatePingSettings(mode: PingMode.icmp),
            ),
          ],
        ),
        SettingsSection(
          title: 'Result',
          children: [
            SettingsTile.radio(
              key: const Key('radio_ping_result_time'),
              title: 'Time',
              subtitle:
                  'Show raw latency values in server lists and detail screens.',
              value: PingResultMode.time,
              groupValue: settings.pingResultMode,
              onChanged: (_) =>
                  notifier.updatePingResultMode(PingResultMode.time),
            ),
            SettingsTile.radio(
              key: const Key('radio_ping_result_icon'),
              title: 'Icon',
              subtitle:
                  'Show quality icons instead of milliseconds in server lists.',
              value: PingResultMode.icon,
              groupValue: settings.pingResultMode,
              onChanged: (_) =>
                  notifier.updatePingResultMode(PingResultMode.icon),
            ),
          ],
        ),
        SettingsSection(
          title: 'Target URL',
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(
                Spacing.md,
                Spacing.sm,
                Spacing.md,
                Spacing.sm,
              ),
              child: TextField(
                key: const Key('input_ping_test_url'),
                controller: _urlController,
                decoration: const InputDecoration(
                  labelText: 'Ping test URL',
                  hintText: 'https://google.com/generate_204',
                  border: OutlineInputBorder(),
                ),
                keyboardType: TextInputType.url,
                onSubmitted: (value) => notifier.updatePingSettings(
                  mode: settings.pingMode,
                  pingTestUrl: value.trim(),
                ),
              ),
            ),
            const ListTile(
              title: Text('Proxy ping target'),
              subtitle: Text(
                'Use a lightweight URL that returns fast responses to keep proxy GET/HEAD checks stable.',
              ),
            ),
          ],
        ),
        const SettingsSection(
          title: 'Runtime behavior',
          children: [
            SettingsTile.info(
              key: Key('info_ping_runtime_fallbacks'),
              title: 'Compatibility notes',
              subtitle:
                  'Diagnostics supports Proxy GET, Proxy HEAD, and TCP directly. Server-list pings use TCP when only panel host metadata is available. ICMP remains a stored preference and falls back where the mobile runtime cannot open raw socket probes.',
            ),
          ],
        ),
        SettingsSection(
          title: 'Diagnostics',
          children: [
            SettingsTile.navigation(
              key: const Key('nav_ping_speed_test'),
              title: 'Open Speed Test',
              subtitle:
                  'Launch the diagnostics speed test with the current ping strategy stored in settings.',
              leading: const Icon(Icons.speed_outlined),
              onTap: () => context.push('/diagnostics/speed-test'),
            ),
          ],
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(
            Spacing.md,
            Spacing.sm,
            Spacing.md,
            Spacing.lg,
          ),
          child: DecoratedBox(
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surfaceContainerHighest,
              borderRadius: BorderRadius.circular(Radii.lg),
            ),
            child: const Padding(
              padding: EdgeInsets.all(Spacing.md),
              child: Text(
                'Ping mode, result style, and target URL are now shared across diagnostics, subscription refresh, and server-list rendering with explicit fallback handling.',
              ),
            ),
          ),
        ),
        SizedBox(height: Spacing.navBarClearance(context)),
      ],
    );
  }
}
