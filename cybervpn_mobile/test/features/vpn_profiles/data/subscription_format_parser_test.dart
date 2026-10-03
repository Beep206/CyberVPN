import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/features/vpn_profiles/data/datasources/subscription_format_parser.dart';

void main() {
  late SubscriptionFormatParser parser;

  setUp(() {
    parser = SubscriptionFormatParser();
  });

  group('SubscriptionFormatParser - URI List', () {
    test('parses line-separated VLESS URIs', () {
      const content = '''
vless://11111111-2222-3333-4444-555555555555@server1.example.com:443?type=tcp&security=tls#Server%20One
vless://66666666-7777-8888-9999-000000000000@server2.example.com:8443?type=ws&security=reality&pbk=pubkey123&sid=shortid456&path=%2Fws#Server%20Two
''';

      final (servers, errors) = parser.parse(content);

      expect(errors, isEmpty);
      expect(servers, hasLength(2));
      expect(servers[0].name, 'Server One');
      expect(servers[0].serverAddress, 'server1.example.com');
      expect(servers[0].port, 443);
      expect(servers[0].protocol, 'vless');

      expect(servers[1].name, 'Server Two');
      expect(servers[1].serverAddress, 'server2.example.com');
      expect(servers[1].port, 8443);
      expect(servers[1].protocol, 'vless');
    });

    test('parses Trojan and Shadowsocks URIs', () {
      const content = '''
trojan://secret-password@trojan.example.com:443?security=tls#Trojan%20Node
ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ=@ss.example.com:8388#Shadowsocks%20Node
''';

      final (servers, errors) = parser.parse(content);

      expect(errors, isEmpty);
      expect(servers, hasLength(2));
      expect(servers[0].protocol, 'trojan');
      expect(servers[0].serverAddress, 'trojan.example.com');

      expect(servers[1].protocol, 'shadowsocks');
      expect(servers[1].serverAddress, 'ss.example.com');
    });

    test('ignores empty lines and records error for invalid lines', () {
      const content = '''
vless://11111111-2222-3333-4444-555555555555@server1.example.com:443#Valid

invalid-uri-scheme://broken
''';

      final (servers, errors) = parser.parse(content);

      expect(servers, hasLength(1));
      expect(errors, hasLength(1));
    });
  });

  group('SubscriptionFormatParser - Clash Meta YAML', () {
    test(
      'parses Clash Meta YAML with vless, trojan, and shadowsocks proxies',
      () {
        const clashYaml = '''
proxies:
  - name: "Clash VLESS Reality"
    type: vless
    server: meta.example.com
    port: 443
    uuid: 11111111-2222-3333-4444-555555555555
    network: tcp
    tls: true
    servername: meta.example.com
    reality-opts:
      public-key: pbk123
      short-id: sid456
    flow: xtls-rprx-vision
  - name: "Clash Trojan WS"
    type: trojan
    server: trojan.example.com
    port: 8443
    password: pass-word-123
    network: tcp
    sni: trojan.example.com
  - name: "Clash Shadowsocks"
    type: ss
    server: ss.example.com
    port: 8388
    cipher: aes-256-gcm
    password: ss-secret-pass
''';

        final (servers, errors) = parser.parse(clashYaml);

        expect(errors, isEmpty);
        expect(servers, hasLength(3));

        expect(servers[0].name, 'Clash VLESS Reality');
        expect(servers[0].serverAddress, 'meta.example.com');
        expect(servers[0].port, 443);
        expect(servers[0].protocol, 'vless');

        expect(servers[1].name, 'Clash Trojan WS');
        expect(servers[1].serverAddress, 'trojan.example.com');
        expect(servers[1].port, 8443);
        expect(servers[1].protocol, 'trojan');

        expect(servers[2].name, 'Clash Shadowsocks');
        expect(servers[2].serverAddress, 'ss.example.com');
        expect(servers[2].port, 8388);
        expect(servers[2].protocol, 'shadowsocks');
      },
    );

    test('ignores non-proxies YAML documents gracefully', () {
      const randomYaml = '''
rules:
  - DOMAIN-SUFFIX,google.com,Proxy
  - MATCH,DIRECT
''';

      final (servers, errors) = parser.parse(randomYaml);
      expect(servers, isEmpty);
      expect(errors, isNotEmpty); // parsed as lines which are not valid URIs
    });
  });

  group('SubscriptionFormatParser - Sing-box JSON', () {
    test('parses Sing-box JSON and filters out non-proxy outbounds', () {
      const singboxJson = '''
{
  "outbounds": [
    {
      "type": "vless",
      "tag": "Singbox VLESS",
      "server": "singbox.example.com",
      "server_port": 443,
      "uuid": "11111111-2222-3333-4444-555555555555",
      "flow": "xtls-rprx-vision",
      "tls": {
        "enabled": true,
        "server_name": "singbox.example.com",
        "reality": {
          "enabled": true,
          "public_key": "pbk_singbox",
          "short_id": "sid_singbox"
        }
      }
    },
    {
      "type": "direct",
      "tag": "direct-out"
    },
    {
      "type": "block",
      "tag": "block-out"
    },
    {
      "type": "dns",
      "tag": "dns-out"
    },
    {
      "type": "trojan",
      "tag": "Singbox Trojan",
      "server": "trojan-singbox.example.com",
      "server_port": 443,
      "password": "trojan-password"
    }
  ]
}
''';

      final (servers, errors) = parser.parse(singboxJson);

      expect(errors, isEmpty);
      expect(servers, hasLength(2));

      expect(servers[0].name, 'Singbox VLESS');
      expect(servers[0].serverAddress, 'singbox.example.com');
      expect(servers[0].port, 443);
      expect(servers[0].protocol, 'vless');

      expect(servers[1].name, 'Singbox Trojan');
      expect(servers[1].serverAddress, 'trojan-singbox.example.com');
      expect(servers[1].port, 443);
      expect(servers[1].protocol, 'trojan');
    });
  });
}
