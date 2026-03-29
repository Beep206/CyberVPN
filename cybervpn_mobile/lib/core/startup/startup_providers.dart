import 'package:flutter_riverpod/flutter_riverpod.dart';

class DeferredStartupReadyNotifier extends Notifier<bool> {
  @override
  bool build() => false;

  void markReady() => state = true;
}

/// Whether deferred startup services have finished initializing.
///
/// This flips to `true` after the app has rendered its first frame and the
/// non-critical startup pipeline has completed. Widgets can use it to delay
/// expensive listeners and integrations until the app is visually ready.
final deferredStartupReadyProvider =
    NotifierProvider<DeferredStartupReadyNotifier, bool>(
      DeferredStartupReadyNotifier.new,
    );
