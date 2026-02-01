import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:share_plus/share_plus.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/widgets/settings_section.dart';
import 'package:cybervpn_mobile/features/settings/presentation/widgets/settings_tile.dart';

// ---------------------------------------------------------------------------
// DebugScreen
// ---------------------------------------------------------------------------

/// Debug and diagnostics settings screen.
///
/// Features:
/// - Log level selector (None/Error/Warning/Info/Debug)
/// - Export logs via share sheet
/// - Clear cache with confirmation
/// - Reset all settings with confirmation
/// - App version and Xray-core version display
/// - Hidden developer mode (7-tap activation on version)
/// - Developer panel with raw config viewer, force crash, experimental features
class DebugScreen extends ConsumerStatefulWidget {
  const DebugScreen({super.key});

  @override
  ConsumerState<DebugScreen> createState() => _DebugScreenState();
}

class _DebugScreenState extends ConsumerState<DebugScreen> {
  // App version info
  String _appVersion = 'Loading...';
  String _buildNumber = '';
  String _xrayCoreVersion = 'Loading...';

  // Developer mode state
  int _versionTapCount = 0;
  bool _developerModeEnabled = false;
  bool _experimentalFeaturesEnabled = false;

  @override
  void initState() {
    super.initState();
    _loadVersionInfo();
  }

  // ── Version Info ─────────────────────────────────────────────────────────

  Future<void> _loadVersionInfo() async {
    try {
      final packageInfo = await PackageInfo.fromPlatform();
      if (mounted) {
        setState(() {
          _appVersion = packageInfo.version;
          _buildNumber = packageInfo.buildNumber;
        });
      }
    } catch (e) {
      AppLogger.error('Failed to load app version', error: e);
      if (mounted) {
        setState(() {
          _appVersion = 'Unknown';
          _buildNumber = '';
        });
      }
    }

    // Load Xray-core version
    try {
      // flutter_v2ray_plus doesn't expose core version directly
      // Use a placeholder or extract from package version
      if (mounted) {
        setState(() {
          _xrayCoreVersion = '1.8.x (flutter_v2ray_plus 1.0.11)';
        });
      }
    } catch (e) {
      AppLogger.error('Failed to load Xray-core version', error: e);
      if (mounted) {
        setState(() {
          _xrayCoreVersion = 'Unknown';
        });
      }
    }
  }

  // ── Build ────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final asyncSettings = ref.watch(settingsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Debug & About'),
      ),
      body: asyncSettings.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _buildError(context, ref, error),
        data: (settings) => _buildBody(context, settings),
      ),
    );
  }

  // ── Error state ──────────────────────────────────────────────────────────

  Widget _buildError(BuildContext context, WidgetRef ref, Object error) {
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
        // --- Diagnostics ---
        SettingsSection(
          title: 'Diagnostics',
          children: [
            _buildLogLevelTile(context, settings),
            SettingsTile.navigation(
              key: const Key('tile_export_logs'),
              title: 'Export Logs',
              subtitle: '${AppLogger.entryCount} entries',
              leading: const Icon(Icons.upload_file_outlined),
              onTap: () => _handleExportLogs(context),
            ),
          ],
        ),

        // --- Cache & Data ---
        SettingsSection(
          title: 'Cache & Data',
          children: [
            SettingsTile.navigation(
              key: const Key('tile_clear_cache'),
              title: 'Clear Cache',
              subtitle: 'Remove cached server lists and configs',
              leading: const Icon(Icons.cleaning_services_outlined),
              onTap: () => _handleClearCache(context),
            ),
            SettingsTile.navigation(
              key: const Key('tile_reset_settings'),
              title: 'Reset All Settings',
              subtitle: 'Restore defaults',
              leading: const Icon(Icons.restart_alt_outlined),
              onTap: () => _handleResetSettings(context),
            ),
          ],
        ),

        // --- About ---
        SettingsSection(
          title: 'About',
          children: [
            GestureDetector(
              onTap: _handleVersionTap,
              child: SettingsTile.info(
                key: const Key('tile_app_version'),
                title: 'App Version',
                subtitle: _buildNumber.isNotEmpty
                    ? '$_appVersion ($_buildNumber)'
                    : _appVersion,
                leading: const Icon(Icons.info_outline),
              ),
            ),
            SettingsTile.info(
              key: const Key('tile_xray_version'),
              title: 'Xray-core Version',
              subtitle: _xrayCoreVersion,
              leading: const Icon(Icons.shield_outlined),
            ),
          ],
        ),

        // --- Developer Panel (hidden until activated) ---
        if (_developerModeEnabled) _buildDeveloperPanel(context),

        // Bottom padding so content is not obscured by navigation bar.
        const SizedBox(height: 80),
      ],
    );
  }

  // ── Log Level Tile ───────────────────────────────────────────────────────

  Widget _buildLogLevelTile(BuildContext context, AppSettings settings) {
    return ListTile(
      key: const Key('tile_log_level'),
      leading: const Icon(Icons.bug_report_outlined),
      title: const Text('Log Level'),
      subtitle: Text(_logLevelLabel(settings.logLevel)),
      trailing: Icon(
        Icons.chevron_right,
        color: Theme.of(context).colorScheme.onSurfaceVariant,
      ),
      onTap: () => _showLogLevelDialog(context, settings.logLevel),
    );
  }

  /// Returns a human-readable label for the [LogLevel].
  String _logLevelLabel(LogLevel level) {
    return switch (level) {
      LogLevel.debug => 'Debug',
      LogLevel.info => 'Info',
      LogLevel.warning => 'Warning',
      LogLevel.error => 'Error',
    };
  }

  // ── Log Level Dialog ─────────────────────────────────────────────────────

  void _showLogLevelDialog(BuildContext context, LogLevel currentLevel) {
    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Log Level'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: LogLevel.values.map((level) {
            return RadioListTile<LogLevel>(
              title: Text(_logLevelLabel(level)),
              subtitle: Text(_logLevelDescription(level)),
              value: level,
              groupValue: currentLevel,
              onChanged: (LogLevel? newLevel) {
                if (newLevel != null) {
                  ref
                      .read(settingsProvider.notifier)
                      .updateLogLevel(newLevel);
                  Navigator.pop(context);
                }
              },
            );
          }).toList(),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
        ],
      ),
    );
  }

  String _logLevelDescription(LogLevel level) {
    return switch (level) {
      LogLevel.debug => 'Detailed diagnostic information',
      LogLevel.info => 'General informational messages',
      LogLevel.warning => 'Potential issues',
      LogLevel.error => 'Errors only',
    };
  }

  // ── Export Logs ──────────────────────────────────────────────────────────

  Future<void> _handleExportLogs(BuildContext context) async {
    if (!mounted) return;

    final logs = AppLogger.exportLogs();
    if (logs.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No logs to export')),
      );
      return;
    }

    try {
      final timestamp = DateTime.now().toIso8601String().replaceAll(':', '-');
      final filename = 'cybervpn_logs_$timestamp.txt';

      await Share.share(
        logs,
        subject: 'CyberVPN Logs',
        sharePositionOrigin: _getSharePositionOrigin(context),
      );

      AppLogger.info('Logs exported: $filename');
    } catch (e) {
      AppLogger.error('Failed to export logs', error: e);
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to export logs: $e')),
      );
    }
  }

  /// Returns the share sheet position origin for iPad/tablet.
  Rect? _getSharePositionOrigin(BuildContext context) {
    final box = context.findRenderObject() as RenderBox?;
    if (box == null) return null;

    return box.localToGlobal(Offset.zero) & box.size;
  }

  // ── Clear Cache ──────────────────────────────────────────────────────────

  Future<void> _handleClearCache(BuildContext context) async {
    if (!mounted) return;

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Clear Cache?'),
        content: const Text(
          'This will remove cached server lists and VPN configurations. '
          'Your settings will not be affected.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Clear'),
          ),
        ],
      ),
    );

    if (confirmed != true || !mounted) return;

    try {
      // Clear SharedPreferences cache (except settings)
      final prefs = await SharedPreferences.getInstance();
      final keys = prefs.getKeys().where((key) {
        // Preserve settings and onboarding state
        return !key.startsWith('settings_') &&
               !key.startsWith('onboarding_') &&
               !key.startsWith('auth_');
      }).toList();

      for (final key in keys) {
        await prefs.remove(key);
      }

      // Clear AppLogger ring buffer
      AppLogger.clearLogs();

      AppLogger.info('Cache cleared successfully');

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Cache cleared successfully')),
      );
    } catch (e) {
      AppLogger.error('Failed to clear cache', error: e);
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to clear cache: $e')),
      );
    }
  }

  // ── Reset Settings ───────────────────────────────────────────────────────

  Future<void> _handleResetSettings(BuildContext context) async {
    if (!mounted) return;

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Reset All Settings?'),
        content: const Text(
          'This will restore all settings to their default values. '
          'This action cannot be undone.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            style: FilledButton.styleFrom(
              backgroundColor: Theme.of(context).colorScheme.error,
            ),
            child: const Text('Reset'),
          ),
        ],
      ),
    );

    if (confirmed != true || !mounted) return;

    try {
      await ref.read(settingsProvider.notifier).resetAll();

      AppLogger.info('Settings reset to defaults');

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Settings reset successfully')),
      );
    } catch (e) {
      AppLogger.error('Failed to reset settings', error: e);
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to reset settings: $e')),
      );
    }
  }

  // ── Version Tap Handler (7-tap easter egg) ──────────────────────────────

  void _handleVersionTap() {
    setState(() {
      _versionTapCount++;
    });

    // Reset counter after 2 seconds of inactivity
    Future.delayed(const Duration(seconds: 2), () {
      if (mounted && _versionTapCount > 0 && _versionTapCount < 7) {
        setState(() {
          _versionTapCount = 0;
        });
      }
    });

    // Activate developer mode on 7th tap
    if (_versionTapCount >= 7 && !_developerModeEnabled) {
      setState(() {
        _developerModeEnabled = true;
        _versionTapCount = 0;
      });

      AppLogger.info('Developer mode activated');

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Developer mode activated'),
            duration: Duration(seconds: 2),
          ),
        );
      }
    }
  }

  // ── Developer Panel ──────────────────────────────────────────────────────

  Widget _buildDeveloperPanel(BuildContext context) {
    return SettingsSection(
      title: 'Developer Options',
      children: [
        SettingsTile.navigation(
          key: const Key('tile_developer_raw_config'),
          title: 'Raw VPN Config Viewer',
          subtitle: 'View current Xray configuration',
          leading: const Icon(Icons.code_outlined),
          onTap: () => _handleRawConfigViewer(context),
        ),
        SettingsTile.navigation(
          key: const Key('tile_developer_force_crash'),
          title: 'Force Crash (Sentry Test)',
          subtitle: 'Test error reporting',
          leading: const Icon(Icons.warning_amber_outlined),
          onTap: () => _handleForceCrash(context),
        ),
        SettingsTile.toggle(
          key: const Key('tile_developer_experimental'),
          title: 'Experimental Features',
          subtitle: 'Enable unreleased features',
          leading: const Icon(Icons.science_outlined),
          value: _experimentalFeaturesEnabled,
          onChanged: (value) => _handleExperimentalToggle(value as bool),
        ),
      ],
    );
  }

  // ── Developer Panel Actions ──────────────────────────────────────────────

  void _handleRawConfigViewer(BuildContext context) {
    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Raw VPN Config'),
        content: SingleChildScrollView(
          child: SelectableText(
            _getRawConfig(),
            style: const TextStyle(fontFamily: 'monospace', fontSize: 12),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Close'),
          ),
          FilledButton.tonal(
            onPressed: () async {
              await Share.share(
                _getRawConfig(),
                subject: 'VPN Configuration',
                sharePositionOrigin: _getSharePositionOrigin(context),
              );
            },
            child: const Text('Share'),
          ),
        ],
      ),
    );
  }

  String _getRawConfig() {
    // In a real implementation, this would retrieve the current Xray config
    // from the VPN engine. For now, return a placeholder.
    return '''
{
  "log": {
    "loglevel": "info"
  },
  "inbounds": [
    {
      "port": 10808,
      "protocol": "socks",
      "settings": {
        "auth": "noauth",
        "udp": true
      }
    }
  ],
  "outbounds": [
    {
      "protocol": "vless",
      "settings": {
        "vnext": [
          {
            "address": "example.com",
            "port": 443,
            "users": [
              {
                "id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                "encryption": "none"
              }
            ]
          }
        ]
      },
      "streamSettings": {
        "network": "ws",
        "security": "tls"
      }
    }
  ]
}

Note: This is a placeholder config. Real implementation would
retrieve the active configuration from the VPN engine.
''';
  }

  void _handleForceCrash(BuildContext context) {
    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Force Crash'),
        content: const Text(
          'This will intentionally crash the app to test error reporting '
          'via Sentry. Only use this for debugging purposes.\n\n'
          'Are you sure you want to continue?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () {
              Navigator.pop(context);
              AppLogger.error('Test crash triggered from developer panel');

              // Delay to allow dialog to close and log to be recorded
              Future.delayed(const Duration(milliseconds: 500), () {
                throw Exception('Test crash from developer panel');
              });
            },
            style: FilledButton.styleFrom(
              backgroundColor: Theme.of(context).colorScheme.error,
            ),
            child: const Text('Crash Now'),
          ),
        ],
      ),
    );
  }

  void _handleExperimentalToggle(bool value) {
    setState(() {
      _experimentalFeaturesEnabled = value;
    });

    AppLogger.info('Experimental features ${value ? 'enabled' : 'disabled'}');

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          'Experimental features ${value ? 'enabled' : 'disabled'}',
        ),
      ),
    );
  }
}
