'use client';

import { motion, useMotionTemplate, useMotionValue } from 'motion/react';
import React from 'react';
import { useMotionCapability } from '@/shared/hooks/use-motion-capability';

interface TiltCardProps {
    children: React.ReactNode;
    className?: string;
}

export function TiltCard({ children, className = '' }: TiltCardProps) {
    const { allowPointerEffects } = useMotionCapability();
    const mouseX = useMotionValue(0);
    const mouseY = useMotionValue(0);
    const rotateX = useMotionValue(0);
    const rotateY = useMotionValue(0);
    const glowBackground = useMotionTemplate`
        radial-gradient(
            650px circle at ${mouseX}px ${mouseY}px,
            var(--glow-color, rgba(0, 255, 255, 0.15)),
            transparent 80%
        )
    `;

    function onMouseMove({ currentTarget, clientX, clientY }: React.MouseEvent) {
        if (!allowPointerEffects) {
            return;
        }

        const { left, top, width, height } = currentTarget.getBoundingClientRect();
        const localX = clientX - left;
        const localY = clientY - top;

        mouseX.set(localX);
        mouseY.set(localY);

        const xPct = localX / width - 0.5;
        const yPct = localY / height - 0.5;

        rotateX.set(yPct * -15);
        rotateY.set(xPct * 15);
    }

    function onMouseLeave() {
        rotateX.set(0);
        rotateY.set(0);
        mouseX.set(0);
        mouseY.set(0);
    }

    const baseClassName = `group relative border border-grid-line/40 bg-terminal-surface/80 dark:bg-black/20 dark:border-white/5 backdrop-blur-xl overflow-hidden shadow-md dark:shadow-none ${className}`;

    return (
        <motion.div
            className={baseClassName}
            onMouseMove={allowPointerEffects ? onMouseMove : undefined}
            onMouseLeave={allowPointerEffects ? onMouseLeave : undefined}
            style={allowPointerEffects ? {
                perspective: 1000,
                rotateX,
                rotateY,
                transformStyle: 'preserve-3d',
            } : undefined}
        >
            <motion.div
                className={`pointer-events-none absolute -inset-px transition duration-300 z-10 ${allowPointerEffects ? 'opacity-0 group-hover:opacity-100' : 'opacity-0'}`}
                style={{
                    background: glowBackground,
                }}
            />
            <div className="relative h-full transform-style-3d">{children}</div>
        </motion.div>
    );
}
