'use client';

import { useQuery } from '@tanstack/react-query';
import { motion } from 'motion/react';
import { useState, useEffect } from 'react';
import {
  CheckCircle,
  XCircle,
  AlertCircle,
  Server,
  Database,
  Activity,
  Zap,
  Clock,
} from 'lucide-react';
import { monitoringApi } from '@/lib/api';

type HealthStatus = 'healthy' | 'degraded' | 'down';

// Local interfaces for monitoring API responses
interface HealthData {
  status?: HealthStatus;
  api_status?: HealthStatus;
  api_response_time?: number;
  api_uptime?: number;
  database_status?: HealthStatus;
  database_response_time?: number;
  database_uptime?: number;
  redis_status?: HealthStatus;
  redis_response_time?: number;
  redis_uptime?: number;
  worker_status?: HealthStatus;
  worker_response_time?: number;
  worker_uptime?: number;
}

interface StatsData {
  total_requests?: number;
  avg_response_time?: number;
  error_rate?: number;
  active_connections?: number;
}

interface BandwidthData {
  inbound_mbps?: number;
  outbound_mbps?: number;
}

/**
 * Monitoring Client Component
 * Displays system health dashboard with API, DB, Redis, Worker status
 */
export function MonitoringClient() {
  // Client-side timestamp state to avoid hydration mismatch
  const [currentTime, setCurrentTime] = useState<string>('');

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- Timer pattern: setState in interval callback is intentional
    setCurrentTime(new Date().toLocaleTimeString());

    const interval = setInterval(() => {
      setCurrentTime(new Date().toLocaleTimeString());
    }, 1000);

    return () => clearInterval(interval);
  }, []);
  // Fetch system health
  const { data: healthData, isLoading: healthLoading } = useQuery({
    queryKey: ['system-health'],
    queryFn: async () => {
      const response = await monitoringApi.health();
      return response.data;
    },
    staleTime: 30 * 1000,
    refetchInterval: 30 * 1000, // Refresh every 30 seconds
  });

  // Fetch system stats
  const { data: statsData, isLoading: statsLoading } = useQuery({
    queryKey: ['system-stats'],
    queryFn: async () => {
      const response = await monitoringApi.getStats();
      return response.data;
    },
    staleTime: 30 * 1000,
    refetchInterval: 30 * 1000,
  });

  // Fetch bandwidth analytics
  const { data: bandwidthData, isLoading: bandwidthLoading } = useQuery({
    queryKey: ['bandwidth-analytics'],
    queryFn: async () => {
      const response = await monitoringApi.getBandwidth();
      return response.data;
    },
    staleTime: 30 * 1000,
    refetchInterval: 30 * 1000,
  });

  const isLoading = healthLoading || statsLoading || bandwidthLoading;

  if (isLoading || !healthData || !statsData || !bandwidthData) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-neon-cyan" />
      </div>
    );
  }

  // Transform API data to component format
  const typedHealthData = healthData as HealthData;
  const typedStatsData = statsData as StatsData;
  const typedBandwidthData = bandwidthData as BandwidthData;
  const lastCheckTime = currentTime || new Date().toISOString();

  const health = {
    overall: typedHealthData.status || ('healthy' as HealthStatus),
    services: [
      {
        name: 'API Server',
        status: typedHealthData.api_status || ('healthy' as HealthStatus),
        responseTime: typedHealthData.api_response_time || 0,
        lastCheck: lastCheckTime,
        uptime: typedHealthData.api_uptime || 100,
      },
      {
        name: 'PostgreSQL Database',
        status: typedHealthData.database_status || ('healthy' as HealthStatus),
        responseTime: typedHealthData.database_response_time || 0,
        lastCheck: lastCheckTime,
        uptime: typedHealthData.database_uptime || 100,
      },
      {
        name: 'Redis Cache',
        status: typedHealthData.redis_status || ('healthy' as HealthStatus),
        responseTime: typedHealthData.redis_response_time || 0,
        lastCheck: lastCheckTime,
        uptime: typedHealthData.redis_uptime || 100,
      },
      {
        name: 'Background Workers',
        status: typedHealthData.worker_status || ('healthy' as HealthStatus),
        responseTime: typedHealthData.worker_response_time || 0,
        lastCheck: lastCheckTime,
        uptime: typedHealthData.worker_uptime || 100,
      },
    ],
    metrics: {
      totalRequests: typedStatsData.total_requests || 0,
      avgResponseTime: typedStatsData.avg_response_time || 0,
      errorRate: typedStatsData.error_rate || 0,
      activeConnections: typedStatsData.active_connections || 0,
      bandwidth: {
        inbound: typedBandwidthData.inbound_mbps || 0,
        outbound: typedBandwidthData.outbound_mbps || 0,
      },
    },
  };

  const getStatusIcon = (status: HealthStatus) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="h-6 w-6 text-matrix-green" />;
      case 'degraded':
        return <AlertCircle className="h-6 w-6 text-neon-pink" />;
      case 'down':
        return <XCircle className="h-6 w-6 text-red-500" />;
    }
  };

  const getStatusColor = (status: HealthStatus) => {
    switch (status) {
      case 'healthy':
        return 'border-matrix-green/50 bg-matrix-green/5';
      case 'degraded':
        return 'border-neon-pink/50 bg-neon-pink/5';
      case 'down':
        return 'border-red-500/50 bg-red-500/5';
    }
  };

  const getStatusText = (status: HealthStatus) => {
    switch (status) {
      case 'healthy':
        return 'Operational';
      case 'degraded':
        return 'Degraded';
      case 'down':
        return 'Down';
    }
  };

  return (
    <div className="space-y-6">
      {/* Overall Status Banner */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`cyber-card p-6 border-2 ${getStatusColor(health.overall)}`}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            {getStatusIcon(health.overall)}
            <div>
              <h2 className="text-2xl font-display text-matrix-green">
                All Systems {getStatusText(health.overall)}
              </h2>
              <p className="text-sm text-muted-foreground font-mono mt-1">
                Last updated: {currentTime}
              </p>
            </div>
          </div>
          <div className="text-right">
            <div className="text-sm text-muted-foreground font-mono">
              {health.services.filter(s => s.status === 'healthy').length} / {health.services.length} services healthy
            </div>
          </div>
        </div>
      </motion.div>

      {/* Service Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {health.services.map((service, index) => (
          <motion.div
            key={service.name}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 + index * 0.1 }}
            className={`cyber-card p-6 border ${getStatusColor(service.status)}`}
          >
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                {index === 0 && <Server className="h-5 w-5 text-neon-cyan" />}
                {index === 1 && <Database className="h-5 w-5 text-neon-purple" />}
                {index === 2 && <Zap className="h-5 w-5 text-matrix-green" />}
                {index === 3 && <Activity className="h-5 w-5 text-neon-pink" />}
                <h3 className="text-sm font-mono text-muted-foreground">{service.name}</h3>
              </div>
              {getStatusIcon(service.status)}
            </div>

            <div className="space-y-3">
              <div>
                <p className="text-xs text-muted-foreground mb-1">Response Time</p>
                <p className="text-2xl font-display text-foreground">
                  {service.responseTime}
                  <span className="text-sm ml-1">ms</span>
                </p>
              </div>

              <div className="flex justify-between text-xs">
                <span className="text-muted-foreground">Uptime</span>
                <span className="font-mono text-matrix-green">
                  {service.uptime.toFixed(2)}%
                </span>
              </div>

              <div className="h-1 bg-grid-line/30 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${service.uptime}%` }}
                  transition={{ delay: 0.2 + index * 0.1, duration: 0.5 }}
                  className={`h-full ${
                    service.status === 'healthy' ? 'bg-matrix-green' : 'bg-neon-pink'
                  }`}
                />
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Total Requests */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="cyber-card p-6"
        >
          <div className="flex items-center gap-3 mb-4">
            <Activity className="h-5 w-5 text-neon-cyan" />
            <h3 className="text-sm font-mono text-muted-foreground">Total Requests (24h)</h3>
          </div>
          <p className="text-3xl font-display text-neon-cyan">
            {health.metrics.totalRequests.toLocaleString()}
          </p>
        </motion.div>

        {/* Avg Response Time */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="cyber-card p-6"
        >
          <div className="flex items-center gap-3 mb-4">
            <Clock className="h-5 w-5 text-neon-purple" />
            <h3 className="text-sm font-mono text-muted-foreground">Avg Response Time</h3>
          </div>
          <p className="text-3xl font-display text-neon-purple">
            {health.metrics.avgResponseTime}
            <span className="text-base ml-2">ms</span>
          </p>
        </motion.div>

        {/* Error Rate */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
          className="cyber-card p-6"
        >
          <div className="flex items-center gap-3 mb-4">
            <AlertCircle className="h-5 w-5 text-neon-pink" />
            <h3 className="text-sm font-mono text-muted-foreground">Error Rate</h3>
          </div>
          <p className="text-3xl font-display text-neon-pink">
            {health.metrics.errorRate.toFixed(2)}%
          </p>
        </motion.div>
      </div>

      {/* Bandwidth & Connections */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Bandwidth */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8 }}
          className="cyber-card p-6"
        >
          <div className="flex items-center gap-2 mb-6">
            <Zap className="h-5 w-5 text-matrix-green" />
            <h3 className="text-lg font-display text-matrix-green">Network Bandwidth</h3>
          </div>

          <div className="space-y-4">
            <div>
              <div className="flex justify-between mb-2">
                <span className="text-sm text-muted-foreground">Inbound</span>
                <span className="text-sm font-mono text-neon-cyan">
                  {health.metrics.bandwidth.inbound.toFixed(1)} MB/s
                </span>
              </div>
              <div className="h-3 bg-grid-line/30 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: '65%' }}
                  transition={{ delay: 0.9, duration: 0.5 }}
                  className="h-full bg-gradient-to-r from-neon-cyan/50 to-neon-cyan"
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between mb-2">
                <span className="text-sm text-muted-foreground">Outbound</span>
                <span className="text-sm font-mono text-neon-purple">
                  {health.metrics.bandwidth.outbound.toFixed(1)} MB/s
                </span>
              </div>
              <div className="h-3 bg-grid-line/30 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: '85%' }}
                  transition={{ delay: 1, duration: 0.5 }}
                  className="h-full bg-gradient-to-r from-neon-purple/50 to-neon-purple"
                />
              </div>
            </div>
          </div>
        </motion.div>

        {/* Active Connections */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.9 }}
          className="cyber-card p-6"
        >
          <div className="flex items-center gap-2 mb-6">
            <Activity className="h-5 w-5 text-neon-pink" />
            <h3 className="text-lg font-display text-neon-pink">Active Connections</h3>
          </div>

          <div className="text-center">
            <p className="text-6xl font-display text-neon-pink mb-4">
              {health.metrics.activeConnections}
            </p>
            <p className="text-sm text-muted-foreground font-mono">
              Concurrent connections
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
