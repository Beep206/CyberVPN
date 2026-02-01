import 'package:cybervpn_mobile/features/auth/domain/entities/user_entity.dart';
import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/plan_entity.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/subscription_entity.dart';
import 'package:cybervpn_mobile/features/config_import/domain/entities/imported_config.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/vpn_config_entity.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/connection_state_entity.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/connection_stats_entity.dart';

/// Factory methods for creating test entity instances with sensible defaults.
///
/// All parameters can be overridden for specific test scenarios.

UserEntity createMockUser({
  String id = 'user-001',
  String email = 'test@example.com',
  String? username = 'testuser',
  String? avatarUrl,
  String? telegramId,
  bool isEmailVerified = true,
  bool isPremium = false,
  String? referralCode = 'REF123',
  DateTime? createdAt,
  DateTime? lastLoginAt,
}) {
  return UserEntity(
    id: id,
    email: email,
    username: username,
    avatarUrl: avatarUrl,
    telegramId: telegramId,
    isEmailVerified: isEmailVerified,
    isPremium: isPremium,
    referralCode: referralCode,
    createdAt: createdAt ?? DateTime(2026, 1, 1),
    lastLoginAt: lastLoginAt ?? DateTime(2026, 1, 31),
  );
}

/// Creates a premium user with all fields populated.
UserEntity createMockPremiumUser({String id = 'user-premium-001'}) {
  return createMockUser(
    id: id,
    email: 'premium@example.com',
    username: 'premiumuser',
    isPremium: true,
    isEmailVerified: true,
    telegramId: '123456789',
  );
}

ServerEntity createMockServer({
  String id = 'server-001',
  String name = 'US East 1',
  String countryCode = 'US',
  String countryName = 'United States',
  String city = 'New York',
  String address = '203.0.113.1',
  int port = 443,
  String protocol = 'vless',
  bool isAvailable = true,
  bool isPremium = false,
  bool isFavorite = false,
  int? ping = 45,
  double? load = 0.35,
}) {
  return ServerEntity(
    id: id,
    name: name,
    countryCode: countryCode,
    countryName: countryName,
    city: city,
    address: address,
    port: port,
    protocol: protocol,
    isAvailable: isAvailable,
    isPremium: isPremium,
    isFavorite: isFavorite,
    ping: ping,
    load: load,
  );
}

/// Creates a list of mock servers across different regions.
List<ServerEntity> createMockServerList({int count = 5}) {
  final configs = [
    ('US', 'United States', 'New York', 'vless'),
    ('DE', 'Germany', 'Frankfurt', 'vmess'),
    ('JP', 'Japan', 'Tokyo', 'trojan'),
    ('NL', 'Netherlands', 'Amsterdam', 'vless'),
    ('SG', 'Singapore', 'Singapore', 'shadowsocks'),
    ('GB', 'United Kingdom', 'London', 'vless'),
    ('CA', 'Canada', 'Toronto', 'vmess'),
    ('AU', 'Australia', 'Sydney', 'trojan'),
  ];

  return List.generate(count.clamp(1, configs.length), (i) {
    final (code, country, city, proto) = configs[i];
    return createMockServer(
      id: 'server-${i + 1}'.padLeft(3, '0'),
      name: '$city ${i + 1}',
      countryCode: code,
      countryName: country,
      city: city,
      protocol: proto,
      address: '203.0.113.${i + 1}',
      ping: 20 + (i * 15),
      load: 0.1 + (i * 0.1),
    );
  });
}

PlanEntity createMockPlan({
  String id = 'plan-monthly-001',
  String name = 'Monthly Pro',
  String description = 'Full access for 30 days',
  double price = 9.99,
  String currency = 'USD',
  PlanDuration duration = PlanDuration.monthly,
  int durationDays = 30,
  int maxDevices = 5,
  int trafficLimitGb = 100,
  bool isPopular = false,
  bool isTrial = false,
  String? storeProductId,
  List<String>? features,
}) {
  return PlanEntity(
    id: id,
    name: name,
    description: description,
    price: price,
    currency: currency,
    duration: duration,
    durationDays: durationDays,
    maxDevices: maxDevices,
    trafficLimitGb: trafficLimitGb,
    isPopular: isPopular,
    isTrial: isTrial,
    storeProductId: storeProductId,
    features: features ?? ['Unlimited bandwidth', 'All servers', 'Kill switch'],
  );
}

/// Creates a list of plans covering all durations.
List<PlanEntity> createMockPlanList() {
  return [
    createMockPlan(
      id: 'plan-trial',
      name: 'Free Trial',
      description: '7-day free trial',
      price: 0.0,
      duration: PlanDuration.monthly,
      durationDays: 7,
      maxDevices: 1,
      trafficLimitGb: 5,
      isTrial: true,
    ),
    createMockPlan(
      id: 'plan-monthly',
      name: 'Monthly',
      description: 'Monthly subscription',
      price: 9.99,
      duration: PlanDuration.monthly,
      durationDays: 30,
      isPopular: true,
    ),
    createMockPlan(
      id: 'plan-quarterly',
      name: 'Quarterly',
      description: '3-month subscription',
      price: 24.99,
      duration: PlanDuration.quarterly,
      durationDays: 90,
    ),
    createMockPlan(
      id: 'plan-yearly',
      name: 'Yearly',
      description: 'Annual subscription',
      price: 79.99,
      duration: PlanDuration.yearly,
      durationDays: 365,
      maxDevices: 10,
      trafficLimitGb: 500,
    ),
  ];
}

SubscriptionEntity createMockSubscription({
  String id = 'sub-001',
  String planId = 'plan-monthly-001',
  String userId = 'user-001',
  SubscriptionStatus status = SubscriptionStatus.active,
  DateTime? startDate,
  DateTime? endDate,
  int trafficUsedBytes = 5368709120, // ~5 GB
  int trafficLimitBytes = 107374182400, // ~100 GB
  int devicesConnected = 1,
  int maxDevices = 5,
  String? subscriptionLink,
  DateTime? cancelledAt,
}) {
  return SubscriptionEntity(
    id: id,
    planId: planId,
    userId: userId,
    status: status,
    startDate: startDate ?? DateTime(2026, 1, 1),
    endDate: endDate ?? DateTime(2026, 2, 1),
    trafficUsedBytes: trafficUsedBytes,
    trafficLimitBytes: trafficLimitBytes,
    devicesConnected: devicesConnected,
    maxDevices: maxDevices,
    subscriptionLink: subscriptionLink,
    cancelledAt: cancelledAt,
  );
}

/// Creates an expired subscription for testing edge cases.
SubscriptionEntity createMockExpiredSubscription() {
  return createMockSubscription(
    id: 'sub-expired-001',
    status: SubscriptionStatus.expired,
    startDate: DateTime(2025, 11, 1),
    endDate: DateTime(2025, 12, 1),
  );
}

ImportedConfig createMockImportedConfig({
  String id = 'config-001',
  String name = 'Test VLESS Server',
  String rawUri = 'vless://uuid@example.com:443?security=tls&type=tcp#TestServer',
  String protocol = 'vless',
  String serverAddress = 'example.com',
  int port = 443,
  ImportSource source = ImportSource.clipboard,
  String? subscriptionUrl,
  DateTime? importedAt,
  DateTime? lastTestedAt,
  bool? isReachable,
}) {
  return ImportedConfig(
    id: id,
    name: name,
    rawUri: rawUri,
    protocol: protocol,
    serverAddress: serverAddress,
    port: port,
    source: source,
    subscriptionUrl: subscriptionUrl,
    importedAt: importedAt ?? DateTime(2026, 1, 15),
    lastTestedAt: lastTestedAt,
    isReachable: isReachable,
  );
}

VpnConfigEntity createMockVpnConfig({
  String id = 'vpn-config-001',
  String name = 'US East VLESS',
  String serverAddress = '203.0.113.1',
  int port = 443,
  VpnProtocol protocol = VpnProtocol.vless,
  String configData = '{"id":"test-uuid","address":"203.0.113.1","port":443}',
  String? remark,
  bool isFavorite = false,
}) {
  return VpnConfigEntity(
    id: id,
    name: name,
    serverAddress: serverAddress,
    port: port,
    protocol: protocol,
    configData: configData,
    remark: remark,
    isFavorite: isFavorite,
  );
}

ConnectionStateEntity createMockConnectionState({
  VpnConnectionStatus status = VpnConnectionStatus.disconnected,
  String? connectedServerId,
  DateTime? connectedAt,
  String? errorMessage,
  int downloadSpeed = 0,
  int uploadSpeed = 0,
  int totalDownload = 0,
  int totalUpload = 0,
}) {
  return ConnectionStateEntity(
    status: status,
    connectedServerId: connectedServerId,
    connectedAt: connectedAt,
    errorMessage: errorMessage,
    downloadSpeed: downloadSpeed,
    uploadSpeed: uploadSpeed,
    totalDownload: totalDownload,
    totalUpload: totalUpload,
  );
}

ConnectionStatsEntity createMockConnectionStats({
  int downloadSpeed = 1024000,
  int uploadSpeed = 512000,
  int totalDownload = 104857600,
  int totalUpload = 52428800,
  Duration connectionDuration = const Duration(hours: 1, minutes: 30),
  String? serverName = 'US East 1',
  String? protocol = 'vless',
  String? ipAddress = '203.0.113.1',
}) {
  return ConnectionStatsEntity(
    downloadSpeed: downloadSpeed,
    uploadSpeed: uploadSpeed,
    totalDownload: totalDownload,
    totalUpload: totalUpload,
    connectionDuration: connectionDuration,
    serverName: serverName,
    protocol: protocol,
    ipAddress: ipAddress,
  );
}
