'use client';

import { useQuery } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import { commerceApi } from '@/lib/api';
import { motion } from 'motion/react';
import {
  Receipt,
  CheckCircle2,
  Clock,
  XCircle,
  RefreshCw,
  Loader2
} from 'lucide-react';
import { useTelegramWebApp } from '../hooks/useTelegramWebApp';

/**
 * Mini App Payment History page
 * Full payment history with status badges and filtering
 */
export default function MiniAppPaymentsPage() {
  const t = useTranslations('MiniApp.payments');
  const { colorScheme } = useTelegramWebApp();

  const { data: orderHistory, isLoading } = useQuery({
    queryKey: ['miniapp-order-history'],
    queryFn: async () => {
      const { data } = await commerceApi.listOrders({ limit: 50, offset: 0 });
      return data;
    },
  });

  const orders = orderHistory || [];

  // Theme colors
  const isDark = colorScheme === 'dark';
  const cardBg = isDark ? 'bg-[var(--tg-bg-color,oklch(0.06_0.015_260))]' : 'bg-[var(--tg-bg-color,oklch(0.70_0.010_250))]';
  const borderColor = isDark ? 'border-[var(--tg-hint-color,oklch(0.25_0.10_195))]' : 'border-[var(--tg-hint-color,oklch(0.45_0.03_250))]';

  const formatCurrency = (amount: number, currency: string) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency || 'USD',
      minimumFractionDigits: 2,
    }).format(amount);
  };

  return (
    <div className="max-w-screen-sm mx-auto space-y-4">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div className="flex items-center gap-2">
          <Receipt className="h-6 w-6 text-neon-cyan" />
          <h1 className="text-xl font-display">{t('title')}</h1>
        </div>
        {orders.length > 0 && (
          <span className="text-sm text-muted-foreground font-mono">
            {orders.length} {t('total')}
          </span>
        )}
      </motion.div>

      {/* Payments List */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-neon-cyan" />
        </div>
      ) : orders.length === 0 ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className={`${cardBg} ${borderColor} border rounded-lg p-8 text-center`}
        >
          <Receipt className="h-12 w-12 text-muted-foreground mx-auto mb-3" />
          <p className="text-sm text-muted-foreground font-mono">{t('noPayments')}</p>
        </motion.div>
      ) : (
        <div className="space-y-2">
          {orders.map((order, index) => (
            <PaymentCard
              key={order.id}
              order={order}
              index={index}
              colorScheme={colorScheme}
              formatCurrency={formatCurrency}
              t={t}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// Payment Card Component
function PaymentCard({
  order,
  index,
  colorScheme,
  formatCurrency,
  t,
}: {
  order: {
    id: string;
    displayed_price: number;
    currency_code: string;
    order_status: string;
    settlement_status: string;
    created_at: string;
    items?: Array<{ display_name?: string | null }>;
  };
  index: number;
  colorScheme: 'light' | 'dark';
  formatCurrency: (amount: number, currency: string) => string;
  t: (key: string) => string;
}) {
  const isDark = colorScheme === 'dark';
  const cardBg = isDark ? 'bg-[var(--tg-bg-color,oklch(0.06_0.015_260))]' : 'bg-[var(--tg-bg-color,oklch(0.70_0.010_250))]';
  const borderColor = isDark ? 'border-[var(--tg-hint-color,oklch(0.25_0.10_195))]' : 'border-[var(--tg-hint-color,oklch(0.45_0.03_250))]';

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.05 }}
      className={`${cardBg} ${borderColor} border rounded-lg p-4`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <div className="text-sm font-mono text-muted-foreground mb-1">
            {order.items?.[0]?.display_name || order.id}
          </div>

          {/* Amount */}
          <div className="text-lg font-display text-neon-cyan mb-1">
            {formatCurrency(order.displayed_price, order.currency_code)}
          </div>

          {/* Status & Date */}
          <div className="flex items-center gap-2 text-xs text-muted-foreground font-mono mb-2">
            <span className="capitalize">{order.order_status}</span>
            <span>•</span>
            <span>{new Date(order.created_at).toLocaleDateString()}</span>
            <span>{new Date(order.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
          </div>

          {/* Status Badge */}
          <StatusBadge status={order.settlement_status || order.order_status} t={t} />
        </div>
      </div>
    </motion.div>
  );
}

// Status Badge Component
function StatusBadge({ status, t }: { status: string; t: (key: string) => string }) {
  const normalizedStatus = status === 'paid' ? 'completed' : status;
  const config: Record<string, { icon: typeof Clock; color: string; bg: string }> = {
    pending: { icon: Clock, color: 'text-yellow-400', bg: 'bg-yellow-400/10' },
    awaiting_payment: { icon: Clock, color: 'text-yellow-400', bg: 'bg-yellow-400/10' },
    completed: { icon: CheckCircle2, color: 'text-neon-cyan', bg: 'bg-neon-cyan/10' },
    committed: { icon: CheckCircle2, color: 'text-neon-cyan', bg: 'bg-neon-cyan/10' },
    failed: { icon: XCircle, color: 'text-destructive', bg: 'bg-destructive/10' },
    refunded: { icon: RefreshCw, color: 'text-neon-purple', bg: 'bg-neon-purple/10' },
  };

  const { icon: Icon, color, bg } = config[normalizedStatus] || config.pending;

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded ${bg} ${color} text-xs font-mono`}>
      <Icon className="h-3 w-3" />
      {t(`status_${normalizedStatus}`)}
    </span>
  );
}
