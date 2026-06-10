'use client';

import { useState } from 'react';
import { Modal } from '@/shared/ui/modal';
import { CyberInput } from '@/features/auth/components/CyberInput';
import { PasswordStrengthMeter } from '@/features/auth/components/PasswordStrengthMeter';
import {
  validatePasswordInput,
  type PasswordValidationCode,
} from '@/features/auth/lib/validation';
import { securityApi } from '@/lib/api/security';
import { motion } from 'motion/react';
import { Key, CheckCircle, AlertCircle } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { RateLimitError } from '@/lib/api/client';
import { getApiErrorDetail, getApiErrorStatus } from './security-modal-utils';

interface ChangePasswordModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function ChangePasswordModal({ isOpen, onClose, onSuccess }: ChangePasswordModalProps) {
  const t = useTranslations('Settings.cabinet.securityFlows.password');
  const commonT = useTranslations('Settings.cabinet.securityFlows.common');
  const passwordRequirementsT = useTranslations('Auth.passwordStrength.requirements');

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [rateLimitSeconds, setRateLimitSeconds] = useState<number | null>(null);
  const newPasswordValidation = validatePasswordInput(newPassword);
  const passwordsMatch = newPassword === confirmPassword && confirmPassword.length > 0;

  const getPasswordMessage = (code: PasswordValidationCode | 'passwordMismatch') => {
    if (code === 'passwordRequired') {
      return t('validation.newPasswordRequired');
    }

    if (code === 'passwordMismatch') {
      return t('validation.passwordMismatch');
    }

    return passwordRequirementsT(code);
  };

  // Start rate limit countdown
  const startRateLimitCountdown = (seconds: number) => {
    setRateLimitSeconds(seconds);
    const interval = setInterval(() => {
      setRateLimitSeconds((prev) => {
        if (prev === null || prev <= 1) {
          clearInterval(interval);
          return null;
        }
        return prev - 1;
      });
    }, 1000);
  };

  // Reset state on close
  const handleClose = () => {
    setCurrentPassword('');
    setNewPassword('');
    setConfirmPassword('');
    setError('');
    setLoading(false);
    setSuccess(false);
    setRateLimitSeconds(null);
    onClose();
  };

  // Handle password change
  const handleChangePassword = async () => {
    // Validation
    if (!currentPassword) {
      setError(t('validation.currentPasswordRequired'));
      return;
    }
    if (!newPassword) {
      setError(t('validation.newPasswordRequired'));
      return;
    }
    if (!newPasswordValidation.isValid) {
      setError(getPasswordMessage(newPasswordValidation.codes[0]));
      return;
    }
    if (!passwordsMatch) {
      setError(getPasswordMessage('passwordMismatch'));
      return;
    }
    if (currentPassword === newPassword) {
      setError(t('validation.passwordMustChange'));
      return;
    }

    setLoading(true);
    setError('');

    try {
      await securityApi.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
        new_password_confirm: confirmPassword,
      });

      setSuccess(true);

      // Auto-close after 2 seconds
      setTimeout(() => {
        onSuccess();
        handleClose();
      }, 2000);
    } catch (err) {
      if (err instanceof RateLimitError) {
        setError(err.message);
        startRateLimitCountdown(err.retryAfter);
      } else {
        const status = getApiErrorStatus(err);
        const detail = getApiErrorDetail(err);

        if (status === 401) {
          setError(t('errors.currentPasswordIncorrect'));
        } else if (status === 422) {
          setError(detail ?? t('errors.validationFailed'));
        } else {
          setError(detail ?? commonT('errors.generic'));
        }
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title={t('modalTitle')}>
      {success ? (
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="text-center space-y-6 py-8"
        >
          <CheckCircle className="h-16 w-16 text-matrix-green mx-auto" />
          <div className="space-y-2">
            <h3 className="text-lg font-display text-matrix-green">
              {t('success.title')}
            </h3>
            <p className="text-sm text-muted-foreground">
              {t('success.description')}
            </p>
          </div>
        </motion.div>
      ) : (
        <div className="space-y-6">
          <div className="text-center space-y-2">
            <Key className="h-12 w-12 text-neon-cyan mx-auto" />
            <h3 className="text-lg font-display text-neon-cyan">
              {t('title')}
            </h3>
            <p className="text-sm text-muted-foreground">
              {t('description')}
            </p>
          </div>

          {/* Current Password */}
          <CyberInput
            label={t('current.label')}
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            placeholder={t('current.placeholder')}
            prefix="auth"
            disabled={loading || rateLimitSeconds !== null}
          />

          {/* New Password */}
          <div className="space-y-2">
            <CyberInput
              label={t('new.label')}
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder={t('new.placeholder')}
              prefix="auth"
              disabled={loading || rateLimitSeconds !== null}
            />

            <PasswordStrengthMeter password={newPassword} />
          </div>

          {/* Confirm Password */}
          <CyberInput
            label={t('confirm.label')}
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder={t('confirm.placeholder')}
            prefix="auth"
            error={confirmPassword && !passwordsMatch ? getPasswordMessage('passwordMismatch') : error}
            success={passwordsMatch}
            disabled={loading || rateLimitSeconds !== null}
            onKeyDown={(e) => e.key === 'Enter' && handleChangePassword()}
          />

          {/* Rate Limit Warning */}
          {rateLimitSeconds !== null && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-center gap-2 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded text-yellow-500 text-sm font-mono"
            >
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              <div>
                <p className="font-semibold">{commonT('rateLimit.title')}</p>
                <p className="text-xs">{commonT('retryIn', { seconds: rateLimitSeconds })}</p>
              </div>
            </motion.div>
          )}

          {/* Submit Button */}
          <button
            onClick={handleChangePassword}
            disabled={
              loading ||
              !currentPassword ||
              !newPasswordValidation.isValid ||
              !confirmPassword ||
              !passwordsMatch ||
              rateLimitSeconds !== null
            }
            className="w-full px-4 py-3 bg-neon-cyan/20 hover:bg-neon-cyan/30 border border-neon-cyan/50 text-neon-cyan font-mono text-sm rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? t('actions.changing') : t('actions.change')}
          </button>

          {/* Rate Limit Info */}
          <p className="text-xs text-muted-foreground text-center font-mono">
            {t('rateLimitInfo')}
          </p>
        </div>
      )}
    </Modal>
  );
}
