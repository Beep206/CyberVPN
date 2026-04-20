'use client';

import dynamic from 'next/dynamic';
import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { AnimatePresence, motion } from 'motion/react';
import {
  Building,
  CheckCircle2,
  Mail,
  Send,
  ShieldAlert,
  User,
} from 'lucide-react';
import { useEnhancementReady } from '@/shared/hooks/use-enhancement-ready';
import { useTime } from '@/shared/hooks/use-time';
import { useVisualTier } from '@/shared/hooks/use-visual-tier';
import { ScrambleText } from '@/shared/ui/scramble-text';
import { MagneticButton } from '@/shared/ui/magnetic-button';
import { ResponsiveSplitShell } from '@/shared/ui/layout/responsive-split-shell';

const ContactFormVisual = dynamic(
  () => import('@/widgets/contact-form-visual').then((mod) => mod.ContactFormVisual),
  {
    ssr: false,
    loading: () => null,
  },
);

type ContactVisualState = 'idle' | 'typing' | 'encrypting' | 'secured';

function ContactVisualFallback({
  visualTier,
  visualState,
}: {
  visualTier: 'minimal' | 'reduced' | 'full';
  visualState: ContactVisualState;
}) {
  const stateClasses: Record<
    ContactVisualState,
    {
      glowClassName: string;
      accentBorderClassName: string;
      accentTextClassName: string;
      label: string;
    }
  > = {
    idle: {
      glowClassName:
        'bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.14),transparent_52%),linear-gradient(180deg,rgba(0,0,0,0)_0%,rgba(0,0,0,0.88)_100%)]',
      accentBorderClassName: 'border-white/20',
      accentTextClassName: 'text-white/70',
      label: 'NODE.IDLE',
    },
    typing: {
      glowClassName:
        'bg-[radial-gradient(circle_at_center,rgba(0,255,136,0.18),transparent_52%),linear-gradient(180deg,rgba(0,0,0,0)_0%,rgba(0,14,8,0.88)_100%)]',
      accentBorderClassName: 'border-matrix-green/30',
      accentTextClassName: 'text-matrix-green/80',
      label: 'SCAN.ACTIVE',
    },
    encrypting: {
      glowClassName:
        'bg-[radial-gradient(circle_at_center,rgba(255,184,0,0.2),transparent_52%),linear-gradient(180deg,rgba(0,0,0,0)_0%,rgba(18,10,0,0.88)_100%)]',
      accentBorderClassName: 'border-warning/30',
      accentTextClassName: 'text-warning/80',
      label: 'PAYLOAD.LOCK',
    },
    secured: {
      glowClassName:
        'bg-[radial-gradient(circle_at_center,rgba(0,255,255,0.2),transparent_52%),linear-gradient(180deg,rgba(0,0,0,0)_0%,rgba(0,8,14,0.88)_100%)]',
      accentBorderClassName: 'border-neon-cyan/30',
      accentTextClassName: 'text-neon-cyan/80',
      label: 'UPLINK.SECURED',
    },
  };

  const style = stateClasses[visualState];

  return (
    <div aria-hidden="true" data-visual-tier={visualTier} className="absolute inset-0 overflow-hidden">
      <div className={`absolute inset-0 ${style.glowClassName}`} />
      <div className="absolute inset-6 rounded-[2rem] border border-white/10 bg-[linear-gradient(165deg,rgba(255,255,255,0.04),rgba(0,0,0,0.88))] backdrop-blur-xl" />
      <div className={`absolute left-1/2 top-1/2 h-56 w-56 -translate-x-1/2 -translate-y-1/2 rounded-full border ${style.accentBorderClassName}`} />
      <div className={`absolute left-1/2 top-1/2 h-72 w-72 -translate-x-1/2 -translate-y-1/2 rounded-full border ${style.accentBorderClassName} opacity-45`} />
      <div className="absolute left-1/2 top-1/2 h-5 w-5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white/85 shadow-[0_0_28px_rgba(255,255,255,0.3)]" />
      {visualTier === 'reduced' ? (
        <div className="absolute inset-x-8 bottom-8 flex flex-wrap items-center gap-3 font-mono text-[11px] tracking-[0.28em]">
          <span className={`rounded-full border px-4 py-2 ${style.accentBorderClassName} ${style.accentTextClassName}`}>
            {style.label}
          </span>
          <span className="rounded-full border border-white/10 px-4 py-2 text-white/60">
            STATIC PREVIEW
          </span>
        </div>
      ) : null}
    </div>
  );
}

export function ContactForm() {
  const t = useTranslations('Contact');
  const currentTime = useTime();
  const { tier: visualTier } = useVisualTier();
  const { isReady: isSceneReady } = useEnhancementReady({
    minimumTier: 'full',
    defer: 'idle',
  });

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [department, setDepartment] = useState('support');
  const [message, setMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isEncrypting, setIsEncrypting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [isHoveringSubmit, setIsHoveringSubmit] = useState(false);
  const [encryptionProgress, setEncryptionProgress] = useState(0);

  const visualState: ContactVisualState = isEncrypting
    ? 'encrypting'
    : isSuccess
      ? 'secured'
      : isTyping
        ? 'typing'
        : 'idle';
  const showScene = visualTier === 'full' && isSceneReady;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!name || !email || !message) {
      return;
    }

    setIsEncrypting(true);
    setIsTyping(false);
    setIsHoveringSubmit(false);

    let progress = 0;
    const interval = setInterval(() => {
      progress += Math.floor(Math.random() * 15) + 5;
      if (progress >= 100) {
        progress = 100;
        clearInterval(interval);
        setTimeout(() => {
          setIsEncrypting(false);
          setIsSuccess(true);
        }, 800);
      }
      setEncryptionProgress(progress);
    }, 150);
  };

  const handleInputFocus = () => setIsTyping(true);
  const handleInputBlur = () => setIsTyping(false);

  const resetForm = () => {
    setIsSuccess(false);
    setName('');
    setEmail('');
    setMessage('');
    setEncryptionProgress(0);
  };

  const content = (
    <div className="flex min-w-0 items-center justify-center lg:min-h-[calc(100dvh-6rem)] lg:py-4">
      <div className="relative w-full max-w-xl">
        <div className="absolute -inset-1 rounded-3xl bg-gradient-to-br from-neon-cyan/20 via-transparent to-neon-purple/20 blur-xl opacity-50" />

        <div className="relative overflow-hidden rounded-3xl border border-white/5 bg-white/[0.02] p-8 shadow-2xl backdrop-blur-2xl md:p-12">
          <div className="relative z-10 mb-10 space-y-2">
            <h1 className="font-display text-4xl font-black text-white md:text-5xl">
              <ScrambleText text={t('title')} />
            </h1>
            <p className="font-mono text-sm uppercase tracking-widest text-neon-cyan">
              {t('subtitle')}
            </p>
          </div>

          <AnimatePresence mode="wait">
            {!isEncrypting && !isSuccess ? (
              <motion.form
                key="form"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, x: -50 }}
                className="keyboard-safe-bottom relative z-10 space-y-6"
                onSubmit={handleSubmit}
              >
                <div className="space-y-2">
                  <label className="pl-1 font-mono text-xs uppercase tracking-wider text-muted-foreground-low">
                    {t('form.name')}
                  </label>
                  <div className="group relative">
                    <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-4">
                      <User className="h-4 w-4 text-white/30 transition-colors group-focus-within:text-neon-cyan" />
                    </div>
                    <input
                      type="text"
                      required
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      onFocus={handleInputFocus}
                      onBlur={handleInputBlur}
                      className="mobile-form-input w-full rounded-xl border border-white/10 bg-black/40 py-3 pl-12 pr-4 font-mono text-white placeholder:text-white/20 transition-all focus:border-neon-cyan/50 focus:outline-none focus:ring-1 focus:ring-neon-cyan/50"
                      placeholder={t('form.placeholder_name')}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="pl-1 font-mono text-xs uppercase tracking-wider text-muted-foreground-low">
                    {t('form.email')}
                  </label>
                  <div className="group relative">
                    <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-4">
                      <Mail className="h-4 w-4 text-white/30 transition-colors group-focus-within:text-neon-cyan" />
                    </div>
                    <input
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      onFocus={handleInputFocus}
                      onBlur={handleInputBlur}
                      className="mobile-form-input w-full rounded-xl border border-white/10 bg-black/40 py-3 pl-12 pr-4 font-mono text-white placeholder:text-white/20 transition-all focus:border-neon-cyan/50 focus:outline-none focus:ring-1 focus:ring-neon-cyan/50"
                      placeholder={t('form.placeholder_email')}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="pl-1 font-mono text-xs uppercase tracking-wider text-muted-foreground-low">
                    {t('form.department')}
                  </label>
                  <div className="group relative">
                    <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-4">
                      <Building className="h-4 w-4 text-white/30 transition-colors group-focus-within:text-neon-cyan" />
                    </div>
                    <select
                      value={department}
                      onChange={(e) => setDepartment(e.target.value)}
                      onFocus={handleInputFocus}
                      onBlur={handleInputBlur}
                      className="mobile-form-input w-full appearance-none rounded-xl border border-white/10 bg-black/40 py-3 pl-12 pr-4 font-mono text-white transition-all focus:border-neon-cyan/50 focus:outline-none focus:ring-1 focus:ring-neon-cyan/50"
                    >
                      <option value="support">{t('form.department_support')}</option>
                      <option value="sales">{t('form.department_sales')}</option>
                    </select>
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="pl-1 font-mono text-xs uppercase tracking-wider text-muted-foreground-low">
                    {t('form.message')}
                  </label>
                  <textarea
                    required
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    onFocus={handleInputFocus}
                    onBlur={handleInputBlur}
                    rows={4}
                    className="mobile-form-input w-full resize-none rounded-xl border border-white/10 bg-black/40 p-4 font-mono text-white placeholder:text-white/20 transition-all focus:border-neon-cyan/50 focus:outline-none focus:ring-1 focus:ring-neon-cyan/50"
                    placeholder={t('form.placeholder_message')}
                  />
                </div>

                <div className="pt-4">
                  <MagneticButton strength={20} className="block w-full">
                    <button
                      type="submit"
                      onMouseEnter={() => setIsHoveringSubmit(true)}
                      onMouseLeave={() => setIsHoveringSubmit(false)}
                      className="touch-target-comfortable group relative w-full overflow-hidden rounded-xl border border-white/10 bg-white/5 p-4 text-center font-display font-bold text-white transition-all hover:border-neon-cyan/50 hover:bg-neon-cyan/10 hover:shadow-[0_0_30px_rgba(0,255,255,0.2)]"
                    >
                      <span className="relative z-10 flex items-center justify-center gap-2">
                        {t('form.submit')}
                        <Send className="h-5 w-5 transition-transform group-hover:translate-x-1" />
                      </span>
                    </button>
                  </MagneticButton>
                </div>
              </motion.form>
            ) : null}

            {isEncrypting ? (
              <motion.div
                key="encrypting"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0 }}
                className="space-y-6 py-20 text-center"
              >
                <ShieldAlert className="mx-auto h-16 w-16 animate-pulse text-warning" />
                <div className="font-display text-xl uppercase tracking-widest text-warning">
                  <ScrambleText text="ENCRYPTING PAYLOAD" />
                </div>

                <div className="h-2 w-full overflow-hidden rounded-full border border-white/5 bg-black/50">
                  <div
                    className="relative h-full bg-warning transition-all duration-150"
                    style={{ width: `${encryptionProgress}%` }}
                  >
                    <div className="absolute inset-0 animate-pulse bg-white/20" />
                  </div>
                </div>

                <div className="font-mono text-xs text-muted-foreground-low">
                  [ {encryptionProgress}% ]{' '}
                  {encryptionProgress < 30
                    ? t('form.scanning')
                    : encryptionProgress < 70
                      ? t('form.establishing')
                      : t('form.verified')}
                </div>
              </motion.div>
            ) : null}

            {isSuccess ? (
              <motion.div
                key="success"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                className="space-y-6 py-20 text-center"
              >
                <div className="relative inline-block">
                  <div className="absolute inset-0 animate-pulse bg-neon-cyan opacity-30 blur-2xl" />
                  <CheckCircle2 className="relative z-10 h-20 w-20 text-neon-cyan" />
                </div>
                <div className="space-y-4">
                  <h2 className="font-display text-2xl font-bold uppercase tracking-widest text-white">
                    <ScrambleText text={t('form.success')} />
                  </h2>
                  <p className="font-mono text-sm text-muted-foreground">
                    Connection terminated. <br /> Awaiting counter-response.
                  </p>
                </div>
                <button
                  onClick={resetForm}
                  className="touch-target mt-8 rounded-full border border-white/10 px-6 py-2 font-mono text-xs text-white/50 transition-all hover:border-white/30 hover:text-white"
                >
                  {t('form.new_uplink')}
                </button>
              </motion.div>
            ) : null}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );

  const visual = (
    <div
      data-visual-tier={visualTier}
      className="relative h-full min-h-[20rem] overflow-hidden bg-[#050505]"
    >
      <div className="pointer-events-none absolute inset-0 z-10 box-shadow-vignette shadow-[inset_0_0_150px_rgba(0,0,0,0.9)]" />
      <div className="absolute inset-0">
        {showScene ? (
          <ContactFormVisual
            isTyping={isTyping}
            isEncrypting={isEncrypting}
            isSuccess={isSuccess}
            isHoveringSubmit={isHoveringSubmit}
          />
        ) : (
          <ContactVisualFallback visualTier={visualTier === 'full' ? 'reduced' : visualTier} visualState={visualState} />
        )}
      </div>
      <div className="absolute bottom-0 left-0 top-0 z-10 hidden w-32 bg-gradient-to-r from-terminal-bg to-transparent lg:block" />
      <div className="absolute left-0 right-0 top-0 z-10 h-32 bg-gradient-to-b from-terminal-bg to-transparent lg:hidden" />

      <div className="pointer-events-none absolute right-8 top-8 z-20 hidden rounded-lg border border-white/10 bg-black/40 p-4 font-mono text-xs backdrop-blur-md md:block">
        <div className="flex flex-col gap-2">
          <div className="flex justify-between gap-8 text-muted-foreground-low">
            <span>SYS_CLK:</span>
            <span className="text-white">
              {currentTime ? currentTime.replace(' UTC', '') : '--:--:--'}
            </span>
          </div>
          <div className="flex justify-between gap-8 text-muted-foreground-low">
            <span>NET_STATUS:</span>
            <span
              className={
                isEncrypting
                  ? 'text-warning'
                  : isSuccess
                    ? 'text-neon-cyan'
                    : isTyping
                      ? 'text-matrix-green'
                      : 'text-white'
              }
            >
              {isEncrypting
                ? '[ ENCRYPTING ]'
                : isSuccess
                  ? '[ SECURED ]'
                  : isTyping
                    ? '[ SCANNING ]'
                    : '[ IDLE ]'}
            </span>
          </div>
          <div className="my-1 h-px w-full bg-white/10" />
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              {showScene && (isTyping || isEncrypting) ? (
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-neon-cyan opacity-75" />
              ) : null}
              <span
                className={`relative inline-flex h-2 w-2 rounded-full ${
                  isEncrypting
                    ? 'bg-warning'
                    : isSuccess
                      ? 'bg-neon-cyan'
                      : isTyping
                        ? 'bg-matrix-green'
                        : 'bg-white/20'
                }`}
              />
            </span>
            <span className="text-[10px] uppercase text-muted-foreground-low">
              {showScene ? 'Live telemetry active' : 'Passive telemetry active'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <ResponsiveSplitShell
      className="min-h-[calc(100dvh-4rem)] bg-terminal-bg"
      containerClassName="max-w-[1680px]"
      contentPaneClassName="lg:col-span-6"
      pinVisualOnDesktop
      safeAreaPadding
      visualPaneClassName="rounded-[1.75rem] border border-white/5 bg-[#050505] lg:col-span-6 lg:rounded-none lg:border-0"
      content={content}
      visual={visual}
    />
  );
}
