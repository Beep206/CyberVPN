import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

/// Test helper for mocking platform channels used by VPN and system features.
///
/// Usage:
/// ```dart
/// late PlatformChannelMocks mocks;
///
/// setUp(() {
///   mocks = PlatformChannelMocks();
///   mocks.setUp();
/// });
///
/// tearDown(() => mocks.tearDown());
/// ```
class PlatformChannelMocks {
  final List<MethodCall> _vpnCalls = [];
  final List<MethodCall> _killSwitchCalls = [];

  /// All method calls received by the VPN platform channel.
  List<MethodCall> get vpnCalls => List.unmodifiable(_vpnCalls);

  /// All method calls received by the kill switch platform channel.
  List<MethodCall> get killSwitchCalls => List.unmodifiable(_killSwitchCalls);

  /// Response map for VPN channel methods. Set return values here.
  final Map<String, dynamic> vpnResponses = {};

  /// Response map for kill switch channel methods.
  final Map<String, dynamic> killSwitchResponses = {};

  /// Registers mock handlers for all platform channels.
  void setUp() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(
      const MethodChannel('com.cybervpn.mobile/vpn'),
      (call) async {
        _vpnCalls.add(call);
        return vpnResponses[call.method];
      },
    );

    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(
      const MethodChannel('com.cybervpn.mobile/kill_switch'),
      (call) async {
        _killSwitchCalls.add(call);
        return killSwitchResponses[call.method];
      },
    );

    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(
      const MethodChannel('com.cybervpn.mobile/split_tunnel'),
      (call) async => null,
    );
  }

  /// Removes all mock handlers.
  void tearDown() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(
      const MethodChannel('com.cybervpn.mobile/vpn'),
      null,
    );
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(
      const MethodChannel('com.cybervpn.mobile/kill_switch'),
      null,
    );
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(
      const MethodChannel('com.cybervpn.mobile/split_tunnel'),
      null,
    );

    _vpnCalls.clear();
    _killSwitchCalls.clear();
  }

  /// Clears recorded calls without removing handlers.
  void reset() {
    _vpnCalls.clear();
    _killSwitchCalls.clear();
  }

  /// Asserts that the VPN channel received a call with the given [method].
  void expectVpnCall(String method) {
    expect(
      _vpnCalls.any((c) => c.method == method),
      isTrue,
      reason: 'Expected VPN channel call "$method" but got: '
          '${_vpnCalls.map((c) => c.method).toList()}',
    );
  }

  /// Asserts that the kill switch channel received a call with the given [method].
  void expectKillSwitchCall(String method) {
    expect(
      _killSwitchCalls.any((c) => c.method == method),
      isTrue,
      reason: 'Expected kill switch channel call "$method" but got: '
          '${_killSwitchCalls.map((c) => c.method).toList()}',
    );
  }
}
