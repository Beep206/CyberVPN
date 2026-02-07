import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/onboarding/presentation/providers/onboarding_provider.dart';
import 'package:cybervpn_mobile/features/onboarding/presentation/widgets/onboarding_page_widget.dart';
import 'package:cybervpn_mobile/features/onboarding/presentation/widgets/page_indicator.dart';

/// Full-screen onboarding carousel displayed on first launch.
///
/// Contains 4 swipeable pages with placeholder icons, a page indicator,
/// a Skip button (pages 0-2), and a Get Started button (page 3).
/// On completion or skip, the user is navigated to the auth screen.
class OnboardingScreen extends ConsumerStatefulWidget {
  const OnboardingScreen({super.key});

  @override
  ConsumerState<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends ConsumerState<OnboardingScreen> {
  late final PageController _pageController;
  int _currentPageIndex = 0;

  @override
  void initState() {
    super.initState();
    _pageController = PageController();
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  void _onPageChanged(int index) {
    setState(() {
      _currentPageIndex = index;
    });
  }

  Future<void> _handleSkip() async {
    try {
      await ref.read(onboardingProvider.notifier).skip();
      if (mounted) {
        context.go('/permissions');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$e')),
        );
      }
    }
  }

  Future<void> _handleGetStarted() async {
    try {
      await ref.read(onboardingProvider.notifier).complete();
      if (mounted) {
        context.go('/permissions');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final asyncState = ref.watch(onboardingProvider);

    return Scaffold(
      body: SafeArea(
        child: asyncState.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (error, _) => Center(
            child: Text('${AppLocalizations.of(context).errorOccurred}: $error'),
          ),
          data: (state) => _buildContent(context, state),
        ),
      ),
    );
  }

  Widget _buildContent(BuildContext context, OnboardingState state) {
    final l10n = AppLocalizations.of(context);
    final pages = state.pages;
    if (pages.isEmpty) {
      return Center(child: Text(l10n.onboardingNoPages));
    }

    return Column(
      children: [
        // -- Skip button (top-right, visible on pages 0 through N-2) --
        Align(
          alignment: AlignmentDirectional.topEnd,
          child: Padding(
            padding: const EdgeInsetsDirectional.only(
              top: Spacing.sm,
              end: Spacing.md,
            ),
            child: AnimatedOpacity(
              opacity: _currentPageIndex >= pages.length - 1 ? 0.0 : 1.0,
              duration: AnimDurations.normal,
              child: IgnorePointer(
                ignoring: _currentPageIndex >= pages.length - 1,
                child: TextButton(
                  onPressed: _handleSkip,
                  child: Text(l10n.onboardingSkip),
                ),
              ),
            ),
          ),
        ),

        // -- Page content --
        Expanded(
          child: PageView.builder(
            controller: _pageController,
            itemCount: pages.length,
            onPageChanged: _onPageChanged,
            itemBuilder: (context, index) {
              return OnboardingPageWidget(
                page: pages[index],
                pageIndex: index,
              );
            },
          ),
        ),

        // -- Bottom controls --
        Padding(
          padding: const EdgeInsets.only(
            bottom: Spacing.xl,
            left: Spacing.xl,
            right: Spacing.xl,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Page indicator dots
              PageIndicator(
                pageCount: pages.length,
                currentPage: _currentPageIndex,
              ),
              const SizedBox(height: Spacing.lg),

              // Get Started button (visible only on last page)
              AnimatedSwitcher(
                duration: AnimDurations.normal,
                child: _currentPageIndex >= pages.length - 1
                    ? SizedBox(
                        key: const ValueKey('get-started'),
                        width: double.infinity,
                        child: ElevatedButton(
                          onPressed: _handleGetStarted,
                          child: Text(l10n.onboardingGetStarted),
                        ),
                      )
                    : const SizedBox(
                        key: ValueKey('spacer'),
                        height: 48,
                      ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
