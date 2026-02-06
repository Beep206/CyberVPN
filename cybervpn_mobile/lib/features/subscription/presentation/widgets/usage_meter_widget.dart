import 'package:flutter/material.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/utils/data_formatters.dart';

class UsageMeterWidget extends StatelessWidget {
  final int usedBytes;
  final int totalBytes;

  const UsageMeterWidget({
    super.key,
    required this.usedBytes,
    required this.totalBytes,
  });

  double get usagePercent => totalBytes > 0 ? usedBytes / totalBytes : 0;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(l10n.subscriptionDataUsage, style: theme.textTheme.titleMedium),
            Text('${DataFormatters.formatBytes(usedBytes)} / ${DataFormatters.formatBytes(totalBytes)}',
              style: theme.textTheme.bodyMedium),
          ],
        ),
        const SizedBox(height: 8),
        ClipRRect(
          borderRadius: BorderRadius.circular(8),
          child: LinearProgressIndicator(
            value: usagePercent.clamp(0.0, 1.0),
            minHeight: 8,
            backgroundColor: theme.colorScheme.surfaceContainerHighest,
          ),
        ),
        const SizedBox(height: 4),
        Text(l10n.subscriptionPercentUsed(DataFormatters.formatPercentage(usagePercent)),
          style: theme.textTheme.bodySmall),
      ],
    );
  }
}
