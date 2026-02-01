import 'dart:convert';
import 'package:cybervpn_mobile/core/constants/vpn_constants.dart';

class XrayConfigGenerator {
  const XrayConfigGenerator._();

  static String generateVlessConfig({
    required String address,
    required int port,
    required String uuid,
    String network = 'ws',
    String security = 'tls',
    String? sni,
    String? path,
    List<String>? dnsServers,
  }) {
    final dns = dnsServers ?? VpnConstants.defaultDnsServers;
    return jsonEncode({
      'outbounds': [{
        'protocol': 'vless',
        'settings': {
          'vnext': [{
            'address': address,
            'port': port,
            'users': [{'id': uuid, 'encryption': 'none'}],
          }],
        },
        'streamSettings': {
          'network': network,
          'security': security,
          if (security == 'tls') 'tlsSettings': {'serverName': sni ?? address},
          if (network == 'ws') 'wsSettings': {'path': path ?? '/'},
        },
      }],
      'dns': {'servers': dns},
    });
  }

  static String generateVmessConfig({
    required String address,
    required int port,
    required String uuid,
    int alterId = 0,
    String security = 'auto',
    String network = 'ws',
    String? path,
    List<String>? dnsServers,
  }) {
    final dns = dnsServers ?? VpnConstants.defaultDnsServers;
    return jsonEncode({
      'outbounds': [{
        'protocol': 'vmess',
        'settings': {
          'vnext': [{
            'address': address,
            'port': port,
            'users': [{'id': uuid, 'alterId': alterId, 'security': security}],
          }],
        },
        'streamSettings': {
          'network': network,
          if (network == 'ws') 'wsSettings': {'path': path ?? '/'},
        },
      }],
      'dns': {'servers': dns},
    });
  }
}
