'use client';

import { useState } from 'react';
import { Modal } from '@/shared/ui/modal';
import { CyberInput } from '@/features/auth/components/CyberInput';
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

type PasswordStrength = 'weak' | 'fair' | 'good' | 'strong';

export function ChangePasswordModal({ isOpen, onClose, onSuccess }: ChangePasswordModalProps) {
  const t = useTranslations('Auth.passwordStrength');
  const tErrors = useTranslations('Auth.errors');

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [rateLimitSeconds, setRateLimitSeconds] = useState<number | null>(null);

  // Password strength calculation
  const calculateStrength = (password: string): PasswordStrength => {
    let score = 0;
    if (password.length >= 8) score++;
    if (password.length >= 12) score++;
    if (/[a-z]/.test(password)) score++;
    if (/[A-Z]/.test(password)) score++;
    if (/[0-9]/.test(password)) score++;
    if (/[^a-zA-Z0-9]/.test(password)) score++;

    if (score <= 2) return 'weak';
    if (score <= 4) return 'fair';
    if (score <= 5) return 'good';
    return 'strong';
  };

  const strength = newPassword ? calculateStrength(newPassword) : null;

  // Password requirements
  const requirements = {
    length: newPassword.length >= 8,
    uppercase: /[A-Z]/.test(newPassword),
    lowercase: /[a-z]/.test(newPassword),
    number: /[0-9]/.test(newPassword),
    special: /[^a-zA-Z0-9]/.test(newPassword),
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
    if (newPassword.length < 8) {
      setError(tErrors('passwordTooShort'));
      return;
    }
    if (newPassword !== confirmPassword) {
      setError(tErrors('passwordMismatch'));
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

  // Strength meter color
  const strengthColors = {
    weak: 'bg-red-500',
    fair: 'bg-yellow-500',
    good: 'bg-blue-500',
    strong: 'bg-matrix-green',
  };

  const strengthTextColors = {
    weak: 'text-red-500',
    fair: 'text-yellow-500',
    good: 'text-blue-500',
    strong: 'text-matrix-green',
  };

  const strengthWidth = {
    weak: 'w-1/4',
    fair: 'w-1/2',
    good: 'w-3/4',
    strong: 'w-full',
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

            {/* Strength Meter */}
            {newPassword && strength && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-2"
              >
                {/* Bar */}
                <div className="h-2 bg-terminal-bg border border-grid-line/30 rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: '100%' }}
                    className={`h-full ${strengthColors[strength]} ${strengthWidth[strength]} transition-all duration-300`}
                  />
                </div>

                {/* Label */}
                <div className="flex items-center justify-between">
                  <span className={`text-xs font-mono ${strengthTextColors[strength]}`}>
                    {t(strength)}
                  </span>
                </div>

                {/* Requirements Checklist */}
                <div className="grid grid-cols-2 gap-2 mt-3 p-3 bg-terminal-bg border border-grid-line/30 rounded">
                  {Object.entries(requirements).map(([key, met]) => (
                    <div
                      key={key}
                      className={`flex items-center gap-2 text-xs font-mono transition-colors ${
                        met ? 'text-matrix-green' : 'text-muted-foreground/50'
                      }`}
                    >
                      <span className="text-[10px]">{met ? '✓' : '○'}</span>
                      <span>{t(`requirements.${key}`)}</span>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </div>

          {/* Confirm Password */}
          <CyberInput
            label="Confirm New Password"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="Confirm new password"
            prefix="auth"
            error={error}
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
              !newPassword ||
              !confirmPassword ||
              newPassword !== confirmPassword ||
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
