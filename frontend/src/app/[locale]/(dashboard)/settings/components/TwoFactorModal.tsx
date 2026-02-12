'use client';

import { useState } from 'react';
import { Modal } from '@/shared/ui/modal';
import { CyberInput } from '@/features/auth/components/CyberInput';
import { twofaApi } from '@/lib/api/twofa';
import { motion } from 'motion/react';
import { ShieldCheck, Key, Copy, CheckCircle, AlertCircle, Smartphone } from 'lucide-react';
import { AxiosError } from 'axios';
import { RateLimitError } from '@/lib/api/client';
import QRCode from 'qrcode';

interface TwoFactorModalProps {
  isOpen: boolean;
  onClose: () => void;
  isEnabled: boolean;
  onSuccess: () => void;
}

type EnableStep = 'reauth' | 'setup' | 'verify' | 'success';
type DisableStep = 'confirm' | 'success';

export function TwoFactorModal({ isOpen, onClose, isEnabled, onSuccess }: TwoFactorModalProps) {
  // Enable flow state
  const [enableStep, setEnableStep] = useState<EnableStep>('reauth');
  const [password, setPassword] = useState('');
  const [totpCode, setTotpCode] = useState('');
  const [, setQrCodeUri] = useState('');
  const [qrCodeDataUrl, setQrCodeDataUrl] = useState('');
  const [secret, setSecret] = useState('');
  const [backupCodes, setBackupCodes] = useState<string[]>([]);

  // Disable flow state
  const [disableStep, setDisableStep] = useState<DisableStep>('confirm');
  const [disablePassword, setDisablePassword] = useState('');
  const [disableTotpCode, setDisableTotpCode] = useState('');

  // UI state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [copiedSecret, setCopiedSecret] = useState(false);
  const [copiedBackupCodes, setCopiedBackupCodes] = useState(false);
  const [rateLimitSeconds, setRateLimitSeconds] = useState<number | null>(null);

  // Reset state on close
  const handleClose = () => {
    setEnableStep('reauth');
    setDisableStep('confirm');
    setPassword('');
    setTotpCode('');
    setDisablePassword('');
    setDisableTotpCode('');
    setQrCodeUri('');
    setQrCodeDataUrl('');
    setSecret('');
    setBackupCodes([]);
    setError('');
    setLoading(false);
    setCopiedSecret(false);
    setCopiedBackupCodes(false);
    setRateLimitSeconds(null);
    onClose();
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

  // Enable flow: Step 1 - Reauth
  const handleReauth = async () => {
    if (!password) {
      setError('Password is required');
      return;
    }

    setLoading(true);
    setError('');

    try {
      await twofaApi.reauth({ password });
      setEnableStep('setup');
      // Automatically call setup
      await handleSetup();
    } catch (err) {
      if (err instanceof RateLimitError) {
        setError(err.message);
        startRateLimitCountdown(err.retryAfter);
      } else if (err instanceof AxiosError) {
        setError(err.response?.data?.detail || 'Invalid password');
      } else {
        setError('An error occurred. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  // Enable flow: Step 2 - Setup (auto-called after reauth)
  const handleSetup = async () => {
    setLoading(true);
    setError('');

    try {
      const response = await twofaApi.setup();
      const data = response.data;

      setSecret(data.secret);
      setQrCodeUri(data.qr_uri);
      setBackupCodes((data as Record<string, unknown>).backup_codes as string[] ?? []);

      // Generate QR code data URL
      const dataUrl = await QRCode.toDataURL(data.qr_uri, {
        width: 256,
        margin: 2,
        color: {
          dark: '#00ffff',
          light: '#0a0e1a',
        },
      });
      setQrCodeDataUrl(dataUrl);

      setEnableStep('verify');
    } catch (err) {
      if (err instanceof AxiosError) {
        setError(err.response?.data?.detail || 'Failed to generate 2FA secret');
      } else {
        setError('An error occurred. Please try again.');
      }
      setEnableStep('reauth');
    } finally {
      setLoading(false);
    }
  };

  // Enable flow: Step 3 - Verify
  const handleVerify = async () => {
    if (!totpCode || totpCode.length !== 6) {
      setError('Please enter a valid 6-digit code');
      return;
    }

    setLoading(true);
    setError('');

    try {
      await twofaApi.verify({ code: totpCode });
      setEnableStep('success');
    } catch (err) {
      if (err instanceof RateLimitError) {
        setError(err.message);
        startRateLimitCountdown(err.retryAfter);
      } else if (err instanceof AxiosError) {
        setError(err.response?.data?.detail || 'Invalid verification code');
      } else {
        setError('An error occurred. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  // Disable flow
  const handleDisable = async () => {
    if (!disablePassword) {
      setError('Password is required');
      return;
    }
    if (!disableTotpCode || disableTotpCode.length !== 6) {
      setError('Please enter a valid 6-digit code');
      return;
    }

    setLoading(true);
    setError('');

    try {
      await twofaApi.disable({ password: disablePassword, code: disableTotpCode });
      setDisableStep('success');
    } catch (err) {
      if (err instanceof RateLimitError) {
        setError(err.message);
        startRateLimitCountdown(err.retryAfter);
      } else if (err instanceof AxiosError) {
        setError(err.response?.data?.detail || 'Invalid credentials');
      } else {
        setError('An error occurred. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  // Copy functions
  const copyToClipboard = async (text: string, setCopied: (val: boolean) => void) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setError('Failed to copy to clipboard');
    }
  };

  const copyBackupCodes = () => copyToClipboard(backupCodes.join('\n'), setCopiedBackupCodes);
  const copySecret = () => copyToClipboard(secret, setCopiedSecret);

  // Final success handler
  const handleFinalSuccess = () => {
    onSuccess();
    handleClose();
  };

  // Render enable flow
  const renderEnableFlow = () => {
    switch (enableStep) {
      case 'reauth':
        return (
          <div className="space-y-6">
            <div className="text-center space-y-2">
              <ShieldCheck className="h-16 w-16 text-neon-cyan mx-auto" />
              <h3 className="text-lg font-display text-neon-cyan">
                Enable Two-Factor Authentication
              </h3>
              <p className="text-sm text-muted-foreground">
                Re-authenticate with your password to continue
              </p>
            </div>

            <CyberInput
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              prefix="2fa"
              error={error}
              disabled={loading || rateLimitSeconds !== null}
              onKeyDown={(e) => e.key === 'Enter' && handleReauth()}
            />

            {rateLimitSeconds !== null && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center gap-2 text-yellow-500 text-sm font-mono"
              >
                <AlertCircle className="h-4 w-4" />
                <span>Retry in {rateLimitSeconds}s</span>
              </motion.div>
            )}

            <button
              onClick={handleReauth}
              disabled={loading || rateLimitSeconds !== null}
              className="w-full px-4 py-3 bg-neon-cyan/20 hover:bg-neon-cyan/30 border border-neon-cyan/50 text-neon-cyan font-mono text-sm rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Verifying...' : 'Continue'}
            </button>
          </div>
        );

      case 'setup':
        return (
          <div className="text-center">
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="space-y-2"
            >
              <Key className="h-8 w-8 text-neon-cyan mx-auto animate-pulse" />
              <p className="text-sm text-muted-foreground">Generating secure secret...</p>
            </motion.div>
          </div>
        );

      case 'verify':
        return (
          <div className="space-y-6">
            <div className="text-center space-y-4">
              <Smartphone className="h-12 w-12 text-neon-cyan mx-auto" />
              <h3 className="text-lg font-display text-neon-cyan">
                Scan QR Code
              </h3>
              <p className="text-sm text-muted-foreground">
                Scan this QR code with your authenticator app (Google Authenticator, Authy, etc.)
              </p>
            </div>

            {/* QR Code */}
            {qrCodeDataUrl && (
              <div className="flex justify-center">
                <div className="p-4 bg-white rounded-lg">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={qrCodeDataUrl} alt="2FA QR Code" className="w-64 h-64" />
                </div>
              </div>
            )}

            {/* Manual Secret */}
            <div className="space-y-2">
              <label className="block text-sm font-mono text-muted-foreground">
                Or enter this secret manually:
              </label>
              <div className="flex items-center gap-2">
                <code className="flex-1 px-4 py-2 bg-terminal-bg border border-grid-line/50 rounded font-mono text-sm text-matrix-green break-all">
                  {secret}
                </code>
                <button
                  onClick={copySecret}
                  className="px-3 py-2 bg-neon-cyan/20 hover:bg-neon-cyan/30 border border-neon-cyan/50 text-neon-cyan rounded transition-colors"
                  aria-label="Copy secret"
                >
                  {copiedSecret ? <CheckCircle className="h-5 w-5" /> : <Copy className="h-5 w-5" />}
                </button>
              </div>
            </div>

            {/* Verify Code Input */}
            <div className="space-y-4">
              <CyberInput
                label="Verification Code"
                type="text"
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                placeholder="000000"
                prefix="2fa"
                error={error}
                disabled={loading || rateLimitSeconds !== null}
                maxLength={6}
                onKeyDown={(e) => e.key === 'Enter' && handleVerify()}
              />

              {rateLimitSeconds !== null && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex items-center gap-2 text-yellow-500 text-sm font-mono"
                >
                  <AlertCircle className="h-4 w-4" />
                  <span>Retry in {rateLimitSeconds}s</span>
                </motion.div>
              )}

              <button
                onClick={handleVerify}
                disabled={loading || totpCode.length !== 6 || rateLimitSeconds !== null}
                className="w-full px-4 py-3 bg-matrix-green/20 hover:bg-matrix-green/30 border border-matrix-green/50 text-matrix-green font-mono text-sm rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Verifying...' : 'Verify & Enable'}
              </button>
            </div>
          </div>
        );

      case 'success':
        return (
          <div className="space-y-6">
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              className="text-center space-y-4"
            >
              <CheckCircle className="h-16 w-16 text-matrix-green mx-auto" />
              <h3 className="text-lg font-display text-matrix-green">
                2FA Enabled Successfully!
              </h3>
              <p className="text-sm text-muted-foreground">
                Your account is now protected with two-factor authentication
              </p>
            </motion.div>

            {/* Backup Codes */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="block text-sm font-mono text-neon-cyan">
                  Backup Recovery Codes
                </label>
                <button
                  onClick={copyBackupCodes}
                  className="px-3 py-1 bg-neon-cyan/20 hover:bg-neon-cyan/30 border border-neon-cyan/50 text-neon-cyan rounded text-xs font-mono transition-colors flex items-center gap-2"
                >
                  {copiedBackupCodes ? <CheckCircle className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                  {copiedBackupCodes ? 'Copied!' : 'Copy All'}
                </button>
              </div>

              <div className="p-4 bg-terminal-bg border border-yellow-500/50 rounded space-y-2">
                <p className="text-xs text-yellow-500 font-mono flex items-center gap-2">
                  <AlertCircle className="h-4 w-4" />
                  Save these codes securely! Each can only be used once.
                </p>
                <div className="grid grid-cols-2 gap-2 mt-3">
                  {backupCodes.map((code, i) => (
                    <code key={i} className="px-3 py-2 bg-black/40 border border-grid-line/30 rounded font-mono text-xs text-matrix-green">
                      {code}
                    </code>
                  ))}
                </div>
              </div>
            </div>

            <button
              onClick={handleFinalSuccess}
              className="w-full px-4 py-3 bg-matrix-green/20 hover:bg-matrix-green/30 border border-matrix-green/50 text-matrix-green font-mono text-sm rounded transition-colors"
            >
              Done
            </button>
          </div>
        );
    }
  };

  // Render disable flow
  const renderDisableFlow = () => {
    switch (disableStep) {
      case 'confirm':
        return (
          <div className="space-y-6">
            <div className="text-center space-y-2">
              <AlertCircle className="h-16 w-16 text-red-500 mx-auto" />
              <h3 className="text-lg font-display text-red-500">
                Disable Two-Factor Authentication
              </h3>
              <p className="text-sm text-muted-foreground">
                This will reduce the security of your account. Enter your password and current 2FA code to confirm.
              </p>
            </div>

            <div className="space-y-4">
              <CyberInput
                label="Password"
                type="password"
                value={disablePassword}
                onChange={(e) => setDisablePassword(e.target.value)}
                placeholder="Enter your password"
                prefix="2fa"
                disabled={loading || rateLimitSeconds !== null}
              />

              <CyberInput
                label="2FA Code"
                type="text"
                value={disableTotpCode}
                onChange={(e) => setDisableTotpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                placeholder="000000"
                prefix="2fa"
                error={error}
                disabled={loading || rateLimitSeconds !== null}
                maxLength={6}
                onKeyDown={(e) => e.key === 'Enter' && handleDisable()}
              />

              {rateLimitSeconds !== null && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex items-center gap-2 text-yellow-500 text-sm font-mono"
                >
                  <AlertCircle className="h-4 w-4" />
                  <span>Retry in {rateLimitSeconds}s</span>
                </motion.div>
              )}

              <button
                onClick={handleDisable}
                disabled={loading || !disablePassword || disableTotpCode.length !== 6 || rateLimitSeconds !== null}
                className="w-full px-4 py-3 bg-red-500/20 hover:bg-red-500/30 border border-red-500/50 text-red-400 font-mono text-sm rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Disabling...' : 'Disable 2FA'}
              </button>
            </div>
          </div>
        );

      case 'success':
        return (
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            className="text-center space-y-6"
          >
            <CheckCircle className="h-16 w-16 text-matrix-green mx-auto" />
            <div className="space-y-2">
              <h3 className="text-lg font-display text-matrix-green">
                2FA Disabled
              </h3>
              <p className="text-sm text-muted-foreground">
                Two-factor authentication has been disabled for your account
              </p>
            </div>

            <button
              onClick={handleFinalSuccess}
              className="w-full px-4 py-3 bg-neon-cyan/20 hover:bg-neon-cyan/30 border border-neon-cyan/50 text-neon-cyan font-mono text-sm rounded transition-colors"
            >
              Done
            </button>
          </motion.div>
        );
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={isEnabled ? '2FA_DISABLE' : '2FA_ENABLE'}
    >
      {isEnabled ? renderDisableFlow() : renderEnableFlow()}
    </Modal>
  );
}
