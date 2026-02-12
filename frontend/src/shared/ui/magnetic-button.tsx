'use client';

import { motion, useMotionValue, useSpring } from 'motion/react';
import React, { useRef } from 'react';

interface MagneticButtonProps {
    children: React.ReactNode;
    strength?: number; // How strong the magnetic pull is (default: 30)
    className?: string;
    onClick?: () => void;
}

export function MagneticButton({
    children,
    strength = 30,
    className,
    onClick
}: MagneticButtonProps) {
    const ref = useRef<HTMLDivElement>(null);

    // Motion values for the button position
    const x = useMotionValue(0);
    const y = useMotionValue(0);

    // Spring physics for smooth return
    const springConfig = { damping: 15, stiffness: 150, mass: 0.1 };
    const springX = useSpring(x, springConfig);
    const springY = useSpring(y, springConfig);

    const handleMouseMove = (e: React.MouseEvent) => {
        const { clientX, clientY } = e;
        const { left, top, width, height } = ref.current?.getBoundingClientRect() || { left: 0, top: 0, width: 0, height: 0 };

        const centerX = left + width / 2;
        const centerY = top + height / 2;

        const distanceX = clientX - centerX;
        const distanceY = clientY - centerY;

        x.set(distanceX / strength);
        y.set(distanceY / strength);
    };

    const handleMouseLeave = () => {
        x.set(0);
        y.set(0);
    };

    return (
        <motion.div
            ref={ref}
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
            style={{ x: springX, y: springY }}
            className={className}
            onClick={onClick}
        >
            {children}
        </motion.div>
    );
}
