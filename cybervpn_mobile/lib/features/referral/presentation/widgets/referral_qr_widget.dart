import 'package:flutter/material.dart';
import 'package:qr_flutter/qr_flutter.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';

// ---------------------------------------------------------------------------
// ReferralQrWidget
// ---------------------------------------------------------------------------

/// Renders a QR code encoding the given [data] string.
///
/// Uses [QrImageView] from `qr_flutter` to generate the code at a fixed size
/// with cyberpunk-themed styling.
class ReferralQrWidget extends StatelessWidget {
  const ReferralQrWidget({
    super.key,
    required this.data,
    this.size = 180,
  });

  /// The data to encode in the QR code (typically a referral link).
  final String data;

  /// The width and height of the QR code widget.
  final double size;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final l10n = AppLocalizations.of(context);

    return Container(
      padding: const EdgeInsets.all(Spacing.md),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(Radii.md),
        border: Border.all(
          color: colorScheme.primary.withAlpha(40),
        ),
      ),
      child: QrImageView(
        data: data,
        version: QrVersions.auto,
        size: size,
        eyeStyle: const QrEyeStyle(
          eyeShape: QrEyeShape.square,
          color: Color(0xFF111827),
        ),
        dataModuleStyle: const QrDataModuleStyle(
          dataModuleShape: QrDataModuleShape.square,
          color: Color(0xFF111827),
        ),
        semanticsLabel: l10n.referralQrCodeSemantics,
      ),
    );
  }
}
