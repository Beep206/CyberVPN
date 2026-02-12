'use client';

import { useState } from 'react';
import { Modal } from '@/shared/ui/modal';
import { subscriptionsApi } from '@/lib/api/subscriptions';
import { motion } from 'motion/react';
import { AlertTriangle, CheckCircle, X } from 'lucide-react';
import { AxiosError } from 'axios';

interface CancelSubscriptionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  subscriptionName?: string;
  expiresAt?: string;
}

type ModalStep = 'confirm' | 'processing' | 'success';

export function CancelSubscriptionModal({
  isOpen,
  onClose,
  onSuccess,
  subscriptionName = 'subscription',
  expiresAt,
}: CancelSubscriptionModalProps) {
  const [step, setStep] = useState<ModalStep>('confirm');
  const [error, setError] = useState('');

  // Reset state on close
  const handleClose = () => {
    setStep('confirm');
    setError('');
    onClose();
  };

  // Handle cancellation
  const handleCancel = async () => {
    setStep('processing');
    setError('');

    try {
      await subscriptionsApi.cancel();
      setStep('success');

      // Auto-close and refresh after 2 seconds
      setTimeout(() => {
        onSuccess();
        handleClose();
      }, 2000);
    } catch (err) {
      setStep('confirm');
      if (err instanceof AxiosError) {
        const detail = err.response?.data?.detail;
        if (err.response?.status === 404) {
          setError('No active subscription found');
        } else if (err.response?.status === 400) {
          setError(detail || 'Subscription already cancelled');
        } else {
          setError(detail || 'Failed to cancel subscription');
        }
      } else {
        setError('An error occurred. Please try again.');
      }
    }
  };

  // Render confirmation step
  if (step === 'confirm') {
    return (
      <Modal isOpen={isOpen} onClose={handleClose} title="CANCEL_SUBSCRIPTION">
        <div className="space-y-6">
          {/* Warning Icon */}
          <div className="text-center space-y-3">
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: 'spring', bounce: 0.5 }}
            >
              <AlertTriangle className="h-16 w-16 text-red-500 mx-auto" />
            </motion.div>
            <h3 className="text-xl font-display text-red-500">
              Cancel Subscription?
            </h3>
          </div>

          {/* Warning Message */}
          <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg space-y-3">
            <p className="text-sm text-red-400 font-mono leading-relaxed">
              You&apos;re about to cancel your <span className="text-red-300 font-semibold">{subscriptionName}</span> subscription.
            </p>

            <div className="space-y-2">
              <div className="flex items-start gap-2">
                <X className="h-4 w-4 text-red-400 flex-shrink-0 mt-0.5" />
                <p className="text-xs text-muted-foreground">
                  You will lose access to premium features
                </p>
              </div>
              <div className="flex items-start gap-2">
                <X className="h-4 w-4 text-red-400 flex-shrink-0 mt-0.5" />
                <p className="text-xs text-muted-foreground">
                  VPN access will be disabled
                </p>
              </div>
              <div className="flex items-start gap-2">
                <X className="h-4 w-4 text-red-400 flex-shrink-0 mt-0.5" />
                <p className="text-xs text-muted-foreground">
                  No refunds for remaining time
                </p>
              </div>
            </div>

            {expiresAt && (
              <div className="pt-3 border-t border-red-500/20">
                <p className="text-xs text-muted-foreground">
                  Your subscription will remain active until{' '}
                  <span className="text-neon-cyan font-mono">
                    {new Date(expiresAt).toLocaleDateString()}
                  </span>
                </p>
              </div>
            )}
          </div>

          {/* Error Message */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="p-3 bg-red-500/10 border border-red-500/30 rounded text-red-500 text-sm font-mono flex items-center gap-2"
            >
              <AlertTriangle className="h-4 w-4 flex-shrink-0" />
              <span>{error}</span>
            </motion.div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-3">
            <button
              onClick={handleClose}
              className="flex-1 px-4 py-3 bg-terminal-bg hover:bg-terminal-surface border border-grid-line/50 text-muted-foreground font-mono text-sm rounded transition-colors"
            >
              Keep Subscription
            </button>
            <button
              onClick={handleCancel}
              className="flex-1 px-4 py-3 bg-red-500/20 hover:bg-red-500/30 border border-red-500/50 text-red-400 font-mono text-sm rounded transition-colors"
            >
              Cancel Subscription
            </button>
          </div>

          {/* Additional Info */}
          <p className="text-xs text-muted-foreground text-center font-mono">
            This action cannot be undone
          </p>
        </div>
      </Modal>
    );
  }

  // Render processing step
  if (step === 'processing') {
    return (
      <Modal isOpen={isOpen} onClose={() => {}} title="CANCEL_SUBSCRIPTION">
        <div className="text-center py-8 space-y-4">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
          >
            <div className="h-12 w-12 border-4 border-neon-cyan border-t-transparent rounded-full mx-auto" />
          </motion.div>
          <p className="text-sm text-muted-foreground font-mono">
            Processing cancellation...
          </p>
        </div>
      </Modal>
    );
  }

  // Render success step
  if (step === 'success') {
    return (
      <Modal isOpen={isOpen} onClose={handleClose} title="CANCEL_SUBSCRIPTION">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="text-center space-y-6 py-8"
        >
          <CheckCircle className="h-16 w-16 text-matrix-green mx-auto" />
          <div className="space-y-2">
            <h3 className="text-lg font-display text-matrix-green">
              Subscription Cancelled
            </h3>
            <p className="text-sm text-muted-foreground">
              Your subscription has been cancelled successfully
            </p>
            {expiresAt && (
              <p className="text-xs text-muted-foreground font-mono mt-3">
                Access remains active until {new Date(expiresAt).toLocaleDateString()}
              </p>
            )}
          </div>
        </motion.div>
      </Modal>
    );
  }

  return null;
}
