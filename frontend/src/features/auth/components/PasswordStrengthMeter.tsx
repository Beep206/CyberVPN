'use client';

import { motion } from 'motion/react';
import { useTranslations } from 'next-intl';
import { getPasswordRequirements, validatePasswordInput } from '@/features/auth/lib/validation';
import { cn } from '@/lib/utils';

interface PasswordStrengthMeterProps {
    password: string;
    className?: string;
}

// Password strength calculation
function calculateStrength(password: string): { score: number; label: string; color: string } {
    if (!password) return { score: 0, label: 'empty', color: 'bg-grid-line/30' };

    const requirements = getPasswordRequirements(password);
    const metCount = requirements.filter((requirement) => requirement.met).length;
    const isValid = validatePasswordInput(password).isValid;
    const normalizedScore = isValid ? 4 : Math.min(3, Math.floor((metCount / requirements.length) * 4));
    const levels = [
        { score: 0, label: 'weak', color: 'bg-red-500' },
        { score: 1, label: 'fair', color: 'bg-orange-500' },
        { score: 2, label: 'good', color: 'bg-yellow-500' },
        { score: 3, label: 'strong', color: 'bg-matrix-green' },
        { score: 4, label: 'excellent', color: 'bg-neon-cyan' },
    ];

    return levels[normalizedScore] || levels[0];
}

export function PasswordStrengthMeter({ password, className }: PasswordStrengthMeterProps) {
    const t = useTranslations('Auth.passwordStrength');
    const strength = calculateStrength(password);
    const requirements = getPasswordRequirements(password);

    if (!password) return null;

    return (
        <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className={cn("space-y-2", className)}
        >
            {/* Strength bar */}
            <div className="flex gap-1">
                {[0, 1, 2, 3].map((index) => (
                    <motion.div
                        key={index}
                        className={cn(
                            "h-1 flex-1 rounded-full transition-colors duration-300",
                            index <= strength.score ? strength.color : "bg-grid-line/30"
                        )}
                        initial={{ scaleX: 0 }}
                        animate={{ scaleX: index <= strength.score ? 1 : 0.3 }}
                        transition={{ delay: index * 0.05, duration: 0.2 }}
                        style={{ transformOrigin: 'left' }}
                    />
                ))}
            </div>

            {/* Label */}
            <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-muted-foreground">
                    {t.has('label') ? t('label') : 'password_strength:'}
                </span>
                <motion.span
                    key={strength.label}
                    initial={{ opacity: 0, x: 5 }}
                    animate={{ opacity: 1, x: 0 }}
                    className={cn(
                        "uppercase tracking-wider",
                        strength.score <= 1 && "text-red-500",
                        strength.score === 2 && "text-yellow-500",
                        strength.score >= 3 && "text-matrix-green"
                    )}
                >
                    [{t.has(strength.label) ? t(strength.label) : strength.label}]
                </motion.span>
            </div>

            {/* Requirements hints */}
            <div className="grid grid-cols-1 gap-1 text-[10px] font-mono text-muted-foreground-low sm:grid-cols-2">
                {requirements.map((requirement) => (
                    <RequirementItem
                        key={requirement.code}
                        met={requirement.met}
                        text={
                            t.has(`requirements.${requirement.code}`)
                                ? t(`requirements.${requirement.code}`)
                                : requirement.code
                        }
                    />
                ))}
            </div>
        </motion.div>
    );
}

function RequirementItem({ met, text }: { met: boolean; text: string }) {
    return (
        <span className={cn(
            "flex items-center gap-1 transition-colors",
            met ? "text-matrix-green" : "text-muted-foreground-low"
        )}>
            <span className={cn(
                "w-1.5 h-1.5 rounded-full transition-colors",
                met ? "bg-matrix-green" : "bg-grid-line/30"
            )} />
            {text}
        </span>
    );
}
