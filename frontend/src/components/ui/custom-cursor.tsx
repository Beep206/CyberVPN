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

        const handleMouseEnter = () => setIsHovering(true);
        const handleMouseLeave = () => setIsHovering(false);

        // Add event listeners for hoverable elements
        const updateHoverables = () => {
            const hoverables = document.querySelectorAll('a, button, input, textarea, [data-hoverable]');
            hoverables.forEach((el) => {
                el.addEventListener('mouseenter', handleMouseEnter);
                el.addEventListener('mouseleave', handleMouseLeave);
            });
        };

        window.addEventListener('mousemove', moveCursor);
        updateHoverables();

        // Re-check hoverables on mutation (navigating pages)
        const observer = new MutationObserver(updateHoverables);
        observer.observe(document.body, { childList: true, subtree: true });

        return () => {
            window.removeEventListener('mousemove', moveCursor);
            observer.disconnect();
            const hoverables = document.querySelectorAll('a, button, input, textarea, [data-hoverable]');
            hoverables.forEach((el) => {
                el.removeEventListener('mouseenter', handleMouseEnter);
                el.removeEventListener('mouseleave', handleMouseLeave);
            });
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
                    backgroundColor: isHovering ? '#00ffff' : '#ffffff'
                }}
                className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-white"
            />

            {/* Outer Ring */}
            <motion.div
                animate={{
                    scale: isHovering ? 1.5 : 1,
                    borderWidth: isHovering ? '2px' : '1px',
                    borderColor: isHovering ? '#00ffff' : '#ffffff',
                    opacity: isHovering ? 1 : 0.5
                }}
                className="absolute inset-0 rounded-full border border-white"
            />
        </motion.div>
    );
}
