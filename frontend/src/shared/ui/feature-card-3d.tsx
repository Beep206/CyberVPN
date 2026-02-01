'use client';

import { motion, useMotionTemplate, useMotionValue } from 'motion/react';
import React from 'react';
import { ScrambleText } from '@/shared/ui/scramble-text';
import type { LucideIcon } from 'lucide-react';

interface FeatureCard3DProps {
    icon: LucideIcon;
    title: string;
    description: string;
    color: string;
    bgColor: string;
    index: number;
    colSpan?: string;
}

export function FeatureCard3D({
    icon: Icon,
    title,
    description,
    color,
    bgColor,
    index,
    colSpan = ''
}: FeatureCard3DProps) {
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

        const xPct = localX / width - 0.5;
        const yPct = localY / height - 0.5;

        rotateX.set(yPct * -12);
        rotateY.set(xPct * 12);
    }

    function onMouseLeave() {
        rotateX.set(0);
        rotateY.set(0);
        mouseX.set(0);
        mouseY.set(0);
    }

    // Stagger animation variants
    const cardVariants = {
        hidden: {
            opacity: 0,
            y: 40,
            scale: 0.95
        },
        visible: {
            opacity: 1,
            y: 0,
            scale: 1,
            transition: {
                type: 'spring',
                stiffness: 100,
                damping: 15,
                delay: index * 0.1
            }
        }
    };

    return (
        <motion.div
            variants={cardVariants}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: '-50px' }}
            className={`${colSpan}`}
        >
            <motion.div
                className="group relative h-full rounded-2xl border border-grid-line/40 bg-terminal-surface/80 dark:bg-black/30 backdrop-blur-xl overflow-hidden shadow-lg dark:shadow-none cursor-pointer"
                onMouseMove={onMouseMove}
                onMouseLeave={onMouseLeave}
                style={{
                    perspective: 1000,
                    rotateX,
                    rotateY,
                    transformStyle: 'preserve-3d'
                }}
                whileHover={{ scale: 1.02 }}
                transition={{ type: 'spring', stiffness: 400, damping: 25 }}
            >
                {/* Hover glow effect */}
                <motion.div
                    className="pointer-events-none absolute -inset-px opacity-0 transition duration-500 group-hover:opacity-100 z-10"
                    style={{
                        background: useMotionTemplate`
                            radial-gradient(
                                600px circle at ${mouseX}px ${mouseY}px,
                                var(--glow-color, rgba(0, 255, 255, 0.15)),
                                transparent 70%
                            )
                        `
                    }}
                />

                {/* Animated border on hover */}
                <div className="absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 z-0">
                    <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-neon-cyan/50 via-neon-purple/50 to-neon-cyan/50 blur-sm" />
                </div>

                {/* Content */}
                <div className="relative h-full p-8 flex flex-col justify-between z-20">
                    {/* Icon container */}
                    <div className="flex items-start justify-between mb-6">
                        <motion.div
                            className={`w-16 h-16 rounded-xl flex items-center justify-center ${bgColor} ${color} border border-foreground/5 shadow-lg`}
                            whileHover={{ scale: 1.1, rotate: 5 }}
                            transition={{ type: 'spring', stiffness: 300 }}
                        >
                            <Icon className="w-8 h-8" />
                        </motion.div>

                        {/* Tech badge */}
                        <div className="text-[10px] font-mono text-foreground/30 tracking-wider">
                            SYS.0{index + 1}
                        </div>
                    </div>

                    {/* Text content */}
                    <div className="flex-1 flex flex-col justify-end">
                        <h3 className="text-2xl font-bold font-display mb-3 text-foreground group-hover:text-neon-cyan transition-colors duration-300">
                            <ScrambleText text={title} triggerOnHover />
                        </h3>
                        <p className="text-muted-foreground font-mono leading-relaxed text-sm">
                            {description}
                        </p>
                    </div>

                    {/* Decorative elements */}
                    <div className="absolute bottom-4 right-4 flex items-center gap-2">
                        <div className="w-8 h-0.5 bg-gradient-to-r from-transparent to-foreground/20 group-hover:to-neon-cyan/50 transition-all duration-300" />
                        <div className="w-2 h-2 rounded-full bg-foreground/10 group-hover:bg-neon-cyan/50 group-hover:shadow-[0_0_10px_rgba(0,255,255,0.5)] transition-all duration-300" />
                    </div>

                    {/* Corner accent */}
                    <div className="absolute top-0 right-0 w-20 h-20 opacity-20 group-hover:opacity-40 transition-opacity duration-300">
                        <svg viewBox="0 0 80 80" className={color}>
                            <path
                                d="M0 0 L80 0 L80 80"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth="1"
                                strokeDasharray="4 4"
                            />
                        </svg>
                    </div>
                </div>
            </motion.div>
        </motion.div>
    );
}
