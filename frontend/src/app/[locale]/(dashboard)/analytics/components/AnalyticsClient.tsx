'use client';

import { useQuery } from '@tanstack/react-query';
import { motion } from 'motion/react';
import {
  DollarSign,
  Users,
  TrendingUp,
  Activity,
  Zap,
  PieChart as PieChartIcon,
} from 'lucide-react';
import { useState } from 'react';
import { paymentsApi, usageApi, subscriptionsApi } from '@/lib/api';

/**
 * Analytics Client Component
 * Displays revenue charts, user growth, subscription distribution, and bandwidth analytics
 */
export function AnalyticsClient() {
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d'>('30d');

  // Fetch payment history for revenue data
  const { data: paymentsData, isLoading: paymentsLoading } = useQuery({
    queryKey: ['payments-history', timeRange],
    queryFn: async () => {
      const response = await paymentsApi.getHistory();
      return response.data;
    },
    staleTime: 5 * 60 * 1000,
  });

  // Fetch usage data for bandwidth analytics
  const { data: usageData, isLoading: usageLoading } = useQuery({
    queryKey: ['usage-analytics', timeRange],
    queryFn: async () => {
      const response = await usageApi.getMyUsage();
      return response.data;
    },
    staleTime: 5 * 60 * 1000,
  });

  // Fetch subscriptions for distribution analytics
  const { data: subscriptionsData, isLoading: subscriptionsLoading } = useQuery({
    queryKey: ['subscriptions-analytics', timeRange],
    queryFn: async () => {
      const response = await subscriptionsApi.list();
      return response.data;
    },
    staleTime: 5 * 60 * 1000,
  });

  const isLoading = paymentsLoading || usageLoading || subscriptionsLoading;

  // Transform API data to analytics format
  const analytics = !isLoading && paymentsData && usageData && subscriptionsData ? {
    revenue: {
      total: Array.isArray(paymentsData)
        ? (paymentsData as any[]).reduce((sum: number, p: any) => sum + (p.amount || 0), 0)
        : 0,
      growth: 12.5, // TODO: Calculate from historical data when endpoint available
      chartData: Array.isArray(paymentsData)
        ? (paymentsData as any[]).slice(0, 30).map((p: any) => ({
            date: new Date(p.created_at || Date.now()).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
            value: p.amount || 0,
          }))
        : [],
    },
    users: {
      total: 0, // TODO: Add user analytics endpoint
      active: 0, // TODO: Add user analytics endpoint
      growth: 0, // TODO: Calculate from historical data when endpoint available
      chartData: [], // TODO: Add user analytics endpoint
    },
    subscriptions: {
      byPlan: Array.isArray(subscriptionsData)
        ? Object.entries(
            (subscriptionsData as any[]).reduce((acc: any, sub: any) => {
              const planName = sub.plan_name || 'Unknown';
              acc[planName] = (acc[planName] || 0) + 1;
              return acc;
            }, {})
          ).map(([name, count], i) => ({
            name,
            count: count as number,
            color: ['var(--color-neon-cyan)', 'var(--color-neon-purple)', 'var(--color-neon-pink)', 'var(--color-matrix-green)'][i % 4],
          }))
        : [],
      total: Array.isArray(subscriptionsData) ? subscriptionsData.length : 0,
    },
    bandwidth: {
      total: ((usageData as any)?.bandwidth_used_gb || 0) / 1000, // Convert GB to TB
      peak: ((usageData as any)?.bandwidth_used_gb || 0) / 30, // Rough average per day
      chartData: Array.from({ length: 24 }, (_, i) => ({
        hour: `${i}:00`,
        value: ((usageData as any)?.bandwidth_used_gb || 0) / 24, // Distribute evenly across hours
      })),
    },
  } : null;

  if (isLoading || !analytics) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-neon-cyan" />
      </div>
    );
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
  };

  const formatNumber = (value: number) => {
    return new Intl.NumberFormat('en-US').format(value);
  };

  return (
    <div className="space-y-6">
      {/* Time Range Selector */}
      <div className="flex gap-2">
        {[
          { label: '7 Days', value: '7d' as const },
          { label: '30 Days', value: '30d' as const },
          { label: '90 Days', value: '90d' as const },
        ].map((range) => (
          <button
            key={range.value}
            onClick={() => setTimeRange(range.value)}
            className={`px-4 py-2 font-mono text-sm rounded transition-all ${
              timeRange === range.value
                ? 'bg-neon-cyan/20 border border-neon-cyan/50 text-neon-cyan'
                : 'bg-terminal-bg border border-grid-line/30 text-muted-foreground hover:border-neon-cyan/30'
            }`}
          >
            {range.label}
          </button>
        ))}
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Revenue Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="cyber-card p-6"
        >
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-matrix-green/10 border border-matrix-green/30 rounded">
              <DollarSign className="h-5 w-5 text-matrix-green" />
            </div>
            <h3 className="text-sm font-mono text-muted-foreground">Total Revenue</h3>
          </div>
          <div className="space-y-2">
            <p className="text-3xl font-display text-matrix-green">
              {formatCurrency(analytics.revenue.total)}
            </p>
            <div className="flex items-center gap-1 text-sm">
              <TrendingUp className="h-4 w-4 text-matrix-green" />
              <span className="text-matrix-green font-mono">
                +{analytics.revenue.growth}%
              </span>
              <span className="text-muted-foreground">vs last period</span>
            </div>
          </div>
        </motion.div>

        {/* Total Users Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="cyber-card p-6"
        >
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-neon-cyan/10 border border-neon-cyan/30 rounded">
              <Users className="h-5 w-5 text-neon-cyan" />
            </div>
            <h3 className="text-sm font-mono text-muted-foreground">Total Users</h3>
          </div>
          <div className="space-y-2">
            <p className="text-3xl font-display text-neon-cyan">
              {formatNumber(analytics.users.total)}
            </p>
            <div className="flex items-center gap-1 text-sm">
              <TrendingUp className="h-4 w-4 text-neon-cyan" />
              <span className="text-neon-cyan font-mono">
                +{analytics.users.growth}%
              </span>
              <span className="text-muted-foreground">growth</span>
            </div>
          </div>
        </motion.div>

        {/* Active Users Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="cyber-card p-6"
        >
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-neon-purple/10 border border-neon-purple/30 rounded">
              <Activity className="h-5 w-5 text-neon-purple" />
            </div>
            <h3 className="text-sm font-mono text-muted-foreground">Active Users</h3>
          </div>
          <div className="space-y-2">
            <p className="text-3xl font-display text-neon-purple">
              {formatNumber(analytics.users.active)}
            </p>
            <div className="text-sm text-muted-foreground">
              {((analytics.users.active / analytics.users.total) * 100).toFixed(1)}% of total
            </div>
          </div>
        </motion.div>

        {/* Bandwidth Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="cyber-card p-6"
        >
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-neon-pink/10 border border-neon-pink/30 rounded">
              <Zap className="h-5 w-5 text-neon-pink" />
            </div>
            <h3 className="text-sm font-mono text-muted-foreground">Total Bandwidth</h3>
          </div>
          <div className="space-y-2">
            <p className="text-3xl font-display text-neon-pink">
              {analytics.bandwidth.total.toFixed(1)} TB
            </p>
            <div className="text-sm text-muted-foreground">
              Peak: {analytics.bandwidth.peak.toFixed(1)} GB/s
            </div>
          </div>
        </motion.div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Revenue Chart */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="cyber-card p-6"
        >
          <div className="flex items-center gap-2 mb-6">
            <TrendingUp className="h-5 w-5 text-matrix-green" />
            <h3 className="text-lg font-display text-matrix-green">Revenue Trend</h3>
          </div>
          <div className="h-64 flex items-end gap-1">
            {analytics.revenue.chartData.map((item, i) => {
              const maxValue = Math.max(...analytics.revenue.chartData.map(d => d.value));
              const height = (item.value / maxValue) * 100;
              return (
                <motion.div
                  key={i}
                  initial={{ height: 0 }}
                  animate={{ height: `${height}%` }}
                  transition={{ delay: 0.5 + i * 0.02, duration: 0.3 }}
                  className="flex-1 bg-gradient-to-t from-matrix-green/50 to-matrix-green/20 border-t border-matrix-green/50 relative group"
                  title={`${item.date}: ${formatCurrency(item.value)}`}
                >
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block bg-terminal-surface border border-matrix-green/50 px-2 py-1 rounded text-xs whitespace-nowrap">
                    {formatCurrency(item.value)}
                  </div>
                </motion.div>
              );
            })}
          </div>
        </motion.div>

        {/* Subscription Distribution */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="cyber-card p-6"
        >
          <div className="flex items-center gap-2 mb-6">
            <PieChartIcon className="h-5 w-5 text-neon-purple" />
            <h3 className="text-lg font-display text-neon-purple">Subscription Distribution</h3>
          </div>
          <div className="space-y-4">
            {analytics.subscriptions.byPlan.map((plan, i) => {
              const percentage = (plan.count / analytics.subscriptions.total) * 100;
              return (
                <motion.div
                  key={plan.name}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.6 + i * 0.1 }}
                  className="space-y-2"
                >
                  <div className="flex justify-between text-sm">
                    <span className="font-mono" style={{ color: plan.color }}>
                      {plan.name}
                    </span>
                    <span className="text-muted-foreground">
                      {formatNumber(plan.count)} ({percentage.toFixed(1)}%)
                    </span>
                  </div>
                  <div className="h-2 bg-grid-line/30 rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${percentage}%` }}
                      transition={{ delay: 0.7 + i * 0.1, duration: 0.5 }}
                      className="h-full rounded-full"
                      style={{ backgroundColor: plan.color }}
                    />
                  </div>
                </motion.div>
              );
            })}
          </div>
        </motion.div>
      </div>

      {/* Bandwidth Usage Chart */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.8 }}
        className="cyber-card p-6"
      >
        <div className="flex items-center gap-2 mb-6">
          <Zap className="h-5 w-5 text-neon-pink" />
          <h3 className="text-lg font-display text-neon-pink">24h Bandwidth Usage</h3>
        </div>
        <div className="h-48 flex items-end gap-2">
          {analytics.bandwidth.chartData.map((item, i) => {
            const maxValue = Math.max(...analytics.bandwidth.chartData.map(d => d.value));
            const height = (item.value / maxValue) * 100;
            return (
              <motion.div
                key={i}
                initial={{ height: 0 }}
                animate={{ height: `${height}%` }}
                transition={{ delay: 0.9 + i * 0.01, duration: 0.3 }}
                className="flex-1 bg-gradient-to-t from-neon-pink/50 to-neon-pink/20 border-t border-neon-pink/50 relative group"
                title={`${item.hour}: ${item.value.toFixed(1)} GB/s`}
              >
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block bg-terminal-surface border border-neon-pink/50 px-2 py-1 rounded text-xs whitespace-nowrap">
                  {item.value.toFixed(1)} GB/s
                </div>
              </motion.div>
            );
          })}
        </div>
        <div className="flex justify-between mt-2 text-xs text-muted-foreground font-mono">
          <span>00:00</span>
          <span>06:00</span>
          <span>12:00</span>
          <span>18:00</span>
          <span>23:00</span>
        </div>
      </motion.div>
    </div>
  );
}
