import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import 'package:cybervpn_mobile/core/haptics/haptic_service.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/config_import/domain/entities/imported_config.dart';
import 'package:cybervpn_mobile/features/config_import/domain/entities/parsed_config.dart';
import 'package:cybervpn_mobile/features/config_import/domain/parsers/vpn_uri_parser.dart';
import 'package:cybervpn_mobile/features/config_import/domain/usecases/parse_vpn_uri.dart';
import 'package:cybervpn_mobile/features/config_import/presentation/providers/config_import_provider.dart';

// ---------------------------------------------------------------------------
// QR Scanner Screen
// ---------------------------------------------------------------------------

/// Full-screen QR code scanner for importing VPN configurations.
///
/// Uses [MobileScanner] from mobile_scanner 7.x to provide a camera preview
/// with an animated scan-line overlay, flash toggle, and front/back camera
/// toggle. On successful scan of a VPN URI, shows a preview bottom sheet
/// where the user can add the server or scan another QR code.
class QrScannerScreen extends ConsumerStatefulWidget {
  const QrScannerScreen({super.key});

  @override
  ConsumerState<QrScannerScreen> createState() => _QrScannerScreenState();
}

class _QrScannerScreenState extends ConsumerState<QrScannerScreen>
    with SingleTickerProviderStateMixin {
  late final MobileScannerController _scannerController;
  late final AnimationController _animationController;
  StreamSubscription<BarcodeCapture>? _barcodeSubscription;

  final _parseVpnUri = ParseVpnUri();

  /// Whether the scanner is currently paused (e.g. while showing the
  /// preview bottom sheet).
  bool _isPaused = false;

  /// Whether we are currently processing a detected barcode.
  bool _isProcessing = false;

  // ── Lifecycle ─────────────────────────────────────────────────────────────

  @override
  void initState() {
    super.initState();

    _scannerController = MobileScannerController(
      formats: const [BarcodeFormat.qrCode],
      detectionSpeed: DetectionSpeed.normal,
      autoStart: true,
    );

    _animationController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    );
    unawaited(_animationController.repeat(reverse: true));

    _barcodeSubscription = _scannerController.barcodes.listen(
      _handleBarcodeCapture,
    );
  }

  @override
  void dispose() {
    unawaited(_barcodeSubscription?.cancel());
    _animationController.dispose();
    unawaited(_scannerController.dispose());
    super.dispose();
  }

  // ── Barcode handling ──────────────────────────────────────────────────────

  /// Called when the scanner detects one or more barcodes.
  void _handleBarcodeCapture(BarcodeCapture capture) {
    if (_isPaused || _isProcessing || !mounted) return;

    final barcode = capture.barcodes.firstOrNull;
    if (barcode == null) return;

    final rawValue = barcode.rawValue;
    if (rawValue == null || rawValue.trim().isEmpty) return;

    _isProcessing = true;
    _processDetectedValue(rawValue.trim());
  }

  /// Process the detected barcode value.
  ///
  /// Attempts to parse as a VPN URI. On success, pauses the scanner and
  /// shows a config preview bottom sheet. On failure, shows an error
  /// snackbar and resumes scanning.
  void _processDetectedValue(String value) {
    final result = _parseVpnUri.call(value);

    switch (result) {
      case ParseSuccess(:final config):
        _pauseScanner();
        _showConfigPreviewSheet(config, value);

      case ParseFailure(:final message):
        AppLogger.debug('Invalid QR: $message');
        _showErrorSnackbar('Not a valid VPN configuration');
        _isProcessing = false;
    }
  }

  // ── Scanner controls ──────────────────────────────────────────────────────

  void _pauseScanner() {
    setState(() => _isPaused = true);
    unawaited(_scannerController.stop());
  }

  void _resumeScanner() {
    if (!mounted) return;
    unawaited(_scannerController.start());
    setState(() {
      _isPaused = false;
      _isProcessing = false;
    });
  }

  Future<void> _toggleFlash() async {
    try {
      await _scannerController.toggleTorch();
      if (mounted) setState(() {});
    } catch (e) {
      AppLogger.debug('Flash toggle failed', error: e);
    }
  }

  Future<void> _switchCamera() async {
    try {
      await _scannerController.switchCamera();
      if (mounted) setState(() {});
    } catch (e) {
      AppLogger.debug('Camera switch failed', error: e);
    }
  }

  // ── UI feedback ───────────────────────────────────────────────────────────

  void _showErrorSnackbar(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        behavior: SnackBarBehavior.floating,
        duration: const Duration(seconds: 2),
      ),
    );
  }

  // ── Config preview bottom sheet ───────────────────────────────────────────

  void _showConfigPreviewSheet(ParsedConfig config, String rawUri) {
    unawaited(showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (sheetContext) => _ConfigPreviewSheet(
        config: config,
        rawUri: rawUri,
        onAddServer: () => _addServer(rawUri, sheetContext),
        onScanAnother: () {
          Navigator.of(sheetContext).pop();
          _resumeScanner();
        },
      ),
    ).whenComplete(() {
      // If dismissed by swipe rather than button press, resume scanning.
      if (_isPaused) _resumeScanner();
    }));
  }

  Future<void> _addServer(String rawUri, BuildContext sheetContext) async {
    final notifier = ref.read(configImportProvider.notifier);
    final navigator = Navigator.of(sheetContext);
    final rootNavigator = Navigator.of(context);

    final imported = await notifier.importFromUri(
      rawUri,
      source: ImportSource.qrCode,
    );

    if (!mounted) return;

    if (imported != null) {
      // Trigger success haptic when config is successfully imported.
      final haptics = ref.read(hapticServiceProvider);
      unawaited(haptics.success());

      navigator.pop();
      _showErrorSnackbar('Server added: ${imported.name}');
      // Brief delay so the user sees the message before popping.
      Future.delayed(const Duration(milliseconds: 600), () {
        if (mounted) rootNavigator.pop();
      });
    } else {
      // Trigger error haptic when import fails.
      final haptics = ref.read(hapticServiceProvider);
      unawaited(haptics.error());

      _showErrorSnackbar('Failed to add server');
      navigator.pop();
      _resumeScanner();
    }
  }

  // ── Build ─────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          key: const Key('qr_back_button'),
          icon: const Icon(Icons.arrow_back, color: Colors.white),
          onPressed: () => Navigator.of(context).pop(),
        ),
        title: const Text(
          'Scan QR Code',
          style: TextStyle(color: Colors.white),
        ),
        actions: [
          IconButton(
            key: const Key('qr_camera_switch'),
            icon: const Icon(Icons.cameraswitch_outlined, color: Colors.white),
            tooltip: 'Switch camera',
            onPressed: _switchCamera,
          ),
        ],
      ),
      body: Stack(
        children: [
          // Camera preview
          MobileScanner(
            key: const Key('qr_mobile_scanner'),
            controller: _scannerController,
            errorBuilder: (context, error) {
              return _ScannerErrorView(
                error: error,
                onRetry: () {
                  unawaited(_scannerController.start());
                },
              );
            },
          ),

          // Semi-transparent overlay with viewfinder cutout
          _ScanOverlay(
            animation: _animationController,
          ),

          // Bottom controls
          Positioned(
            left: 0,
            right: 0,
            bottom: MediaQuery.of(context).padding.bottom + 32,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                // Flash toggle
                FloatingActionButton(
                  key: const Key('qr_flash_toggle'),
                  heroTag: 'flash',
                  mini: true,
                  backgroundColor:
                      theme.colorScheme.surface.withValues(alpha: 0.8),
                  onPressed: _toggleFlash,
                  child: ValueListenableBuilder<MobileScannerState>(
                    valueListenable: _scannerController,
                    builder: (context, state, child) {
                      return Icon(
                        state.torchState == TorchState.on
                            ? Icons.flash_on
                            : Icons.flash_off,
                        color: state.torchState == TorchState.on
                            ? Colors.amber
                            : theme.colorScheme.onSurface,
                      );
                    },
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Scan Overlay
// ---------------------------------------------------------------------------

/// Animated overlay with a semi-transparent background and a clear viewfinder
/// rectangle. A scan line animates vertically within the viewfinder area.
class _ScanOverlay extends StatelessWidget {
  const _ScanOverlay({required this.animation});

  final AnimationController animation;

  static const double _viewfinderSize = 260;
  static const double _borderRadius = 12;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final viewfinderRect = Rect.fromCenter(
          center: Offset(
            constraints.maxWidth / 2,
            constraints.maxHeight / 2 - 40,
          ),
          width: _viewfinderSize,
          height: _viewfinderSize,
        );

        return Stack(
          children: [
            // Dark overlay with cutout
            CustomPaint(
              size: Size(constraints.maxWidth, constraints.maxHeight),
              painter: _OverlayPainter(
                viewfinderRect: viewfinderRect,
                borderRadius: _borderRadius,
              ),
            ),

            // Viewfinder border corners
            Positioned.fromRect(
              rect: viewfinderRect,
              child: DecoratedBox(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(_borderRadius),
                  border: Border.all(
                    color: Colors.white.withValues(alpha: 0.6),
                    width: 2,
                  ),
                ),
              ),
            ),

            // Animated scan line
            AnimatedBuilder(
              animation: animation,
              builder: (context, child) {
                final yOffset = viewfinderRect.top +
                    (animation.value * viewfinderRect.height);
                return Positioned(
                  left: viewfinderRect.left + 8,
                  top: yOffset,
                  width: viewfinderRect.width - 16,
                  child: Container(
                    height: 2,
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: [
                          Colors.greenAccent.withValues(alpha: 0),
                          Colors.greenAccent.withValues(alpha: 0.8),
                          Colors.greenAccent.withValues(alpha: 0),
                        ],
                      ),
                    ),
                  ),
                );
              },
            ),

            // Instruction text below viewfinder
            Positioned(
              left: 0,
              right: 0,
              top: viewfinderRect.bottom + 24,
              child: const Text(
                'Point your camera at a VPN QR code',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: Colors.white70,
                  fontSize: 14,
                ),
              ),
            ),
          ],
        );
      },
    );
  }
}

// ---------------------------------------------------------------------------
// Overlay Painter
// ---------------------------------------------------------------------------

/// Custom painter that draws a semi-transparent overlay with a clear
/// rounded-rectangle cutout for the viewfinder area.
class _OverlayPainter extends CustomPainter {
  _OverlayPainter({
    required this.viewfinderRect,
    required this.borderRadius,
  });

  final Rect viewfinderRect;
  final double borderRadius;

  @override
  void paint(Canvas canvas, Size size) {
    final backgroundPath = Path()
      ..addRect(Offset.zero & size);

    final cutoutPath = Path()
      ..addRRect(
        RRect.fromRectAndRadius(
          viewfinderRect,
          Radius.circular(borderRadius),
        ),
      );

    final overlayPath = Path.combine(
      PathOperation.difference,
      backgroundPath,
      cutoutPath,
    );

    canvas.drawPath(
      overlayPath,
      Paint()..color = Colors.black.withValues(alpha: 0.6),
    );
  }

  @override
  bool shouldRepaint(covariant _OverlayPainter oldDelegate) {
    return oldDelegate.viewfinderRect != viewfinderRect;
  }
}

// ---------------------------------------------------------------------------
// Scanner Error View
// ---------------------------------------------------------------------------

/// Shown when the camera fails to initialize (e.g. permission denied).
class _ScannerErrorView extends StatelessWidget {
  const _ScannerErrorView({
    required this.error,
    required this.onRetry,
  });

  final MobileScannerException error;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final String title;
    final String subtitle;

    switch (error.errorCode) {
      case MobileScannerErrorCode.permissionDenied:
        title = 'Camera Permission Required';
        subtitle =
            'Please grant camera access in your device settings to scan '
            'QR codes.';
      default:
        title = 'Camera Error';
        subtitle = error.errorDetails?.message ?? 'Failed to start camera.';
    }

    return Container(
      color: Colors.black,
      child: Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.videocam_off_outlined,
                size: 64,
                color: theme.colorScheme.error,
              ),
              const SizedBox(height: 16),
              Text(
                title,
                style: theme.textTheme.titleLarge?.copyWith(
                  color: Colors.white,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),
              Text(
                subtitle,
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: Colors.white70,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 24),
              FilledButton.tonal(
                onPressed: onRetry,
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Config Preview Bottom Sheet
// ---------------------------------------------------------------------------

/// Bottom sheet shown after a valid VPN QR code is detected.
///
/// Displays the parsed configuration details and provides actions to
/// add the server or scan another code.
class _ConfigPreviewSheet extends StatelessWidget {
  const _ConfigPreviewSheet({
    required this.config,
    required this.rawUri,
    required this.onAddServer,
    required this.onScanAnother,
  });

  final ParsedConfig config;
  final String rawUri;
  final VoidCallback onAddServer;
  final VoidCallback onScanAnother;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(24, 16, 24, 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Handle bar
            Center(
              child: Container(
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: theme.colorScheme.outline.withValues(alpha: 0.4),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Title
            Text(
              'VPN Configuration Found',
              style: theme.textTheme.titleLarge,
            ),
            const SizedBox(height: 16),

            // Server details card
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Server name
                    _DetailRow(
                      icon: Icons.dns_outlined,
                      label: 'Name',
                      value: config.remark ?? 'Unknown Server',
                    ),
                    const SizedBox(height: 12),

                    // Protocol badge
                    _DetailRow(
                      icon: Icons.shield_outlined,
                      label: 'Protocol',
                      value: config.protocol.toUpperCase(),
                    ),
                    const SizedBox(height: 12),

                    // Address
                    _DetailRow(
                      icon: Icons.language_outlined,
                      label: 'Address',
                      value: '${config.serverAddress}:${config.port}',
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 20),

            // Add server button
            FilledButton.icon(
              key: const Key('qr_add_server_button'),
              onPressed: onAddServer,
              icon: const Icon(Icons.add),
              label: const Text('Add Server'),
            ),
            const SizedBox(height: 8),

            // Scan another button
            OutlinedButton.icon(
              key: const Key('qr_scan_another_button'),
              onPressed: onScanAnother,
              icon: const Icon(Icons.qr_code_scanner),
              label: const Text('Scan Another'),
            ),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Detail Row
// ---------------------------------------------------------------------------

/// A simple row showing an icon, label, and value for the config preview.
class _DetailRow extends StatelessWidget {
  const _DetailRow({
    required this.icon,
    required this.label,
    required this.value,
  });

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Row(
      children: [
        Icon(icon, size: 20, color: theme.colorScheme.primary),
        const SizedBox(width: 12),
        Text(
          '$label: ',
          style: theme.textTheme.bodySmall?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
        Expanded(
          child: Text(
            value,
            style: theme.textTheme.bodyMedium?.copyWith(
              fontWeight: FontWeight.w500,
            ),
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ],
    );
  }
}
