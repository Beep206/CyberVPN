'use client';

import { motion, useMotionTemplate, useMotionValue } from 'motion/react';
import React from 'react';

interface TiltCardProps {
    children: React.ReactNode;
    className?: string;
}

export function TiltCard({ children, className = '' }: TiltCardProps) {
    const mouseX = useMotionValue(0);
    const mouseY = useMotionValue(0);

    // Rotation values
    const rotateX = useMotionValue(0);
    const rotateY = useMotionValue(0);

    function onMouseMove({ currentTarget, clientX, clientY }: React.MouseEvent) {
        const { left, top, width, height } = currentTarget.getBoundingClientRect();

        // Local coordinates
        const localX = clientX - left;
        const localY = clientY - top;

        mouseX.set(localX);
        mouseY.set(localY);

        // Calculate tilt (max 15 degrees)
        const xPct = localX / width - 0.5;
        const yPct = localY / height - 0.5;

        rotateX.set(yPct * -15); // Invert Y for correct tilt direction
        rotateY.set(xPct * 15);
    }

    function onMouseLeave() {
        rotateX.set(0);
        rotateY.set(0);
        mouseX.set(0);
        mouseY.set(0);
    }

    return (
        <motion.div
            className={`group relative border border-white/5 bg-black/20 backdrop-blur-xl overflow-hidden ${className}`}
            onMouseMove={onMouseMove}
            onMouseLeave={onMouseLeave}
            style={{
                perspective: 1000,
                rotateX,
                rotateY,
                transformStyle: "preserve-3d"
            }}
        >
            <motion.div
                className="pointer-events-none absolute -inset-px opacity-0 transition duration-300 group-hover:opacity-100 z-10"
                style={{
                    background: useMotionTemplate`
            radial-gradient(
              650px circle at ${mouseX}px ${mouseY}px,
              rgba(0, 255, 255, 0.15),
              transparent 80%
            )
          `,
                }}
            />
            <div className="relative h-full transform-style-3d">{children}</div>
        </motion.div>
    );
}
