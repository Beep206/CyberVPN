'use client';

import { motion, useMotionTemplate, useMotionValue } from 'motion/react';
import React from 'react';
import { cn } from '@/lib/utils';

interface AuthFormCardProps {
    children: React.ReactNode;
    className?: string;
    title?: string;
    subtitle?: string;
}

export function AuthFormCard({ children, className, title, subtitle }: AuthFormCardProps) {
    const mouseX = useMotionValue(0);
    const mouseY = useMotionValue(0);
    const rotateX = useMotionValue(0);
    const rotateY = useMotionValue(0);

    function onMouseMove({ currentTarget, clientX, clientY }: React.MouseEvent) {
        const { left, top, width, height } = currentTarget.getBoundingClientRect();
        const localX = clientX - left;
        const localY = clientY - top;

        mouseX.set(localX);
        mouseY.set(localY);

        // Subtle tilt (max 8 degrees)
        const xPct = localX / width - 0.5;
        const yPct = localY / height - 0.5;
        rotateX.set(yPct * -8);
        rotateY.set(xPct * 8);
    }

    function onMouseLeave() {
        rotateX.set(0);
        rotateY.set(0);
        mouseX.set(0);
        mouseY.set(0);
    }

    return (
        <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.6, ease: [0.23, 1, 0.32, 1] }}
            className={cn(
                // Base
                "relative w-full max-w-md mx-auto",
                // Glassmorphic effect
                "bg-terminal-surface/80 dark:bg-black/40",
                "backdrop-blur-xl",
                // Border with gradient glow
                "border border-grid-line/40 dark:border-white/10",
                // Shadow
                "shadow-lg dark:shadow-2xl dark:shadow-neon-cyan/5",
                // Rounded
                "rounded-2xl",
                // Overflow for glow effect
                "overflow-hidden",
                className
            )}
            onMouseMove={onMouseMove}
            onMouseLeave={onMouseLeave}
            style={{
                perspective: 1000,
                rotateX,
                rotateY,
                transformStyle: "preserve-3d",
            }}
        >
            {/* Animated gradient border glow */}
            <motion.div
                className="pointer-events-none absolute -inset-px opacity-0 transition-opacity duration-500 group-hover:opacity-100 z-0"
                style={{
                    background: useMotionTemplate`
                        radial-gradient(
                            400px circle at ${mouseX}px ${mouseY}px,
                            rgba(0, 255, 255, 0.15),
                            transparent 60%
                        )
                    `,
                }}
            />

            {/* Top accent line */}
            <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-neon-cyan/50 to-transparent" />

            {/* Content */}
            <div className="relative z-10 p-8">
                {/* Header */}
                {(title || subtitle) && (
                    <div className="text-center mb-8">
                        {title && (
                            <motion.h1
                                initial={{ opacity: 0, y: -10 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: 0.1, duration: 0.5 }}
                                className="text-2xl md:text-3xl font-display font-bold text-foreground mb-2"
                            >
                                {title}
                            </motion.h1>
                        )}
                        {subtitle && (
                            <motion.p
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                transition={{ delay: 0.2, duration: 0.5 }}
                                className="text-sm text-muted-foreground font-mono"
                            >
                                {subtitle}
                            </motion.p>
                        )}
                    </div>
                )}

                {children}
            </div>

            {/* Corner decorations */}
            <div className="absolute top-2 left-2 w-4 h-4 border-l-2 border-t-2 border-neon-cyan/30 rounded-tl" />
            <div className="absolute top-2 right-2 w-4 h-4 border-r-2 border-t-2 border-neon-cyan/30 rounded-tr" />
            <div className="absolute bottom-2 left-2 w-4 h-4 border-l-2 border-b-2 border-neon-cyan/30 rounded-bl" />
            <div className="absolute bottom-2 right-2 w-4 h-4 border-r-2 border-b-2 border-neon-cyan/30 rounded-br" />
        </motion.div>
    );
}
