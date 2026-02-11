'use client';

import { useState } from 'react';
import { usePartnerDashboard, usePartnerCodes, usePartnerEarnings } from '../hooks/usePartner';
import { partnerApi } from '@/lib/api/partner';
import { CyberInput } from '@/features/auth/components/CyberInput';
import { motion } from 'motion/react';
import { Handshake, DollarSign, Users, Code, Plus, Edit, CheckCircle, AlertCircle } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { AxiosError } from 'axios';

export function PartnerClient() {
  const t = useTranslations('Partner');
  const { data: dashboard, isLoading: dashboardLoading, error: dashboardError } = usePartnerDashboard();
  const { data: codes, isLoading: codesLoading, refetch: refetchCodes } = usePartnerCodes();
  const { data: earnings, isLoading: earningsLoading } = usePartnerEarnings();

  const [bindCode, setBindCode] = useState('');
  const [bindLoading, setBindLoading] = useState(false);
  const [bindError, setBindError] = useState('');
  const [bindSuccess, setBindSuccess] = useState('');

  const [newCodeName, setNewCodeName] = useState('');
  const [newCodeMarkup, setNewCodeMarkup] = useState('');
  const [creatingCode, setCreatingCode] = useState(false);
  const [createError, setCreateError] = useState('');

  const isPartner = !dashboardError || (dashboardError as any)?.response?.status !== 403;

  // Handle binding to partner
  const handleBind = async () => {
    if (!bindCode.trim()) {
      setBindError('Please enter a partner code');
      return;
    }

    setBindLoading(true);
    setBindError('');
    setBindSuccess('');

    try {
      await partnerApi.bindToPartner({ code: bindCode });
      setBindSuccess('Successfully bound to partner!');
      setBindCode('');
      setTimeout(() => window.location.reload(), 2000);
    } catch (err) {
      if (err instanceof AxiosError) {
        setBindError(err.response?.data?.detail || 'Failed to bind to partner');
      } else {
        setBindError('An error occurred');
      }
    } finally {
      setBindLoading(false);
    }
  };

  // Handle code creation
  const handleCreateCode = async () => {
    if (!newCodeName.trim()) {
      setCreateError('Code name is required');
      return;
    }
    const markup = parseFloat(newCodeMarkup);
    if (isNaN(markup) || markup < 0 || markup > 100) {
      setCreateError('Markup must be between 0-100');
      return;
    }

    setCreatingCode(true);
    setCreateError('');

    try {
      await partnerApi.createCode({ code: newCodeName.toUpperCase(), markup_percent: markup });
      setNewCodeName('');
      setNewCodeMarkup('');
      await refetchCodes();
    } catch (err) {
      if (err instanceof AxiosError) {
        setCreateError(err.response?.data?.detail || 'Failed to create code');
      } else {
        setCreateError('An error occurred');
      }
    } finally {
      setCreatingCode(false);
    }
  };

  // Non-partner view - bind form
  if (dashboardError && (dashboardError as any)?.response?.status === 403) {
    return (
      <div className="space-y-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="cyber-card p-8 text-center"
        >
          <Handshake className="h-16 w-16 text-neon-cyan mx-auto mb-4" />
          <h2 className="text-2xl font-display text-neon-cyan mb-2">
            Become a Partner
          </h2>
          <p className="text-muted-foreground mb-6">
            Enter your partner code to access the partner dashboard
          </p>

          <div className="max-w-md mx-auto space-y-4">
            <CyberInput
              label="Partner Code"
              type="text"
              value={bindCode}
              onChange={(e) => setBindCode(e.target.value.toUpperCase())}
              placeholder="PARTNER2024"
              prefix="partner"
              error={bindError}
              disabled={bindLoading}
              onKeyDown={(e) => e.key === 'Enter' && handleBind()}
            />

            {bindSuccess && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center gap-2 p-3 bg-matrix-green/10 border border-matrix-green/30 rounded text-matrix-green text-sm font-mono"
              >
                <CheckCircle className="h-4 w-4" />
                <span>{bindSuccess}</span>
              </motion.div>
            )}

            <button
              onClick={handleBind}
              disabled={bindLoading || !bindCode.trim()}
              className="w-full px-4 py-3 bg-neon-cyan/20 hover:bg-neon-cyan/30 border border-neon-cyan/50 text-neon-cyan font-mono text-sm rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {bindLoading ? 'Binding...' : 'Bind Partner Code'}
            </button>
          </div>
        </motion.div>
      </div>
    );
  }

  // Partner view
  return (
    <div className="space-y-8">
      {/* Dashboard Stats */}
      <section>
        <h2 className="text-xl font-display text-neon-purple mb-4 pl-2 border-l-4 border-neon-purple">
          Dashboard
        </h2>

        {dashboardLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[1, 2, 3].map((i) => (
              <div key={i} className="cyber-card p-6 animate-pulse">
                <div className="h-6 bg-grid-line/30 rounded w-1/2 mb-2" />
                <div className="h-8 bg-grid-line/30 rounded w-3/4" />
              </div>
            ))}
          </div>
        ) : dashboard ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="cyber-card p-6"
            >
              <div className="flex items-center gap-3 mb-2">
                <DollarSign className="h-5 w-5 text-matrix-green" />
                <h3 className="text-sm text-muted-foreground">Total Earnings</h3>
              </div>
              <p className="text-3xl font-display text-matrix-green">
                ${dashboard.total_earnings || 0}
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="cyber-card p-6"
            >
              <div className="flex items-center gap-3 mb-2">
                <Code className="h-5 w-5 text-neon-cyan" />
                <h3 className="text-sm text-muted-foreground">Active Codes</h3>
              </div>
              <p className="text-3xl font-display text-neon-cyan">
                {dashboard.active_codes_count || 0}
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="cyber-card p-6"
            >
              <div className="flex items-center gap-3 mb-2">
                <Users className="h-5 w-5 text-neon-pink" />
                <h3 className="text-sm text-muted-foreground">Referrals</h3>
              </div>
              <p className="text-3xl font-display text-neon-pink">
                {dashboard.referrals_count || 0}
              </p>
            </motion.div>
          </div>
        ) : null}
      </section>

      {/* Partner Codes */}
      <section>
        <h2 className="text-xl font-display text-neon-purple mb-4 pl-2 border-l-4 border-neon-purple">
          Partner Codes
        </h2>

        {/* Create Code Form */}
        <div className="cyber-card p-6 mb-6">
          <h3 className="text-lg font-display text-neon-cyan mb-4 flex items-center gap-2">
            <Plus className="h-5 w-5" />
            Create New Code
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <CyberInput
              label="Code Name"
              type="text"
              value={newCodeName}
              onChange={(e) => setNewCodeName(e.target.value.toUpperCase())}
              placeholder="SUMMER2024"
              prefix="code"
              disabled={creatingCode}
            />

            <CyberInput
              label="Markup %"
              type="number"
              value={newCodeMarkup}
              onChange={(e) => setNewCodeMarkup(e.target.value)}
              placeholder="10"
              prefix="markup"
              error={createError}
              disabled={creatingCode}
            />

            <div className="flex items-end">
              <button
                onClick={handleCreateCode}
                disabled={creatingCode || !newCodeName || !newCodeMarkup}
                className="w-full px-4 py-3 bg-matrix-green/20 hover:bg-matrix-green/30 border border-matrix-green/50 text-matrix-green font-mono text-sm rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {creatingCode ? 'Creating...' : 'Create'}
              </button>
            </div>
          </div>
        </div>

        {/* Codes Table */}
        {codesLoading ? (
          <div className="cyber-card p-6 animate-pulse">
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-12 bg-grid-line/30 rounded" />
              ))}
            </div>
          </div>
        ) : codes && codes.length > 0 ? (
          <div className="cyber-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-grid-line/30">
                    <th className="text-left p-4 text-sm text-muted-foreground font-mono">Code</th>
                    <th className="text-left p-4 text-sm text-muted-foreground font-mono">Markup</th>
                    <th className="text-left p-4 text-sm text-muted-foreground font-mono">Uses</th>
                    <th className="text-left p-4 text-sm text-muted-foreground font-mono">Earnings</th>
                  </tr>
                </thead>
                <tbody>
                  {codes.map((code: any, i: number) => (
                    <tr key={i} className="border-b border-grid-line/10 hover:bg-terminal-surface/50 transition-colors">
                      <td className="p-4">
                        <code className="text-neon-cyan font-mono text-sm">{code.code}</code>
                      </td>
                      <td className="p-4 font-mono text-sm">{code.markup_percent}%</td>
                      <td className="p-4 font-mono text-sm">{code.uses_count || 0}</td>
                      <td className="p-4 font-mono text-sm text-matrix-green">${code.earnings || 0}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="cyber-card p-8 text-center">
            <p className="text-muted-foreground font-mono">No partner codes yet</p>
          </div>
        )}
      </section>

      {/* Earnings History */}
      {earnings && earnings.length > 0 && (
        <section>
          <h2 className="text-xl font-display text-neon-purple mb-4 pl-2 border-l-4 border-neon-purple">
            Recent Earnings
          </h2>

          <div className="cyber-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-grid-line/30">
                    <th className="text-left p-4 text-sm text-muted-foreground font-mono">Date</th>
                    <th className="text-left p-4 text-sm text-muted-foreground font-mono">Code</th>
                    <th className="text-left p-4 text-sm text-muted-foreground font-mono">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {earnings.slice(0, 10).map((earning: any, i: number) => (
                    <tr key={i} className="border-b border-grid-line/10">
                      <td className="p-4 text-sm font-mono">{new Date(earning.created_at).toLocaleDateString()}</td>
                      <td className="p-4"><code className="text-neon-cyan text-sm">{earning.code}</code></td>
                      <td className="p-4 font-mono text-sm text-matrix-green">${earning.amount}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
