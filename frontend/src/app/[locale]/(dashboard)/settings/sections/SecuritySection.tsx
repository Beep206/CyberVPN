'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { useTwoFactorStatus } from '../hooks/useSettings';
import { TwoFactorModal } from '../components/TwoFactorModal';
import { ChangePasswordModal } from '../components/ChangePasswordModal';
import { AntiphishingModal } from '../components/AntiphishingModal';

export function SecuritySection() {
  const t = useTranslations('Settings');
  const { data: tfaStatus, isLoading, refetch } = useTwoFactorStatus();

  // Modal states
  const [show2FAModal, setShow2FAModal] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [showAntiphishingModal, setShowAntiphishingModal] = useState(false);

  if (isLoading) {
    return (
      <section className="cyber-card p-6 animate-pulse">
        <div className="h-6 bg-grid-line/30 rounded w-1/4 mb-4" />
        <div className="h-4 bg-grid-line/20 rounded w-1/2" />
      </section>
    );
  }

  return (
    <section>
      <h2 className="text-xl font-display text-neon-purple mb-4 pl-2 border-l-4 border-neon-purple">
        {t('security') || 'Security'}
      </h2>

      <div className="space-y-4">
        {/* Two-Factor Authentication */}
        <div className="cyber-card p-6">
          <div className="flex justify-between items-start">
            <div>
              <h3 className="font-display text-lg text-neon-cyan">{t('twoFactor') || 'Two-Factor Authentication'}</h3>
              <p className="text-sm text-muted-foreground mt-1">
                {tfaStatus?.status === 'enabled'
                  ? t('tfaEnabled') || 'Your account is protected with 2FA'
                  : t('tfaDisabled') || 'Add an extra layer of security'}
              </p>
            </div>
            <button
              onClick={() => setShow2FAModal(true)}
              className={`px-4 py-2 font-mono text-sm rounded border transition-colors ${
                tfaStatus?.status === 'enabled'
                  ? 'bg-red-500/20 hover:bg-red-500/30 border-red-500/50 text-red-400'
                  : 'bg-matrix-green/20 hover:bg-matrix-green/30 border-matrix-green/50 text-matrix-green'
              }`}
            >
              {tfaStatus?.status === 'enabled' ? t('disable') || 'Disable' : t('enable') || 'Enable'}
            </button>
          </div>
        </div>

        {/* Password Change */}
        <div className="cyber-card p-6">
          <div className="flex justify-between items-start">
            <div>
              <h3 className="font-display text-lg text-neon-cyan">{t('password') || 'Password'}</h3>
              <p className="text-sm text-muted-foreground mt-1">
                {t('passwordDesc') || 'Change your account password'}
              </p>
            </div>
            <button
              onClick={() => setShowPasswordModal(true)}
              className="px-4 py-2 bg-neon-cyan/20 hover:bg-neon-cyan/30 border border-neon-cyan/50 text-neon-cyan font-mono text-sm rounded transition-colors"
            >
              {t('change') || 'Change'}
            </button>
          </div>
        </div>

        {/* Antiphishing Code */}
        <div className="cyber-card p-6">
          <div className="flex justify-between items-start">
            <div>
              <h3 className="font-display text-lg text-neon-cyan">{t('antiphishing') || 'Antiphishing Code'}</h3>
              <p className="text-sm text-muted-foreground mt-1">
                {t('antiphishingDesc') || 'Protect yourself from phishing emails'}
              </p>
            </div>
            <button
              onClick={() => setShowAntiphishingModal(true)}
              className="px-4 py-2 bg-neon-cyan/20 hover:bg-neon-cyan/30 border border-neon-cyan/50 text-neon-cyan font-mono text-sm rounded transition-colors"
            >
              {t('manage') || 'Manage'}
            </button>
          </div>
        </div>
      </div>

      {/* 2FA Modal */}
      <TwoFactorModal
        isOpen={show2FAModal}
        onClose={() => setShow2FAModal(false)}
        isEnabled={tfaStatus?.status === 'enabled'}
        onSuccess={() => {
          refetch();
        }}
      />

      {/* Password Change Modal */}
      <ChangePasswordModal
        isOpen={showPasswordModal}
        onClose={() => setShowPasswordModal(false)}
        onSuccess={() => {
          // Password changed successfully - could show a toast notification
        }}
      />

      {/* Antiphishing Modal */}
      <AntiphishingModal
        isOpen={showAntiphishingModal}
        onClose={() => setShowAntiphishingModal(false)}
        onSuccess={() => {
          // Antiphishing code updated successfully
        }}
      />
    </section>
  );
}
