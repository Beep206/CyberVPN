import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:cybervpn_mobile/shared/services/tooltip_preferences_service.dart';

void main() {
  group('TooltipPreferencesService', () {
    late TooltipPreferencesService service;

    setUp(() async {
      // Initialize with empty SharedPreferences
      SharedPreferences.setMockInitialValues({});
      service = TooltipPreferencesService();
      await service.initialize();
    });

    test('hasShownTooltip returns false initially', () async {
      final hasShown = await service.hasShownTooltip('test_tooltip');
      expect(hasShown, isFalse);
    });

    test('markTooltipAsShown sets the flag correctly', () async {
      const tooltipId = 'test_tooltip';

      // Initially not shown
      expect(await service.hasShownTooltip(tooltipId), isFalse);

      // Mark as shown
      await service.markTooltipAsShown(tooltipId);

      // Now should be shown
      expect(await service.hasShownTooltip(tooltipId), isTrue);
    });

    test('hasShownTooltip returns true after marking', () async {
      const tooltipId = 'another_tooltip';

      await service.markTooltipAsShown(tooltipId);
      final hasShown = await service.hasShownTooltip(tooltipId);

      expect(hasShown, isTrue);
    });

    test('resetTooltip clears a specific tooltip', () async {
      const tooltipId = 'reset_test';

      // Mark as shown
      await service.markTooltipAsShown(tooltipId);
      expect(await service.hasShownTooltip(tooltipId), isTrue);

      // Reset the tooltip
      await service.resetTooltip(tooltipId);
      expect(await service.hasShownTooltip(tooltipId), isFalse);
    });

    test('resetAllTooltips clears all tooltips', () async {
      const tooltip1 = 'tooltip_1';
      const tooltip2 = 'tooltip_2';
      const tooltip3 = 'tooltip_3';

      // Mark all as shown
      await service.markTooltipAsShown(tooltip1);
      await service.markTooltipAsShown(tooltip2);
      await service.markTooltipAsShown(tooltip3);

      expect(await service.hasShownTooltip(tooltip1), isTrue);
      expect(await service.hasShownTooltip(tooltip2), isTrue);
      expect(await service.hasShownTooltip(tooltip3), isTrue);

      // Reset all
      await service.resetAllTooltips();

      expect(await service.hasShownTooltip(tooltip1), isFalse);
      expect(await service.hasShownTooltip(tooltip2), isFalse);
      expect(await service.hasShownTooltip(tooltip3), isFalse);
    });

    test('multiple tooltips can be tracked independently', () async {
      const tooltip1 = 'servers_fastest_button';
      const tooltip2 = 'connection_speed_monitor';

      await service.markTooltipAsShown(tooltip1);

      expect(await service.hasShownTooltip(tooltip1), isTrue);
      expect(await service.hasShownTooltip(tooltip2), isFalse);

      await service.markTooltipAsShown(tooltip2);

      expect(await service.hasShownTooltip(tooltip1), isTrue);
      expect(await service.hasShownTooltip(tooltip2), isTrue);
    });
  });
}
