import 'package:cybervpn_mobile/features/settings/domain/entities/routing_profile.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('RoutingRule', () {
    test('serializes to storage json and back', () {
      const rule = RoutingRule(
        id: 'rule-1',
        matchType: RoutingRuleMatchType.domainSuffix,
        value: 'netflix.com',
        action: RoutingRuleAction.direct,
        note: 'Bypass streaming',
      );

      final json = rule.toStorageJson();
      final restored = RoutingRule.fromStorageJson(json);

      expect(restored, rule);
    });

    test('falls back to safe defaults for invalid enum values', () {
      final restored = RoutingRule.fromStorageJson({
        'id': 'rule-1',
        'matchType': 'invalid',
        'value': 'example.com',
        'action': 'invalid',
      });

      expect(restored.matchType, RoutingRuleMatchType.domain);
      expect(restored.action, RoutingRuleAction.proxy);
      expect(restored.enabled, isTrue);
    });
  });

  group('RoutingProfile', () {
    test('serializes nested rules to storage json and back', () {
      const profile = RoutingProfile(
        id: 'profile-1',
        name: 'Media Bypass',
        description: 'Send media domains direct',
        rules: [
          RoutingRule(
            id: 'rule-1',
            matchType: RoutingRuleMatchType.domainSuffix,
            value: 'youtube.com',
            action: RoutingRuleAction.direct,
          ),
          RoutingRule(
            id: 'rule-2',
            matchType: RoutingRuleMatchType.geoSite,
            value: 'category-ads-all',
            action: RoutingRuleAction.block,
          ),
        ],
      );

      final json = profile.toStorageJson();
      final restored = RoutingProfile.fromStorageJson(json);

      expect(restored, profile);
    });

    test('ignores invalid rules payload and returns empty rules list', () {
      final restored = RoutingProfile.fromStorageJson({
        'id': 'profile-1',
        'name': 'Broken',
        'rules': 'not-a-list',
      });

      expect(restored.rules, isEmpty);
      expect(restored.enabled, isTrue);
    });
  });
}
