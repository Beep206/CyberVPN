import { apiClient } from './client';
import type { operations } from './generated/types';

// Extract types from OpenAPI operations
type HealthResponse = operations['health_check_api_v1_monitoring_health_get']['responses'][200]['content']['application/json'];
type SystemStatsResponse = operations['get_system_stats_api_v1_monitoring_stats_get']['responses'][200]['content']['application/json'];
type BandwidthResponse = operations['get_bandwidth_analytics_api_v1_monitoring_bandwidth_get']['responses'][200]['content']['application/json'];

/**
 * Monitoring API client
 * Provides system health checks, statistics, and bandwidth analytics
 */
export const monitoringApi = {
  /**
   * System health check
   * GET /api/v1/monitoring/health
   *
   * Returns overall system health status including:
   * - API server status
   * - Database connectivity
   * - Redis cache status
   * - External service dependencies
   */
  health: () =>
    apiClient.get<HealthResponse>('/monitoring/health'),

  /**
   * Get system statistics
   * GET /api/v1/monitoring/stats
   *
   * Returns real-time system metrics:
   * - Active connections count
   * - Total registered users
   * - Active subscriptions
   * - System uptime
   * - Resource utilization
   */
  getStats: () =>
    apiClient.get<SystemStatsResponse>('/monitoring/stats'),

  /**
   * Get bandwidth analytics
   * GET /api/v1/monitoring/bandwidth
   *
   * Returns network bandwidth metrics:
   * - Current aggregate throughput
   * - Total data transferred (period)
   * - Peak bandwidth usage
   * - Per-protocol breakdown
   */
  getBandwidth: () =>
    apiClient.get<BandwidthResponse>('/monitoring/bandwidth'),
};
