'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useTranslations } from 'next-intl';
import { TerminalHeader } from '@/widgets/terminal-header';
import { Footer } from '@/widgets/footer';

export default function DeleteAccountPage() {
    const t = useTranslations('DeleteAccount');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [reason, setReason] = useState('');
    const [feedback, setFeedback] = useState('');
    const [confirmed, setConfirmed] = useState(false);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        if (!email || !password) {
            setError(t('form.fields.email.error'));
            return;
        }

        if (!confirmed) {
            setError(t('form.fields.confirmation.error'));
            return;
        }

        setIsSubmitting(true);

        try {
            // TODO: Implement actual API call to backend
            const response = await fetch('/api/v1/users/delete-account', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    email,
                    password,
                    reason,
                    feedback,
                }),
            });

            if (!response.ok) {
                throw new Error('Failed to delete account');
            }

            setSuccess(true);
        } catch {
            setError(t('error.message'));
        } finally {
            setIsSubmitting(false);
        }
    };

    if (success) {
        return (
            <main className="min-h-screen bg-terminal-bg selection:bg-neon-pink selection:text-black">
                <TerminalHeader />
                <div className="container mx-auto px-4 py-16 max-w-2xl">
                    <div className="bg-terminal-bg-light border border-matrix-green p-8 rounded-lg">
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
                                className="inline-block px-6 py-3 bg-neon-cyan text-black font-semibold rounded hover:bg-neon-cyan/80 transition-colors"
                            >
                                Return to Home
                            </Link>
                        </div>
                    </div>
                </div>
                <Footer />
            </main>
        );
    }

    return (
        <main className="min-h-screen bg-terminal-bg selection:bg-neon-pink selection:text-black">
            <TerminalHeader />
            <div className="container mx-auto px-4 py-16 max-w-4xl">
                <div className="mb-12">
                    <h1 className="text-4xl font-display font-bold text-matrix-green mb-4">
                        {t('title')}
                    </h1>
                    <p className="text-lg text-gray-300">
                        {t('subtitle')}
                    </p>
                </div>

                {/* Warning */}
                <div className="bg-red-950/30 border border-red-500/50 p-6 rounded-lg mb-8">
                    <h2 className="text-xl font-display font-semibold text-red-400 mb-2">
                        {t('warning.title')}
                    </h2>
                    <p className="text-gray-300">
                        {t('warning.message')}
                    </p>
                </div>

                <div className="grid md:grid-cols-2 gap-8 mb-12">
                    {/* What will be deleted */}
                    <div className="bg-terminal-bg-light p-6 rounded-lg border border-neon-cyan/20">
                        <h2 className="text-xl font-display font-semibold text-neon-cyan mb-4">
                            {t('sections.consequences.title')}
                        </h2>
                        <ul className="space-y-2 text-gray-300">
                            <li className="flex items-start">
                                <span className="text-red-400 mr-2">✗</span>
                                {t('sections.consequences.items.accountData')}
                            </li>
                            <li className="flex items-start">
                                <span className="text-red-400 mr-2">✗</span>
                                {t('sections.consequences.items.subscriptions')}
                            </li>
                            <li className="flex items-start">
                                <span className="text-red-400 mr-2">✗</span>
                                {t('sections.consequences.items.configs')}
                            </li>
                            <li className="flex items-start">
                                <span className="text-red-400 mr-2">✗</span>
                                {t('sections.consequences.items.referrals')}
                            </li>
                            <li className="flex items-start">
                                <span className="text-red-400 mr-2">✗</span>
                                {t('sections.consequences.items.support')}
                            </li>
                        </ul>
                    </div>

                    {/* Before you delete */}
                    <div className="bg-terminal-bg-light p-6 rounded-lg border border-neon-cyan/20">
                        <h2 className="text-xl font-display font-semibold text-neon-cyan mb-4">
                            {t('sections.beforeDelete.title')}
                        </h2>
                        <ul className="space-y-2 text-gray-300">
                            <li className="flex items-start">
                                <span className="text-matrix-green mr-2">→</span>
                                {t('sections.beforeDelete.items.exportData')}
                            </li>
                            <li className="flex items-start">
                                <span className="text-matrix-green mr-2">→</span>
                                {t('sections.beforeDelete.items.cancelSubscriptions')}
                            </li>
                            <li className="flex items-start">
                                <span className="text-matrix-green mr-2">→</span>
                                {t('sections.beforeDelete.items.useReferrals')}
                            </li>
                            <li className="flex items-start">
                                <span className="text-matrix-green mr-2">→</span>
                                {t('sections.beforeDelete.items.saveConfigs')}
                            </li>
                        </ul>
                    </div>
                </div>

                {/* Alternative options */}
                <div className="bg-terminal-bg-light p-6 rounded-lg border border-neon-cyan/20 mb-12">
                    <h2 className="text-xl font-display font-semibold text-neon-cyan mb-4">
                        {t('sections.alternativeOptions.title')}
                    </h2>
                    <p className="text-gray-300 mb-4">
                        {t('sections.alternativeOptions.description')}
                    </p>
                    <ul className="space-y-2 text-gray-300">
                        <li className="flex items-start">
                            <span className="text-matrix-green mr-2">•</span>
                            {t('sections.alternativeOptions.items.pauseSubscription')}
                        </li>
                        <li className="flex items-start">
                            <span className="text-matrix-green mr-2">•</span>
                            {t('sections.alternativeOptions.items.contactSupport')}
                        </li>
                        <li className="flex items-start">
                            <span className="text-matrix-green mr-2">•</span>
                            {t('sections.alternativeOptions.items.changeSettings')}
                        </li>
                    </ul>
                </div>

                {/* Deletion form */}
                <div className="bg-terminal-bg-light p-8 rounded-lg border border-neon-cyan/20">
                    <h2 className="text-2xl font-display font-semibold text-neon-cyan mb-4">
                        {t('form.title')}
                    </h2>
                    <p className="text-gray-300 mb-6">
                        {t('form.description')}
                    </p>

                    {error && (
                        <div className="bg-red-950/30 border border-red-500/50 p-4 rounded mb-6 text-red-400">
                            {error}
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-6">
                        <div>
                            <label className="block text-gray-300 mb-2">
                                {t('form.fields.email.label')}
                            </label>
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder={t('form.fields.email.placeholder')}
                                className="w-full px-4 py-2 bg-terminal-bg border border-neon-cyan/30 rounded text-gray-300 focus:outline-none focus:border-neon-cyan"
                                required
                            />
                        </div>

                        <div>
                            <label className="block text-gray-300 mb-2">
                                {t('form.fields.password.label')}
                            </label>
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder={t('form.fields.password.placeholder')}
                                className="w-full px-4 py-2 bg-terminal-bg border border-neon-cyan/30 rounded text-gray-300 focus:outline-none focus:border-neon-cyan"
                                required
                            />
                        </div>

                        <div>
                            <label className="block text-gray-300 mb-2">
                                {t('form.fields.reason.label')}
                            </label>
                            <select
                                value={reason}
                                onChange={(e) => setReason(e.target.value)}
                                className="w-full px-4 py-2 bg-terminal-bg border border-neon-cyan/30 rounded text-gray-300 focus:outline-none focus:border-neon-cyan"
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
                            <label className="block text-gray-300 mb-2">
                                {t('form.fields.feedback.label')}
                            </label>
                            <textarea
                                value={feedback}
                                onChange={(e) => setFeedback(e.target.value)}
                                placeholder={t('form.fields.feedback.placeholder')}
                                rows={4}
                                className="w-full px-4 py-2 bg-terminal-bg border border-neon-cyan/30 rounded text-gray-300 focus:outline-none focus:border-neon-cyan resize-none"
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
                            />
                            <label htmlFor="confirmation" className="text-gray-300">
                                {t('form.fields.confirmation.label')}
                            </label>
                        </div>

                        <div className="flex gap-4">
                            <button
                                type="submit"
                                disabled={isSubmitting}
                                className="flex-1 px-6 py-3 bg-red-600 text-white font-semibold rounded hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {isSubmitting ? t('form.submitting') : t('form.submit')}
                            </button>
                            <Link
                                href="/"
                                className="flex-1 px-6 py-3 bg-gray-700 text-white font-semibold rounded hover:bg-gray-600 transition-colors text-center"
                            >
                                {t('form.cancel')}
                            </Link>
                        </div>
                    </form>
                </div>

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
                        <a href="mailto:privacy@cybervpn.app" className="text-matrix-green hover:underline">
                            {t('contact.emailAddress')}
                        </a>
                    </p>
                </div>
            </div>
            <Footer />
        </main>
    );
}
