'use client';

import { AnimatePresence, motion } from 'motion/react';
import { useTranslations } from 'next-intl';
import { useState, useTransition } from 'react';
import { Link } from '@/i18n/navigation';
import { authApi } from '@/lib/api';
import { useIsAuthenticated } from '@/stores/auth-store';

const DEFAULT_DELETION_FULFILLMENT_DAYS = 30;

type DeleteAccountOutcome = {
  fulfillmentDays: number;
  reference: string | null;
};

type DeleteAccountClientSurface = 'cabinet' | 'marketing';

type DeleteAccountClientProps = {
  cancelHref?: string;
  returnHref?: string;
  surface?: DeleteAccountClientSurface;
};

function buildDeletionNotes(reason: string, feedback: string): string | null {
  const normalizedReason = reason.trim();
  const normalizedFeedback = feedback.trim();
  const notes = [
    normalizedReason ? `reason=${normalizedReason}` : null,
    normalizedFeedback ? `feedback=${normalizedFeedback}` : null,
  ].filter((item): item is string => item !== null);

  return notes.length > 0 ? notes.join('\n') : null;
}

export function DeleteAccountClient({
  cancelHref = '/',
  returnHref = '/',
  surface = 'marketing',
}: DeleteAccountClientProps = {}) {
  const t = useTranslations('DeleteAccount');
  const isAuthenticated = useIsAuthenticated();

  const [confirmText, setConfirmText] = useState('');
  const [reason, setReason] = useState('');
  const [feedback, setFeedback] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState('');
  const [success, setSuccess] = useState<DeleteAccountOutcome | null>(null);

  const confirmKeyword = t('form.fields.confirmInput.keyword');
  const isConfirmTextValid = confirmText === confirmKeyword;
  const cancelLabel = surface === 'cabinet' ? t('form.cancelToSettings') : t('form.cancel');
  const returnLabel =
    surface === 'cabinet' ? t('success.returnSettings') : t('success.returnHome');

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');

    if (!isAuthenticated) {
      setError(t('error.unauthenticated'));
      return;
    }

    if (!isConfirmTextValid) {
      setError(t('form.fields.confirmInput.error'));
      return;
    }

    if (!confirmed) {
      setError(t('form.fields.confirmation.error'));
      return;
    }

    startTransition(async () => {
      try {
        const response = await authApi.requestPrivacyAction({
          notes: buildDeletionNotes(reason, feedback),
          request_type: 'account_deletion',
        });
        setSuccess({
          fulfillmentDays:
            response.data.manual_fulfillment_target_days ?? DEFAULT_DELETION_FULFILLMENT_DAYS,
          reference: response.data.ticket_reference,
        });
      } catch {
        setError(t('error.message'));
      }
    });
  };

  if (success) {
    return (
      <div className="container mx-auto px-4 py-16 max-w-2xl">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="bg-terminal-bg-light border border-matrix-green p-8 rounded-lg"
        >
          <div className="text-center">
            <h1 className="text-3xl font-display font-bold text-matrix-green mb-4">
              {t('success.title')}
            </h1>
            <p className="text-gray-300 mb-6">{t('success.message')}</p>
            <p className="text-sm text-gray-400 mb-3">
              {t('success.details', { days: success.fulfillmentDays })}
            </p>
            {success.reference ? (
              <p className="mb-6 font-mono text-xs text-matrix-green">
                {t('success.reference', { reference: success.reference })}
              </p>
            ) : null}
            <Link
              href={returnHref}
              className="inline-block px-6 py-3 bg-neon-cyan text-black font-semibold rounded-sm hover:bg-neon-cyan/80 transition-colors"
              aria-label={returnLabel}
            >
              {returnLabel}
            </Link>
          </div>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-16 max-w-4xl">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="mb-12"
      >
        <h1 className="text-4xl font-display font-bold text-matrix-green mb-4">{t('title')}</h1>
        <p className="text-lg text-gray-300">{t('subtitle')}</p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.1 }}
        className="bg-red-950/30 border border-red-500/50 p-6 rounded-lg mb-8"
      >
        <h2 className="text-xl font-display font-semibold text-red-400 mb-2">{t('warning.title')}</h2>
        <p className="text-gray-300">{t('warning.message')}</p>
      </motion.div>

      <div className="grid md:grid-cols-2 gap-8 mb-12">
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.4, delay: 0.2 }}
          className="bg-terminal-bg-light p-6 rounded-lg border border-neon-cyan/20"
        >
          <h2 className="text-xl font-display font-semibold text-neon-cyan mb-4">
            {t('sections.consequences.title')}
          </h2>
          <ul className="space-y-2 text-gray-300">
            <li className="flex items-start"><span className="text-red-400 mr-2" aria-hidden="true">&#10007;</span>{t('sections.consequences.items.accountData')}</li>
            <li className="flex items-start"><span className="text-red-400 mr-2" aria-hidden="true">&#10007;</span>{t('sections.consequences.items.subscriptions')}</li>
            <li className="flex items-start"><span className="text-red-400 mr-2" aria-hidden="true">&#10007;</span>{t('sections.consequences.items.configs')}</li>
            <li className="flex items-start"><span className="text-red-400 mr-2" aria-hidden="true">&#10007;</span>{t('sections.consequences.items.referrals')}</li>
            <li className="flex items-start"><span className="text-red-400 mr-2" aria-hidden="true">&#10007;</span>{t('sections.consequences.items.support')}</li>
          </ul>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.4, delay: 0.2 }}
          className="bg-terminal-bg-light p-6 rounded-lg border border-neon-cyan/20"
        >
          <h2 className="text-xl font-display font-semibold text-neon-cyan mb-4">
            {t('sections.beforeDelete.title')}
          </h2>
          <ul className="space-y-2 text-gray-300">
            <li className="flex items-start"><span className="text-matrix-green mr-2" aria-hidden="true">&rarr;</span>{t('sections.beforeDelete.items.exportData')}</li>
            <li className="flex items-start"><span className="text-matrix-green mr-2" aria-hidden="true">&rarr;</span>{t('sections.beforeDelete.items.cancelSubscriptions')}</li>
            <li className="flex items-start"><span className="text-matrix-green mr-2" aria-hidden="true">&rarr;</span>{t('sections.beforeDelete.items.useReferrals')}</li>
            <li className="flex items-start"><span className="text-matrix-green mr-2" aria-hidden="true">&rarr;</span>{t('sections.beforeDelete.items.saveConfigs')}</li>
          </ul>
        </motion.div>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.3 }}
        className="bg-terminal-bg-light p-6 rounded-lg border border-neon-cyan/20 mb-12"
      >
        <h2 className="text-xl font-display font-semibold text-neon-cyan mb-4">
          {t('sections.alternativeOptions.title')}
        </h2>
        <p className="text-gray-300 mb-4">{t('sections.alternativeOptions.description')}</p>
        <ul className="space-y-2 text-gray-300">
          <li className="flex items-start"><span className="text-matrix-green mr-2" aria-hidden="true">&bull;</span>{t('sections.alternativeOptions.items.pauseSubscription')}</li>
          <li className="flex items-start"><span className="text-matrix-green mr-2" aria-hidden="true">&bull;</span>{t('sections.alternativeOptions.items.contactSupport')}</li>
          <li className="flex items-start"><span className="text-matrix-green mr-2" aria-hidden="true">&bull;</span>{t('sections.alternativeOptions.items.changeSettings')}</li>
        </ul>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.4 }}
        className="bg-terminal-bg-light p-8 rounded-lg border border-neon-cyan/20"
      >
        <h2 className="text-2xl font-display font-semibold text-neon-cyan mb-4">{t('form.title')}</h2>
        <p className="text-gray-300 mb-6">{t('form.description')}</p>

        <AnimatePresence>
          {error ? (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="bg-red-950/30 border border-red-500/50 p-4 rounded-sm mb-6 text-red-400"
              role="alert"
            >
              {error}
            </motion.div>
          ) : null}
        </AnimatePresence>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="delete-reason" className="block text-gray-300 mb-2">{t('form.fields.reason.label')}</label>
            <select
              id="delete-reason"
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              className="w-full px-4 py-2 bg-terminal-bg border border-neon-cyan/30 rounded-sm text-gray-300 focus:outline-hidden focus:border-neon-cyan"
              aria-label={t('form.fields.reason.label')}
            >
              <option value="">{t('form.fields.reason.placeholder')}</option>
              <option value="notUsing">{t('form.fields.reason.options.notUsing')}</option>
              <option value="tooExpensive">{t('form.fields.reason.options.tooExpensive')}</option>
              <option value="technicalIssues">{t('form.fields.reason.options.technicalIssues')}</option>
              <option value="privacyConcerns">{t('form.fields.reason.options.privacyConcerns')}</option>
              <option value="foundAlternative">{t('form.fields.reason.options.foundAlternative')}</option>
              <option value="other">{t('form.fields.reason.options.other')}</option>
            </select>
          </div>

          <div>
            <label htmlFor="delete-feedback" className="block text-gray-300 mb-2">{t('form.fields.feedback.label')}</label>
            <textarea
              id="delete-feedback"
              value={feedback}
              onChange={(event) => setFeedback(event.target.value)}
              placeholder={t('form.fields.feedback.placeholder')}
              rows={4}
              className="w-full px-4 py-2 bg-terminal-bg border border-neon-cyan/30 rounded-sm text-gray-300 focus:outline-hidden focus:border-neon-cyan resize-none"
              aria-label={t('form.fields.feedback.label')}
            />
          </div>

          <div>
            <label htmlFor="delete-confirm-input" className="block text-gray-300 mb-2">{t('form.fields.confirmInput.label')}</label>
            <input
              id="delete-confirm-input"
              type="text"
              value={confirmText}
              onChange={(event) => setConfirmText(event.target.value)}
              placeholder={t('form.fields.confirmInput.placeholder')}
              className="w-full px-4 py-2 bg-terminal-bg border border-red-500/30 rounded-sm text-gray-300 focus:outline-hidden focus:border-red-500 font-mono tracking-wider"
              autoComplete="off"
              aria-label={t('form.fields.confirmInput.label')}
              required
            />
          </div>

          <div className="flex items-start">
            <input
              type="checkbox"
              id="confirmation"
              checked={confirmed}
              onChange={(event) => setConfirmed(event.target.checked)}
              className="mt-1 mr-3"
              required
              aria-label={t('form.fields.confirmation.label')}
            />
            <label htmlFor="confirmation" className="text-gray-300">{t('form.fields.confirmation.label')}</label>
          </div>

          <div className="flex gap-4">
            <button
              type="submit"
              disabled={isPending || !isConfirmTextValid || !confirmed}
              className="flex-1 px-6 py-3 bg-red-600 text-white font-semibold rounded-sm hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label={t('form.submit')}
            >
              {isPending ? t('form.submitting') : t('form.submit')}
            </button>
            <Link
              href={cancelHref}
              className="flex-1 px-6 py-3 bg-gray-700 text-white font-semibold rounded-sm hover:bg-gray-600 transition-colors text-center"
              aria-label={cancelLabel}
            >
              {cancelLabel}
            </Link>
          </div>
        </form>
      </motion.div>

      <div className="mt-12 text-center">
        <h3 className="text-lg font-display font-semibold text-neon-cyan mb-2">{t('contact.title')}</h3>
        <p className="text-gray-300 mb-2">{t('contact.description')}</p>
        <p className="text-gray-300">
          <strong>{t('contact.email')}:</strong>{' '}
          <a
            href={`mailto:${t('contact.emailAddress')}`}
            className="text-matrix-green hover:underline"
            aria-label={t('contact.emailAddress')}
          >
            {t('contact.emailAddress')}
          </a>
        </p>
      </div>
    </div>
  );
}
