import { forwardRef } from 'react';
import { cn } from '@/lib/utils';
import { motion, HTMLMotionProps } from 'framer-motion';

export interface GlassCardProps extends Omit<HTMLMotionProps<"div">, "ref" | "children"> {
    variant?: 'default' | 'elevated' | 'cyber' | 'stealth';
    withScanlines?: boolean;
    children?: React.ReactNode;
}

export const GlassCard = forwardRef<HTMLDivElement, GlassCardProps>(({
    className,
    variant = 'default',
    withScanlines = false,
    children,
    ...props
}, ref) => {
    
    const variants = {
        default: "border-white/10 bg-white/[0.03] backdrop-blur-[12px] shadow-[var(--panel-shadow)] dark:border-white/5 dark:bg-black/10",
        elevated: "border-white/15 bg-white/[0.05] backdrop-blur-[16px] shadow-[var(--panel-shadow-strong)] dark:border-white/10 dark:bg-black/20",
        cyber: "border-[color:color-mix(in_oklab,var(--color-matrix-green)_20%,transparent)] bg-[color:color-mix(in_oklab,var(--color-matrix-green)_5%,transparent)] backdrop-blur-[16px] shadow-[0_10px_30px_color-mix(in_oklab,var(--color-matrix-green)_5%,transparent)]",
        stealth: "border-[color:color-mix(in_oklab,var(--color-neon-pink)_20%,transparent)] bg-[color:color-mix(in_oklab,var(--color-neon-pink)_5%,transparent)] backdrop-blur-[16px] shadow-[0_10px_30px_color-mix(in_oklab,var(--color-neon-pink)_5%,transparent)]"
    };

    return (
        <motion.div
            ref={ref}
            className={cn(
                "relative overflow-hidden rounded-[var(--radius-lg)] border",
                variants[variant],
                className
            )}
            {...props}
        >
            {/* Ambient inner glow */}
            <div className="pointer-events-none absolute inset-0 z-0 bg-gradient-to-br from-white/[0.06] to-transparent opacity-50" />
            
            {/* Subtle Noise / Scanlines mix if requested */}
            {withScanlines && (
                 <div className="pointer-events-none absolute inset-0 z-0 opacity-10 mix-blend-overlay bg-[linear-gradient(rgba(255,255,255,0)_50%,rgba(0,0,0,0.1)_50%)] bg-[length:100%_4px]" />
            )}

            {/* Content layer */}
            <div className="relative z-10 h-full w-full">
                {children}
            </div>
        </motion.div>
    );
});

GlassCard.displayName = "GlassCard";
