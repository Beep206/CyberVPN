import 'package:flutter/material.dart';
import 'dart:async';

import 'package:cybervpn_mobile/app/theme/tokens.dart';

/// A widget that animates its child with a staggered fade-slide animation.
///
/// Use this to wrap list items for a staggered reveal effect when the list
/// first loads. The animation respects [MediaQuery.disableAnimations].
///
/// Example:
/// ```dart
/// ListView.builder(
///   itemCount: items.length,
///   itemBuilder: (context, index) {
///     return StaggeredListItem(
///       index: index,
///       child: MyListTile(item: items[index]),
///     );
///   },
/// )
/// ```
class StaggeredListItem extends StatefulWidget {
  const StaggeredListItem({
    super.key,
    required this.index,
    required this.child,
    this.baseDelay = const Duration(milliseconds: 50),
    this.duration = AnimDurations.normal,
    this.curve = Curves.easeOutCubic,
    this.slideOffset = const Offset(0, 0.1),
  });

  /// The index of this item in the list (used to calculate stagger delay).
  final int index;

  /// The widget to animate.
  final Widget child;

  /// Base delay between each item's animation start.
  final Duration baseDelay;

  /// Duration of the animation.
  final Duration duration;

  /// Animation curve.
  final Curve curve;

  /// Initial offset as a fraction of the widget's size.
  final Offset slideOffset;

  @override
  State<StaggeredListItem> createState() => _StaggeredListItemState();
}

class _StaggeredListItemState extends State<StaggeredListItem>
    with SingleTickerProviderStateMixin {
  /// Maximum number of items to animate. Items beyond this index render
  /// immediately to avoid allocating controllers for large lists.
  static const _maxAnimatedItems = 10;

  AnimationController? _controller;
  Animation<double>? _opacity;
  Animation<Offset>? _slide;

  bool get _shouldAnimate => widget.index < _maxAnimatedItems;

  @override
  void initState() {
    super.initState();

    if (!_shouldAnimate) return;

    _controller = AnimationController(
      duration: widget.duration,
      vsync: this,
    );

    final curved = CurvedAnimation(
      parent: _controller!,
      curve: widget.curve,
    );

    _opacity = Tween<double>(begin: 0, end: 1).animate(curved);
    _slide = Tween<Offset>(
      begin: widget.slideOffset,
      end: Offset.zero,
    ).animate(curved);

    unawaited(_startAnimation());
  }

  Future<void> _startAnimation() async {
    final delay = widget.baseDelay * widget.index;
    await Future<void>.delayed(delay);

    if (mounted) {
      unawaited(_controller?.forward());
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!_shouldAnimate) return widget.child;

    final disableAnimations = MediaQuery.of(context).disableAnimations;
    if (disableAnimations) return widget.child;

    return SlideTransition(
      position: _slide!,
      child: FadeTransition(
        opacity: _opacity!,
        child: widget.child,
      ),
    );
  }
}

/// A widget that conditionally applies animations based on accessibility settings.
///
/// Wraps standard animation widgets and bypasses them when
/// [MediaQuery.disableAnimations] is true.
class AnimationAware extends StatelessWidget {
  const AnimationAware({
    super.key,
    required this.child,
    required this.animatedChild,
  });

  /// The static version of the child (no animation).
  final Widget child;

  /// The animated version of the child.
  final Widget animatedChild;

  @override
  Widget build(BuildContext context) {
    final disableAnimations = MediaQuery.of(context).disableAnimations;
    return disableAnimations ? child : animatedChild;
  }
}

/// Extension methods for animation-aware durations.
extension AnimationDurationExtension on Duration {
  /// Returns [Duration.zero] if animations are disabled, otherwise returns this duration.
  Duration accessibilityAware(BuildContext context) {
    final disableAnimations = MediaQuery.of(context).disableAnimations;
    return disableAnimations ? Duration.zero : this;
  }
}
