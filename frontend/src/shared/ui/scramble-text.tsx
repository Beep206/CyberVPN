'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useInView } from 'motion/react';

interface ScrambleTextProps {
    text: string;
    className?: string;
    revealDelay?: number;
    scrambleSpeed?: number;
    triggerOnHover?: boolean;
    loop?: boolean; // NEW: infinite loop animation
    loopDelay?: number; // Delay between loops
}

export function ScrambleText({
    text,
    className,
    revealDelay = 0,
    scrambleSpeed = 30,
    triggerOnHover = false,
    loop = false,
    loopDelay = 2000
}: ScrambleTextProps) {
    const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%&";
    const [display, setDisplay] = useState(text);
    const ref = useRef(null);
    const isInView = useInView(ref, { once: !loop, amount: 0.5 });
    // Internal state to track if interaction is happening
    const isAnimating = useRef(false);

    const scramble = useCallback(() => {
        if (isAnimating.current) return;
        isAnimating.current = true;

        let iterations = 0;
        const interval = setInterval(() => {
            setDisplay(
                text
                    .split("")
                    .map((letter, index) => {
                        if (index < iterations) {
                            return text[index];
                        }
                        return letters[Math.floor(Math.random() * letters.length)];
                    })
                    .join("")
            );

            if (iterations >= text.length) {
                clearInterval(interval);
                isAnimating.current = false;
            }
            iterations += 1 / 3;
        }, scrambleSpeed);

        return () => clearInterval(interval);
    }, [text, scrambleSpeed]);

    // Initial animation on view
    useEffect(() => {
        if (isInView && !loop) {
            const timeout = setTimeout(() => {
                scramble();
            }, revealDelay);
            return () => clearTimeout(timeout);
        }
    }, [isInView, text, revealDelay, scramble, loop]);

    // Loop animation
    useEffect(() => {
        if (!loop || !isInView) return;

        // Start immediately
        scramble();

        // Then loop
        const loopInterval = setInterval(() => {
            scramble();
        }, loopDelay + (text.length * scrambleSpeed / 3));

        return () => clearInterval(loopInterval);
    }, [loop, isInView, scramble, loopDelay, text.length, scrambleSpeed]);

    const handleMouseEnter = () => {
        if (triggerOnHover) {
            scramble();
        }
    };

    const handleMouseLeave = () => {
    };

    return (
        <span
            ref={ref}
            className={className}
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
        >
            {display}
        </span>
    );
}

