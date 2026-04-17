import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:share_plus/share_plus.dart' as share_plus;

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/di/providers.dart';
import 'package:cybervpn_mobile/core/services/log_file_store.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/core/utils/data_formatters.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/other_settings_providers.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/widgets/settings_section.dart';
import 'package:cybervpn_mobile/features/settings/presentation/widgets/settings_tile.dart';

class LogsCenterScreen extends ConsumerStatefulWidget {
  const LogsCenterScreen({super.key, this.embedded = false});

  final bool embedded;

  @override
  ConsumerState<LogsCenterScreen> createState() => _LogsCenterScreenState();
}

class _LogsCenterScreenState extends ConsumerState<LogsCenterScreen> {
  Future<void> _showLogLevelDialog(LogLevel currentLevel) async {
    await showDialog<void>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('Log Level'),
          content: SingleChildScrollView(
            child: RadioGroup<LogLevel>(
              groupValue: currentLevel,
              onChanged: (LogLevel? value) {
                Navigator.of(dialogContext).pop();
                if (value != null) {
                  unawaited(
                    ref.read(settingsProvider.notifier).updateLogLevel(value),
                  );
                }
              },
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: LogLevel.values
                    .map(
                      (level) => RadioListTile<LogLevel>(
                        value: level,
                        title: Text(_logLevelLabel(level)),
                      ),
                    )
                    .toList(growable: false),
              ),
            ),
          ),
        );
      },
    );
  }

  Future<void> _exportBufferedLogs() async {
    final logs = AppLogger.exportLogs();
    if (logs.isEmpty) {
      return;
    }

    await share_plus.SharePlus.instance.share(
      share_plus.ShareParams(
        text: logs,
        subject: 'CyberVPN buffered logs',
      ),
    );
  }

  Future<void> _clearAllLogs() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('Clear Logs'),
          content: const Text(
            'This removes the in-memory buffer and all persistent log files. This action cannot be undone.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(dialogContext).pop(true),
              child: const Text('Clear'),
            ),
          ],
        );
      },
    );

    if (confirmed != true) {
      return;
    }

    AppLogger.clearLogs();
    await ref.read(logFileStoreProvider).clearPersistentLogs();
    ref.invalidate(logFilesProvider);
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Logs cleared')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final settings = ref.watch(settingsProvider).value ?? const AppSettings();
    final filesAsync = ref.watch(logFilesProvider);
    final bufferCount = AppLogger.entryCount;

    final content = ListView(
      children: [
        SettingsSection(
          title: 'Summary',
          children: [
            SettingsTile.info(
              key: const Key('logs_summary_level'),
              title: 'Effective Log Level',
              subtitle: _logLevelLabel(settings.logLevel),
              leading: const Icon(Icons.tune_outlined),
            ),
            SettingsTile.info(
              key: const Key('logs_summary_buffered'),
              title: 'Buffered Entries',
              subtitle: '$bufferCount live entry(s)',
              leading: const Icon(Icons.memory_outlined),
            ),
            SettingsTile.info(
              key: const Key('logs_summary_files'),
              title: 'Persistent Files',
              subtitle: filesAsync.when(
                data: (files) => '${files.length} file(s)',
                loading: () => 'Scanning files',
                error: (_, _) => 'Unavailable',
              ),
              leading: const Icon(Icons.folder_outlined),
            ),
          ],
        ),
        SettingsSection(
          title: 'Diagnostics',
          children: [
            SettingsTile.navigation(
              key: const Key('logs_log_level'),
              title: 'Log Level',
              subtitle: _logLevelLabel(settings.logLevel),
              leading: const Icon(Icons.settings_suggest_outlined),
              onTap: () => _showLogLevelDialog(settings.logLevel),
            ),
            SettingsTile.navigation(
              key: const Key('logs_view_buffered'),
              title: 'View Buffered Logs',
              subtitle: 'Open the live ring-buffer viewer.',
              leading: const Icon(Icons.article_outlined),
              onTap: () => context.push('/diagnostics/logs'),
            ),
            SettingsTile.navigation(
              key: const Key('logs_export_buffered'),
              title: 'Export Buffered Logs',
              subtitle: 'Share the current in-memory log buffer.',
              leading: const Icon(Icons.upload_file_outlined),
              onTap: _exportBufferedLogs,
            ),
            SettingsTile.navigation(
              key: const Key('logs_clear_all'),
              title: 'Clear All Logs',
              subtitle: 'Remove buffered entries and persistent files.',
              leading: const Icon(Icons.delete_outline),
              onTap: _clearAllLogs,
            ),
          ],
        ),
        SettingsSection(
          title: 'Persistent Files',
          children: filesAsync.when(
            data: (files) => files.isEmpty
                ? [
                    const SettingsTile.info(
                      key: Key('logs_no_files'),
                      title: 'No persistent log files yet',
                      subtitle:
                          'Files will appear after app activity, subscription refresh, or a VPN connect runtime snapshot.',
                      leading: Icon(Icons.hourglass_empty_outlined),
                    ),
                  ]
                : files
                    .map(
                      (file) => SettingsTile.navigation(
                        key: Key('logs_file_${file.name}'),
                        title: file.name,
                        subtitle:
                            '${_kindLabel(file.kind)} • ${DataFormatters.formatBytes(file.sizeBytes)} • ${DataFormatters.formatDate(file.modifiedAt)}',
                        leading: Icon(_iconForKind(file.kind)),
                        onTap: () => context.push(
                          '/settings/other/logs/file',
                          extra: file,
                        ),
                      ),
                    )
                    .toList(growable: false),
            loading: () => const [
              SettingsTile.info(
                title: 'Scanning log files',
                subtitle: 'Loading persistent file inventory.',
                leading: Icon(Icons.folder_open_outlined),
              ),
            ],
            error: (error, _) => [
              SettingsTile.info(
                title: 'Persistent files unavailable',
                subtitle: error.toString(),
                leading: const Icon(Icons.error_outline),
              ),
            ],
          ),
        ),
        SizedBox(height: Spacing.navBarClearance(context)),
      ],
    );

    if (widget.embedded) {
      return content;
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Logs')),
      body: content,
    );
  }

  String _logLevelLabel(LogLevel level) {
    return switch (level) {
      LogLevel.auto => 'Auto',
      LogLevel.debug => 'Debug',
      LogLevel.info => 'Info',
      LogLevel.warning => 'Warning',
      LogLevel.error => 'Error',
      LogLevel.none => 'None',
    };
  }

  String _kindLabel(PersistentLogFileKind kind) {
    return switch (kind) {
      PersistentLogFileKind.access => 'Access',
      PersistentLogFileKind.subscription => 'Subscription',
      PersistentLogFileKind.xraySnapshot => 'Xray snapshot',
    };
  }

  IconData _iconForKind(PersistentLogFileKind kind) {
    return switch (kind) {
      PersistentLogFileKind.access => Icons.receipt_long_outlined,
      PersistentLogFileKind.subscription => Icons.cloud_sync_outlined,
      PersistentLogFileKind.xraySnapshot => Icons.memory_outlined,
    };
  }
}
