/// Centralized cache TTL configuration for all data types.
///
/// ## Cache Strategy by Data Type
///
/// | Data Type          | Strategy               | TTL            | Invalidation Trigger       |
/// |--------------------|------------------------|----------------|----------------------------|
/// | Auth tokens        | Proactive refresh       | 5 min          | Token expiry - 60s buffer  |
/// | Server list        | Stale-while-revalidate  | 15 min         | Pull-to-refresh, WS event  |
/// | User profile       | Cache-first             | 1 hr           | Profile screen open        |
/// | Subscription       | Event-driven            | 30 min         | Purchase, WS subscription  |
/// | Referral           | In-memory + TTL         | 5 min          | Screen open                |
/// | Notifications      | Local DB + max age      | 30 days        | Fetch on open, auto-prune  |
/// | Ping latency       | In-memory               | 60 sec         | Manual refresh             |
/// | Server detail      | FutureProvider.family    | Until dispose  | Navigation away            |
///
/// ## Where TTL is Enforced
///
/// - `SecureStorageWrapper._cacheTtl` — auth token in-memory cache (5 min)
/// - `SubscriptionLocalDs._cacheTtl` — subscription data (30 min)
/// - `ReferralRemoteDs._cacheDuration` — referral availability (5 min)
/// - `NotificationLocalDatasource.maxAgeDays` — notification pruning (30 days)
/// - `PingService._cacheDuration` — ping results (60 sec)
/// - `TokenRefreshScheduler` — proactive token refresh before expiry
class CacheConstants {
  const CacheConstants._();

  /// Auth token in-memory cache duration.
  static const Duration authTokenCacheTtl = Duration(minutes: 5);

  /// Server list stale-while-revalidate window.
  static const Duration serverListSwrTtl = Duration(minutes: 15);

  /// User profile cache-first duration.
  static const Duration userProfileCacheTtl = Duration(hours: 1);

  /// Subscription state cache duration.
  static const Duration subscriptionCacheTtl = Duration(minutes: 30);

  /// Referral data in-memory cache duration.
  static const Duration referralCacheTtl = Duration(minutes: 5);

  /// Maximum age for stored notifications before auto-pruning.
  static const Duration notificationMaxAge = Duration(days: 30);

  /// Ping latency in-memory cache duration.
  static const Duration pingCacheTtl = Duration(seconds: 60);
}
