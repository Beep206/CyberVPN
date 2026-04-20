
import { motion } from 'framer-motion';
import { Shield, ShieldAlert, ShieldCheck } from 'lucide-react';
import { ConnectionStatus } from '@/shared/api/ipc';
import { desktopMotionEase, useDesktopMotionBudget } from '../shared/lib/motion';
import { useTranslation } from 'react-i18next';

interface ConnectButtonProps {
    status: ConnectionStatus;
    onConnect: () => void;
    onDisconnect: () => void;
}

export function ConnectButton({ status, onConnect, onDisconnect }: ConnectButtonProps) {
    const { t } = useTranslation();
    const { prefersReducedMotion, durations, scales } = useDesktopMotionBudget();
    const isConnected = status.status === "connected";
    const isConnecting = status.status === "connecting";
    const isDisconnecting = status.status === "disconnecting";
    const isDegraded = status.status === "degraded";
    const isConnectedLike = isConnected || isDegraded;
    const isBusy = isConnecting || isDisconnecting;
    const orbitDuration = isBusy ? 3.2 : 7.2;

    const getStatusColor = () => {
        if (isConnected) return "var(--color-matrix-green)";
        if (isDegraded) return "var(--color-neon-pink)";
        if (isConnecting) return "var(--color-neon-cyan)";
        if (isDisconnecting) return "var(--color-neon-cyan)";
        return "var(--muted-foreground)";
    };

    const getIcon = () => {
        if (isConnected) return <ShieldCheck size={48} />;
        if (isDegraded) return <ShieldAlert size={48} />;
        if (isConnecting) return <Shield size={48} className="animate-pulse" />;
        if (isDisconnecting) return <Shield size={48} className="animate-pulse" />;
        return <ShieldAlert size={48} />;
    };

    const handleClick = () => {
        if (isDisconnecting) {
            return;
        }

        if (isConnectedLike || isConnecting) {
            onDisconnect();
        } else {
            onConnect();
        }
    };

    return (
        <div className="flex flex-col items-center justify-center gap-6">
            <motion.button
                onClick={handleClick}
                whileHover={isDisconnecting ? undefined : { scale: scales.hover }}
                whileTap={isDisconnecting ? undefined : { scale: scales.tap }}
                disabled={isDisconnecting}
                className="group relative flex h-52 w-52 items-center justify-center overflow-hidden rounded-full border shadow-[var(--panel-shadow-strong)] transition-all duration-200 disabled:cursor-not-allowed disabled:opacity-80"
                style={{
                    borderColor: `color-mix(in oklab, ${getStatusColor()} 28%, var(--border))`,
                    boxShadow: isConnectedLike || isConnecting || isDisconnecting ? `0 18px 56px ${getStatusColor()}28` : 'var(--panel-shadow-strong)',
                    backgroundColor: 'var(--panel-surface)',
                }}
            >
                <div
                    className="absolute inset-[6px] rounded-full border border-white/30"
                    style={{ background: "linear-gradient(180deg, color-mix(in oklab, var(--panel-surface) 92%, white), var(--panel-subtle))" }}
                />
                {(isConnectedLike || isBusy) && !prefersReducedMotion ? (
                    <motion.div
                        aria-hidden
                        className="absolute inset-[4px] rounded-full opacity-55"
                        style={{
                            background: `conic-gradient(from 0deg, transparent 0deg, transparent 42deg, ${getStatusColor()}55 96deg, transparent 160deg, transparent 360deg)`,
                            filter: "blur(1px)",
                        }}
                        animate={{ rotate: 360 }}
                        transition={{ repeat: Infinity, duration: orbitDuration, ease: "linear" }}
                    />
                ) : null}
                <div 
                    className="absolute inset-0 opacity-16 transition-opacity duration-200 group-hover:opacity-28"
                    style={{ background: `radial-gradient(circle at 30% 30%, ${getStatusColor()}24, transparent 58%)` }}
                />
                <div
                    className="absolute inset-[28px] rounded-full border border-white/35 bg-[color:var(--chrome-elevated)]/72 backdrop-blur-xl"
                />

                <motion.div 
                    className="relative z-10 flex flex-col items-center gap-2 will-change-[opacity,transform]"
                    style={{ color: getStatusColor() }}
                    animate={
                        isBusy && !prefersReducedMotion
                            ? { y: [0, -2, 0], opacity: [1, 0.88, 1] }
                            : { y: 0, opacity: 1 }
                    }
                    transition={
                        isBusy && !prefersReducedMotion
                            ? {
                                repeat: Infinity,
                                duration: 1.1,
                                ease: desktopMotionEase,
                              }
                            : { duration: durations.micro, ease: desktopMotionEase }
                    }
                >
                    {getIcon()}
                    <motion.span
                        aria-hidden
                        className="h-2.5 w-2.5 rounded-full"
                        style={{ backgroundColor: getStatusColor(), boxShadow: `0 0 16px ${getStatusColor()}` }}
                        animate={
                            isConnectedLike || isBusy
                                ? { opacity: [0.42, 1, 0.54], scale: [0.92, 1.12, 0.98] }
                                : { opacity: 0.68, scale: 1 }
                        }
                        transition={
                            isConnectedLike || isBusy
                                ? { repeat: Infinity, duration: 1.8, ease: desktopMotionEase }
                                : { duration: durations.micro, ease: desktopMotionEase }
                        }
                    />
                    <span className="font-bold tracking-[0.22em] uppercase text-sm">
                        {t(`dashboard.status_${status.status}`, { defaultValue: status.status })}
                    </span>
                </motion.div>
                
                {(isConnectedLike || isBusy) && (
                    <>
                       <motion.div
                          className="absolute inset-0 rounded-full border-2 border-dashed opacity-30"
                          style={{ borderColor: getStatusColor() }}
                          animate={
                              isBusy && !prefersReducedMotion
                                  ? { scale: [1, 1.02, 1], opacity: [0.2, 0.32, 0.2] }
                                  : { scale: 1, opacity: 0.24 }
                          }
                          transition={
                              isBusy && !prefersReducedMotion
                                  ? { repeat: Infinity, duration: 1.4, ease: desktopMotionEase }
                                  : { duration: durations.accent, ease: desktopMotionEase }
                          }
                       />
                       <motion.div 
                          className="absolute inset-2 rounded-full border border-dotted opacity-20"
                          style={{ borderColor: getStatusColor() }}
                          animate={
                              isBusy && !prefersReducedMotion
                                  ? { scale: [1, 0.985, 1], opacity: [0.14, 0.24, 0.14] }
                                  : { scale: 1, opacity: 0.16 }
                          }
                          transition={
                              isBusy && !prefersReducedMotion
                                  ? { repeat: Infinity, duration: 1.4, ease: desktopMotionEase }
                                  : { duration: durations.accent, ease: desktopMotionEase }
                          }
                       />
                    </>
                )}
            </motion.button>
            
            {(isConnectedLike || isConnecting || isDisconnecting) && status.activeId && (
                    <div className="rounded-full border border-border/60 bg-[color:var(--chrome-elevated)]/88 px-4 py-2 font-mono text-sm text-muted-foreground shadow-[var(--panel-shadow)] backdrop-blur-xl">
                        {t('dashboard.profileId')}: <span className="text-[var(--color-neon-cyan)]">{status.activeId}</span>
                    </div>
            )}
        </div>
    );
}
