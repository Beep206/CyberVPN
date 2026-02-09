'use client';

import { useState, useTransition } from 'react';
import { useTranslations } from 'next-intl';
import { motion, AnimatePresence } from 'motion/react';
import { TerminalHeader } from '@/widgets/terminal-header';
import { Footer } from '@/widgets/footer';
import { Link, useRouter } from '@/i18n/navigation';
import { useAuthStore, useIsAuthenticated } from '@/stores/auth-store';

export default function DeleteAccountPage() {
    const t = useTranslations('DeleteAccount');
    const router = useRouter();
    const isAuthenticated = useIsAuthenticated();
    const deleteAccount = useAuthStore((s) => s.deleteAccount);

    const [confirmText, setConfirmText] = useState('');
    const [reason, setReason] = useState('');
    const [feedback, setFeedback] = useState('');
    const [confirmed, setConfirmed] = useState(false);
    const [isPending, startTransition] = useTransition();
    const [error, setError] = useState('');
    const [success, setSuccess] = useState(false);

    const CONFIRM_KEYWORD = t('form.fields.confirmInput.keyword');
    const isConfirmTextValid = confirmText === CONFIRM_KEYWORD;

    const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
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
                await deleteAccount();
                setSuccess(true);
                // Redirect to home after a short delay so the user sees the success message
                setTimeout(() => {
                    router.push('/');
                }, 3000);
            } catch {
                setError(t('error.message'));
            }
        });
    };

    if (success) {
        return (
            <main className="min-h-screen bg-terminal-bg selection:bg-neon-pink selection:text-black">
                <TerminalHeader />
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
                            <p className="text-gray-300 mb-6">
                                {t('success.message')}
                            </p>
                            <p className="text-sm text-gray-400 mb-6">
                                {t('success.details')}
                            </p>
                            <Link
                                href="/"
                                className="inline-block px-6 py-3 bg-neon-cyan text-black font-semibold rounded-sm hover:bg-neon-cyan/80 transition-colors"
                                aria-label={t('success.returnHome')}
                            >
                                {t('success.returnHome')}
                            </Link>
                        </div>
                    </motion.div>
                </div>
                <Footer />
            </main>
        );
    }

    return (
        <main className="min-h-screen bg-terminal-bg selection:bg-neon-pink selection:text-black">
            <TerminalHeader />
            <div className="container mx-auto px-4 py-16 max-w-4xl">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4 }}
                    className="mb-12"
                >
                    <h1 className="text-4xl font-display font-bold text-matrix-green mb-4">
                        {t('title')}
                    </h1>
                    <p className="text-lg text-gray-300">
                        {t('subtitle')}
                    </p>
                </motion.div>

                {/* Warning */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4, delay: 0.1 }}
                    className="bg-red-950/30 border border-red-500/50 p-6 rounded-lg mb-8"
                >
                    <h2 className="text-xl font-display font-semibold text-red-400 mb-2">
                        {t('warning.title')}
                    </h2>
                    <p className="text-gray-300">
                        {t('warning.message')}
                    </p>
                </motion.div>

                <div className="grid md:grid-cols-2 gap-8 mb-12">
                    {/* What will be deleted */}
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
                            <li className="flex items-start">
                                <span className="text-red-400 mr-2" aria-hidden="true">&#10007;</span>
                                {t('sections.consequences.items.accountData')}
                            </li>
                            <li className="flex items-start">
                                <span className="text-red-400 mr-2" aria-hidden="true">&#10007;</span>
                                {t('sections.consequences.items.subscriptions')}
                            </li>
                            <li className="flex items-start">
                                <span className="text-red-400 mr-2" aria-hidden="true">&#10007;</span>
                                {t('sections.consequences.items.configs')}
                            </li>
                            <li className="flex items-start">
                                <span className="text-red-400 mr-2" aria-hidden="true">&#10007;</span>
                                {t('sections.consequences.items.referrals')}
                            </li>
                            <li className="flex items-start">
                                <span className="text-red-400 mr-2" aria-hidden="true">&#10007;</span>
                                {t('sections.consequences.items.support')}
                            </li>
                        </ul>
                    </motion.div>

                    {/* Before you delete */}
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
                            <li className="flex items-start">
                                <span className="text-matrix-green mr-2" aria-hidden="true">&rarr;</span>
                                {t('sections.beforeDelete.items.exportData')}
                            </li>
                            <li className="flex items-start">
                                <span className="text-matrix-green mr-2" aria-hidden="true">&rarr;</span>
                                {t('sections.beforeDelete.items.cancelSubscriptions')}
                            </li>
                            <li className="flex items-start">
                                <span className="text-matrix-green mr-2" aria-hidden="true">&rarr;</span>
                                {t('sections.beforeDelete.items.useReferrals')}
                            </li>
                            <li className="flex items-start">
                                <span className="text-matrix-green mr-2" aria-hidden="true">&rarr;</span>
                                {t('sections.beforeDelete.items.saveConfigs')}
                            </li>
                        </ul>
                    </motion.div>
                </div>

                {/* Alternative options */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4, delay: 0.3 }}
                    className="bg-terminal-bg-light p-6 rounded-lg border border-neon-cyan/20 mb-12"
                >
                    <h2 className="text-xl font-display font-semibold text-neon-cyan mb-4">
                        {t('sections.alternativeOptions.title')}
                    </h2>
                    <p className="text-gray-300 mb-4">
                        {t('sections.alternativeOptions.description')}
                    </p>
                    <ul className="space-y-2 text-gray-300">
                        <li className="flex items-start">
                            <span className="text-matrix-green mr-2" aria-hidden="true">&bull;</span>
                            {t('sections.alternativeOptions.items.pauseSubscription')}
                        </li>
                        <li className="flex items-start">
                            <span className="text-matrix-green mr-2" aria-hidden="true">&bull;</span>
                            {t('sections.alternativeOptions.items.contactSupport')}
                        </li>
                        <li className="flex items-start">
                            <span className="text-matrix-green mr-2" aria-hidden="true">&bull;</span>
                            {t('sections.alternativeOptions.items.changeSettings')}
                        </li>
                    </ul>
                </motion.div>

                {/* Deletion form */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4, delay: 0.4 }}
                    className="bg-terminal-bg-light p-8 rounded-lg border border-neon-cyan/20"
                >
                    <h2 className="text-2xl font-display font-semibold text-neon-cyan mb-4">
                        {t('form.title')}
                    </h2>
                    <p className="text-gray-300 mb-6">
                        {t('form.description')}
                    </p>

                    <AnimatePresence>
                        {error && (
                            <motion.div
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: 'auto' }}
                                exit={{ opacity: 0, height: 0 }}
                                className="bg-red-950/30 border border-red-500/50 p-4 rounded-sm mb-6 text-red-400"
                                role="alert"
                            >
                                {error}
                            </motion.div>
                        )}
                    </AnimatePresence>

                    <form onSubmit={handleSubmit} className="space-y-6">
                        <div>
                            <label htmlFor="delete-reason" className="block text-gray-300 mb-2">
                                {t('form.fields.reason.label')}
                            </label>
                            <select
                                id="delete-reason"
                                value={reason}
                                onChange={(e) => setReason(e.target.value)}
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
                            <label htmlFor="delete-feedback" className="block text-gray-300 mb-2">
                                {t('form.fields.feedback.label')}
                            </label>
                            <textarea
                                id="delete-feedback"
                                value={feedback}
                                onChange={(e) => setFeedback(e.target.value)}
                                placeholder={t('form.fields.feedback.placeholder')}
                                rows={4}
                                className="w-full px-4 py-2 bg-terminal-bg border border-neon-cyan/30 rounded-sm text-gray-300 focus:outline-hidden focus:border-neon-cyan resize-none"
                                aria-label={t('form.fields.feedback.label')}
                            />
                        </div>

                        <div>
                            <label htmlFor="delete-confirm-input" className="block text-gray-300 mb-2">
                                {t('form.fields.confirmInput.label')}
                            </label>
                            <input
                                id="delete-confirm-input"
                                type="text"
                                value={confirmText}
                                onChange={(e) => setConfirmText(e.target.value)}
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
                                onChange={(e) => setConfirmed(e.target.checked)}
                                className="mt-1 mr-3"
                                required
                                aria-label={t('form.fields.confirmation.label')}
                            />
                            <label htmlFor="confirmation" className="text-gray-300">
                                {t('form.fields.confirmation.label')}
                            </label>
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
                                href="/"
                                className="flex-1 px-6 py-3 bg-gray-700 text-white font-semibold rounded-sm hover:bg-gray-600 transition-colors text-center"
                                aria-label={t('form.cancel')}
                            >
                                {t('form.cancel')}
                            </Link>
                        </div>
                    </form>
                </motion.div>

                {/* Contact section */}
                <div className="mt-12 text-center">
                    <h3 className="text-lg font-display font-semibold text-neon-cyan mb-2">
                        {t('contact.title')}
                    </h3>
                    <p className="text-gray-300 mb-2">
                        {t('contact.description')}
                    </p>
                    <p className="text-gray-300">
                        <strong>{t('contact.email')}:</strong>{' '}
                        <a
                            href="mailto:privacy@cybervpn.app"
                            className="text-matrix-green hover:underline"
                            aria-label={t('contact.emailAddress')}
                        >
                            {t('contact.emailAddress')}
                        </a>
                    </p>
                </div>
            </div>
            <Footer />
        </main>
    );
}
