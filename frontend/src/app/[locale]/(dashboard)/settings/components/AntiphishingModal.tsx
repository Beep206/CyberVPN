'use client';

import { useState, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { Modal } from '@/shared/ui/modal';
import { CyberInput } from '@/features/auth/components/CyberInput';
import { securityApi } from '@/lib/api/security';
import { motion } from 'motion/react';
import { Shield, Eye, EyeOff, CheckCircle, AlertCircle, Trash2 } from 'lucide-react';
import { getApiErrorDetail } from './security-modal-utils';

interface AntiphishingModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

type ModalView = 'view' | 'edit' | 'delete-confirm' | 'success';

export function AntiphishingModal({ isOpen, onClose, onSuccess }: AntiphishingModalProps) {
  const t = useTranslations('Settings.cabinet.securityFlows.antiphishing');
  const commonT = useTranslations('Settings.cabinet.securityFlows.common');

  const [view, setView] = useState<ModalView>('view');
  const [currentCode, setCurrentCode] = useState<string | null>(null);
  const [newCode, setNewCode] = useState('');
  const [showCode, setShowCode] = useState(false);

  const [loading, setLoading] = useState(false);
  const [loadingData, setLoadingData] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    let isActive = true;

    const fetchCurrentCode = async () => {
      setLoadingData(true);
      setError('');

      try {
        const response = await securityApi.getAntiphishingCode();
        if (isActive) {
          setCurrentCode(response.data.code);
          setView('view');
        }
      } catch (err) {
        if (isActive) {
          setError(getApiErrorDetail(err) ?? t('errors.loadFailed'));
        }
      } finally {
        if (isActive) {
          setLoadingData(false);
        }
      }
    };

    void fetchCurrentCode();

    return () => {
      isActive = false;
    };
  }, [isOpen, t]);

  // Mask code for display (show first 2 and last 2 characters)
  const maskCode = (code: string): string => {
    if (code.length <= 4) return code;
    const first = code.slice(0, 2);
    const last = code.slice(-2);
    const masked = '*'.repeat(Math.max(code.length - 4, 4));
    return `${first}${masked}${last}`;
  };

  // Reset state on close
  const handleClose = () => {
    setView('view');
    setCurrentCode(null);
    setNewCode('');
    setShowCode(false);
    setError('');
    setLoading(false);
    setLoadingData(false);
    setSuccessMessage('');
    onClose();
  };

  // Set or update code
  const handleSetCode = async () => {
    if (!newCode) {
      setError(t('validation.required'));
      return;
    }
    if (newCode.length < 1 || newCode.length > 50) {
      setError(t('validation.length'));
      return;
    }

    setLoading(true);
    setError('');

    try {
      await securityApi.setAntiphishingCode({ code: newCode });
      setSuccessMessage(currentCode ? t('success.updated') : t('success.created'));
      setView('success');

      // Auto-close after 2 seconds
      setTimeout(() => {
        onSuccess();
        handleClose();
      }, 2000);
    } catch (err) {
      setError(getApiErrorDetail(err) ?? t('errors.saveFailed'));
    } finally {
      setLoading(false);
    }
  };

  // Delete code
  const handleDeleteCode = async () => {
    setLoading(true);
    setError('');

    try {
      await securityApi.deleteAntiphishingCode();
      setSuccessMessage(t('success.deleted'));
      setView('success');

      // Auto-close after 2 seconds
      setTimeout(() => {
        onSuccess();
        handleClose();
      }, 2000);
    } catch (err) {
      setError(getApiErrorDetail(err) ?? t('errors.deleteFailed'));
    } finally {
      setLoading(false);
    }
  };

  // Render loading state
  if (loadingData) {
    return (
      <Modal isOpen={isOpen} onClose={handleClose} title={t('modalTitle')}>
        <div className="text-center py-8">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="space-y-4"
          >
            <Shield className="h-12 w-12 text-neon-cyan mx-auto animate-pulse" />
            <p className="text-sm text-muted-foreground">{t('loading')}</p>
          </motion.div>
        </div>
      </Modal>
    );
  }

  // Render view state (show current code)
  if (view === 'view') {
    return (
      <Modal isOpen={isOpen} onClose={handleClose} title={t('modalTitle')}>
        <div className="space-y-6">
          <div className="text-center space-y-2">
            <Shield className="h-12 w-12 text-neon-cyan mx-auto" />
            <h3 className="text-lg font-display text-neon-cyan">
              {t('view.title')}
            </h3>
            <p className="text-sm text-muted-foreground">
              {t('view.description')}
            </p>
          </div>

          {/* Current Code Display */}
          {currentCode ? (
            <div className="space-y-4">
              <div className="space-y-2">
                <label className="block text-sm font-mono text-muted-foreground">
                  {t('view.currentCode')}
                </label>
                <div className="flex items-center gap-2">
                  <div className="flex-1 px-4 py-3 bg-terminal-bg border border-grid-line/50 rounded font-mono text-sm text-matrix-green">
                    {showCode ? currentCode : maskCode(currentCode)}
                  </div>
                  <button
                    onClick={() => setShowCode(!showCode)}
                    className="px-3 py-3 bg-neon-cyan/20 hover:bg-neon-cyan/30 border border-neon-cyan/50 text-neon-cyan rounded transition-colors"
                    aria-label={showCode ? t('actions.hideCode') : t('actions.showCode')}
                  >
                    {showCode ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                  </button>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-3">
                <button
                  onClick={() => {
                    setNewCode(currentCode);
                    setView('edit');
                  }}
                  className="flex-1 px-4 py-3 bg-neon-cyan/20 hover:bg-neon-cyan/30 border border-neon-cyan/50 text-neon-cyan font-mono text-sm rounded transition-colors"
                >
                  {t('actions.edit')}
                </button>
                <button
                  onClick={() => setView('delete-confirm')}
                  className="flex-1 px-4 py-3 bg-red-500/20 hover:bg-red-500/30 border border-red-500/50 text-red-400 font-mono text-sm rounded transition-colors flex items-center justify-center gap-2"
                >
                  <Trash2 className="h-4 w-4" />
                  {t('actions.delete')}
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="p-4 bg-terminal-bg border border-yellow-500/50 rounded">
                <p className="text-sm text-yellow-500 font-mono flex items-center gap-2">
                  <AlertCircle className="h-4 w-4" />
                  {t('empty.title')}
                </p>
              </div>

              <button
                onClick={() => setView('edit')}
                className="w-full px-4 py-3 bg-matrix-green/20 hover:bg-matrix-green/30 border border-matrix-green/50 text-matrix-green font-mono text-sm rounded transition-colors"
              >
                {t('actions.create')}
              </button>
            </div>
          )}
        </div>
      </Modal>
    );
  }

  // Render edit state (set/update code)
  if (view === 'edit') {
    return (
      <Modal isOpen={isOpen} onClose={handleClose} title={t('modalTitle')}>
        <div className="space-y-6">
          <div className="text-center space-y-2">
            <Shield className="h-12 w-12 text-neon-cyan mx-auto" />
            <h3 className="text-lg font-display text-neon-cyan">
              {currentCode ? t('edit.title') : t('create.title')}
            </h3>
            <p className="text-sm text-muted-foreground">
              {t('edit.description')}
            </p>
          </div>

          <CyberInput
            label={t('input.label')}
            type="text"
            value={newCode}
            onChange={(e) => setNewCode(e.target.value.slice(0, 50))}
            placeholder={t('input.placeholder')}
            prefix="security"
            error={error}
            disabled={loading}
            maxLength={50}
            onKeyDown={(e) => e.key === 'Enter' && handleSetCode()}
          />

          <div className="flex items-center justify-between text-xs text-muted-foreground font-mono">
            <span>{t('input.length', { count: newCode.length })}</span>
            {newCode.length > 0 && newCode.length < 1 && (
              <span className="text-red-500">{t('validation.tooShort')}</span>
            )}
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => {
                setNewCode('');
                setView('view');
              }}
              className="flex-1 px-4 py-3 bg-terminal-bg hover:bg-terminal-surface border border-grid-line/50 text-muted-foreground font-mono text-sm rounded transition-colors"
            >
              {commonT('actions.cancel')}
            </button>
            <button
              onClick={handleSetCode}
              disabled={loading || !newCode || newCode.length < 1 || newCode.length > 50}
              className="flex-1 px-4 py-3 bg-matrix-green/20 hover:bg-matrix-green/30 border border-matrix-green/50 text-matrix-green font-mono text-sm rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? commonT('actions.saving') : t('actions.save')}
            </button>
          </div>
        </div>
      </Modal>
    );
  }

  // Render delete confirmation
  if (view === 'delete-confirm') {
    return (
      <Modal isOpen={isOpen} onClose={handleClose} title={t('modalTitle')}>
        <div className="space-y-6">
          <div className="text-center space-y-2">
            <AlertCircle className="h-16 w-16 text-red-500 mx-auto" />
            <h3 className="text-lg font-display text-red-500">
              {t('deleteConfirm.title')}
            </h3>
            <p className="text-sm text-muted-foreground">
              {t('deleteConfirm.description')}
            </p>
          </div>

          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="p-3 bg-red-500/10 border border-red-500/30 rounded text-red-500 text-sm font-mono flex items-center gap-2"
            >
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              <span>{error}</span>
            </motion.div>
          )}

          <div className="flex gap-3">
            <button
              onClick={() => setView('view')}
              disabled={loading}
              className="flex-1 px-4 py-3 bg-terminal-bg hover:bg-terminal-surface border border-grid-line/50 text-muted-foreground font-mono text-sm rounded transition-colors disabled:opacity-50"
            >
              {commonT('actions.cancel')}
            </button>
            <button
              onClick={handleDeleteCode}
              disabled={loading}
              className="flex-1 px-4 py-3 bg-red-500/20 hover:bg-red-500/30 border border-red-500/50 text-red-400 font-mono text-sm rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? t('actions.deleting') : t('actions.deleteCode')}
            </button>
          </div>
        </div>
      </Modal>
    );
  }

  // Render success state
  if (view === 'success') {
    return (
      <Modal isOpen={isOpen} onClose={handleClose} title={t('modalTitle')}>
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="text-center space-y-6 py-8"
        >
          <CheckCircle className="h-16 w-16 text-matrix-green mx-auto" />
          <div className="space-y-2">
            <h3 className="text-lg font-display text-matrix-green">
              {commonT('successTitle')}
            </h3>
            <p className="text-sm text-muted-foreground">
              {successMessage}
            </p>
          </div>
        </motion.div>
      </Modal>
    );
  }

  return null;
}
