import { forwardRef } from 'react';
import { motion, HTMLMotionProps } from 'framer-motion';
import { cn } from '@/lib/utils';
import { useDesktopMotionBudget } from '@/shared/lib/motion';

export interface CyberButtonProps extends Omit<HTMLMotionProps<"button">, "ref" | "children"> {
    variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
    size?: 'sm' | 'md' | 'lg' | 'icon';
    glow?: boolean;
    children?: React.ReactNode;
}

export const CyberButton = forwardRef<HTMLButtonElement, CyberButtonProps>(({
    className,
    variant = 'primary',
    size = 'md',
    glow = true,
    children,
    ...props
}, ref) => {
    const { prefersReducedMotion, durations, scales } = useDesktopMotionBudget();

    const variants = {
        primary: "bg-[color:color-mix(in_oklab,var(--color-matrix-green)_15%,transparent)] text-[var(--color-matrix-green)] border-[var(--color-matrix-green)] hover:bg-[color:color-mix(in_oklab,var(--color-matrix-green)_25%,transparent)] hover:shadow-[0_0_15px_color-mix(in_oklab,var(--color-matrix-green)_40%,transparent)]",
        secondary: "bg-[color:color-mix(in_oklab,var(--color-neon-cyan)_15%,transparent)] text-[var(--color-neon-cyan)] border-[var(--color-neon-cyan)] hover:bg-[color:color-mix(in_oklab,var(--color-neon-cyan)_25%,transparent)] hover:shadow-[0_0_15px_color-mix(in_oklab,var(--color-neon-cyan)_40%,transparent)]",
        danger: "bg-[color:color-mix(in_oklab,var(--color-neon-pink)_15%,transparent)] text-[var(--color-neon-pink)] border-[var(--color-neon-pink)] hover:bg-[color:color-mix(in_oklab,var(--color-neon-pink)_25%,transparent)] hover:shadow-[0_0_15px_color-mix(in_oklab,var(--color-neon-pink)_40%,transparent)]",
        ghost: "bg-transparent text-foreground border-transparent hover:bg-white/5",
    };

    const sizes = {
        sm: "h-8 px-3 text-xs",
        md: "h-10 px-4 py-2 text-sm",
        lg: "h-12 px-8 text-base",
        icon: "h-10 w-10 p-2",
    };

    const isGhost = variant === 'ghost';

    return (
        <motion.button
            ref={ref}
            whileHover={!prefersReducedMotion ? { scale: scales.hover } : undefined}
            whileTap={!prefersReducedMotion ? { scale: scales.tap } : undefined}
            transition={{ duration: durations.micro }}
            className={cn(
                "relative inline-flex items-center justify-center font-mono font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50",
                "border backdrop-blur-sm overflow-hidden",
                !isGhost && "[clip-path:polygon(0_0,calc(100%-10px)_0,100%_10px,100%_100%,10px_100%,0_calc(100%-10px))]",
                isGhost && "rounded-md",
                variants[variant],
                sizes[size],
                className
            )}
            {...props}
        >
            {/* Cyberpunk decorator line */}
            {!isGhost && (
                <span className="absolute bottom-0 left-2 right-[10px] h-[2px] bg-current opacity-30" />
            )}
            
            {/* Inner glow sweep effect */}
            {glow && !prefersReducedMotion && !isGhost && (
                <motion.span
                    className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -skew-x-12"
                    initial={{ x: '-150%' }}
                    whileHover={{ x: '150%' }}
                    transition={{ duration: 0.6, ease: 'easeInOut' }}
                />
            )}
            
            <span className="relative z-10 flex items-center justify-center gap-2">
                {children}
            </span>
        </motion.button>
    );
});

CyberButton.displayName = "CyberButton";
