'use client';

import { useTranslations } from 'next-intl';
import { usePaymentHistory } from '../hooks/usePaymentHistory';
import { CreditCard, CheckCircle, Clock, XCircle } from 'lucide-react';

export function PaymentHistoryClient() {
  const t = useTranslations('PaymentHistory');
  const { data: paymentsData, isLoading } = usePaymentHistory();

  const payments = (paymentsData as any)?.payments || [];

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'paid':
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-matrix-green" />;
      case 'pending':
        return <Clock className="h-5 w-5 text-neon-cyan" />;
      case 'failed':
      case 'expired':
        return <XCircle className="h-5 w-5 text-neon-pink" />;
      default:
        return <CreditCard className="h-5 w-5 text-muted-foreground" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'paid':
      case 'completed':
        return 'text-matrix-green';
      case 'pending':
        return 'text-neon-cyan';
      case 'failed':
      case 'expired':
        return 'text-neon-pink';
      default:
        return 'text-muted-foreground';
    }
  };

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Payment History List */}
      <section>
        <h2 className="text-xl font-display text-neon-purple mb-4 pl-2 border-l-4 border-neon-purple">
          {t('history') || 'Payment History'}
        </h2>

        {isLoading ? (
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="cyber-card p-4 animate-pulse">
                <div className="h-4 bg-grid-line/20 rounded w-3/4 mb-2" />
                <div className="h-3 bg-grid-line/20 rounded w-1/2" />
              </div>
            ))}
          </div>
        ) : payments.length === 0 ? (
          <div className="cyber-card p-8 text-center">
            <CreditCard className="h-12 w-12 text-muted-foreground mx-auto mb-3 opacity-50" />
            <p className="text-muted-foreground font-mono">{t('noPayments') || 'No payment history yet'}</p>
          </div>
        ) : (
          <div className="space-y-2">
            {payments.map((payment: any) => (
              <div
                key={payment.id}
                className="cyber-card p-4 flex items-center justify-between hover:bg-terminal-surface/50 transition-colors"
              >
                <div className="flex items-center gap-4 flex-1">
                  {getStatusIcon(payment.status)}
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-1">
                      <p className="font-mono text-sm">{payment.description || payment.type || 'Payment'}</p>
                      <span className={`text-xs font-mono px-2 py-0.5 rounded border ${getStatusColor(payment.status)} border-current/30 bg-current/10`}>
                        {payment.status?.toUpperCase()}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 text-xs text-muted-foreground">
                      <span>{new Date(payment.created_at).toLocaleString()}</span>
                      {payment.currency && (
                        <span className="font-mono">{payment.currency.toUpperCase()}</span>
                      )}
                      {payment.invoice_id && (
                        <span className="font-mono">ID: {payment.invoice_id.slice(0, 8)}...</span>
                      )}
                    </div>
                  </div>
                </div>
                <div className={`font-display text-lg ${getStatusColor(payment.status)}`}>
                  {formatCurrency(payment.amount || 0)}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
