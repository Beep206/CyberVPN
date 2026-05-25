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
import { AxiosError } from 'axios';
import { RateLimitError } from '@/lib/api/client';

interface ChangePasswordModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const FALLBACK_PASSWORD_MESSAGES: Record<PasswordValidationCode | 'passwordMismatch', string> = {
  passwordRequired: 'Password is required',
  passwordMinLength: 'Password must be at least 12 characters',
  passwordUppercase: 'Password must contain one uppercase letter',
  passwordLowercase: 'Password must contain one lowercase letter',
  passwordNumber: 'Password must contain one number',
  passwordSpecial: 'Password must contain one special character',
  passwordLatinLayout: 'Use Latin letters, digits and supported symbols only',
  passwordCommon: 'Choose a less common password',
  passwordRepeated: 'Password cannot be one repeated character',
  passwordNumericSequence: 'Password cannot be a simple numeric sequence',
  passwordMismatch: 'Passwords do not match',
};

export function ChangePasswordModal({ isOpen, onClose, onSuccess }: ChangePasswordModalProps) {
  const t = useTranslations('Auth.passwordStrength');

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
    const key = `validation.${code}`;
    return t.has(key) ? t(key) : FALLBACK_PASSWORD_MESSAGES[code];
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
      setError('Current password is required');
      return;
    }
    if (!newPassword) {
      setError('New password is required');
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
      setError('New password must be different from current password');
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
      } else if (err instanceof AxiosError) {
        const detail = err.response?.data?.detail;
        if (err.response?.status === 401) {
          setError('Current password is incorrect');
        } else if (err.response?.status === 422) {
          setError(detail || 'Password validation failed');
        } else {
          setError(detail || 'An error occurred. Please try again.');
        }
      } else {
        setError('An error occurred. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="CHANGE_PASSWORD">
      {success ? (
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="text-center space-y-6 py-8"
        >
          <CheckCircle className="h-16 w-16 text-matrix-green mx-auto" />
          <div className="space-y-2">
            <h3 className="text-lg font-display text-matrix-green">
              Password Changed Successfully!
            </h3>
            <p className="text-sm text-muted-foreground">
              Your password has been updated
            </p>
          </div>
        </motion.div>
      ) : (
        <div className="space-y-6">
          <div className="text-center space-y-2">
            <Key className="h-12 w-12 text-neon-cyan mx-auto" />
            <h3 className="text-lg font-display text-neon-cyan">
              Update Your Password
            </h3>
            <p className="text-sm text-muted-foreground">
              Enter your current password and choose a new one
            </p>
          </div>

          {/* Current Password */}
          <CyberInput
            label="Current Password"
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            placeholder="Enter current password"
            prefix="auth"
            disabled={loading || rateLimitSeconds !== null}
          />

          {/* New Password */}
          <div className="space-y-2">
            <CyberInput
              label="New Password"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="Enter new password"
              prefix="auth"
              disabled={loading || rateLimitSeconds !== null}
            />

            <PasswordStrengthMeter password={newPassword} />
          </div>

          {/* Confirm Password */}
          <CyberInput
            label="Confirm New Password"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="Confirm new password"
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
                <p className="font-semibold">Rate Limit Active</p>
                <p className="text-xs">Retry in {rateLimitSeconds}s</p>
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
            {loading ? 'Changing Password...' : 'Change Password'}
          </button>

          {/* Rate Limit Info */}
          <p className="text-xs text-muted-foreground text-center font-mono">
            Rate limited to 3 attempts per hour
          </p>
        </div>
      )}
    </Modal>
  );
}
