'use client';

import { motion, useMotionValue, useSpring } from 'motion/react';
import React, { useRef } from 'react';
import { useMotionCapability } from '@/shared/hooks/use-motion-capability';

interface MagneticButtonProps {
    children: React.ReactNode;
    strength?: number;
    className?: string;
    onClick?: () => void;
}

export function MagneticButton({
    children,
    strength = 30,
    className,
    onClick,
}: MagneticButtonProps) {
    const ref = useRef<HTMLDivElement>(null);
    const { allowPointerEffects } = useMotionCapability();
    const x = useMotionValue(0);
    const y = useMotionValue(0);
    const springConfig = { damping: 15, stiffness: 150, mass: 0.1 };
    const springX = useSpring(x, springConfig);
    const springY = useSpring(y, springConfig);

    const handleMouseMove = (event: React.MouseEvent) => {
        if (!allowPointerEffects) {
            return;
        }

        const { clientX, clientY } = event;
        const bounds = ref.current?.getBoundingClientRect();

        if (!bounds) {
            return;
        }

        const centerX = bounds.left + bounds.width / 2;
        const centerY = bounds.top + bounds.height / 2;

        x.set((clientX - centerX) / strength);
        y.set((clientY - centerY) / strength);
    };

    const handleMouseLeave = () => {
        x.set(0);
        y.set(0);
    };

    return (
        <motion.div
            ref={ref}
            onMouseMove={allowPointerEffects ? handleMouseMove : undefined}
            onMouseLeave={allowPointerEffects ? handleMouseLeave : undefined}
            style={allowPointerEffects ? { x: springX, y: springY } : undefined}
            className={className}
            onClick={onClick}
        >
            {children}
        </motion.div>
    );
}
