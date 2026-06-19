'use client';

import axios from 'axios';
import { AnimatePresence, motion } from 'motion/react';
import { useTranslations } from 'next-intl';
import { useEffect, useState, useTransition } from 'react';
import { Link } from '@/i18n/navigation';
import {
  privacyRequestsApi,
  type PrivacyRequestAcceptedResponse,
  type PrivacyRequestSummary,
} from '@/lib/api/privacy-requests';
import { useIsAuthenticated } from '@/stores/auth-store';

const DEFAULT_DELETION_FULFILLMENT_DAYS = 30;
const ACTIVE_DELETION_STATUSES = new Set([
  'submitted',
  'identity_verification',
  'pending_decision',
  'approved',
  'scheduled',
  'failed',
]);

type DeleteAccountOutcome = PrivacyRequestAcceptedResponse;
type DeleteAccountClientSurface = 'cabinet' | 'marketing';

type DeleteAccountClientProps = {
  cancelHref?: string;
  returnHref?: string;
  surface?: DeleteAccountClientSurface;
};

function createIdempotencyKey() {
  if (typeof globalThis.crypto?.randomUUID === 'function') {
    return globalThis.crypto.randomUUID();
  }

  const suffix = Math.random().toString(16).slice(2, 14).padEnd(12, '0');
  return `00000000-0000-4000-8000-${suffix}`;
}

function formatRequestDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

function errorKeyForRequest(error: unknown) {
  if (!axios.isAxiosError(error) || !error.response) {
    return 'error.networkError';
  }

  if (error.response.status === 401) return 'error.unauthenticated';
  if (error.response.status === 409) return 'error.activeExists';
  if (error.response.status === 422) return 'error.validation';
  if (error.response.status === 429) return 'error.rateLimited';
  if (error.response.status >= 500) return 'error.serverError';

  return 'error.message';
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
  const [isLoadingExisting, setIsLoadingExisting] = useState(false);
  const [isCanceling, setIsCanceling] = useState(false);
  const [error, setError] = useState('');
  const [attemptIdempotencyKey, setAttemptIdempotencyKey] = useState<string | null>(null);
  const [existingRequest, setExistingRequest] = useState<PrivacyRequestSummary | null>(null);
  const [success, setSuccess] = useState<DeleteAccountOutcome | null>(null);

  const confirmKeyword = t('form.fields.confirmInput.keyword');
  const isConfirmTextValid = confirmText === confirmKeyword;
  const cancelLabel = surface === 'cabinet' ? t('form.cancelToSettings') : t('form.cancel');
  const returnLabel =
    surface === 'cabinet' ? t('success.returnSettings') : t('success.returnHome');

  useEffect(() => {
    if (!isAuthenticated) {
      return;
    }

    let canceled = false;
    void Promise.resolve().then(async () => {
      if (canceled) return;
      setIsLoadingExisting(true);
      try {
        const response = await privacyRequestsApi.list({ limit: 10, request_type: 'account_deletion' });
        if (canceled) return;
        const active = response.data.requests.find((request) =>
          ACTIVE_DELETION_STATUSES.has(request.status)
        );
        setExistingRequest(active ?? null);
      } catch (requestError) {
        if (!canceled) {
          setError(t(errorKeyForRequest(requestError)));
        }
      } finally {
        if (!canceled) {
          setIsLoadingExisting(false);
        }
      }
    });

    return () => {
      canceled = true;
    };
  }, [isAuthenticated, t]);

  const handleCancelExisting = () => {
    if (!existingRequest || !existingRequest.allowed_actions.includes('cancel')) return;
    setIsCanceling(true);
    setError('');
    privacyRequestsApi
      .cancel(existingRequest.privacy_request_reference)
      .then(() => {
        setExistingRequest(null);
      })
      .catch((requestError) => {
        setError(t(errorKeyForRequest(requestError)));
      })
      .finally(() => {
        setIsCanceling(false);
      });
  };

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
        const idempotencyKey = attemptIdempotencyKey ?? createIdempotencyKey();
        setAttemptIdempotencyKey(idempotencyKey);
        const response = await privacyRequestsApi.create({
          notes: feedback.trim() || null,
          reason_code: reason.trim() || null,
          request_type: 'account_deletion',
        }, idempotencyKey);
        setSuccess(response.data);
        setExistingRequest(null);
        setAttemptIdempotencyKey(null);
      } catch (requestError) {
        setError(t(errorKeyForRequest(requestError)));
      }
    });
  };

  if (success) {
    return (
      <div className="container mx-auto max-w-2xl px-4 py-16">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="rounded-lg border border-matrix-green bg-terminal-bg-light p-8"
        >
          <div className="text-center">
            <h1 className="mb-4 text-3xl font-display font-bold text-matrix-green">
              {t('success.title')}
            </h1>
            <p className="mb-6 text-gray-300">{t('success.message')}</p>
            <p className="mb-3 text-sm text-gray-400">
              {t('success.details', {
                days: success.manual_fulfillment_target_days ?? DEFAULT_DELETION_FULFILLMENT_DAYS,
              })}
            </p>
            <p className="mb-6 break-all font-mono text-xs text-matrix-green">
              {t('success.references', {
                privacyReference: success.privacy_request_reference,
                ticketReference: success.ticket_reference,
              })}
            </p>
            <Link
              href={returnHref}
              className="inline-block rounded-sm bg-neon-cyan px-6 py-3 font-semibold text-black transition-colors hover:bg-neon-cyan/80"
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
    <div className="container mx-auto max-w-4xl px-4 py-16">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="mb-12"
      >
        <h1 className="mb-4 text-4xl font-display font-bold text-matrix-green">{t('title')}</h1>
        <p className="text-lg text-gray-300">{t('subtitle')}</p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.1 }}
        className="mb-8 rounded-lg border border-red-500/50 bg-red-950/30 p-6"
      >
        <h2 className="mb-2 text-xl font-display font-semibold text-red-400">
          {t('warning.title')}
        </h2>
        <p className="text-gray-300">{t('warning.message')}</p>
      </motion.div>

      <div className="mb-12 grid gap-8 md:grid-cols-2">
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.4, delay: 0.2 }}
          className="rounded-lg border border-neon-cyan/20 bg-terminal-bg-light p-6"
        >
          <h2 className="mb-4 text-xl font-display font-semibold text-neon-cyan">
            {t('sections.consequences.title')}
          </h2>
          <ul className="space-y-2 text-gray-300">
            <li className="flex items-start"><span className="mr-2 text-red-400" aria-hidden="true">&#10007;</span>{t('sections.consequences.items.accountData')}</li>
            <li className="flex items-start"><span className="mr-2 text-red-400" aria-hidden="true">&#10007;</span>{t('sections.consequences.items.subscriptions')}</li>
            <li className="flex items-start"><span className="mr-2 text-red-400" aria-hidden="true">&#10007;</span>{t('sections.consequences.items.configs')}</li>
            <li className="flex items-start"><span className="mr-2 text-red-400" aria-hidden="true">&#10007;</span>{t('sections.consequences.items.referrals')}</li>
            <li className="flex items-start"><span className="mr-2 text-red-400" aria-hidden="true">&#10007;</span>{t('sections.consequences.items.support')}</li>
          </ul>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.4, delay: 0.2 }}
          className="rounded-lg border border-neon-cyan/20 bg-terminal-bg-light p-6"
        >
          <h2 className="mb-4 text-xl font-display font-semibold text-neon-cyan">
            {t('sections.beforeDelete.title')}
          </h2>
          <ul className="space-y-2 text-gray-300">
            <li className="flex items-start"><span className="mr-2 text-matrix-green" aria-hidden="true">&rarr;</span>{t('sections.beforeDelete.items.exportData')}</li>
            <li className="flex items-start"><span className="mr-2 text-matrix-green" aria-hidden="true">&rarr;</span>{t('sections.beforeDelete.items.cancelSubscriptions')}</li>
            <li className="flex items-start"><span className="mr-2 text-matrix-green" aria-hidden="true">&rarr;</span>{t('sections.beforeDelete.items.useReferrals')}</li>
            <li className="flex items-start"><span className="mr-2 text-matrix-green" aria-hidden="true">&rarr;</span>{t('sections.beforeDelete.items.saveConfigs')}</li>
          </ul>
        </motion.div>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.3 }}
        className="mb-12 rounded-lg border border-neon-cyan/20 bg-terminal-bg-light p-6"
      >
        <h2 className="mb-4 text-xl font-display font-semibold text-neon-cyan">
          {t('sections.alternativeOptions.title')}
        </h2>
        <p className="mb-4 text-gray-300">{t('sections.alternativeOptions.description')}</p>
        <ul className="space-y-2 text-gray-300">
          <li className="flex items-start"><span className="mr-2 text-matrix-green" aria-hidden="true">&bull;</span>{t('sections.alternativeOptions.items.pauseSubscription')}</li>
          <li className="flex items-start"><span className="mr-2 text-matrix-green" aria-hidden="true">&bull;</span>{t('sections.alternativeOptions.items.contactSupport')}</li>
          <li className="flex items-start"><span className="mr-2 text-matrix-green" aria-hidden="true">&bull;</span>{t('sections.alternativeOptions.items.changeSettings')}</li>
        </ul>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.4 }}
        className="rounded-lg border border-neon-cyan/20 bg-terminal-bg-light p-8"
      >
        <h2 className="mb-4 text-2xl font-display font-semibold text-neon-cyan">{t('form.title')}</h2>
        <p className="mb-6 text-gray-300">{t('form.description')}</p>

        {isLoadingExisting ? (
          <div className="mb-6 rounded-sm border border-grid-line/30 bg-terminal-bg/60 p-4 text-sm font-mono text-muted-foreground">
            {t('existing.loading')}
          </div>
        ) : null}

        {existingRequest ? (
          <div className="mb-6 rounded-lg border border-amber-300/40 bg-amber-300/10 p-5">
            <h3 className="font-display text-lg font-semibold text-amber-200">
              {t('existing.title')}
            </h3>
            <p className="mt-2 text-sm text-gray-300">{t('existing.description')}</p>
            <dl className="mt-4 grid gap-3 text-sm font-mono sm:grid-cols-2">
              <div>
                <dt className="text-muted-foreground">{t('existing.privacyReference')}</dt>
                <dd className="break-all text-matrix-green">{existingRequest.privacy_request_reference}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">{t('existing.ticketReference')}</dt>
                <dd className="break-all text-neon-cyan">
                  {existingRequest.ticket_reference ?? t('existing.notAvailable')}
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">{t('existing.status')}</dt>
                <dd className="text-white">{t(`status.${existingRequest.status}`)}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">{t('existing.submittedAt')}</dt>
                <dd className="text-white">{formatRequestDate(existingRequest.submitted_at)}</dd>
              </div>
            </dl>
            <div className="mt-5 flex flex-col gap-3 sm:flex-row">
              {existingRequest.allowed_actions.includes('cancel') ? (
                <button
                  type="button"
                  onClick={handleCancelExisting}
                  disabled={isCanceling}
                  className="min-h-11 rounded-sm border border-red-500/40 bg-red-600/20 px-4 py-2 font-mono text-sm uppercase tracking-[0.14em] text-red-200 transition-colors hover:bg-red-600/30 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isCanceling ? t('existing.canceling') : t('existing.cancel')}
                </button>
              ) : null}
              <Link
                href={returnHref}
                className="min-h-11 rounded-sm border border-neon-cyan/30 bg-terminal-bg/70 px-4 py-2 text-center font-mono text-sm uppercase tracking-[0.14em] text-neon-cyan transition-colors hover:border-neon-cyan/60 hover:text-white"
              >
                {returnLabel}
              </Link>
            </div>
          </div>
        ) : null}

        <AnimatePresence>
          {error ? (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mb-6 rounded-sm border border-red-500/50 bg-red-950/30 p-4 text-red-400"
              role="alert"
            >
              {error}
            </motion.div>
          ) : null}
        </AnimatePresence>

        {!existingRequest ? (
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="delete-reason" className="mb-2 block text-gray-300">{t('form.fields.reason.label')}</label>
              <select
                id="delete-reason"
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                className="w-full rounded-sm border border-neon-cyan/30 bg-terminal-bg px-4 py-2 text-gray-300 focus:border-neon-cyan focus:outline-hidden"
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
              <label htmlFor="delete-feedback" className="mb-2 block text-gray-300">{t('form.fields.feedback.label')}</label>
              <textarea
                id="delete-feedback"
                value={feedback}
                onChange={(event) => setFeedback(event.target.value)}
                placeholder={t('form.fields.feedback.placeholder')}
                rows={4}
                className="w-full resize-none rounded-sm border border-neon-cyan/30 bg-terminal-bg px-4 py-2 text-gray-300 focus:border-neon-cyan focus:outline-hidden"
                aria-label={t('form.fields.feedback.label')}
              />
            </div>

            <div>
              <label htmlFor="delete-confirm-input" className="mb-2 block text-gray-300">{t('form.fields.confirmInput.label')}</label>
              <input
                id="delete-confirm-input"
                type="text"
                value={confirmText}
                onChange={(event) => setConfirmText(event.target.value)}
                placeholder={t('form.fields.confirmInput.placeholder')}
                className="w-full rounded-sm border border-red-500/30 bg-terminal-bg px-4 py-2 font-mono tracking-wider text-gray-300 focus:border-red-500 focus:outline-hidden"
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
                className="mr-3 mt-1"
                required
                aria-label={t('form.fields.confirmation.label')}
              />
              <label htmlFor="confirmation" className="text-gray-300">{t('form.fields.confirmation.label')}</label>
            </div>

            <div className="flex flex-col gap-4 sm:flex-row">
              <button
                type="submit"
                disabled={isPending || isLoadingExisting || !isConfirmTextValid || !confirmed}
                className="min-h-12 w-full rounded-sm bg-red-600 px-6 py-3 font-semibold text-white transition-colors hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-50 sm:flex-1"
                aria-label={t('form.submit')}
              >
                {isPending ? t('form.submitting') : t('form.submit')}
              </button>
              <Link
                href={cancelHref}
                className="min-h-12 w-full rounded-sm bg-gray-700 px-6 py-3 text-center font-semibold text-white transition-colors hover:bg-gray-600 sm:flex-1"
                aria-label={cancelLabel}
              >
                {cancelLabel}
              </Link>
            </div>
          </form>
        ) : null}
      </motion.div>

      <div className="mt-12 text-center">
        <h3 className="mb-2 text-lg font-display font-semibold text-neon-cyan">{t('contact.title')}</h3>
        <p className="mb-2 text-gray-300">{t('contact.description')}</p>
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
