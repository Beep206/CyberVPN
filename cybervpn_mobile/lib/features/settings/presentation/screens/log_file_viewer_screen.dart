import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:share_plus/share_plus.dart' as share_plus;

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/services/log_file_store.dart';
import 'package:cybervpn_mobile/core/utils/data_formatters.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/other_settings_providers.dart';

class LogFileViewerScreen extends ConsumerWidget {
  const LogFileViewerScreen({
    required this.file,
    super.key,
  });

  final PersistentLogFile file;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final contentsAsync = ref.watch(logFileContentsProvider(file.path));

    return Scaffold(
      appBar: AppBar(
        title: Text(file.name),
        actions: [
          IconButton(
            icon: const Icon(Icons.share_outlined),
            onPressed: () async {
              final contents = await ref.read(
                logFileContentsProvider(file.path).future,
              );
              if (contents.isEmpty) {
                return;
              }

              await share_plus.SharePlus.instance.share(
                share_plus.ShareParams(
                  text: contents,
                  subject: file.name,
                ),
              );
            },
          ),
        ],
      ),
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.all(Spacing.md),
            child: Wrap(
              spacing: Spacing.sm,
              runSpacing: Spacing.xs,
              children: [
                _MetaChip(label: file.name),
                _MetaChip(label: DataFormatters.formatBytes(file.sizeBytes)),
                _MetaChip(label: DataFormatters.formatDate(file.modifiedAt)),
              ],
            ),
          ),
          const Divider(height: 1),
          Expanded(
            child: contentsAsync.when(
              data: (contents) {
                if (contents.isEmpty) {
                  return const Center(
                    child: Text('This file is empty.'),
                  );
                }

                return SingleChildScrollView(
                  padding: const EdgeInsets.all(Spacing.md),
                  child: SelectableText(
                    contents,
                    style: const TextStyle(
                      fontFamily: 'monospace',
                      fontSize: 12,
                      height: 1.4,
                    ),
                  ),
                );
              },
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (error, _) => Center(child: Text(error.toString())),
            ),
          ),
        ],
      ),
    );
  }
}

class _MetaChip extends StatelessWidget {
  const _MetaChip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(Radii.xl),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: Spacing.sm,
          vertical: Spacing.xs,
        ),
        child: Text(
          label,
          style: Theme.of(context).textTheme.bodySmall,
        ),
      ),
    );
  }
}
