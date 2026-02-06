import 'package:flutter/material.dart';

import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';

class ErrorView extends StatelessWidget {
  final String message;
  final VoidCallback? onRetry;
  final IconData icon;

  const ErrorView({super.key, required this.message, this.onRetry, this.icon = Icons.error_outline});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 64, color: theme.colorScheme.error),
            const SizedBox(height: 16),
            Text(message, style: theme.textTheme.bodyLarge, textAlign: TextAlign.center),
            if (onRetry != null) ...[
              const SizedBox(height: 24),
              ElevatedButton.icon(onPressed: onRetry, icon: const Icon(Icons.refresh), label: Text(AppLocalizations.of(context).retry)),
            ],
          ],
        ),
      ),
    );
  }
}
