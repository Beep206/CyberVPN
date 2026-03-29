'use client';

import type { ReactNode } from 'react';
import { motion, type Transition } from 'motion/react';

type RevealVariant = 'up' | 'left' | 'right' | 'scale';

const INITIAL_VARIANTS: Record<RevealVariant, Record<string, number>> = {
  up: { opacity: 0, y: 30 },
  left: { opacity: 0, x: -20 },
  right: { opacity: 0, x: 20 },
  scale: { opacity: 0, scale: 0.95 },
};

const TARGET_VARIANT = { opacity: 1, x: 0, y: 0, scale: 1 };

interface RevealProps {
  children: ReactNode;
  className?: string;
  delay?: number;
  margin?: string;
  once?: boolean;
  transition?: Transition;
  variant?: RevealVariant;
}

export function Reveal({
  children,
  className,
  delay = 0,
  margin = '-50px',
  once = true,
  transition,
  variant = 'up',
}: RevealProps) {
  return (
    <motion.div
      initial={INITIAL_VARIANTS[variant]}
      whileInView={TARGET_VARIANT}
      viewport={{ once, margin }}
      transition={transition ?? { duration: 0.8, delay, ease: 'easeOut' }}
      className={className}
    >
      {children}
    </motion.div>
  );
}
