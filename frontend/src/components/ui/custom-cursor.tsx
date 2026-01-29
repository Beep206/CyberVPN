'use client';

import { useEffect, useState } from 'react';
import { motion, useMotionValue, useSpring } from 'motion/react';

export function CustomCursor() {
    const [isHovering, setIsHovering] = useState(false);
    const cursorX = useMotionValue(-100);
    const cursorY = useMotionValue(-100);

    const springConfig = { damping: 25, stiffness: 700 };
    const cursorXSpring = useSpring(cursorX, springConfig);
    const cursorYSpring = useSpring(cursorY, springConfig);

    useEffect(() => {
        const moveCursor = (e: MouseEvent) => {
            cursorX.set(e.clientX - 16);
            cursorY.set(e.clientY - 16);
        };

        const handleOver = (e: Event) => {
            const target = (e.target as HTMLElement).closest?.('a, button, input, textarea, [data-hoverable]');
            if (target) setIsHovering(true);
        };

        const handleOut = (e: Event) => {
            const target = (e.target as HTMLElement).closest?.('a, button, input, textarea, [data-hoverable]');
            if (target) setIsHovering(false);
        };

        window.addEventListener('mousemove', moveCursor);
        document.addEventListener('mouseover', handleOver);
        document.addEventListener('mouseout', handleOut);

        return () => {
            window.removeEventListener('mousemove', moveCursor);
            document.removeEventListener('mouseover', handleOver);
            document.removeEventListener('mouseout', handleOut);
        };
    }, [cursorX, cursorY]);

    return (
        <motion.div
            className="fixed top-0 left-0 w-8 h-8 pointer-events-none z-[9999] mix-blend-difference"
            style={{
                x: cursorXSpring,
                y: cursorYSpring,
            }}
        >
            {/* Core Dot */}
            <motion.div
                animate={{
                    scale: isHovering ? 0.5 : 1,
                    backgroundColor: isHovering ? 'var(--color-neon-cyan)' : 'var(--foreground)'
                }}
                className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-white"
            />

            {/* Outer Ring */}
            <motion.div
                animate={{
                    scale: isHovering ? 1.5 : 1,
                    borderWidth: isHovering ? '2px' : '1px',
                    borderColor: isHovering ? 'var(--color-neon-cyan)' : 'var(--foreground)',
                    opacity: isHovering ? 1 : 0.5
                }}
                className="absolute inset-0 rounded-full border border-white"
            />
        </motion.div>
    );
}
