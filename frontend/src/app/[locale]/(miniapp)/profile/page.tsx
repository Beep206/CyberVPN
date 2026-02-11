'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import { useRouter } from '@/i18n/navigation';
import { authApi, referralApi, twofaApi, paymentsApi, securityApi, partnerApi } from '@/lib/api';
import { useAuthStore } from '@/stores/auth-store';
import { motion } from 'motion/react';
import {
  User,
  Gift,
  Shield,
  Receipt,
  Settings,
  Briefcase,
  LogOut,
  Trash2,
  ChevronDown,
  ChevronUp,
  Copy,
  Share2,
  Lock,
  Check,
  Key,
  AlertTriangle,
  Loader2,
  Smartphone
} from 'lucide-react';
import { useTelegramWebApp } from '../hooks/useTelegramWebApp';
import { MiniAppBottomSheet } from '../components/MiniAppBottomSheet';
import { VpnConfigCard } from '../components/VpnConfigCard';

/**
 * Mini App Profile page
 * User info, referral, security, payment history, settings, partner, account management
 */
export default function MiniAppProfilePage() {
  const t = useTranslations('MiniApp.profile');
  const { haptic, colorScheme, webApp } = useTelegramWebApp();
  const router = useRouter();
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({});
  const [passwordSheetOpen, setPasswordSheetOpen] = useState(false);
  const [antiphishingSheetOpen, setAntiphishingSheetOpen] = useState(false);

  // Password change form state
  const [passwordForm, setPasswordForm] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  });

  // Antiphishing form state
  const [antiphishingCode, setAntiphishingCode] = useState('');

  // Partner bind form state
  const [partnerCode, setPartnerCode] = useState('');

  // Fetch referral data
  const { data: referralCode } = useQuery({
    queryKey: ['referral-code'],
    queryFn: async () => {
      const { data } = await referralApi.getCode();
      return data;
    },
  });

  const { data: referralStats } = useQuery({
    queryKey: ['referral-stats'],
    queryFn: async () => {
      const { data } = await referralApi.getStats();
      return data;
    },
  });

  // Fetch 2FA status
  const { data: twofaStatus } = useQuery({
    queryKey: ['twofa-status'],
    queryFn: async () => {
      const { data } = await twofaApi.getStatus();
      return data;
    },
  });

  // Fetch payment history (limited)
  const { data: paymentHistory } = useQuery({
    queryKey: ['payment-history-preview'],
    queryFn: async () => {
      const { data } = await paymentsApi.getHistory();
      return data;
    },
  });

  // Fetch antiphishing code
  const { data: antiphishingData } = useQuery({
    queryKey: ['antiphishing-code'],
    queryFn: async () => {
      const { data } = await securityApi.getAntiphishingCode();
      return data;
    },
  });

  // Fetch partner dashboard
  const { data: partnerData } = useQuery({
    queryKey: ['partner-dashboard'],
    queryFn: async () => {
      const { data } = await partnerApi.getDashboard();
      return data;
    },
  });

  // Password change mutation
  const changePasswordMutation = useMutation({
    mutationFn: async (data: { current_password: string; new_password: string; new_password_confirm: string }) => {
      const { data: response } = await securityApi.changePassword(data);
      return response;
    },
    onSuccess: () => {
      haptic('heavy');
      webApp?.showAlert(t('passwordChange.success'));
      setPasswordSheetOpen(false);
      setPasswordForm({ currentPassword: '', newPassword: '', confirmPassword: '' });
    },
    onError: (error: unknown) => {
      haptic('heavy');
      const axiosError = error as { response?: { data?: { detail?: string } } };
      webApp?.showAlert(axiosError.response?.data?.detail || t('passwordChange.error'));
    },
  });

  // Antiphishing set/update mutation
  const setAntiphishingMutation = useMutation({
    mutationFn: async (code: string) => {
      const { data } = await securityApi.setAntiphishingCode({ code });
      return data;
    },
    onSuccess: () => {
      haptic('heavy');
      queryClient.invalidateQueries({ queryKey: ['antiphishing-code'] });
      webApp?.showAlert(t('antiphishing.success'));
      setAntiphishingSheetOpen(false);
      setAntiphishingCode('');
    },
    onError: (error: unknown) => {
      haptic('heavy');
      const axiosError = error as { response?: { data?: { detail?: string } } };
      webApp?.showAlert(axiosError.response?.data?.detail || t('antiphishing.error'));
    },
  });

  // Antiphishing delete mutation
  const deleteAntiphishingMutation = useMutation({
    mutationFn: async () => {
      const { data } = await securityApi.deleteAntiphishingCode();
      return data;
    },
    onSuccess: () => {
      haptic('heavy');
      queryClient.invalidateQueries({ queryKey: ['antiphishing-code'] });
      webApp?.showAlert(t('antiphishing.deleteSuccess'));
      setAntiphishingSheetOpen(false);
    },
    onError: (error: unknown) => {
      haptic('heavy');
      const axiosError = error as { response?: { data?: { detail?: string } } };
      webApp?.showAlert(axiosError.response?.data?.detail || t('antiphishing.deleteError'));
    },
  });

  const toggleSection = (section: string) => {
    haptic('light');
    setExpandedSections((prev) => ({ ...prev, [section]: !prev[section] }));
  };

  const handleLogout = async () => {
    haptic('heavy');
    const confirmed = await webApp?.showConfirm(t('logoutConfirm'));
    if (confirmed) {
      await logout();
      router.push('/');
    }
  };

  const handleDeleteAccount = async () => {
    haptic('heavy');
    const confirmed = await webApp?.showConfirm(t('deleteAccountConfirm'));
    if (confirmed) {
      try {
        await authApi.deleteAccount();
        webApp?.showAlert(t('accountDeleted'));
        router.push('/');
      } catch (error: unknown) {
        const axiosError = error as { response?: { data?: { detail?: string } } };
        webApp?.showAlert(axiosError.response?.data?.detail || t('deleteAccountError'));
      }
    }
  };

  const copyToClipboard = async (text: string, successMessage: string) => {
    haptic('medium');
    try {
      await navigator.clipboard.writeText(text);
      webApp?.showAlert(successMessage);
    } catch {
      webApp?.showAlert(t('copyError'));
    }
  };

  const shareReferralCode = () => {
    haptic('medium');
    if (referralCode?.referral_code) {
      const shareText = t('referralShareText', { code: referralCode.referral_code });
      webApp?.openTelegramLink(`https://t.me/share/url?url=${encodeURIComponent(shareText)}`);
    }
  };

  const handlePasswordChange = () => {
    haptic('medium');
    const { currentPassword, newPassword, confirmPassword } = passwordForm;

    // Validation
    if (!currentPassword) {
      webApp?.showAlert(t('passwordChange.currentPasswordRequired'));
      return;
    }
    if (!newPassword) {
      webApp?.showAlert(t('passwordChange.newPasswordRequired'));
      return;
    }
    if (!confirmPassword) {
      webApp?.showAlert(t('passwordChange.confirmPasswordRequired'));
      return;
    }
    if (newPassword !== confirmPassword) {
      webApp?.showAlert(t('passwordChange.passwordMismatch'));
      return;
    }
    if (newPassword.length < 8) {
      webApp?.showAlert(t('passwordChange.passwordTooShort'));
      return;
    }

    changePasswordMutation.mutate({
      current_password: currentPassword,
      new_password: newPassword,
      new_password_confirm: confirmPassword,
    });
  };

  const handleAntiphishingSubmit = () => {
    haptic('medium');

    // Validation
    if (!antiphishingCode) {
      webApp?.showAlert(t('antiphishing.codeRequired'));
      return;
    }
    if (antiphishingCode.length < 4) {
      webApp?.showAlert(t('antiphishing.codeTooShort'));
      return;
    }
    if (antiphishingCode.length > 32) {
      webApp?.showAlert(t('antiphishing.codeTooLong'));
      return;
    }

    setAntiphishingMutation.mutate(antiphishingCode);
  };

  const handleAntiphishingDelete = async () => {
    haptic('heavy');
    const confirmed = await webApp?.showConfirm(t('antiphishing.deleteConfirm'));
    if (confirmed) {
      deleteAntiphishingMutation.mutate();
    }
  };

  // Partner bind mutation
  const bindPartnerMutation = useMutation({
    mutationFn: async (code: string) => {
      const { data } = await partnerApi.bindCode({ partner_code: code });
      return data;
    },
    onSuccess: () => {
      haptic('heavy');
      queryClient.invalidateQueries({ queryKey: ['partner-dashboard'] });
      webApp?.showAlert(t('partnerDashboard.bindSuccess'));
      setPartnerCode('');
    },
    onError: (error: unknown) => {
      haptic('heavy');
      const axiosError = error as { response?: { data?: { detail?: string } } };
      webApp?.showAlert(axiosError.response?.data?.detail || t('partnerDashboard.bindError'));
    },
  });

  const handlePartnerBind = () => {
    haptic('medium');
    if (!partnerCode) {
      webApp?.showAlert(t('partnerDashboard.codeRequired'));
      return;
    }
    bindPartnerMutation.mutate(partnerCode);
  };

  // Theme colors
  const isDark = colorScheme === 'dark';
  const cardBg = isDark ? 'bg-[var(--tg-bg-color,oklch(0.06_0.015_260))]' : 'bg-[var(--tg-bg-color,oklch(0.70_0.010_250))]';
  const borderColor = isDark ? 'border-[var(--tg-hint-color,oklch(0.25_0.10_195))]' : 'border-[var(--tg-hint-color,oklch(0.45_0.03_250))]';

  return (
    <div className="max-w-screen-sm mx-auto space-y-4">
      {/* User Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`${cardBg} ${borderColor} border rounded-lg p-6`}
      >
        <div className="flex items-center gap-4">
          <div className="h-16 w-16 rounded-full bg-neon-cyan/20 flex items-center justify-center">
            <User className="h-8 w-8 text-neon-cyan" />
          </div>
          <div className="flex-1">
            <h2 className="text-xl font-display">{user?.login || t('guest')}</h2>
            <p className="text-sm text-muted-foreground font-mono">{user?.email || t('noEmail')}</p>
          </div>
        </div>
      </motion.div>

      {/* VPN Config Card */}
      <VpnConfigCard colorScheme={colorScheme} />

      {/* Referral Section */}
      <CollapsibleSection
        title={t('referral')}
        icon={Gift}
        isExpanded={expandedSections['referral']}
        onToggle={() => toggleSection('referral')}
        colorScheme={colorScheme}
      >
        <div className="space-y-4">
          {referralCode && (
            <div>
              <label className="text-xs text-muted-foreground font-mono block mb-2">
                {t('yourReferralCode')}
              </label>
              <div className="flex gap-2">
                <div className="flex-1 px-3 py-2 bg-muted border border-border rounded-lg font-mono text-lg">
                  {referralCode.referral_code}
                </div>
                <button
                  onClick={() => copyToClipboard(referralCode.referral_code, t('codeCopied'))}
                  className="p-2 bg-neon-cyan text-black rounded-lg hover:bg-neon-cyan/90 transition-colors touch-manipulation"
                  aria-label={t('copy')}
                >
                  <Copy className="h-5 w-5" />
                </button>
                <button
                  onClick={shareReferralCode}
                  className="p-2 bg-neon-purple text-white rounded-lg hover:bg-neon-purple/90 transition-colors touch-manipulation"
                  aria-label={t('share')}
                >
                  <Share2 className="h-5 w-5" />
                </button>
              </div>
            </div>
          )}

          {referralStats && (
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 bg-muted rounded-lg">
                <div className="text-2xl font-display text-neon-cyan">{referralStats.total_referrals || 0}</div>
                <div className="text-xs text-muted-foreground font-mono">{t('totalReferrals')}</div>
              </div>
              <div className="p-3 bg-muted rounded-lg">
                <div className="text-2xl font-display text-neon-cyan">
                  ${(referralStats.total_earned || 0).toFixed(2)}
                </div>
                <div className="text-xs text-muted-foreground font-mono">{t('totalEarnings')}</div>
              </div>
            </div>
          )}
        </div>
      </CollapsibleSection>

      {/* Security Section */}
      <CollapsibleSection
        title={t('security')}
        icon={Shield}
        isExpanded={expandedSections['security']}
        onToggle={() => toggleSection('security')}
        colorScheme={colorScheme}
      >
        <div className="space-y-3">
          {/* 2FA Status */}
          <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
            <div className="flex items-center gap-2">
              <Lock className="h-4 w-4 text-muted-foreground" />
              <span className="font-mono text-sm">{t('twoFactorAuth')}</span>
            </div>
            <div className={`flex items-center gap-1 text-xs font-mono ${twofaStatus?.status === 'enabled' ? 'text-neon-cyan' : 'text-muted-foreground'}`}>
              {twofaStatus?.status === 'enabled' ? (
                <>
                  <Check className="h-3 w-3" />
                  {t('enabled')}
                </>
              ) : (
                t('disabled')
              )}
            </div>
          </div>

          {/* Change Password Button */}
          <button
            onClick={() => {
              haptic('medium');
              setPasswordSheetOpen(true);
            }}
            className="w-full flex items-center justify-between p-3 bg-muted rounded-lg hover:bg-muted/70 transition-colors touch-manipulation"
          >
            <div className="flex items-center gap-2">
              <Key className="h-4 w-4 text-neon-cyan" />
              <span className="font-mono text-sm">{t('changePassword')}</span>
            </div>
          </button>

          {/* Antiphishing Code Button */}
          <button
            onClick={() => {
              haptic('medium');
              setAntiphishingSheetOpen(true);
            }}
            className="w-full flex items-center justify-between p-3 bg-muted rounded-lg hover:bg-muted/70 transition-colors touch-manipulation"
          >
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-neon-cyan" />
              <span className="font-mono text-sm">{t('antiphishingCode')}</span>
            </div>
            {antiphishingData?.code && (
              <span className="text-xs text-muted-foreground font-mono">{antiphishingData.code}</span>
            )}
          </button>

          {/* Active Devices Button */}
          <button
            onClick={() => {
              haptic('medium');
              router.push('/devices');
            }}
            className="w-full flex items-center justify-between p-3 bg-muted rounded-lg hover:bg-muted/70 transition-colors touch-manipulation"
          >
            <div className="flex items-center gap-2">
              <Smartphone className="h-4 w-4 text-neon-cyan" />
              <span className="font-mono text-sm">{t('activeDevices') || 'Active Devices'}</span>
            </div>
          </button>

          <p className="text-xs text-muted-foreground font-mono">
            {t('securityNote')}
          </p>
        </div>
      </CollapsibleSection>

      {/* Payment History Section */}
      <CollapsibleSection
        title={t('paymentHistory')}
        icon={Receipt}
        isExpanded={expandedSections['payments']}
        onToggle={() => toggleSection('payments')}
        colorScheme={colorScheme}
      >
        <div className="space-y-2">
          {paymentHistory?.payments && paymentHistory.payments.length > 0 ? (
            <>
              {paymentHistory.payments.slice(0, 3).map((payment: { id?: string; amount?: number; status?: string; created_at?: string }, index: number) => (
                <div key={payment.id || index} className="p-3 bg-muted rounded-lg">
                  <div className="flex justify-between items-start mb-1">
                    <span className="text-sm font-mono">${(payment.amount || 0).toFixed(2)}</span>
                    <span className={`text-xs font-mono ${payment.status === 'completed' ? 'text-neon-cyan' : 'text-yellow-400'}`}>
                      {payment.status}
                    </span>
                  </div>
                  {payment.created_at && (
                    <div className="text-xs text-muted-foreground font-mono">
                      {new Date(payment.created_at).toLocaleDateString()}
                    </div>
                  )}
                </div>
              ))}
              <button
                onClick={() => {
                  haptic('medium');
                  router.push('/payments');
                }}
                className="w-full py-2 text-sm font-mono text-neon-cyan hover:text-neon-cyan/80 transition-colors"
              >
                {t('viewAll')} →
              </button>
            </>
          ) : (
            <p className="text-sm text-muted-foreground font-mono text-center py-4">
              {t('noPayments')}
            </p>
          )}
        </div>
      </CollapsibleSection>

      {/* Settings Section */}
      <CollapsibleSection
        title={t('settings')}
        icon={Settings}
        isExpanded={expandedSections['settings']}
        onToggle={() => toggleSection('settings')}
        colorScheme={colorScheme}
      >
        <div className="space-y-3">
          <div className="p-3 bg-muted rounded-lg">
            <div className="text-sm font-mono mb-1">{t('language')}</div>
            <div className="text-xs text-muted-foreground font-mono">{t('languageNote')}</div>
          </div>
          <div className="p-3 bg-muted rounded-lg">
            <div className="text-sm font-mono mb-1">{t('notifications')}</div>
            <div className="text-xs text-muted-foreground font-mono">{t('notificationsNote')}</div>
          </div>
        </div>
      </CollapsibleSection>

      {/* Partner Section */}
      <CollapsibleSection
        title={t('partner')}
        icon={Briefcase}
        isExpanded={expandedSections['partner']}
        onToggle={() => toggleSection('partner')}
        colorScheme={colorScheme}
      >
        {partnerData?.is_partner ? (
          /* Partner Dashboard */
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-neon-cyan mb-3">
              <Check className="h-4 w-4" />
              <span className="text-sm font-mono">{t('partnerDashboard.isPartner')}</span>
            </div>

            {/* Stats Grid */}
            {partnerData.tier && (
              <div className="grid grid-cols-3 gap-2">
                <div className="p-3 bg-muted rounded-lg">
                  <div className="text-xs text-muted-foreground font-mono mb-1">
                    {t('partnerDashboard.tier')}
                  </div>
                  <div className="text-lg font-display text-neon-cyan">
                    {partnerData.tier}
                  </div>
                </div>
                <div className="p-3 bg-muted rounded-lg">
                  <div className="text-xs text-muted-foreground font-mono mb-1">
                    {t('partnerDashboard.totalClients')}
                  </div>
                  <div className="text-lg font-display text-neon-cyan">
                    {partnerData.total_clients || 0}
                  </div>
                </div>
                <div className="p-3 bg-muted rounded-lg">
                  <div className="text-xs text-muted-foreground font-mono mb-1">
                    {t('partnerDashboard.totalEarned')}
                  </div>
                  <div className="text-lg font-display text-neon-cyan">
                    ${(partnerData.total_earned || 0).toFixed(2)}
                  </div>
                </div>
              </div>
            )}

            {/* Partner Codes */}
            <div>
              <h4 className="text-xs text-muted-foreground font-mono mb-2">
                {t('partnerDashboard.partnerCodes')}
              </h4>
              {partnerData.codes && partnerData.codes.length > 0 ? (
                <div className="space-y-2">
                  {partnerData.codes.map((code, index) => (
                    <div key={code.partner_code || index} className="p-3 bg-muted rounded-lg">
                      <div className="flex justify-between items-start mb-1">
                        <span className="text-sm font-mono text-neon-cyan">{code.partner_code}</span>
                        <span className="text-xs font-mono text-muted-foreground">
                          {t('partnerDashboard.markup')}: {code.markup_pct}%
                        </span>
                      </div>
                      {code.created_at && (
                        <div className="text-xs text-muted-foreground font-mono">
                          {t('partnerDashboard.createdAt')}: {new Date(code.created_at).toLocaleDateString()}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground font-mono text-center py-4">
                  {t('partnerDashboard.noCodes')}
                </p>
              )}
            </div>
          </div>
        ) : (
          /* Bind Partner Code Form */
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground font-mono">
              {t('partnerDashboard.bindCodeDescription')}
            </p>

            <div>
              <label className="text-xs text-muted-foreground font-mono block mb-2">
                {t('partnerDashboard.bindCode')}
              </label>
              <input
                type="text"
                value={partnerCode}
                onChange={(e) => setPartnerCode(e.target.value.toUpperCase())}
                placeholder={t('partnerDashboard.codePlaceholder')}
                className="w-full px-3 py-2 bg-muted border border-border rounded-lg font-mono text-sm focus:outline-none focus:ring-2 focus:ring-neon-cyan uppercase"
                disabled={bindPartnerMutation.isPending}
              />
            </div>

            <button
              onClick={handlePartnerBind}
              disabled={bindPartnerMutation.isPending}
              className="w-full py-3 px-4 bg-neon-cyan text-black font-mono rounded-lg hover:bg-neon-cyan/90 transition-colors disabled:opacity-50 touch-manipulation"
            >
              {bindPartnerMutation.isPending ? (
                <span className="flex items-center justify-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {t('partnerDashboard.submitting')}
                </span>
              ) : (
                t('partnerDashboard.submit')
              )}
            </button>
          </div>
        )}
      </CollapsibleSection>

      {/* Account Actions */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="space-y-3"
      >
        <button
          onClick={handleLogout}
          className="w-full py-3 px-4 bg-muted border border-border rounded-lg font-mono flex items-center justify-center gap-2 hover:border-neon-cyan/50 transition-colors touch-manipulation"
        >
          <LogOut className="h-4 w-4" />
          {t('logout')}
        </button>
        <button
          onClick={handleDeleteAccount}
          className="w-full py-3 px-4 bg-destructive/10 border border-destructive/30 text-destructive rounded-lg font-mono flex items-center justify-center gap-2 hover:bg-destructive/20 transition-colors touch-manipulation"
        >
          <Trash2 className="h-4 w-4" />
          {t('deleteAccount')}
        </button>
      </motion.div>

      {/* Password Change Bottom Sheet */}
      <MiniAppBottomSheet
        isOpen={passwordSheetOpen}
        onClose={() => {
          setPasswordSheetOpen(false);
          setPasswordForm({ currentPassword: '', newPassword: '', confirmPassword: '' });
        }}
        title={t('passwordChange.title')}
        colorScheme={colorScheme}
      >
        <div className="space-y-4">
          <div>
            <label className="text-xs text-muted-foreground font-mono block mb-2">
              {t('passwordChange.currentPassword')}
            </label>
            <input
              type="password"
              value={passwordForm.currentPassword}
              onChange={(e) => setPasswordForm({ ...passwordForm, currentPassword: e.target.value })}
              className="w-full px-3 py-2 bg-muted border border-border rounded-lg font-mono text-sm focus:outline-none focus:ring-2 focus:ring-neon-cyan"
              disabled={changePasswordMutation.isPending}
            />
          </div>

          <div>
            <label className="text-xs text-muted-foreground font-mono block mb-2">
              {t('passwordChange.newPassword')}
            </label>
            <input
              type="password"
              value={passwordForm.newPassword}
              onChange={(e) => setPasswordForm({ ...passwordForm, newPassword: e.target.value })}
              className="w-full px-3 py-2 bg-muted border border-border rounded-lg font-mono text-sm focus:outline-none focus:ring-2 focus:ring-neon-cyan"
              disabled={changePasswordMutation.isPending}
            />
          </div>

          <div>
            <label className="text-xs text-muted-foreground font-mono block mb-2">
              {t('passwordChange.confirmPassword')}
            </label>
            <input
              type="password"
              value={passwordForm.confirmPassword}
              onChange={(e) => setPasswordForm({ ...passwordForm, confirmPassword: e.target.value })}
              className="w-full px-3 py-2 bg-muted border border-border rounded-lg font-mono text-sm focus:outline-none focus:ring-2 focus:ring-neon-cyan"
              disabled={changePasswordMutation.isPending}
            />
          </div>

          <button
            onClick={handlePasswordChange}
            disabled={changePasswordMutation.isPending}
            className="w-full py-3 px-4 bg-neon-cyan text-black font-mono rounded-lg hover:bg-neon-cyan/90 transition-colors disabled:opacity-50 touch-manipulation"
          >
            {changePasswordMutation.isPending ? (
              <span className="flex items-center justify-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                {t('passwordChange.submitting')}
              </span>
            ) : (
              t('passwordChange.submit')
            )}
          </button>
        </div>
      </MiniAppBottomSheet>

      {/* Antiphishing Code Bottom Sheet */}
      <MiniAppBottomSheet
        isOpen={antiphishingSheetOpen}
        onClose={() => {
          setAntiphishingSheetOpen(false);
          setAntiphishingCode('');
        }}
        title={t('antiphishing.title')}
        colorScheme={colorScheme}
      >
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground font-mono">
            {t('antiphishing.description')}
          </p>

          {antiphishingData?.code && (
            <div>
              <label className="text-xs text-muted-foreground font-mono block mb-2">
                {t('antiphishing.currentCode')}
              </label>
              <div className="px-3 py-2 bg-muted border border-border rounded-lg font-mono text-sm">
                {antiphishingData.code}
              </div>
            </div>
          )}

          <div>
            <label className="text-xs text-muted-foreground font-mono block mb-2">
              {antiphishingData?.code ? t('antiphishing.newCode') : t('antiphishing.newCode')}
            </label>
            <input
              type="text"
              value={antiphishingCode}
              onChange={(e) => setAntiphishingCode(e.target.value)}
              placeholder={t('antiphishing.codePlaceholder')}
              maxLength={32}
              className="w-full px-3 py-2 bg-muted border border-border rounded-lg font-mono text-sm focus:outline-none focus:ring-2 focus:ring-neon-cyan"
              disabled={setAntiphishingMutation.isPending || deleteAntiphishingMutation.isPending}
            />
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleAntiphishingSubmit}
              disabled={setAntiphishingMutation.isPending || deleteAntiphishingMutation.isPending}
              className="flex-1 py-3 px-4 bg-neon-cyan text-black font-mono rounded-lg hover:bg-neon-cyan/90 transition-colors disabled:opacity-50 touch-manipulation"
            >
              {setAntiphishingMutation.isPending ? (
                <span className="flex items-center justify-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {t('antiphishing.submitting')}
                </span>
              ) : (
                antiphishingData?.code ? t('antiphishing.updateCode') : t('antiphishing.setCode')
              )}
            </button>

            {antiphishingData?.code && (
              <button
                onClick={handleAntiphishingDelete}
                disabled={setAntiphishingMutation.isPending || deleteAntiphishingMutation.isPending}
                className="py-3 px-4 bg-destructive/10 border border-destructive/30 text-destructive font-mono rounded-lg hover:bg-destructive/20 transition-colors disabled:opacity-50 touch-manipulation"
              >
                {deleteAntiphishingMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  t('antiphishing.deleteCode')
                )}
              </button>
            )}
          </div>
        </div>
      </MiniAppBottomSheet>
    </div>
  );
}

// Collapsible Section Component
function CollapsibleSection({
  title,
  icon: Icon,
  isExpanded,
  onToggle,
  colorScheme,
  children,
}: {
  title: string;
  icon: typeof Gift;
  isExpanded: boolean;
  onToggle: () => void;
  colorScheme: 'light' | 'dark';
  children: React.ReactNode;
}) {
  const isDark = colorScheme === 'dark';
  const cardBg = isDark ? 'bg-[var(--tg-bg-color,oklch(0.06_0.015_260))]' : 'bg-[var(--tg-bg-color,oklch(0.70_0.010_250))]';
  const borderColor = isDark ? 'border-[var(--tg-hint-color,oklch(0.25_0.10_195))]' : 'border-[var(--tg-hint-color,oklch(0.45_0.03_250))]';

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`${cardBg} ${borderColor} border rounded-lg overflow-hidden`}
    >
      <button
        onClick={onToggle}
        className="w-full p-4 flex items-center justify-between hover:bg-muted/50 transition-colors touch-manipulation"
      >
        <div className="flex items-center gap-3">
          <Icon className="h-5 w-5 text-neon-cyan" />
          <span className="font-display">{title}</span>
        </div>
        {isExpanded ? (
          <ChevronUp className="h-5 w-5 text-muted-foreground" />
        ) : (
          <ChevronDown className="h-5 w-5 text-muted-foreground" />
        )}
      </button>

      {isExpanded && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="px-4 pb-4"
        >
          {children}
        </motion.div>
      )}
    </motion.div>
  );
}
