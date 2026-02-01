/// VPN protocol, network, and connection constants for CyberVPN.
class VpnConstants {
  const VpnConstants._();

  // ── Supported Protocols ───────────────────────────────────────────────

  static const List<String> supportedProtocols = [
    'VLESS',
    'VMess',
    'Trojan',
    'Shadowsocks',
  ];

  static const String defaultProtocol = 'VLESS';

  // ── Default Ports ─────────────────────────────────────────────────────

  static const int vlessPort = 443;
  static const int vmessPort = 443;
  static const int trojanPort = 443;
  static const int shadowsocksPort = 8388;

  static const Map<String, int> defaultPortByProtocol = {
    'VLESS': vlessPort,
    'VMess': vmessPort,
    'Trojan': trojanPort,
    'Shadowsocks': shadowsocksPort,
  };

  // ── DNS Servers ───────────────────────────────────────────────────────

  static const String cloudflareIPv4Primary = '1.1.1.1';
  static const String cloudflareIPv4Secondary = '1.0.0.1';
  static const String googleIPv4Primary = '8.8.8.8';
  static const String googleIPv4Secondary = '8.8.4.4';
  static const String quad9IPv4Primary = '9.9.9.9';
  static const String quad9IPv4Secondary = '149.112.112.112';

  static const List<String> defaultDnsServers = [
    cloudflareIPv4Primary,
    cloudflareIPv4Secondary,
    googleIPv4Primary,
    googleIPv4Secondary,
  ];

  // ── MTU (Maximum Transmission Unit) ───────────────────────────────────

  static const int defaultMtu = 1400;
  static const int minMtu = 1280;
  static const int maxMtu = 1500;

  // ── Connection Retry Settings ─────────────────────────────────────────

  /// Maximum number of automatic reconnection attempts.
  static const int maxRetryAttempts = 5;

  /// Alias used by [AutoReconnectService].
  static const int maxReconnectAttempts = maxRetryAttempts;

  /// Base delay between reconnection attempts (seconds).
  static const int reconnectDelaySeconds = 2;

  /// Initial delay between retry attempts (milliseconds).
  static const int retryDelayMs = 1000;

  /// Multiplier applied to the delay after each failed attempt (exponential backoff).
  static const double retryBackoffMultiplier = 2.0;

  /// Upper cap for the retry delay (milliseconds).
  static const int maxRetryDelayMs = 30000;

  // ── Connection Health ─────────────────────────────────────────────────

  /// Interval for periodic ping checks while connected (milliseconds).
  static const int pingIntervalMs = 10000;

  /// A ping higher than this value is considered poor (milliseconds).
  static const int highPingThresholdMs = 200;

  /// A connection is considered lost after this many consecutive ping failures.
  static const int maxPingFailures = 3;

  // ── Speed Test ────────────────────────────────────────────────────────

  /// Duration of a single speed test sample (milliseconds).
  static const int speedTestDurationMs = 10000;

  /// Number of parallel streams used during speed tests.
  static const int speedTestStreams = 4;

  // ── Encryption ────────────────────────────────────────────────────────

  static const String defaultEncryption = 'auto';
  static const List<String> supportedEncryptions = [
    'auto',
    'aes-128-gcm',
    'aes-256-gcm',
    'chacha20-poly1305',
    'none',
  ];

  // ── Transport Types ───────────────────────────────────────────────────

  static const List<String> supportedTransports = [
    'tcp',
    'ws',
    'grpc',
    'http',
  ];

  static const String defaultTransport = 'ws';
}
